import pandas as pd
import os
import sys
import json
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

def load_secure_kg():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    
    uri = os.environ.get("NEO4J_URI", "neo4j://127.0.0.1:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "abcd1234")
    database = os.environ.get("NEO4J_DATABASE", "kb-hops")

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
    except (ServiceUnavailable, AuthError) as e:
        print("Neo4j is not available or auth failed.")
        return

    print("Connected to Neo4j successfully.")
    
    chunks_secure_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed', 'chunks_secure.csv')
    df_chunks = pd.read_csv(chunks_secure_path)
    
    # Pre-parse roles from string to list
    def parse_roles(roles_str):
        try:
            return json.loads(roles_str)
        except:
            return ["Admin", "Staff", "Guest"]
            
    df_chunks['roles_list'] = df_chunks['allowed_roles'].apply(parse_roles)
    
    print("Loading security tags into DieuKhoan nodes...")
    def update_dieukhoan(tx, batch):
        query = """
        UNWIND $batch AS row
        MERGE (d:DieuKhoan {id: row.chunk_id})
        SET d.allowed_roles = row.roles,
            d.lab_session_buoi15 = 'buoi_15'
        """
        tx.run(query, batch=batch)

    batch = []
    for _, row in df_chunks.iterrows():
        batch.append({
            'chunk_id': str(row['chunk_id']),
            'roles': row['roles_list']
        })
        if len(batch) >= 1000:
            with driver.session(database=database) as session:
                session.execute_write(update_dieukhoan, batch)
            batch = []
    if batch:
        with driver.session(database=database) as session:
            session.execute_write(update_dieukhoan, batch)
            
    print("Loading security tags into VanBan nodes (Union of child roles)...")
    with driver.session(database=database) as session:
        # Update VanBan to have all roles that any of its DieuKhoan has
        # This makes sure if a user has access to ANY chunk, they can see the Document node in the graph
        query = """
        MATCH (v:VanBan)-[:CONTAINS]->(d:DieuKhoan)
        WITH v, collect(DISTINCT d.allowed_roles) AS nested_roles
        UNWIND nested_roles AS role_list
        UNWIND role_list AS role
        WITH v, collect(DISTINCT role) AS all_roles
        SET v.allowed_roles = all_roles,
            v.lab_session_buoi15 = 'buoi_15'
        """
        session.run(query)

    print("Generating report...")
    with driver.session(database=database) as session:
        secured_nodes = session.run("""
            MATCH (n)
            WHERE n.allowed_roles IS NOT NULL
            RETURN labels(n)[0] AS label, count(n) AS count
        """).data()
        
        sample_node = session.run("""
            MATCH (v:VanBan)-[:CONTAINS]->(d:DieuKhoan)
            WHERE v.allowed_roles IS NOT NULL
            RETURN v.id AS document_id, v.allowed_roles AS doc_roles, d.id AS chunk_id, d.allowed_roles AS chunk_roles
            LIMIT 1
        """).data()

    print("\n--- SECURE GRAPH REPORT ---")
    for n in secured_nodes:
        print(f"Secured {n['label']} nodes: {n['count']}")
        
    print("\nSample Node Distribution:")
    if sample_node:
        print(sample_node[0])
    
    print("Graph security tags loaded successfully.")

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    load_secure_kg()
