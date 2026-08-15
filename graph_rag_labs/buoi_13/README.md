# Wiki Risk Graph Project

Dự án này là một bài thực hành hướng dẫn cách sử dụng AI Coding Agent (Vibe Coding) để chuyển đổi dữ liệu rủi ro từ dạng bảng (CSV) thành một Wiki Knowledge Graph có thể xem trên Obsidian, đồng thời có thể nạp vào CSDL Neo4j.

## Các tệp tin dữ liệu ban đầu
- `data/risk_profiles_seed.csv`
- `data/controls_seed.csv`
- `data/risk_events_seed.csv`
- `data/relationships_seed.csv`

## Cài đặt môi trường
Đảm bảo bạn đã cài đặt các thư viện Python cần thiết:
```bash
pip install pandas python-dotenv neo4j
```

Nếu muốn chạy tệp nạp Neo4j, hãy tạo tệp `.env` tại thư mục `buoi_13` với nội dung cấu hình như sau:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

## Thứ tự thực thi lệnh (Workflow)

Để xây dựng hệ thống, hãy chạy lần lượt các script sau trong terminal (tại thư mục `buoi_13`):

### 1. Kiểm tra dữ liệu gốc
Đọc và phân tích thông tin về các Node/Edge từ các file CSV.
```bash
python scripts/inspect_data.py
```

### 2. Chuẩn hóa dữ liệu (Build Entities & Relations)
Chuyển đổi dữ liệu từ dạng nghiệp vụ sang schema chuẩn (entities và relations), kết quả lưu trong thư mục `outputs/`.
```bash
python scripts/build_entities.py
```

### 3. Sinh Wiki Markdown
Tạo các tệp tin Markdown dựa trên dữ liệu đã chuẩn hóa, kết quả nằm trong thư mục `wiki/`.
```bash
python scripts/build_wiki.py
```
*(Lúc này bạn có thể mở thư mục `wiki/` dưới dạng Vault trong ứng dụng Obsidian để xem Graph View).*

### 4. Kiểm tra Validation (Kiểm tra lỗi liên kết)
Kiểm tra các Broken Link, Orphan Page, và thiếu quan hệ nghiệp vụ, xuất báo cáo tại `outputs/wiki_validation_report.md`.
```bash
python scripts/validate_wiki.py
```

### 5. Nạp dữ liệu lên Neo4j
Sử dụng dữ liệu đã chuẩn hóa để đẩy lên Neo4j. Script sẽ áp dụng Constraints và Index cần thiết, dùng cơ chế `MERGE` để tránh trùng lặp.
```bash
python scripts/load_neo4j.py
```

---
*Các câu truy vấn Cypher demo đã được sinh ra và lưu tại: `cypher/demo_queries.cypher`.*
