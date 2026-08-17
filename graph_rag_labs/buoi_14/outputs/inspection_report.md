# Báo cáo Kiểm tra Dự án - Buổi 14

## 1. Cấu trúc và File hiện có
Cấu trúc dự án trong `buoi_14/` gồm các thư mục và file chính:
- **Thư mục:** `.venv/`, `cache/`, `cypher/`, `data/`, `outputs/`, `scripts/`, `src/`
- **File gốc:** `app.py`, `buoi14.md`, `README.md`, `requirements.txt`, các script khởi chạy PowerShell.
- **Code hiện có:**
  - Trong `scripts/`: `prepare_corpus.py`, `baseline_retrieval.py`, `hybrid_search.py`, `compare_retrieval.py`, `rerank.py`, `inspect_project.py`, `load_mini_kg.py`, `query_demo.py`
  - Trong `src/`: `bm25_retriever.py`, `dense_retriever.py`, `hybrid_retriever.py`, `reranker.py`, `citation.py`
- **Rủi ro mã độc/Phá dữ liệu:** Đã rà soát qua code bằng grep để tìm các lệnh nguy hiểm (`os.remove`, `shutil.rmtree`, `open("w")`, lệnh Cypher xóa như `DELETE`, `DROP`, `DETACH DELETE`). Các file code không chứa lệnh phá hoại dữ liệu (ngoại trừ một số lệnh `drop_duplicates` trong tiền xử lý pandas và xóa node cũ lúc nạp Knowledge Graph trong file markdown/load scripts đã được biết trước và là cần thiết, không đụng đến dữ liệu nguồn ở `../kb+hops`).

## 2. Phân tích Dữ liệu Nguồn (`../kb+hops/`)
Đã tiến hành đọc 3 file nguồn mà không làm thay đổi hay ghi đè nội dung.

### 2.1 `metadata.csv`
- **Số dòng:** 15
- **Tên cột:** `id`, `title`, `so_ky_hieu`, `ngay_ban_hanh`, `loai_van_ban`, `ngay_co_hieu_luc`, `ngay_het_hieu_luc`, `nguon_thu_thap`, `ngay_dang_cong_bao`, `nganh`, `linh_vuc`, `co_quan_ban_hanh`, `chuc_danh`, `nguoi_ky`, `pham_vi`, `thong_tin_ap_dung`, `tinh_trang_hieu_luc`
- **Encoding:** `utf-8` (mặc định xử lý)
- **Duplicate:** 0
- **Nulls:** `ngay_co_hieu_luc` (1), `ngay_het_hieu_luc` (14), `nguon_thu_thap` (5), `ngay_dang_cong_bao` (11), `nganh` (3), `linh_vuc` (2), `thong_tin_ap_dung` (15)
- **Khóa có thể sử dụng:** `id`
- **Metadata phù hợp citation:** `title`, `so_ky_hieu`, `loai_van_ban`, `co_quan_ban_hanh`, `ngay_ban_hanh`.

### 2.2 `content.csv`
- **Số dòng:** 15
- **Tên cột:** `id`, `content_html`
- **Encoding:** `utf-8`
- **Duplicate:** 0
- **Nulls:** Không có
- **Khóa có thể sử dụng:** `id`
- **Trường text phù hợp retrieval:** `content_html`

### 2.3 `relationships.csv`
- **Số dòng:** 8
- **Tên cột:** `doc_id`, `other_doc_id`, `relationship`, `relationship_type`
- **Encoding:** `utf-8`
- **Duplicate:** 0
- **Nulls:** Không có
- **Khóa có thể sử dụng:** `doc_id`, `other_doc_id`