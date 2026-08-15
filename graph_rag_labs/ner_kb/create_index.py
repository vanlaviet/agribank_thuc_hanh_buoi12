from neo4j import GraphDatabase

driver = GraphDatabase.driver("neo4j://127.0.0.1:7687", auth=("neo4j", "abcd1234"))

def create_vector_index(driver):
    cypher_query = """
    CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
    FOR (c:Chunk)
    ON (c.embedding)
    OPTIONS {indexConfig: {
      `vector.dimensions`: 384,
      `vector.similarity_function`: 'cosine'
    }}
    """
    with driver.session(database="kb-hops") as session:
        session.run(cypher_query)
        print("Vector index created successfully!")

if __name__ == "__main__":
    create_vector_index(driver)
    driver.close()
