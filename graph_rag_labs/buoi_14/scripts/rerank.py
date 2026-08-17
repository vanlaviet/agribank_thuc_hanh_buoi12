import argparse
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.hybrid_retriever import HybridRetriever
from src.reranker import Reranker

def main():
    parser = argparse.ArgumentParser(description="Hybrid + Reranking Search")
    parser.add_argument('--query', type=str, required=True, help='Query text')
    parser.add_argument('--top-k', type=int, default=5, help='Number of final results to retrieve')
    parser.add_argument('--candidate-k', type=int, default=20, help='Number of candidates per retriever to fetch before reranking')
    args = parser.parse_args()

    corpus_path = 'data/processed/chunks_normalized.csv'
    
    print("Initializing Hybrid Retriever...")
    hybrid = HybridRetriever(corpus_path)
    print("Initializing Reranker...")
    reranker = Reranker()
    
    print("\n" + "="*50)
    print("BEFORE RERANK (Top Hybrid Candidates)")
    print("="*50)
    print(f"{'Rank':<5} | {'Chunk':<15} | {'RRF':<8} | {'Citation'}")
    print("-" * 100)
    
    hybrid_results = hybrid.retrieve(args.query, candidate_k=args.candidate_k, top_k=args.candidate_k)
    
    for res in hybrid_results[:args.top_k]:
        print(f"{res['final_rank']:<5} | {res['chunk_id'][:15]:<15} | {res['rrf_score']:.4f} | {res['citation']}")

    print("\n" + "="*50)
    print("AFTER RERANK")
    print("="*50)
    print(f"{'Rank':<5} | {'Prev Rank':<10} | {'Chunk':<15} | {'Rerank Score':<12} | {'Citation'}")
    print("-" * 100)
    
    final_results = reranker.rerank(args.query, hybrid_results, top_k=args.top_k)
    for res in final_results:
        print(f"{res['final_rank']:<5} | {res['hybrid_rank']:<10} | {res['chunk_id'][:15]:<15} | {res['rerank_score']:.4f} | {res['citation']}")

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
