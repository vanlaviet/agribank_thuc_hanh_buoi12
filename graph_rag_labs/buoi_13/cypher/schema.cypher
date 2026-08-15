// 1. Tạo unique constraints trên thuộc tính id
CREATE CONSTRAINT ruiro_id IF NOT EXISTS FOR (r:RuiRo) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT kiemsoat_id IF NOT EXISTS FOR (k:KiemSoat) REQUIRE k.id IS UNIQUE;
CREATE CONSTRAINT sukienruiro_id IF NOT EXISTS FOR (s:SuKienRuiRo) REQUIRE s.id IS UNIQUE;

// Các index hỗ trợ tìm kiếm nhanh theo tên
CREATE INDEX ruiro_name IF NOT EXISTS FOR (r:RuiRo) ON (r.name);
CREATE INDEX kiemsoat_name IF NOT EXISTS FOR (k:KiemSoat) ON (k.name);
CREATE INDEX sukienruiro_name IF NOT EXISTS FOR (s:SuKienRuiRo) ON (s.name);
