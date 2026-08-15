import pandas as pd
import unicodedata
import os
import uuid

def normalize_text(text):
    if pd.isna(text):
        return ""
    # Unicode NFKC
    text = unicodedata.normalize('NFKC', str(text))
    # Bỏ khoảng trắng thừa
    text = ' '.join(text.split())
    return text

def get_canonical_name(name):
    lower_name = name.lower()
    
    # Alias mapping
    aliases = {
        'nhnn': 'Ngân hàng Nhà nước Việt Nam',
        'ngân hàng nhà nước': 'Ngân hàng Nhà nước Việt Nam',
        'btc': 'Bộ Tài chính',
        'cp': 'Chính phủ',
        'qh': 'Quốc hội',
        'ubnd': 'Ủy ban nhân dân',
        'hđnd': 'Hội đồng nhân dân'
    }
    
    if lower_name in aliases:
        return aliases[lower_name], True
        
    # Return Title Case for CoQuan or just capitalized first letter, but generally keep original case or Title Case
    # To keep it simple and safe, just return the normalized original name with first letter capitalized if needed, 
    # but since it's canonical, let's keep original casing but stripped, unless it's a known alias.
    return name, False

def step4():
    print("--- BƯỚC 4: Chuẩn hóa Entity ---")
    
    try:
        raw_ent = pd.read_csv('extracted_entities_raw.csv')
        enr_meta = pd.read_csv('enriched_metadata.csv')
    except Exception as e:
        print(f"[FAIL] Lỗi đọc file input: {e}")
        return
        
    all_entities = []
    
    # 1. Gather entities từ extracted_entities_raw
    if not raw_ent.empty:
        for idx, row in raw_ent.iterrows():
            if pd.isna(row['entity']) or not str(row['entity']).strip(): continue
            all_entities.append({
                'entity_type': row.get('entity_type', 'Unknown'),
                'original_name': str(row['entity']),
                'source_doc_id': row.get('source_id', ''),
                'method': row.get('method', 'gemini'),
                'confidence': row.get('confidence', 0.0),
                'evidence': row.get('evidence', '')
            })
            
    # 2. Gather entities từ enriched_metadata (các trường gốc và enrich)
    for idx, row in enr_meta.iterrows():
        doc_id = row['id']
        
        # CoQuan
        cq = row.get('co_quan_ban_hanh')
        if pd.notna(cq) and str(cq).strip() not in ['', 'Chưa phân loại']:
            all_entities.append({
                'entity_type': 'CoQuan',
                'original_name': str(cq),
                'source_doc_id': doc_id,
                'method': 'metadata',
                'confidence': 1.0,
                'evidence': 'metadata'
            })
            
        # NguoiKy
        nk = row.get('nguoi_ky')
        if pd.notna(nk) and str(nk).strip() not in ['', 'Chưa phân loại']:
            all_entities.append({
                'entity_type': 'NguoiKy',
                'original_name': str(nk),
                'source_doc_id': doc_id,
                'method': 'metadata',
                'confidence': 1.0,
                'evidence': 'metadata'
            })
            
        # LinhVuc
        lv = row.get('linh_vuc')
        if pd.notna(lv) and str(lv).strip() not in ['', 'Chưa phân loại']:
            all_entities.append({
                'entity_type': 'LinhVuc',
                'original_name': str(lv),
                'source_doc_id': doc_id,
                'method': 'metadata',
                'confidence': 1.0,
                'evidence': 'metadata'
            })
            
        # DoiTuongApDung (có thể phân tách bằng dấu chấm phẩy)
        dt = row.get('thong_tin_ap_dung')
        if pd.notna(dt) and str(dt).strip() not in ['', 'Chưa phân loại']:
            for part in str(dt).split(';'):
                if part.strip():
                    all_entities.append({
                        'entity_type': 'DoiTuongApDung',
                        'original_name': part.strip(),
                        'source_doc_id': doc_id,
                        'method': 'metadata/gemini',
                        'confidence': 1.0, # Or average if from gemini
                        'evidence': 'metadata/enrichment'
                    })
                    
    df_ent = pd.DataFrame(all_entities)
    
    if df_ent.empty:
        print("[FAIL] Không có entity nào để chuẩn hóa.")
        return
        
    before_count = len(df_ent)
    
    merged_aliases = set()
    normalized_rows = []
    
    for idx, row in df_ent.iterrows():
        orig = row['original_name']
        norm = normalize_text(orig)
        canon, is_alias = get_canonical_name(norm)
        
        # Upper case first letter for consistency if not alias, just simple capitalize
        if not is_alias and len(canon) > 0:
            canon = canon[0].upper() + canon[1:]
            
        if is_alias:
            merged_aliases.add(f"{norm} -> {canon}")
            
        row_dict = row.to_dict()
        row_dict['canonical_name'] = canon
        row_dict['original_name'] = orig
        row_dict['entity_id'] = f"{row['entity_type']}_{hash(canon.lower()) % 1000000000}"
        
        normalized_rows.append(row_dict)
        
    norm_df = pd.DataFrame(normalized_rows)
    
    # Loại bỏ duplicate theo (source_doc_id, canonical_name, entity_type)
    # Giữ lại row có confidence cao hơn hoặc evidence tốt hơn
    norm_df = norm_df.sort_values('confidence', ascending=False).drop_duplicates(
        subset=['source_doc_id', 'canonical_name', 'entity_type']
    )
    
    after_count = len(norm_df)
    
    # Sắp xếp lại cột
    cols = ['entity_id', 'entity_type', 'canonical_name', 'original_name', 'source_doc_id', 'method', 'confidence', 'evidence']
    norm_df = norm_df[cols]
    
    out_path = 'entities.csv'
    norm_df.to_csv(out_path, index=False)
    
    print(f"Số entity trước normalize (kể cả raw metadata): {before_count}")
    print(f"Số entity sau normalize và deduplicate: {after_count}")
    print(f"\nCác alias đã merge ({len(merged_aliases)}):")
    for a in merged_aliases:
        print("-", a)
        
    print("\n--- 10 Entity Mẫu ---")
    sample = norm_df.sample(min(10, len(norm_df))) if len(norm_df) > 0 else norm_df
    for _, row in sample.iterrows():
        print(f"[{row['entity_type']}] {row['original_name']} -> {row['canonical_name']} (Doc: {row['source_doc_id']}, Method: {row['method']})")
        
    if os.path.exists(out_path):
        print("\n[PASS] BƯỚC 4 hoàn thành thành công.")
    else:
        print("\n[FAIL] Không tạo được entities.csv.")

if __name__ == "__main__":
    step4()
