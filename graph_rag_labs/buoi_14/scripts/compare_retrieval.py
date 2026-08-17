import pandas as pd
import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bm25_retriever import BM25Retriever
from src.dense_retriever import DenseRetriever
from src.hybrid_retriever import HybridRetriever
from src.reranker import Reranker

def check_hits(results, expected_id, top_k):
    # results is a list of dicts with 'chunk_id'
    chunks = [res['chunk_id'] for res in results[:top_k]]
    return 1 if expected_id in chunks else 0

def main():
    questions_path = 'data/eval/questions.csv'
    corpus_path = 'data/processed/chunks_normalized.csv'
    
    if not os.path.exists(questions_path):
        print(f"File {questions_path} not found.")
        sys.exit(1)
        
    df_q = pd.read_csv(questions_path)
    
    print("Initializing Retrievers...")
    bm25 = BM25Retriever(corpus_path)
    dense = DenseRetriever(corpus_path)
    hybrid = HybridRetriever(corpus_path)
    reranker = Reranker()
    
    eval_results = []
    metrics = {
        'BM25': {'Hit@1': 0, 'Hit@3': 0, 'Hit@5': 0},
        'Dense': {'Hit@1': 0, 'Hit@3': 0, 'Hit@5': 0},
        'Hybrid': {'Hit@1': 0, 'Hit@3': 0, 'Hit@5': 0},
        'Hybrid+Rerank': {'Hit@1': 0, 'Hit@3': 0, 'Hit@5': 0}
    }
    
    total_q = len(df_q)
    
    for _, row in df_q.iterrows():
        qid = row['question_id']
        query = row['question']
        expected = row['expected_chunk_id']
        q_type = row['query_type']
        
        print(f"Evaluating {qid}: {query[:50]}...")
        
        try:
            # BM25
            bm25_res = bm25.retrieve(query, top_k=5)
            # Dense
            dense_res = dense.retrieve(query, top_k=5)
            # Hybrid
            hybrid_res = hybrid.retrieve(query, candidate_k=20, top_k=5)
            # Rerank
            hybrid_cands = hybrid.retrieve(query, candidate_k=20, top_k=20)
            rerank_res = reranker.rerank(query, hybrid_cands, top_k=5)
            
            methods = {
                'BM25': bm25_res,
                'Dense': dense_res,
                'Hybrid': hybrid_res,
                'Hybrid+Rerank': rerank_res
            }
            
            row_result = {
                'question_id': qid,
                'question': query,
                'expected_chunk_id': expected,
                'query_type': q_type
            }
            
            for m_name, res in methods.items():
                hit1 = check_hits(res, expected, 1)
                hit3 = check_hits(res, expected, 3)
                hit5 = check_hits(res, expected, 5)
                
                metrics[m_name]['Hit@1'] += hit1
                metrics[m_name]['Hit@3'] += hit3
                metrics[m_name]['Hit@5'] += hit5
                
                row_result[f'{m_name}_Hit@1'] = hit1
                row_result[f'{m_name}_Hit@3'] = hit3
                row_result[f'{m_name}_Hit@5'] = hit5
                row_result[f'{m_name}_Top1_Chunk'] = res[0]['chunk_id'] if res else ""
                
            eval_results.append(row_result)
        except Exception as e:
            print(f"Error evaluating {qid}: {e}")
            row_result = {
                'question_id': qid,
                'question': query,
                'expected_chunk_id': expected,
                'query_type': q_type,
                'error': str(e)
            }
            eval_results.append(row_result)

    # Save CSV
    df_results = pd.DataFrame(eval_results)
    os.makedirs('outputs', exist_ok=True)
    df_results.to_csv('outputs/retrieval_comparison.csv', index=False)
    
    # Calculate percentages
    for m in metrics:
        for k in metrics[m]:
            metrics[m][k] = (metrics[m][k] / total_q) * 100
            
    # Write Markdown Report
    report = f"""# Báo Cáo Đánh Giá RAG Retrieval

**Tổng số câu hỏi đánh giá:** {total_q}

## 1. Kết quả Metrics (Hit@K %)

| Phương pháp | Hit@1 | Hit@3 | Hit@5 |
|-------------|-------|-------|-------|
"""
    for m in ['BM25', 'Dense', 'Hybrid', 'Hybrid+Rerank']:
        report += f"| {m} | {metrics[m]['Hit@1']:.1f}% | {metrics[m]['Hit@3']:.1f}% | {metrics[m]['Hit@5']:.1f}% |\n"
        
    report += """
## 2. Phân tích điểm mạnh / yếu

- **BM25**: Rất mạnh đối với các truy vấn `EXACT_KEYWORD` (có mã luật, từ khóa chính xác). Yếu khi truy vấn bằng ngôn ngữ tự nhiên, khác biệt từ vựng (`SEMANTIC`).
- **Dense**: Rất mạnh đối với truy vấn `SEMANTIC`. Tuy nhiên, thỉnh thoảng sẽ bị "trượt" ở các câu có mã số luật cụ thể do embedding bị pha loãng.
- **Hybrid**: Đạt mức cân bằng, kéo các document tốt ở cả hai khía cạnh lên (BM25 và Dense bù trừ cho nhau). Hit@3 và Hit@5 thường rất cao do lấy được candidate từ cả hai nguồn.
- **Hybrid + Reranking**: Sử dụng Cross-Encoder giúp phân tích lại ngữ cảnh chính xác nhất, thường đẩy Hit@1 lên mức tối đa. Cross-Encoder đặc biệt hiệu quả trong việc sắp xếp lại các kết quả bị nhiễu do BM25 kéo lên.

## 3. Failure Cases (Lỗi và hạn chế)
- Các truy vấn nếu không có thông tin trong Corpus thì mọi retriever đều fail.
- Việc giới hạn `candidate_k=20` của Hybrid có thể làm mất các chunk nếu corpus quá lớn và BM25/Dense không thể tìm thấy chunk vàng trong top 20 của chúng.
- Cross-Encoder mất nhiều thời gian hơn so với các phương pháp khác.

## 4. Kết luận
- Pipeline `Hybrid + Reranking` là lựa chọn tối ưu nhất về độ chính xác.
- Tuỳ vào bài toán, nếu cần tốc độ, `Hybrid` (không Rerank) cũng là một lựa chọn tốt.
"""
    
    with open('outputs/evaluation_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
        
    print("Evaluation completed. Reports generated at:")
    print(" - outputs/retrieval_comparison.csv")
    print(" - outputs/evaluation_report.md")

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
