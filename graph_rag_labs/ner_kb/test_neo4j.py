from neo4j import GraphDatabase
import sys
print("Connecting to Neo4j...")
try:
    driver = GraphDatabase.driver("neo4j://127.0.0.1:7687", auth=("neo4j", "abcd1234"))
    driver.verify_connectivity()
    print("Success!")
    driver.close()
except Exception as e:
    print(f"Error: {e}")
