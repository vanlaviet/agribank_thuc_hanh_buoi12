---
id: RR-002
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---
# Phê duyệt tín dụng vượt thẩm quyền

**Mô tả:** Kiểm tra hạn mức phê duyệt không hiệu lực

- **Category:** Rui ro tin dung
- **Cause:** Phân quyền trên hệ thống không cập nhật
- **Event:** Khoản vay được phê duyệt vượt thẩm quyền
- **Impact:** Tăng nợ xấu và vi phạm quy định
- **Inherent Level:** Cao
- **Residual Level:** Trung binh
- **Owner Unit ID:** DV-CREDIT

## Kiểm soát liên quan
- [[Kiểm tra hạn mức phê duyệt trên hệ thống]] (MITIGATES) [Status: VERIFIED] - Evidence: Dữ liệu mô phỏng: kiểm tra hạn mức ngăn phê duyệt vượt thẩm quyền

## Sự kiện liên quan
- [[Sự kiện SK-002]] (OBSERVED_AS) [Status: VERIFIED] - Evidence: Dữ liệu mô phỏng: sự kiện vượt thẩm quyền