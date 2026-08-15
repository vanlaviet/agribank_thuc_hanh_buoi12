import os
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

def create_constraints(session):
    constraints = [
        "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
        "CREATE CONSTRAINT cq_id IF NOT EXISTS FOR (e:CoQuan) REQUIRE e.id IS UNIQUE",
        "CREATE CONSTRAINT nk_id IF NOT EXISTS FOR (e:NguoiKy) REQUIRE e.id IS UNIQUE",
        "CREATE CONSTRAINT dt_id IF NOT EXISTS FOR (e:DoiTuongApDung) REQUIRE e.id IS UNIQUE",
        "CREATE CONSTRAINT lv_id IF NOT EXISTS FOR (e:LinhVuc) REQUIRE e.id IS UNIQUE",
    ]
    for q in constraints:
        try:
            session.run(q).consume()
        except Exception as e:
            pass

def step8():
    print("--- BƯỚC 8: Import Knowledge Graph vào Neo4j ---")
    load_dotenv()
    
    uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")
    
    try:
        docs = pd.read_csv('cleaned_documents.csv')
        ents = pd.read_csv('entities.csv')
        rels = pd.read_csv('relationships.csv')
    except Exception as e:
        print(f"[FAIL] Lỗi đọc CSV: {e}")
        return
        
    docs['id'] = docs['id'].astype(str)
    ents['entity_id'] = ents['entity_id'].astype(str)
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session(database=database) as session:
            print("Creating constraints...")
            # 1. Constraints
            create_constraints(session)
            
            print("Importing Documents...")
            # 2. Import Nodes (MERGE)
            doc_query = """
            UNWIND $rows AS row
            MERGE (d:Document {id: row.id})
            SET d.so_ky_hieu = row.so_ky_hieu,
                d.title = row.title,
                d.ngay_ban_hanh = row.ngay_ban_hanh,
                d.loai_van_ban = row.loai_van_ban
            """
            session.run(doc_query, rows=docs.to_dict('records')).consume()
            
            print("Importing Entities...")
            for etype in ['CoQuan', 'NguoiKy', 'DoiTuongApDung', 'LinhVuc']:
                sub_ents = ents[ents['entity_type'] == etype]
                if not sub_ents.empty:
                    ent_query = f"""
                    UNWIND $rows AS row
                    MERGE (e:{etype} {{id: row.entity_id}})
                    SET e.canonical_name = row.canonical_name,
                        e.original_name = row.original_name
                    """
                    session.run(ent_query, rows=sub_ents.to_dict('records')).consume()
                    
            print("Importing Relationships...")
            # 3. Import Relationships (MERGE)
            rel_errors = 0
            doc_ids = set(docs['id'])
            ent_map = {row['entity_id']: row['entity_type'] for _, row in ents.iterrows()}
            
            groups = []
            for _, row in rels.iterrows():
                src = str(row['source'])
                tgt = str(row['target'])
                rt = row['relationship_type']
                
                src_label = 'Document'
                if tgt in doc_ids:
                    tgt_label = 'Document'
                elif tgt in ent_map:
                    tgt_label = ent_map[tgt]
                else:
                    rel_errors += 1
                    continue
                    
                groups.append({
                    'src_label': src_label,
                    'tgt_label': tgt_label,
                    'rel_type': rt,
                    'src_id': src,
                    'tgt_id': tgt,
                    'method': row.get('method', ''),
                    'evidence': str(row.get('evidence', ''))
                })
                
            df_groups = pd.DataFrame(groups)
            if not df_groups.empty:
                for (sl, tl, rt), group in df_groups.groupby(['src_label', 'tgt_label', 'rel_type']):
                    q = f"""
                    UNWIND $rows AS row
                    MATCH (s:{sl} {{id: row.src_id}})
                    MATCH (t:{tl} {{id: row.tgt_id}})
                    MERGE (s)-[r:{rt}]->(t)
                    SET r.method = row.method,
                        r.evidence = row.evidence
                    """
                    try:
                        session.run(q, rows=group.to_dict('records')).consume()
                    except Exception as e:
                        print(f"Error creating relation {rt}: {e}")
                        rel_errors += len(group)
                        
            print("Counting statistics...")
            # Thống kê
            node_counts = {}
            for lbl in ['Document', 'CoQuan', 'NguoiKy', 'DoiTuongApDung', 'LinhVuc']:
                res = session.run(f"MATCH (n:{lbl}) RETURN count(n) AS c").single()
                node_counts[lbl] = res['c'] if res else 0
                
            rel_counts = {}
            for rt in rels['relationship_type'].unique():
                res = session.run(f"MATCH ()-[r:{rt}]->() RETURN count(r) AS c").single()
                rel_counts[rt] = res['c'] if res else 0
                
        print("\nSố node theo label:")
        for k, v in node_counts.items(): print(f"- {k}: {v}")
        
        print("\nSố relationship theo type:")
        for k, v in rel_counts.items(): print(f"- {k}: {v}")
        
        print(f"\nSố lỗi import (không tìm thấy target/source): {rel_errors}")
        print("\n[PASS] BƯỚC 8 hoàn thành.")
        
    except Exception as e:
        print(f"\n[FAIL] Quá trình import gặp lỗi: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    step8()
