from neo4j import GraphDatabase
uri = 'neo4j://127.0.0.1:7687'
driver = GraphDatabase.driver(uri, auth=('neo4j', 'abcd1234'))
with driver.session(database='system') as session:
    try:
        session.run("CREATE DATABASE `kb-hops` IF NOT EXISTS")
        print("Database created successfully")
    except Exception as e:
        print("Failed:", e)
