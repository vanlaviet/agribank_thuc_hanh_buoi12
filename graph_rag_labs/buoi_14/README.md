# Buổi 14 — Nâng cấp RAG với Hybrid Search + Reranking và xây Knowledge Graph mini

Bài thực hành nâng cấp hệ thống RAG lên Hybrid Search (kết hợp Lexical BM25 và Vector Dense) kết hợp Reranking với Cross-Encoder. Đồng thời xây dựng Knowledge Graph mini để trực quan hoá mối quan hệ giữa các văn bản và điều khoản.

## Chuẩn bị dữ liệu

Trước khi chạy ứng dụng, bạn cần chạy script để chuẩn hóa corpus:
```bash
python scripts/prepare_corpus.py
```
Lệnh này sẽ tạo ra file `data/processed/chunks_normalized.csv`.

## Cách chạy ứng dụng Streamlit

1. Cài đặt các thư viện (đảm bảo bạn đang ở môi trường ảo):
   ```bash
   pip install -r requirements.txt
   ```
   Nếu báo thiếu Streamlit, chạy thêm: `pip install streamlit`

2. Kích hoạt giao diện ứng dụng Demo:
   Tại thư mục `buoi_14/`, chạy:
   ```bash
   streamlit run app.py
   ```
   
3. **Cách dừng Streamlit**:
   Nhấn `Ctrl + C` trên terminal đang chạy lệnh `streamlit run app.py` để dừng máy chủ.

## Cách sử dụng

1. **Câu hỏi**: Nhập truy vấn của bạn.
2. **Method options** (Phương pháp tìm kiếm):
   - `BM25`: Chỉ dựa vào đối sánh từ khoá (Lexical).
   - `Dense`: Semantic Search (tìm kiếm ngữ nghĩa).
   - `Hybrid`: Kết hợp `BM25` và `Dense` bằng thuật toán Reciprocal Rank Fusion (RRF).
   - `Hybrid + Rerank`: Chạy `Hybrid`, sau đó dùng mô hình Neural Network (Cross-Encoder) để đánh giá lại mức độ phù hợp và sắp xếp (Reranking). Đây là lựa chọn tối ưu nhất.
3. **Top-k**: Số lượng kết quả hiển thị cuối cùng.
4. Nhấn **Tìm kiếm**.

## Các trường trong kết quả

- **Chunk / Document**: ID của phần văn bản và ID của văn bản gốc.
- **Score**: Điểm tính toán tuỳ vào method (điểm RRF hoặc Rerank score).
- **Citation**: Nguồn trích dẫn cấu trúc gốc để dễ truy xuất.
- **Before / After Rerank**: Bảng so sánh 20 candidate ban đầu được mang đi rerank và top-k sau khi đã được rerank để học viên dễ quan sát sự dịch chuyển thứ hạng do Reranking mang lại.
- **Graph hints**: Gợi ý kết nối đồ thị (Neo4j). Sau khi lấy ra các kết quả top_k, hệ thống lấy các node đó và chọc vào Neo4j để xem nó có liên kết trực tiếp (Quan hệ `NEXT`, Quan hệ `THAY_THE`, v.v.) với các node khác hay không.
