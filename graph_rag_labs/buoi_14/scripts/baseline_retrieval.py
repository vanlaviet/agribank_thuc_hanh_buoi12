import argparse
import sys
import os

# Add parent dir to path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bm25_retriever import BM25Retriever
from src.dense_retriever import DenseRetriever

def main():
    parser = argparse.ArgumentParser(description="Baseline Retrieval")
    parser.add_argument('--query', type=str, required=True, help='Query text')
    parser.add_argument('--top-k', type=int, default=5, help='Number of top results to retrieve')
    args = parser.parse_args()

    corpus_path = 'data/processed/chunks_normalized.csv'
    
    print("Initializing BM25 Retriever...")
    bm25 = BM25Retriever(corpus_path)
    
    print("Initializing Dense Retriever...")
    dense = DenseRetriever(corpus_path)
    
    # Run BM25
    print("\n" + "="*50)
    print("BM25 RESULTS")
    print("="*50)
    bm25_results = bm25.retrieve(args.query, top_k=args.top_k)
    for res in bm25_results:
        print(f"Rank {res['rank']} | Score {res['retrieval_score']:.4f} | {res['citation']}")
        print(f"Text: {res['text'][:200]}...\n")
        
    # Run Dense
    print("="*50)
    print("DENSE RESULTS")
    print("="*50)
    dense_results = dense.retrieve(args.query, top_k=args.top_k)
    for res in dense_results:
        print(f"Rank {res['rank']} | Score {res['retrieval_score']:.4f} | {res['citation']}")
        print(f"Text: {res['text'][:200]}...\n")

if __name__ == '__main__':
    # Fix encoding for windows
    sys.stdout.reconfigure(encoding='utf-8')
    main()
