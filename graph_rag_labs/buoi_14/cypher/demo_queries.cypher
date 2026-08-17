// Query A — Xem graph Buổi 14
MATCH (n {lab_session: "buoi_14"})-[r]->(m {lab_session: "buoi_14"})
RETURN n, r, m
LIMIT 100;

// Query B — Từ văn bản tới điều khoản
MATCH (v:VanBan {lab_session: "buoi_14"})-[:CONTAINS]->(d:DieuKhoan)
RETURN v, d
LIMIT 50;

// Query C — Xem chuỗi điều khoản
MATCH path = (d1:DieuKhoan {lab_session: "buoi_14"})-[:NEXT*1..5]->(d2:DieuKhoan)
RETURN path
LIMIT 20;

// Query D — Quan hệ văn bản có trong dữ liệu
MATCH (v1:VanBan {lab_session: "buoi_14"})-[r]->(v2:VanBan {lab_session: "buoi_14"})
WHERE type(r) <> 'CONTAINS' AND type(r) <> 'NEXT'
RETURN v1, r, v2
LIMIT 50;

// Query E — Tìm node không có liên kết
MATCH (n {lab_session: "buoi_14"})
WHERE NOT (n)--()
RETURN n
LIMIT 50;
