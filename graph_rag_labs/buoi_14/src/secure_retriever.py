import os
import json
import pandas as pd
from rank_bm25 import BM25Okapi
import re
from .citation import generate_citation
import pickle
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from neo4j import GraphDatabase

def has_access(allowed_roles_str, user_roles):
    if not user_roles:
        return False
    try:
        allowed = json.loads(allowed_roles_str)
        return any(r in allowed for r in user_roles)
    except:
        return any(r in ["Admin", "Staff", "Guest"] for r in user_roles)

class SecureBM25Retriever:
    def __init__(self, corpus_path):
        self.df = pd.read_csv(corpus_path)
        self.df['text'] = self.df['text'].fillna('')
        
    def _tokenize(self, text):
        text = text.lower()
        return re.findall(r'\b[\w-]+\b', text)
        
    def retrieve(self, query, user_roles, top_k=5):
        # Lọc bảo mật TRƯỚC KHI tính BM25
        mask = self.df['allowed_roles'].apply(lambda x: has_access(x, user_roles))
        filtered_df = self.df[mask].copy()
        
        if filtered_df.empty:
            return []
            
        tokenized_corpus = [self._tokenize(doc) for doc in filtered_df['text']]
        bm25 = BM25Okapi(tokenized_corpus)
        
        tokenized_query = self._tokenize(query)
        doc_scores = bm25.get_scores(tokenized_query)
        
        filtered_df['retrieval_score'] = doc_scores
        top_results = filtered_df.nlargest(top_k, 'retrieval_score')
        
        results = []
        for rank, (idx, row) in enumerate(top_results.iterrows(), 1):
            if row['retrieval_score'] <= 0:
                continue
            results.append({
                'rank': rank,
                'chunk_id': row['chunk_id'],
                'document_id': row['document_id'],
                'text': row['text'],
                'retrieval_score': row['retrieval_score'],
                'retrieval_method': 'BM25',
                'citation': generate_citation(row),
                'allowed_roles': row['allowed_roles']
            })
        return results

