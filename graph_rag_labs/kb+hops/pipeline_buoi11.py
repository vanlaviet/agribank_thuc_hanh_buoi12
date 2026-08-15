import os
from google import genai
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# Cấu hình
# ==========================================
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "abcd1234" # Đổi nếu cần

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY không được tìm thấy. Vui lòng thêm vào file .env")
    client = None
else:
    client = genai.Client(api_key=GEMINI_API_KEY)


MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"

# Câu hỏi kiểm thử
questions = [
    "Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào, và nghị định bị thay thế đó có nội dung gì nổi bật về kinh doanh bảo hiểm?",
    "Văn bản hợp nhất số 52/VBHN-NHNN được hợp nhất từ văn bản nào, và quy định về hồ sơ, thủ tục cấp giấy phép lần đầu của ngân hàng thương mại gồm những tài liệu gì?",
    "Thông tư số 01/2025/TT-NHNN quy định về cấp giấy phép quỹ tín dụng nhân dân được sửa đổi, bổ sung bởi văn bản nào, và những nội dung sửa đổi bổ sung chính là gì?",
    "Thông tư số 41/2016/TT-NHNN về tỷ lệ an toàn vốn của ngân hàng căn cứ vào luật nào, và luật đó quy định chức năng nhiệm vụ của cơ quan nào?",
    "Hoạt động giao nhận, vận chuyển tiền mặt và tài sản quý của Ngân hàng Nhà nước được điều chỉnh bởi Thông tư nào, và Thông tư đó có được sửa đổi bổ sung bởi văn bản nào không?"
]

def setup_vector_index(driver):
    with driver.session() as session:
        session.run("""
        CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
        FOR (c:Chunk)
        ON (c.embedding)
        OPTIONS {indexConfig: {
         `vector.dimensions`: 384,
         `vector.similarity_function`: 'cosine'
        }}
        """)
        # Wait a bit for index to populate
        import time
        time.sleep(2)
        print("Vector index 'chunk_embedding' ready.")

def search_graph_rag(driver, embedding, num_hops, top_k=3):
    """
    Truy vấn vector lấy top_k chunks.
    Mở rộng N hops để lấy tiêu đề của các Document liên quan.
    """
    with driver.session() as session:
        query = f"""
        CALL db.index.vector.queryNodes('chunk_embedding', $top_k, $embedding)
        YIELD node AS chunk, score
        MATCH (chunk)-[:PART_OF]->(d:Document)
        OPTIONAL MATCH p = (d)-[*1..{num_hops}]-(related_doc:Document)
        RETURN chunk.text AS text, d.so_ky_hieu AS so_ky_hieu, d.title AS title, score,
               collect(distinct related_doc.so_ky_hieu + " - " + related_doc.title) AS related_docs
        """
        if num_hops == 0:
            query = """
            CALL db.index.vector.queryNodes('chunk_embedding', $top_k, $embedding)
            YIELD node AS chunk, score
            MATCH (chunk)-[:PART_OF]->(d:Document)
            RETURN chunk.text AS text, d.so_ky_hieu AS so_ky_hieu, d.title AS title, score,
                   [] AS related_docs
            """
            
        result = session.run(query, top_k=top_k, embedding=embedding)
        
        contexts = []
        for record in result:
            context = f"Văn bản: {record['so_ky_hieu']} - {record['title']}\n"
            context += f"Nội dung trích xuất: {record['text']}\n"
            if record['related_docs']:
                context += f"Các văn bản liên quan (trong vòng {num_hops} bước nhảy): " + ", ".join(record['related_docs']) + "\n"
            contexts.append(context)
            
        return "\n---\n".join(contexts)

def generate_answer(question, context):
    if not client: return "Error: Không có GEMINI_API_KEY. Vui lòng cập nhật file .env"
    prompt = f"""Bạn là một trợ lý ảo am hiểu pháp luật Việt Nam. Dưới đây là ngữ cảnh trích xuất từ cơ sở dữ liệu đồ thị (Graph RAG) chứa thông tin của các văn bản pháp luật và các liên kết (như thay thế, căn cứ, hợp nhất) giữa chúng.

Ngữ cảnh:
{context}

Dựa vào ngữ cảnh trên, hãy trả lời câu hỏi sau. Nếu ngữ cảnh không có thông tin để trả lời, hãy nói "Tôi không tìm thấy thông tin trong ngữ cảnh được cung cấp" và không tự suy đoán.
Câu hỏi: {question}
"""
    response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    return response.text

def main():
    print("Khởi tạo mô hình Embedding (Pytorch CPU)...")
    model = SentenceTransformer(MODEL_NAME, device='cpu')
    
    print("Kết nối Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        setup_vector_index(driver)
        
        with open("qa_comparison.md", "w", encoding="utf-8") as f:
            f.write("# Đánh giá So sánh RAG Đa bước (Multi-hop Graph RAG)\n\n")
            
            for i, q in enumerate(questions):
                print(f"\nĐang xử lý câu hỏi {i+1}...")
                f.write(f"## Câu hỏi {i+1}: {q}\n\n")
                
                # Embedding question
                q_emb = model.encode([q], show_progress_bar=False)[0].tolist()
                
                for hops in [0, 1, 2]:
                    print(f"  - Đang truy vấn với Hops = {hops}")
                    context = search_graph_rag(driver, q_emb, hops, top_k=3)
                    
                    answer = generate_answer(q, context)
                    
                    f.write(f"### Cấu hình: {hops} bước nhảy (Hops)\n")
                    f.write(f"**Ngữ cảnh truy xuất được:**\n```text\n{context}\n```\n\n")
                    f.write(f"**Trả lời:**\n{answer}\n\n")
                    
        print("\nĐã hoàn thành! Kết quả được lưu tại 'qa_comparison.md'.")
        
    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    main()
