from neo4j import GraphDatabase
driver = GraphDatabase.driver("neo4j://127.0.0.1:7687", auth=("neo4j", "abcd1234"))
with driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n")
    session.run("DROP CONSTRAINT FOR (d:Document) REQUIRE d.id IS UNIQUE", raise_on_empty=False)
    session.run("DROP CONSTRAINT FOR (c:Chunk) REQUIRE c.id IS UNIQUE", raise_on_empty=False)
driver.close()
print("Cleaned Neo4j!")
