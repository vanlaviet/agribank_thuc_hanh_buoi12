try:
    from sentence_transformers.cross_encoder import CrossEncoder
    HAS_CROSS_ENCODER = True
except ImportError:
    HAS_CROSS_ENCODER = False
import sys

class Reranker:
    def __init__(self, model_name='cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'):
        self.model_name = model_name
        self.is_fallback = not HAS_CROSS_ENCODER
        if not self.is_fallback:
            print(f"Loading Cross-Encoder model: {self.model_name}", file=sys.stderr)
            try:
                self.model = CrossEncoder(self.model_name, max_length=512)
                print("Model loaded successfully.", file=sys.stderr)
            except Exception as e:
                print(f"Failed to load CrossEncoder ({e}). Using fallback.", file=sys.stderr)
                self.is_fallback = True
        else:
            print("sentence-transformers CrossEncoder not available. Using fallback.", file=sys.stderr)

    def rerank(self, query, candidates, top_k=5):
        if not candidates:
            return []
            
        if self.is_fallback:
            # FALLBACK: Just use the original hybrid ranking
            print("WARNING: Using FALLBACK reranker (no actual neural reranking applied).", file=sys.stderr)
            for item in candidates:
                item['rerank_score'] = item.get('rrf_score', 0)
            
            # Sort by fallback score (which is just rrf_score)
            sorted_candidates = sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
        else:
            # Prepare pairs: (query, text)
            pairs = [[query, doc['text']] for doc in candidates]
            scores = self.model.predict(pairs)
            
            # Attach scores
            for i, doc in enumerate(candidates):
                doc['rerank_score'] = float(scores[i])
                
            sorted_candidates = sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
            
        final_results = []
        for rank, doc in enumerate(sorted_candidates[:top_k], 1):
            doc['hybrid_rank'] = doc.get('final_rank', doc.get('rank', 0))
            doc['hybrid_score'] = doc.get('rrf_score', 0)
            doc['final_rank'] = rank
            final_results.append(doc)
            
        return final_results