class SecureDenseRetriever:
    def __init__(self, corpus_path, cache_dir='cache', model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        self.df = pd.read_csv(corpus_path)
        self.df['text'] = self.df['text'].fillna('')
        self.model = SentenceTransformer(model_name)
        
        # We reuse the same cache if possible, assuming chunks haven't changed text, only added a column
        cache_path = os.path.join(cache_dir, f'dense_embeddings_{model_name.replace("/", "_")}.pkl')
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                self.embeddings = pickle.load(f)
        else:
            self.embeddings = self.model.encode(self.df['text'].tolist())

    def retrieve(self, query, user_roles, top_k=5):
        query_embedding = self.model.encode([query])
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        self.df['retrieval_score'] = similarities
        
        # Lọc bảo mật SAU KHI (hoặc đồng thời) tính Dense
        mask = self.df['allowed_roles'].apply(lambda x: has_access(x, user_roles))
        filtered_df = self.df[mask].copy()
        
        if filtered_df.empty:
            return []
            
        top_results = filtered_df.nlargest(top_k, 'retrieval_score')
        
        results = []
        for rank, (idx, row) in enumerate(top_results.iterrows(), 1):
            results.append({
                'rank': rank,
                'chunk_id': row['chunk_id'],
                'document_id': row['document_id'],
                'text': row['text'],
                'retrieval_score': row['retrieval_score'],
                'retrieval_method': 'Dense',
                'citation': generate_citation(row),
                'allowed_roles': row['allowed_roles']
            })
        return results

class SecureHybridRetriever:
    def __init__(self, corpus_path, rrf_k=60):
        self.bm25 = SecureBM25Retriever(corpus_path)
        self.dense = SecureDenseRetriever(corpus_path)
        self.rrf_k = rrf_k
        
    def retrieve(self, query, user_roles, candidate_k=20, top_k=5):
        bm25_results = self.bm25.retrieve(query, user_roles, top_k=candidate_k)
        dense_results = self.dense.retrieve(query, user_roles, top_k=candidate_k)
        
        merged = {}
        for res in bm25_results:
            chunk_id = res['chunk_id']
            merged[chunk_id] = res.copy()
            merged[chunk_id]['bm25_rank'] = res['rank']
            merged[chunk_id]['dense_rank'] = None
            
        for res in dense_results:
            chunk_id = res['chunk_id']
            if chunk_id not in merged:
                merged[chunk_id] = res.copy()
                merged[chunk_id]['bm25_rank'] = None
                merged[chunk_id]['dense_rank'] = res['rank']
            else:
                merged[chunk_id]['dense_rank'] = res['rank']
                
        for chunk_id, data in merged.items():
            score = 0.0
            if data['bm25_rank'] is not None:
                score += 1.0 / (self.rrf_k + data['bm25_rank'])
            if data['dense_rank'] is not None:
                score += 1.0 / (self.rrf_k + data['dense_rank'])
            data['rrf_score'] = score
            
        sorted_results = sorted(merged.values(), key=lambda x: x['rrf_score'], reverse=True)
        final_results = []
        for rank, data in enumerate(sorted_results[:top_k], 1):
            data['final_rank'] = rank
            final_results.append(data)
            
        return final_results

# Neo4j query helper for secure graph search
def get_secure_graph_hints(doc_ids, chunk_ids, user_roles):
    from dotenv import load_dotenv
    # Allow looking in one dir up or current dir
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    
    uri = os.environ.get("NEO4J_URI", "neo4j://127.0.0.1:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "abcd1234")
    database = os.environ.get("NEO4J_DATABASE", "kb-hops")

    hints = []
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
    except Exception:
        return ["*Neo4j chưa sẵn sàng hoặc không thể kết nối.*"]

    with driver.session(database=database) as session:
        if doc_ids:
            doc_query = """
            MATCH (v1:VanBan)-[r]->(v2:VanBan)
            WHERE v1.id IN $doc_ids 
              AND v1.lab_session_buoi15 = 'buoi_15' 
              AND v2.lab_session_buoi15 = 'buoi_15'
              AND any(role IN v1.allowed_roles WHERE role IN $user_roles)
              AND any(role IN v2.allowed_roles WHERE role IN $user_roles)
            RETURN v1.id AS source, type(r) AS rel, v2.id AS target
            LIMIT 10
            """
            doc_rels = session.run(doc_query, doc_ids=list(doc_ids), user_roles=user_roles).data()
            if doc_rels:
                hints.append("**Document Relationships (Neo4j - SECURED):**")
                for row in doc_rels:
                    hints.append(f"- `[{row['source']}] --{row['rel']}--> [{row['target']}]`")
            
        if chunk_ids:
            chunk_query = """
            MATCH (d1:DieuKhoan)-[r:NEXT]->(d2:DieuKhoan)
            WHERE d1.id IN $chunk_ids 
              AND d1.lab_session_buoi15 = 'buoi_15' 
              AND d2.lab_session_buoi15 = 'buoi_15'
              AND any(role IN d1.allowed_roles WHERE role IN $user_roles)
              AND any(role IN d2.allowed_roles WHERE role IN $user_roles)
            RETURN d1.id AS source, type(r) AS rel, d2.id AS target
            LIMIT 10
            """
            chunk_rels = session.run(chunk_query, chunk_ids=list(chunk_ids), user_roles=user_roles).data()
            if chunk_rels:
                hints.append("**Chunk Context (Neo4j NEXT - SECURED):**")
                for row in chunk_rels:
                    hints.append(f"- `[{row['source']}] --{row['rel']}--> [{row['target']}]`")
                    
    if not hints:
        hints.append("Không tìm thấy kết nối nào hợp lệ theo quyền của bạn.")
        
    return hints
