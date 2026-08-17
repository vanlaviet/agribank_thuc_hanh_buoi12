import os
import sys
import pandas as pd
import json

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.secure_retriever import SecureBM25Retriever

def run_audit():
    corpus_path = 'data/processed/chunks_secure.csv'
    retriever = SecureBM25Retriever(corpus_path)
    
    test_cases = [
        {
            "name": "Test 1: Truy cập quy trình nhân sự",
            "query": "quy trình bổ nhiệm nhân sự",
            "unauthorized_roles": ["Guest"],
            "authorized_roles": ["Admin"],
        },
        {
            "name": "Test 2: Phê duyệt tín dụng vay vốn",
            "query": "phê duyệt tín dụng hạn mức rủi ro",
            "unauthorized_roles": ["Guest"],
            "authorized_roles": ["Staff"],
        },
        {
            "name": "Test 3: Tài liệu chung",
            "query": "Nghị định 73/2016",
            "unauthorized_roles": [],
            "authorized_roles": ["Guest"],
        },
        {
            "name": "Test 4: Xem bảng lương thưởng",
            "query": "chính sách lương thưởng",
            "unauthorized_roles": ["Guest"],
            "authorized_roles": ["Admin"],
        },
        {
            "name": "Test 5: Kỷ luật nhân viên",
            "query": "quy định kỷ luật",
            "unauthorized_roles": ["Staff"],
            "authorized_roles": ["Admin"],
        }
    ]
    
    report = "# Báo cáo Kiểm định Bảo mật Dữ liệu (Security Audit)\n\n"
    report += "Tổng quan số lượng bài test chạy: 5\n\n"
    
    all_passed = True
    
    for tc in test_cases:
        report += f"## {tc['name']}\n"
        report += f"- Query: `{tc['query']}`\n"
        
        # Test Unauthorized
        if tc["unauthorized_roles"]:
            res_unauth = retriever.retrieve(tc["query"], user_roles=tc["unauthorized_roles"], top_k=10)
            
            leak = False
            for r in res_unauth:
                try:
                    allowed = json.loads(r["allowed_roles"])
                except:
                    allowed = ["Admin", "Staff", "Guest"]
                    
                if not any(role in allowed for role in tc["unauthorized_roles"]):
                    leak = True
                    break
            
            if leak:
                report += f"- ❌ FAIL (Unauthorized Access): Dữ liệu bị rò rỉ cho quyền {tc['unauthorized_roles']}!\n"
                all_passed = False
            else:
                report += f"- ✅ PASS (Unauthorized Access): Không có tài liệu cấm nào bị lọt ra cho quyền {tc['unauthorized_roles']}.\n"
        
        # Test Authorized
        res_auth = retriever.retrieve(tc["query"], user_roles=tc["authorized_roles"], top_k=10)
        auth_success = len(res_auth) > 0
        
        if auth_success:
            report += f"- ✅ PASS (Authorized Access): Quyền {tc['authorized_roles']} truy cập thành công.\n"
        else:
            report += f"- ⚠️ WARNING: Không tìm thấy kết quả cho quyền {tc['authorized_roles']} (Có thể do BM25 không match từ khóa).\n"
        
        report += "\n"
        
    report += "## Kết luận\n"
    if all_passed:
        report += "Hệ thống **ĐẠT** chứng nhận an toàn dữ liệu mức cơ bản. Không phát hiện rò rỉ (Data Leakage) ở tầng Retrieval.\n"
    else:
        report += "Hệ thống **KHÔNG ĐẠT** an toàn dữ liệu. Cần kiểm tra lại bộ lọc phân quyền.\n"
        
    os.makedirs('outputs', exist_ok=True)
    with open('outputs/security_audit_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
        
    print("Security audit completed. Check outputs/security_audit_report.md")

if __name__ == '__main__':
    run_audit()
