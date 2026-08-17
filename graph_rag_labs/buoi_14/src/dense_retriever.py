import os
import pickle
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from .citation import generate_citation

class DenseRetriever:
    def __init__(self, corpus_path, cache_dir='cache', model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        self.corpus_path = corpus_path
        self.df = pd.read_csv(corpus_path)
        self.df['text'] = self.df['text'].fillna('')
        
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        self.model_name = model_name
        self.model = SentenceTransformer(self.model_name)
        
        self.embeddings = self._load_or_compute_embeddings()

    def _load_or_compute_embeddings(self):
        # We use a hash of the corpus path or just a simple filename to cache
        cache_path = os.path.join(self.cache_dir, f'dense_embeddings_{self.model_name.replace("/", "_")}.pkl')
        
        if os.path.exists(cache_path):
            print(f"Loading cached embeddings from {cache_path}")
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        else:
            print(f"Computing embeddings for corpus using {self.model_name}...")
            # Compute embeddings for all text
            texts = self.df['text'].tolist()
            embeddings = self.model.encode(texts, show_progress_bar=True)
            with open(cache_path, 'wb') as f:
                pickle.dump(embeddings, f)
            print(f"Saved embeddings to {cache_path}")
            return embeddings

    def retrieve(self, query, top_k=5):
        query_embedding = self.model.encode([query])
        
        # Calculate cosine similarity
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        # Add scores to dataframe
        self.df['retrieval_score'] = similarities
        
        # Get top k
        top_results = self.df.nlargest(top_k, 'retrieval_score')
        
        results = []
        for rank, (idx, row) in enumerate(top_results.iterrows(), 1):
            result = {
                'rank': rank,
                'chunk_id': row['chunk_id'],
                'document_id': row['document_id'],
                'text': row['text'],
                'retrieval_score': row['retrieval_score'],
                'retrieval_method': 'Dense',
                'citation': generate_citation(row)
            }
            results.append(result)
            
        return results
