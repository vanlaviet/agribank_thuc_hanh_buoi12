import pandas as pd
import json
import os
import time
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class Entity(BaseModel):
    entity: str
    entity_type: str = Field(description="Must be exactly one of: CoQuan, NguoiKy, DoiTuongApDung, LinhVuc")
    confidence: float = Field(description="Confidence from 0.0 to 1.0. Don't always use 1.0.")
    evidence: str = Field(description="Exact quote from the text.")

class ExtractionResult(BaseModel):
    entities: list[Entity]

def step3():
    print("--- BƯỚC 3: Entity Extraction và Metadata Enrichment ---")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[FAIL] Thiếu GEMINI_API_KEY trong .env")
        return
        
    client = genai.Client()
    
    try:
        df = pd.read_csv('cleaned_documents.csv')
    except Exception as e:
        print(f"[FAIL] Lỗi đọc cleaned_documents.csv: {e}")
        return
        
    all_entities = []
    enriched_rows = []
    
    success_cnt = 0
    fail_cnt = 0
    errors = []
    enriched_stats = {'CoQuan': 0, 'NguoiKy': 0, 'DoiTuongApDung': 0, 'LinhVuc': 0}
    enriched_examples = []
    
    print(f"Bắt đầu trích xuất cho {len(df)} documents. Vui lòng đợi...")
    
    for idx, row in df.iterrows():
        doc_id = row['id']
        content = str(row.get('content_clean', ''))
        
        if not content or content == 'nan':
            fail_cnt += 1
            errors.append(f"Doc {doc_id}: content rỗng")
            enriched_rows.append(row.to_dict())
            continue
            
        # Truncate content to avoid massive payloads.
        if len(content) > 30000:
            text_to_process = content[:20000] + "\n...[TRUNCATED]...\n" + content[-10000:]
        else:
            text_to_process = content
            
        prompt = f"""
        Trích xuất các thực thể (CoQuan, NguoiKy, DoiTuongApDung, LinhVuc) từ văn bản pháp lý.
        - CoQuan: Cơ quan ban hành (VD: Chính phủ, Quốc hội, Ngân hàng Nhà nước...)
        - NguoiKy: Người ký hoặc người có thẩm quyền ban hành
        - DoiTuongApDung: Đối tượng chịu sự điều chỉnh (thường nằm ở Điều 2 hoặc phần đầu)
        - LinhVuc: Lĩnh vực pháp lý (VD: Tín dụng, Kiểm toán, Bảo hiểm, Chứng khoán, v.v.)
        
        Nếu không có bằng chứng (evidence) rõ ràng, KHÔNG trích xuất entity đó.
        
        Văn bản:
        {text_to_process}
        """
        
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractionResult,
                    temperature=0.0
                )
            )
            
            res_json = json.loads(response.text)
            extracted_list = res_json.get('entities', [])
            
            for ent in extracted_list:
                all_entities.append({
                    'source_id': doc_id,
                    'entity': ent.get('entity', ''),
                    'entity_type': ent.get('entity_type', ''),
                    'source': 'content_clean',
                    'method': 'gemini',
                    'confidence': ent.get('confidence', 0.0),
                    'evidence': ent.get('evidence', '')
                })
                
            # Enrichment
            new_row = row.to_dict()
            
            def get_best(etype):
                cands = [e for e in extracted_list if e.get('entity_type') == etype and e.get('confidence', 0) > 0.5]
                if cands:
                    return sorted(cands, key=lambda x: x.get('confidence', 0), reverse=True)[0].get('entity')
                return None
                
            co_quan = get_best('CoQuan')
            nguoi_ky = get_best('NguoiKy')
            linh_vuc = get_best('LinhVuc')
            
            old_co_quan = new_row.get('co_quan_ban_hanh')
            if pd.isna(old_co_quan) or str(old_co_quan).strip() in ['', 'Chưa phân loại', 'nan']:
                if co_quan:
                    new_row['co_quan_ban_hanh'] = co_quan
                    enriched_stats['CoQuan'] += 1
                    if len(enriched_examples) < 5:
                        enriched_examples.append(f"Doc {doc_id} [CoQuan]: '{old_co_quan}' -> '{co_quan}'")
                        
            old_nguoi_ky = new_row.get('nguoi_ky')
            if pd.isna(old_nguoi_ky) or str(old_nguoi_ky).strip() in ['', 'Chưa phân loại', 'nan']:
                if nguoi_ky:
                    new_row['nguoi_ky'] = nguoi_ky
                    enriched_stats['NguoiKy'] += 1
                    if len(enriched_examples) < 5:
                        enriched_examples.append(f"Doc {doc_id} [NguoiKy]: '{old_nguoi_ky}' -> '{nguoi_ky}'")
                        
            old_linh_vuc = new_row.get('linh_vuc')
            if pd.isna(old_linh_vuc) or str(old_linh_vuc).strip() in ['', 'Chưa phân loại', 'nan']:
                if linh_vuc:
                    new_row['linh_vuc'] = linh_vuc
                    enriched_stats['LinhVuc'] += 1
                    if len(enriched_examples) < 5:
                        enriched_examples.append(f"Doc {doc_id} [LinhVuc]: '{old_linh_vuc}' -> '{linh_vuc}'")
                        
            old_doi_tuong = new_row.get('thong_tin_ap_dung')
            if pd.isna(old_doi_tuong) or str(old_doi_tuong).strip() in ['', 'Chưa phân loại', 'nan']:
                dt_cands = [e.get('entity') for e in extracted_list if e.get('entity_type') == 'DoiTuongApDung' and e.get('confidence', 0) > 0.5]
                if dt_cands:
                    dt_str = "; ".join(dt_cands)
                    new_row['thong_tin_ap_dung'] = dt_str
                    enriched_stats['DoiTuongApDung'] += 1
                    if len(enriched_examples) < 5:
                        enriched_examples.append(f"Doc {doc_id} [DoiTuongApDung]: '{old_doi_tuong}' -> '{dt_str}'")
            
            enriched_rows.append(new_row)
            success_cnt += 1
            
        except Exception as e:
            fail_cnt += 1
            errors.append(f"Doc {doc_id}: {str(e)}")
            enriched_rows.append(row.to_dict())
            
        # Sleep để tránh rate limit nếu account free
        time.sleep(2)
        
    ent_df = pd.DataFrame(all_entities)
    ent_df.to_csv('extracted_entities_raw.csv', index=False)
    
    enr_df = pd.DataFrame(enriched_rows)
    enr_df.to_csv('enriched_metadata.csv', index=False)
    
    print(f"\n[PASS] BƯỚC 3 hoàn thành.")
    print(f"Số document thành công: {success_cnt}")
    print(f"Số document thất bại: {fail_cnt}")
    
    print(f"\nSố entity theo loại đã trích xuất:")
    if not ent_df.empty:
        print(ent_df['entity_type'].value_counts().to_string())
        
    print(f"\nSố giá trị metadata được bổ sung:")
    for k, v in enriched_stats.items():
        print(f"- {k}: {v}")
        
    print(f"\n5 ví dụ metadata gốc -> metadata làm giàu:")
    for ex in enriched_examples:
        print("-", ex)
        
    if errors:
        print(f"\nDanh sách lỗi ({len(errors)}):")
        for err in errors[:5]:
            print("-", err)
        if len(errors) > 5:
            print("...")

if __name__ == "__main__":
    step3()
