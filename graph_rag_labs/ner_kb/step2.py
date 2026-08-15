import pandas as pd
import re
import os

def extract_candidates():
    print("--- BƯỚC 2: Rule-based Candidate Extraction ---")
    try:
        df = pd.read_csv('cleaned_documents.csv')
    except Exception as e:
        print(f"[FAIL] Lỗi đọc cleaned_documents.csv: {e}")
        return

    # Regex target: digit(s) / digit(s) / characters (A-Z, Đ, numbers, dash)
    # Ví dụ: 22/2023/TT-NHNN, 73/2016/NĐ-CP, 32/2024/QH15
    target_pattern = r'(\d+/\d+/[A-ZĐ0-9\-]+)'
    
    triggers = ['căn cứ', 'sửa đổi, bổ sung', 'sửa đổi bổ sung', 'bãi bỏ', 'thay thế']
    
    candidates = []
    
    for idx, row in df.iterrows():
        src_id = row['id']
        src_so = row['so_ky_hieu']
        content = row.get('content_clean', '')
        if pd.isna(content):
            continue
            
        # Tách câu (theo dấu ., \n, hoặc ;)
        sentences = re.split(r'[\.\n;]', str(content))
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence: continue
            
            sentence_lower = sentence.lower()
            matched_trigger = None
            for t in triggers:
                if t in sentence_lower:
                    matched_trigger = t
                    break
            
            targets = re.findall(target_pattern, sentence, re.IGNORECASE)
            
            if targets:
                trigger_str = matched_trigger if matched_trigger else 'nhắc đến'
                
                for target in targets:
                    target_upper = target.upper()
                    # Loại bỏ tự tham chiếu
                    if str(src_so).upper() == target_upper:
                        continue
                        
                    candidates.append({
                        'source_id': src_id,
                        'source_so_ky_hieu': src_so,
                        'target_so_ky_hieu': target_upper,
                        'trigger': trigger_str,
                        'evidence': sentence
                    })
    
    cand_df = pd.DataFrame(candidates)
    
    if len(cand_df) == 0:
        print("[FAIL] Không tìm thấy candidate nào.")
        return
        
    # Loại duplicate candidate
    # Drop trùng target trong cùng một source với cùng trigger
    cand_df = cand_df.drop_duplicates(subset=['source_id', 'target_so_ky_hieu', 'trigger'])
    
    print(f"Tổng số candidate (sau khi loại trùng): {len(cand_df)}")
    print("\nSố candidate theo trigger:")
    print(cand_df['trigger'].value_counts().to_string())
    
    # In 10 mẫu
    print("\n--- 10 Candidate Mẫu ---")
    sample = cand_df.head(10)
    for _, row in sample.iterrows():
        print(f"- {row['source_so_ky_hieu']} -> [{row['trigger']}] -> {row['target_so_ky_hieu']}")
        print(f"  Evidence: {row['evidence'][:150]}...\n")
        
    out_path = 'relation_candidates.csv'
    cand_df.to_csv(out_path, index=False)
    
    if os.path.exists(out_path):
        print(f"[PASS] BƯỚC 2 hoàn thành. Đã lưu {out_path}.")
    else:
        print("[FAIL] Không lưu được file.")

if __name__ == "__main__":
    extract_candidates()
