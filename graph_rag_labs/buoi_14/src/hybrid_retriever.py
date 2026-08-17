from .bm25_retriever import BM25Retriever
from .dense_retriever import DenseRetriever

class HybridRetriever:
    def __init__(self, corpus_path, rrf_k=60):
        self.bm25 = BM25Retriever(corpus_path)
        self.dense = DenseRetriever(corpus_path)
        self.rrf_k = rrf_k

    def retrieve(self, query, candidate_k=20, top_k=5):
        bm25_results = self.bm25.retrieve(query, top_k=candidate_k)
        dense_results = self.dense.retrieve(query, top_k=candidate_k)

        merged = {}
        
        for res in bm25_results:
            chunk_id = res['chunk_id']
            merged[chunk_id] = {
                'chunk_id': chunk_id,
                'document_id': res['document_id'],
                'text': res['text'],
                'citation': res['citation'],
                'bm25_rank': res['rank'],
                'dense_rank': None
            }
            
        for res in dense_results:
            chunk_id = res['chunk_id']
            if chunk_id not in merged:
                merged[chunk_id] = {
                    'chunk_id': chunk_id,
                    'document_id': res['document_id'],
                    'text': res['text'],
                    'citation': res['citation'],
                    'bm25_rank': None,
                    'dense_rank': res['rank']
                }
            else:
                merged[chunk_id]['dense_rank'] = res['rank']

        # Calculate RRF
        for chunk_id, data in merged.items():
            score = 0.0
            if data['bm25_rank'] is not None:
                score += 1.0 / (self.rrf_k + data['bm25_rank'])
            if data['dense_rank'] is not None:
                score += 1.0 / (self.rrf_k + data['dense_rank'])
            data['rrf_score'] = score

        # Sort by RRF
        sorted_results = sorted(merged.values(), key=lambda x: x['rrf_score'], reverse=True)

        # Return top_k
        final_results = []
        for rank, data in enumerate(sorted_results[:top_k], 1):
            data['final_rank'] = rank
            final_results.append(data)
            
        return final_results
