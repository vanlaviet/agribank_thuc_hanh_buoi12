import pandas as pd
from rank_bm25 import BM25Okapi
import re
from .citation import generate_citation

class BM25Retriever:
    def __init__(self, corpus_path):
        self.corpus_path = corpus_path
        self.df = pd.read_csv(corpus_path)
        # Handle NA text
        self.df['text'] = self.df['text'].fillna('')
        
        # Tokenize
        # Basic tokenization: split by non-alphanumeric, but keep some special characters like '-', '_' for article numbers (e.g. DK-014)
        # Using a regex that captures words and terms with hyphens
        self.tokenized_corpus = [self._tokenize(doc) for doc in self.df['text']]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def _tokenize(self, text):
        text = text.lower()
        # Keep words and words with hyphens (e.g., QĐ-125, DK-014)
        tokens = re.findall(r'\b[\w-]+\b', text)
        return tokens

    def retrieve(self, query, top_k=5):
        tokenized_query = self._tokenize(query)
        doc_scores = self.bm25.get_scores(tokenized_query)
        
        # Add scores to dataframe to sort
        self.df['retrieval_score'] = doc_scores
        
        # Get top k
        top_results = self.df.nlargest(top_k, 'retrieval_score')
        
        results = []
        for rank, (idx, row) in enumerate(top_results.iterrows(), 1):
            if row['retrieval_score'] <= 0:
                # BM25 score 0 means no keyword match
                continue
            
            result = {
                'rank': rank,
                'chunk_id': row['chunk_id'],
                'document_id': row['document_id'],
                'text': row['text'],
                'retrieval_score': row['retrieval_score'],
                'retrieval_method': 'BM25',
                'citation': generate_citation(row)
            }
            results.append(result)
            
        return results
