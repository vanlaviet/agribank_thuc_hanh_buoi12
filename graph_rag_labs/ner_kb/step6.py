import pandas as pd
import os

def step6():
    print("--- BƯỚC 6: Validate Relationship ---")
    
    try:
        raw_rels = pd.read_csv('relationships_raw.csv')
        docs = pd.read_csv('cleaned_documents.csv')
        ents = pd.read_csv('entities.csv')
    except Exception as e:
        print(f"[FAIL] Lỗi đọc file input: {e}")
        return
        
    valid_doc_ids = set(docs['id'].astype(str).tolist())
    valid_ent_ids = set(ents['entity_id'].astype(str).tolist())
    
    allowed_types = {
        'THAM_CHIEU', 'SUA_DOI_BO_SUNG', 'THAY_THE_BOI',
        'BAN_HANH_BOI', 'KY_BOI', 'AP_DUNG_CHO', 'THUOC_LINH_VUC'
    }
    
    pass_relations = []
    fail_reports = []
    
    seen_edges = set()
    
    for idx, row in raw_rels.iterrows():
        src = str(row.get('source', ''))
        tgt = str(row.get('target', ''))
        rel_type = str(row.get('relationship_type', ''))
        evidence = str(row.get('evidence', ''))
        
        reasons = []
        
        # 1. Missing fields
        if not src or src == 'nan': reasons.append("Missing source")
        if not tgt or tgt == 'nan': reasons.append("Missing target")
        if not rel_type or rel_type == 'nan': reasons.append("Missing relationship_type")
        if not evidence or evidence == 'nan' or evidence.strip() == '': reasons.append("Missing evidence")
        
        # 2. Validate source
        if src and src not in valid_doc_ids:
            reasons.append(f"Source ID '{src}' không tồn tại trong corpus")
            
        # 3. Validate target (Closed-corpus requirement)
        if tgt:
            is_doc = tgt in valid_doc_ids
            is_ent = tgt in valid_ent_ids
            if not is_doc and not is_ent:
                reasons.append(f"Target ID không tồn tại trong corpus hay entities.csv (closed-corpus)")
                
        # 4. Validate relationship_type
        if rel_type not in allowed_types:
            reasons.append(f"Invalid relationship_type '{rel_type}'")
            
        # 5. Check self-loop
        if src and tgt and src == tgt:
            reasons.append("Self-loop (source == target)")
            
        # 6. Check duplicate
        edge_key = (src, tgt, rel_type)
        if edge_key in seen_edges:
            reasons.append("Duplicate edge")
        else:
            if src and tgt and rel_type:
                seen_edges.add(edge_key)
            
        if reasons:
            fail_row = row.to_dict()
            fail_row['fail_reason'] = " | ".join(reasons)
            fail_reports.append(fail_row)
        else:
            pass_relations.append(row.to_dict())
            
    df_pass = pd.DataFrame(pass_relations)
    df_fail = pd.DataFrame(fail_reports)
    
    df_pass.to_csv('relationships.csv', index=False)
    df_fail.to_csv('validation_report.csv', index=False)
    
    print(f"Tổng relation raw: {len(raw_rels)}")
    print(f"Số PASS: {len(df_pass)}")
    print(f"Số FAIL: {len(df_fail)}")
    
    if len(df_pass) > 0:
        print("\nSố relation PASS theo type:")
        print(df_pass['relationship_type'].value_counts().to_string())
        
    if len(df_fail) > 0:
        print("\nNguyên nhân FAIL phổ biến:")
        all_reasons = []
        for r in df_fail['fail_reason']:
            all_reasons.extend(r.split(' | '))
        reason_counts = pd.Series(all_reasons).value_counts()
        print(reason_counts.to_string())
        
    print("\n--- 10 Relation PASS Mẫu ---")
    if len(df_pass) > 0:
        sample = df_pass.sample(min(10, len(df_pass)))
        for _, row in sample.iterrows():
            print(f"({row['source']}) -[{row['relationship_type']}]-> ({row['target']})")
            
    if os.path.exists('relationships.csv') and os.path.exists('validation_report.csv'):
        print("\n[PASS] BƯỚC 6 hoàn thành thành công.")
    else:
        print("\n[FAIL] Lỗi tạo file đầu ra.")

if __name__ == "__main__":
    step6()
