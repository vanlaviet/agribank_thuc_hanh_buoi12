# Ví dụ Retrieval (BM25 vs Dense vs Hybrid vs Rerank)

## Câu hỏi 1: "Quy định phê duyệt tín dụng" (Semantic + Keyword)

**1. BM25 RESULTS**
- Bắt được các từ khóa như "quy định", "phê duyệt" trong Thông tư 43/2024 và Nghị định 135/2015.
- Top 1: `169221_art_5`

**2. DENSE RESULTS**
- Bắt được ngữ nghĩa cấp phép, tổ chức tín dụng.
- Top 1: `177271_art_18` (Thông tư số 01/2025/TT-NHNN)

**3. HYBRID RESULTS**
- Kết hợp cả hai, đẩy các kết quả xuất hiện ở cả hai luồng lên cao nhất bằng RRF.
- Top 1: `185630_art_17` (Từ hạng 4 BM25 và hạng 5 Dense -> Hạng 1 Hybrid).

**4. AFTER RERANK (Cross-Encoder)**
- Mô hình Cross-Encoder đánh giá lại chi tiết mức độ phù hợp giữa câu hỏi và đoạn văn.
- Kết quả được sắp xếp lại dựa trên ngữ nghĩa sâu (Deep Semantic).
