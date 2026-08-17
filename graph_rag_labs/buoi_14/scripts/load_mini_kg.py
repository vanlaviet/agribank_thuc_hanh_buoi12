import pandas as pd
import os
import sys
import re
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

def normalize_rel_type(rel_type):
    if pd.isna(rel_type):
        return "RELATED_TO"
    # Convert to uppercase, replace spaces/hyphens with underscore
    normalized = re.sub(r'[^A-Z0-9]', '_', str(rel_type).upper())
    return normalized

def load_mini_kg():
    # Load Environment variables
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    
    # Actually neo4j connection params were mentioned by user earlier:
    # url: neo4j://127.0.0.1:7687, db: kb-hops, pass: abcd1234
    uri = os.environ.get("NEO4J_URI", "neo4j://127.0.0.1:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "abcd1234")
    database = os.environ.get("NEO4J_DATABASE", "kb-hops")

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
    except (ServiceUnavailable, AuthError) as e:
        print("Neo4j is not available or auth failed. Please start Neo4j and check credentials.")
        print(f"Error: {e}")
        return

    print("Connected to Neo4j successfully.")

    # Apply schema
    with driver.session(database=database) as session:
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (v:VanBan) REQUIRE v.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:DieuKhoan) REQUIRE d.id IS UNIQUE")
        session.run("CREATE INDEX IF NOT EXISTS FOR (v:VanBan) ON (v.lab_session)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (d:DieuKhoan) ON (d.lab_session)")
    
    # Read Data
    metadata_path = os.path.join(os.path.dirname(__file__), '..', '..', 'kb+hops', 'metadata.csv')
    rels_path = os.path.join(os.path.dirname(__file__), '..', '..', 'kb+hops', 'relationships.csv')
    chunks_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed', 'chunks_normalized.csv')

    df_meta = pd.read_csv(metadata_path)
    df_chunks = pd.read_csv(chunks_path)
    
    df_rels = pd.DataFrame()
    if os.path.exists(rels_path):
        df_rels = pd.read_csv(rels_path)

    # 1. Load VanBan nodes
    print("Loading VanBan nodes...")
    def create_vanban(tx, batch):
        query = """
        UNWIND $batch AS row
        MERGE (v:VanBan {id: row.id})
        SET v.title = row.title,
            v.document_type = row.loai_van_ban,
            v.status = row.tinh_trang_hieu_luc,
            v.lab_session = 'buoi_14'
        """
        tx.run(query, batch=batch)

    batch = []
    for _, row in df_meta.iterrows():
        batch.append({
            'id': str(row['id']),
            'title': str(row.get('title', '')),
            'loai_van_ban': str(row.get('loai_van_ban', '')),
            'tinh_trang_hieu_luc': str(row.get('tinh_trang_hieu_luc', ''))
        })
        if len(batch) >= 1000:
            with driver.session(database=database) as session:
                session.execute_write(create_vanban, batch)
            batch = []
    if batch:
        with driver.session(database=database) as session:
            session.execute_write(create_vanban, batch)

    # 2. Load DieuKhoan nodes & CONTAINS relations
    print("Loading DieuKhoan nodes and CONTAINS relations...")
    def create_dieukhoan(tx, batch):
        query = """
        UNWIND $batch AS row
        MERGE (d:DieuKhoan {id: row.chunk_id})
        SET d.text = row.text,
            d.document_id = row.document_id,
            d.lab_session = 'buoi_14'
        WITH d, row
        MATCH (v:VanBan {id: row.document_id})
        MERGE (v)-[r:CONTAINS]->(d)
        SET r.lab_session = 'buoi_14'
        """
        tx.run(query, batch=batch)

    batch = []
    for _, row in df_chunks.iterrows():
        batch.append({
            'chunk_id': str(row['chunk_id']),
            'document_id': str(row['document_id']),
            'text': str(row['text'])
        })
        if len(batch) >= 1000:
            with driver.session(database=database) as session:
                session.execute_write(create_dieukhoan, batch)
            batch = []
    if batch:
        with driver.session(database=database) as session:
            session.execute_write(create_dieukhoan, batch)

    # 3. Load NEXT relations between chunks
    print("Loading NEXT relations...")
    def create_next_rels(tx, batch):
        query = """
        UNWIND $batch AS row
        MATCH (d1:DieuKhoan {id: row.from_id})
        MATCH (d2:DieuKhoan {id: row.to_id})
        MERGE (d1)-[r:NEXT]->(d2)
        SET r.lab_session = 'buoi_14'
        """
        tx.run(query, batch=batch)
        
    next_batch = []
    for doc_id, group in df_chunks.groupby('document_id'):
        chunk_ids = group['chunk_id'].tolist()
        for i in range(len(chunk_ids) - 1):
            next_batch.append({
                'from_id': str(chunk_ids[i]),
                'to_id': str(chunk_ids[i+1])
            })
            if len(next_batch) >= 1000:
                with driver.session(database=database) as session:
                    session.execute_write(create_next_rels, next_batch)
                next_batch = []
    if next_batch:
        with driver.session(database=database) as session:
            session.execute_write(create_next_rels, next_batch)

    # 4. Load metadata relationships
    print("Loading document relationships...")
    if not df_rels.empty:
        def create_doc_rels(tx, batch, rel_type):
            query = f"""
            UNWIND $batch AS row
            MATCH (v1:VanBan {{id: row.doc_id}})
            MATCH (v2:VanBan {{id: row.other_doc_id}})
            MERGE (v1)-[r:`{rel_type}`]->(v2)
            SET r.lab_session = 'buoi_14',
                r.description = row.relationship
            """
            tx.run(query, batch=batch)
            
        rel_groups = {}
        for _, row in df_rels.iterrows():
            r_type = normalize_rel_type(row.get('relationship_type', 'RELATED'))
            if r_type not in rel_groups:
                rel_groups[r_type] = []
            rel_groups[r_type].append({
                'doc_id': str(row['doc_id']),
                'other_doc_id': str(row['other_doc_id']),
                'relationship': str(row.get('relationship', ''))
            })
            
        for r_type, batch in rel_groups.items():
            for i in range(0, len(batch), 1000):
                sub_batch = batch[i:i+1000]
                with driver.session(database=database) as session:
                    session.execute_write(create_doc_rels, sub_batch, r_type)

    # 5. Stats reporting
    print("Generating report...")
    with driver.session(database=database) as session:
        node_counts = session.run("""
            MATCH (n {lab_session: 'buoi_14'})
            RETURN labels(n)[0] AS label, count(n) AS count
        """).data()
        
        rel_counts = session.run("""
            MATCH ()-[r {lab_session: 'buoi_14'}]->()
            RETURN type(r) AS type, count(r) AS count
        """).data()
        
        orphan_count = session.run("""
            MATCH (n {lab_session: 'buoi_14'})
            WHERE NOT (n)--()
            RETURN count(n) AS count
        """).single()["count"]

    report = f"""# Báo Cáo Xây Dựng Knowledge Graph Mini (Buổi 14)

## Thống kê Node
"""
    for n in node_counts:
        report += f"- **{n['label']}**: {n['count']}\n"
        
    report += "\n## Thống kê Relationship\n"
    for r in rel_counts:
        report += f"- **{r['type']}**: {r['count']}\n"
        
    report += f"\n## Nodes mồ côi (Orphans)\n- Số lượng node không có liên kết: {orphan_count}\n"

    os.makedirs('outputs', exist_ok=True)
    with open('outputs/kg_build_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
        
    print("Knowledge Graph loading completed. Report generated at outputs/kg_build_report.md")

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    load_mini_kg()
