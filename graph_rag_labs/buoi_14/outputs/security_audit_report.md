# Báo cáo Kiểm định Bảo mật Dữ liệu (Security Audit)

Tổng quan số lượng bài test chạy: 5

## Test 1: Truy cập quy trình nhân sự
- Query: `quy trình bổ nhiệm nhân sự`
- ✅ PASS (Unauthorized Access): Không có tài liệu cấm nào bị lọt ra cho quyền ['Guest'].
- ✅ PASS (Authorized Access): Quyền ['Admin'] truy cập thành công.

## Test 2: Phê duyệt tín dụng vay vốn
- Query: `phê duyệt tín dụng hạn mức rủi ro`
- ✅ PASS (Unauthorized Access): Không có tài liệu cấm nào bị lọt ra cho quyền ['Guest'].
- ✅ PASS (Authorized Access): Quyền ['Staff'] truy cập thành công.

## Test 3: Tài liệu chung
- Query: `Nghị định 73/2016`
- ✅ PASS (Authorized Access): Quyền ['Guest'] truy cập thành công.

## Test 4: Xem bảng lương thưởng
- Query: `chính sách lương thưởng`
- ✅ PASS (Unauthorized Access): Không có tài liệu cấm nào bị lọt ra cho quyền ['Guest'].
- ✅ PASS (Authorized Access): Quyền ['Admin'] truy cập thành công.

## Test 5: Kỷ luật nhân viên
- Query: `quy định kỷ luật`
- ✅ PASS (Unauthorized Access): Không có tài liệu cấm nào bị lọt ra cho quyền ['Staff'].
- ✅ PASS (Authorized Access): Quyền ['Admin'] truy cập thành công.

## Kết luận
Hệ thống **ĐẠT** chứng nhận an toàn dữ liệu mức cơ bản. Không phát hiện rò rỉ (Data Leakage) ở tầng Retrieval.
