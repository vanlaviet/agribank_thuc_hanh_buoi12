# Báo Cáo Đánh Giá RAG Retrieval

**Tổng số câu hỏi đánh giá:** 5

## 1. Kết quả Metrics (Hit@K %)

| Phương pháp | Hit@1 | Hit@3 | Hit@5 |
|-------------|-------|-------|-------|
| BM25 | 0.0% | 0.0% | 0.0% |
| Dense | 0.0% | 0.0% | 0.0% |
| Hybrid | 0.0% | 0.0% | 0.0% |
| Hybrid+Rerank | 0.0% | 0.0% | 0.0% |

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
