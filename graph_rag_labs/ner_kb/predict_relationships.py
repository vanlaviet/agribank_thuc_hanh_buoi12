import pandas as pd
import json
import time
import os
from google import genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Tìm file .env ở thư mục cha nếu không có ở hiện tại
load_dotenv(dotenv_path='../kb+hops/.env')
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_GENERATION_MODEL", "gemini-1.5-flash-latest")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=GEMINI_API_KEY)

# Định nghĩa cấu trúc kết quả trả về của LLM
class Relationship(BaseModel):
    other_doc_id: str = Field(description="ID của văn bản được tham chiếu (phải nằm trong danh sách được cung cấp)")
    relationship_type: str = Field(description="Loại quan hệ: CAN_CU, THAY_THE, SUA_DOI_BO_SUNG, HOP_NHAT, DAN_CHIEU")

class DocumentRelationships(BaseModel):
    relationships: list[Relationship]

def predict():
    df_meta = pd.read_csv("metadata.csv")
    df_content = pd.read_csv("content.csv")
    
    # Danh sách các văn bản để LLM đối chiếu
    doc_catalog = []
    for _, row in df_meta.iterrows():
        doc_catalog.append(f"ID: {row['id']} | Số ký hiệu: {row['so_ky_hieu']} | Tiêu đề: {row['title']}")
        
    catalog_str = "\n".join(doc_catalog)
    
    results = []
    
    # Chúng ta có 31 văn bản. Xử lý từng văn bản.
    for idx, row in df_content.iterrows():
        doc_id = str(row['id'])
        content_html = str(row['content_html'])
        
        # Lấy văn bản thô (chỉ lấy phần đầu để tránh quá dài nếu cần, nhưng Gemini Flash hỗ trợ context lớn)
        # Giới hạn khoảng 20000 ký tự đầu tiên để tối ưu tốc độ và chi phí
        content_text = content_html[:20000] 
        
        prompt = f"""Bạn là một chuyên gia pháp lý. Nhiệm vụ của bạn là đọc nội dung của văn bản sau đây và xác định xem nó có tham chiếu (căn cứ, thay thế, sửa đổi, bổ sung, hợp nhất, dẫn chiếu) đến bất kỳ văn bản nào khác nằm trong DANH MỤC VĂN BẢN được cung cấp hay không.

DANH MỤC VĂN BẢN HIỆN CÓ:
{catalog_str}

NỘI DUNG VĂN BẢN CẦN PHÂN TÍCH (ID: {doc_id}):
{content_text}

Hãy trả về danh sách các mối quan hệ dưới dạng JSON array dựa trên schema quy định. 
Chỉ liệt kê các mối quan hệ với những văn bản có trong DANH MỤC VĂN BẢN (sử dụng đúng ID).
Nếu không có mối quan hệ nào, trả về danh sách rỗng []."""

        print(f"Đang phân tích tài liệu ID: {doc_id} ({idx+1}/{len(df_content)})")
        
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': DocumentRelationships,
                    'temperature': 0.1,
                },
            )
            
            # Xử lý kết quả trả về
            data = json.loads(response.text)
            for rel in data.get('relationships', []):
                other_id = str(rel['other_doc_id'])
                if other_id != doc_id: # Tránh tự trỏ vào chính nó
                    results.append({
                        'doc_id': doc_id,
                        'other_doc_id': other_id,
                        'relationship': rel['relationship_type'],
                        'relationship_type': rel['relationship_type']
                    })
                    print(f"  -> Tìm thấy quan hệ: {rel['relationship_type']} với {other_id}")
                    
        except Exception as e:
            print(f"  Lỗi khi gọi API: {e}")
            
        # Tạm nghỉ để tránh Rate Limit
        time.sleep(2)
        
    # Lưu kết quả
    df_results = pd.DataFrame(results, columns=['doc_id', 'other_doc_id', 'relationship', 'relationship_type'])
    df_results.to_csv("relationships.csv", index=False)
    print(f"\nĐã lưu {len(df_results)} mối quan hệ vào relationships.csv!")

if __name__ == "__main__":
    predict()
