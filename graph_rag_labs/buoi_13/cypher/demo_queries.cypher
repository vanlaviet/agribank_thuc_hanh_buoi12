// A. Xem toàn bộ graph
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 100;

// B. Tìm kiểm soát giảm thiểu một rủi ro (Ví dụ rủi ro RR-001)
MATCH (k:KiemSoat)-[r:MITIGATES]->(ri:RuiRo {id: 'RR-001'})
RETURN k, r, ri;

// C. Tìm sự kiện của một rủi ro (Ví dụ rủi ro RR-001)
MATCH (ri:RuiRo {id: 'RR-001'})-[r:OBSERVED_AS]->(s:SuKienRuiRo)
RETURN ri, r, s;

// D. Tìm đường: KiemSoat -> RuiRo -> SuKienRuiRo
MATCH path = (k:KiemSoat)-[:MITIGATES]->(r:RuiRo)-[:OBSERVED_AS]->(s:SuKienRuiRo)
RETURN path
LIMIT 50;

// E. Tìm rủi ro không có kiểm soát
MATCH (r:RuiRo)
WHERE NOT ()-[:MITIGATES]->(r)
RETURN r;

// F. Tìm relation chưa VERIFIED
MATCH ()-[r]->()
WHERE r.verification_status <> 'VERIFIED'
RETURN r;
