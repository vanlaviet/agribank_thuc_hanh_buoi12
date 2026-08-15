# Báo cáo Kiểm tra Wiki Risk Graph

## 1 & 2. Thống kê chung
- Tổng số file Markdown: 35
- Tổng số Wikilink: 78

## Chi tiết Lỗi Kỹ Thuật (Code Bugs)
### 3. Broken Wikilinks (Trỏ tới trang không tồn tại)
- (Không có lỗi)

### 4. Entity trùng ID (entities.csv)
- (Không có lỗi)

### 5. Trang có ID nhưng không có trong entities.csv
- (Không có lỗi)

### 6. Lỗi Relation (source/target mồ côi)
- (Không có lỗi)

### 9. Orphan Pages (Trang hoàn toàn cô lập)
- (Không có lỗi)

## Chi tiết Lỗi Dữ Liệu Nghiệp Vụ (Data Missing)
> Lưu ý: Các lỗi dưới đây do dữ liệu seed ban đầu thiếu, không phải lỗi hệ thống.

### 7. Rủi ro không có KiemSoat (MITIGATES)
- Rủi ro ID: `RR-011`
- Rủi ro ID: `RR-012`

### 8. Rủi ro không có SuKienRuiRo (OBSERVED_AS)
- (Mọi rủi ro đều đã được ghi nhận bằng ít nhất 1 sự kiện)