import argparse
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.hybrid_retriever import HybridRetriever

def main():
    parser = argparse.ArgumentParser(description="Hybrid Search")
    parser.add_argument('--query', type=str, required=True, help='Query text')
    parser.add_argument('--top-k', type=int, default=5, help='Number of top results to retrieve')
    parser.add_argument('--candidate-k', type=int, default=20, help='Number of candidates per retriever')
    args = parser.parse_args()

    corpus_path = 'data/processed/chunks_normalized.csv'
    
    print("Initializing Hybrid Retriever...")
    hybrid = HybridRetriever(corpus_path)
    
    print("\n" + "="*50)
    print("HYBRID RESULTS")
    print("="*50)
    print(f"{'Rank':<5} | {'Chunk':<15} | {'BM25 rank':<10} | {'Dense rank':<10} | {'RRF':<8} | {'Citation'}")
    print("-" * 100)
    
    results = hybrid.retrieve(args.query, candidate_k=args.candidate_k, top_k=args.top_k)
    for res in results:
        bm25_r = res['bm25_rank'] if res['bm25_rank'] else 'N/A'
        dense_r = res['dense_rank'] if res['dense_rank'] else 'N/A'
        print(f"{res['final_rank']:<5} | {res['chunk_id'][:15]:<15} | {str(bm25_r):<10} | {str(dense_r):<10} | {res['rrf_score']:.4f} | {res['citation']}")

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
