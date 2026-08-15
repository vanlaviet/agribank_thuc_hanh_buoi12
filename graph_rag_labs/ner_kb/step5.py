import pandas as pd
import os

def step5():
    print("--- BƯỚC 5: Relationship Extraction ---")
    
    try:
        cands = pd.read_csv('relation_candidates.csv')
        ents = pd.read_csv('entities.csv')
        docs = pd.read_csv('cleaned_documents.csv')
    except Exception as e:
        print(f"[FAIL] Lỗi đọc file input: {e}")
        return
        
    # Tạo mapping từ so_ky_hieu sang id
    so_to_id = {}
    for _, row in docs.iterrows():
        so_to_id[str(row['so_ky_hieu']).upper()] = row['id']
        
    relations = []
    
    # 1. Document -> Document
    for _, row in cands.iterrows():
        src_so = str(row['source_so_ky_hieu']).upper()
        tgt_so = str(row['target_so_ky_hieu']).upper()
        trigger = str(row['trigger']).lower()
        evidence = row['evidence']
        
        src_id = so_to_id.get(src_so, src_so)
        tgt_id = so_to_id.get(tgt_so, tgt_so)
        
        # Determine relationship type & direction
        rel_type = 'THAM_CHIEU'
        final_src = src_id
        final_tgt = tgt_id
        
        if 'sửa đổi' in trigger or 'bổ sung' in trigger:
            rel_type = 'SUA_DOI_BO_SUNG'
        elif 'thay thế' in trigger or 'bãi bỏ' in trigger:
            # Document cũ (Target) -> THAY_THE_BOI -> Document mới (Source)
            rel_type = 'THAY_THE_BOI'
            final_src = tgt_id
            final_tgt = src_id
        elif 'căn cứ' in trigger or 'nhắc đến' in trigger:
            rel_type = 'THAM_CHIEU'
            
        relations.append({
            'source': final_src,
            'target': final_tgt,
            'relationship_type': rel_type,
            'method': 'rule',
            'confidence': 1.0,
            'evidence': evidence
        })
        
    # 2. Document -> Entity
    for _, row in ents.iterrows():
        doc_id = row['source_doc_id']
        ent_id = row['entity_id']
        etype = row['entity_type']
        
        rel_type = None
        if etype == 'CoQuan':
            rel_type = 'BAN_HANH_BOI'
        elif etype == 'NguoiKy':
            rel_type = 'KY_BOI'
        elif etype == 'DoiTuongApDung':
            rel_type = 'AP_DUNG_CHO'
        elif etype == 'LinhVuc':
            rel_type = 'THUOC_LINH_VUC'
            
        if rel_type:
            relations.append({
                'source': doc_id,
                'target': ent_id,
                'relationship_type': rel_type,
                'method': row['method'],
                'confidence': row['confidence'],
                'evidence': row['evidence']
            })
            
    df_rel = pd.DataFrame(relations)
    
    if df_rel.empty:
        print("[FAIL] Không có relation nào được tạo.")
        return
        
    # Loại duplicate
    df_rel = df_rel.drop_duplicates(subset=['source', 'target', 'relationship_type'])
    
    out_path = 'relationships_raw.csv'
    df_rel.to_csv(out_path, index=False)
    
    print(f"Tổng số quan hệ đã tạo (đã loại trùng lặp): {len(df_rel)}")
    print("\nSố relation theo type:")
    print(df_rel['relationship_type'].value_counts().to_string())
    
    print("\n--- 10 Relation Mẫu ---")
    sample = df_rel.sample(min(10, len(df_rel)))
    for _, row in sample.iterrows():
        print(f"({row['source']}) -[{row['relationship_type']}]-> ({row['target']})")
        ev = str(row['evidence']).replace('\n', ' ')
        print(f"  Method: {row['method']} | Evidence: {ev[:100]}...\n")
        
    if os.path.exists(out_path):
        print("[PASS] BƯỚC 5 hoàn thành thành công.")
    else:
        print("[FAIL] Lỗi lưu file.")

if __name__ == "__main__":
    step5()
