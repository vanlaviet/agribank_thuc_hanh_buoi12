import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

def step7():
    print("--- BƯỚC 7: Kiểm tra kết nối Neo4j ---")
    load_dotenv()
    
    uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")
    
    print(f"URI: {uri}")
    print(f"Username: {user}")
    print(f"Database: {database}")
    print(f"Password: {'*' * len(password) if password else 'None'}")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        
        with driver.session(database=database) as session:
            result = session.run("RETURN 1 AS number")
            record = result.single()
            if record and record["number"] == 1:
                print(f"[PASS] Chạy query thử nghiệm thành công trên database '{database}'.")
                
        driver.close()
        
        print("\nNeo4j connection: PASS")
        
    except Exception as e:
        print(f"\n[FAIL] Lỗi kết nối Neo4j: {e}")
        print("Neo4j connection: FAIL")

if __name__ == "__main__":
    step7()
