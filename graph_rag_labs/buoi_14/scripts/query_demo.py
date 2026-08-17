import argparse
import sys
import os
from neo4j import GraphDatabase

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bm25_retriever import BM25Retriever
from src.dense_retriever import DenseRetriever
from src.hybrid_retriever import HybridRetriever
from src.reranker import Reranker

def unified_retrieve(query, method, top_k, corpus_path):
    if method == 'bm25':
        retriever = BM25Retriever(corpus_path)
        results = retriever.retrieve(query, top_k=top_k)
        for r in results:
            r['retrieval_method'] = 'bm25'
        return results
    elif method == 'dense':
        retriever = DenseRetriever(corpus_path)
        results = retriever.retrieve(query, top_k=top_k)
        for r in results:
            r['retrieval_method'] = 'dense'
        return results
    elif method == 'hybrid':
        retriever = HybridRetriever(corpus_path)
        results = retriever.retrieve(query, candidate_k=20, top_k=top_k)
        for r in results:
            r['retrieval_method'] = 'hybrid'
            r['score'] = r['rrf_score']
        return results
    elif method == 'hybrid_rerank':
        hybrid = HybridRetriever(corpus_path)
        reranker = Reranker()
        hybrid_cands = hybrid.retrieve(query, candidate_k=20, top_k=20)
        results = reranker.rerank(query, hybrid_cands, top_k=top_k)
        for r in results:
            r['retrieval_method'] = 'hybrid_rerank'
            r['score'] = r['rerank_score']
        return results
    else:
        raise ValueError(f"Unknown method {method}")

def get_graph_hints(chunk_ids, doc_ids):
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    uri = os.environ.get("NEO4J_URI", "neo4j://127.0.0.1:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "abcd1234")
    database = os.environ.get("NEO4J_DATABASE", "kb-hops")

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
    except Exception:
        print("Neo4j not available, skipping graph hints.")
        return

    print("\n" + "="*50)
    print("GRAPH HINTS")
    print("="*50)
    
    with driver.session(database=database) as session:
        # 1. Document relations
        if doc_ids:
            doc_query = """
            MATCH (v1:VanBan)-[r]->(v2:VanBan)
            WHERE v1.id IN $doc_ids AND v1.lab_session = 'buoi_14' AND v2.lab_session = 'buoi_14'
            RETURN v1.id AS source, type(r) AS rel, v2.id AS target
            LIMIT 10
            """
            doc_rels = session.run(doc_query, doc_ids=list(doc_ids)).data()
            if doc_rels:
                print("\nDocument Relationships:")
                for row in doc_rels:
                    print(f"  [{row['source']}] --{row['rel']}--> [{row['target']}]")
            else:
                print("\nNo direct document relationships found for these documents.")
                
        # 2. Chunk next relations
        if chunk_ids:
            chunk_query = """
            MATCH (d1:DieuKhoan)-[r:NEXT]->(d2:DieuKhoan)
            WHERE d1.id IN $chunk_ids AND d1.lab_session = 'buoi_14' AND d2.lab_session = 'buoi_14'
            RETURN d1.id AS source, type(r) AS rel, d2.id AS target
            LIMIT 10
            """
            chunk_rels = session.run(chunk_query, chunk_ids=list(chunk_ids)).data()
            if chunk_rels:
                print("\nChunk Context (NEXT):")
                for row in chunk_rels:
                    print(f"  [{row['source']}] --{row['rel']}--> [{row['target']}]")
            else:
                print("\nNo immediate NEXT chunks found (or at end of document).")

def main():
    parser = argparse.ArgumentParser(description="Unified Retrieval Demo")
    parser.add_argument('--query', type=str, required=True, help='Query text')
    parser.add_argument('--method', type=str, choices=['bm25', 'dense', 'hybrid', 'hybrid_rerank'], required=True)
    parser.add_argument('--top-k', type=int, default=5, help='Number of results')
    args = parser.parse_args()

    corpus_path = 'data/processed/chunks_normalized.csv'
    
    print(f"Running retrieval using method: {args.method.upper()}")
    
    results = unified_retrieve(args.query, args.method, args.top_k, corpus_path)
    
    print("\n" + "="*50)
    print("RETRIEVAL RESULTS")
    print("="*50)
    
    chunk_ids = set()
    doc_ids = set()
    
    for rank, res in enumerate(results, 1):
        print(f"Rank {rank} | Chunk: {res['chunk_id']} | Method: {res['retrieval_method']} | Score: {res.get('score', 0):.4f}")
        print(f"Citation: {res['citation']}")
        text = str(res['text']).replace('\n', ' ')
        print(f"Text: {text[:200]}...")
        print("-" * 50)
        chunk_ids.add(res['chunk_id'])
        doc_ids.add(res['document_id'])
        
    get_graph_hints(chunk_ids, doc_ids)

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
