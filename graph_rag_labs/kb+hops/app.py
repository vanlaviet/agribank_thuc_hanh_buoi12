import streamlit as st
import os
from google import genai
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

# ==========================================
# Cấu hình UI
# ==========================================
st.set_page_config(page_title="Graph RAG QA", page_icon="⚖️", layout="wide")

st.title("⚖️ Hỏi đáp Pháp luật với Multi-hop Graph RAG")
st.markdown("Hệ thống kết hợp biểu đồ tri thức (Neo4j) và mô hình ngôn ngữ lớn (Gemini) để trả lời các câu hỏi pháp lý dựa trên nhiều văn bản liên quan.")

# ==========================================
# Tải Model Embedding (Cache để tránh tải lại)
# ==========================================
@st.cache_resource
def load_embedding_model():
    return SentenceTransformer("thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5", device='cpu')

try:
    with st.spinner("Đang tải mô hình Embedding..."):
        embedding_model = load_embedding_model()
except Exception as e:
    st.error(f"Lỗi tải mô hình: {e}")

# ==========================================
# Sidebar Cấu hình
# ==========================================
st.sidebar.header("⚙️ Cấu hình Hệ thống")

gemini_api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Lấy API Key từ Google AI Studio")

available_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
if gemini_api_key:
    try:
        client = genai.Client(api_key=gemini_api_key)
        models = client.models.list()
        # The new SDK model object structure might differ, let's just show standard models and allow typing or dynamically mapping it.
        # Since the new SDK might not have supported_generation_methods exposed the same way, we'll gracefully fallback.
        available_models = [m.name.replace("models/", "") for m in models if "gemini" in m.name.lower()]
        if not available_models:
            available_models = ["gemini-1.5-flash"]
    except Exception as e:
        st.sidebar.error(f"Lỗi xác thực API Key: {e}")

model_choice = st.sidebar.selectbox("Model Gemini", available_models, index=0)

st.sidebar.markdown("---")
num_hops = st.sidebar.slider("Số bước nhảy (Hops)", min_value=0, max_value=3, value=1, help="Số lượng văn bản liên quan sẽ mở rộng trong đồ thị.")

st.sidebar.markdown("---")
with st.sidebar.expander("Cấu hình Neo4j"):
    neo4j_uri = st.text_input("URI", value="neo4j://127.0.0.1:7687")
    neo4j_user = st.text_input("Username", value="neo4j")
    neo4j_pass = st.text_input("Password", type="password", value="abcd1234")

# ==========================================
# Hàm Truy vấn Đồ thị
# ==========================================
def search_graph_rag(driver, embedding, hops, top_k=3):
    with driver.session() as session:
        if hops == 0:
            query = """
            CALL db.index.vector.queryNodes('chunk_embedding', $top_k, $embedding)
            YIELD node AS chunk, score
            MATCH (chunk)-[:PART_OF]->(d:Document)
            RETURN chunk.text AS text, d.so_ky_hieu AS so_ky_hieu, d.title AS title, score,
                   [] AS related_docs
            """
        else:
            query = f"""
            CALL db.index.vector.queryNodes('chunk_embedding', $top_k, $embedding)
            YIELD node AS chunk, score
            MATCH (chunk)-[:PART_OF]->(d:Document)
            OPTIONAL MATCH p = (d)-[*1..{hops}]-(related_doc:Document)
            RETURN chunk.text AS text, d.so_ky_hieu AS so_ky_hieu, d.title AS title, score,
                   collect(distinct related_doc.so_ky_hieu + " - " + related_doc.title) AS related_docs
            """
            
        result = session.run(query, top_k=top_k, embedding=embedding)
        
        contexts = []
        for record in result:
            context = f"Văn bản: {record['so_ky_hieu']} - {record['title']}\n"
            context += f"Nội dung trích xuất: {record['text']}\n"
            if record['related_docs']:
                context += f"Các văn bản liên quan (trong vòng {hops} bước nhảy): " + ", ".join(record['related_docs']) + "\n"
            contexts.append(context)
            
        return "\n---\n".join(contexts)

# ==========================================
# Main Chat
# ==========================================
question = st.chat_input("Nhập câu hỏi pháp lý của bạn...")

if question:
    st.chat_message("user").write(question)
    
    with st.chat_message("assistant"):
        context = ""
        try:
            # 1. Connect Neo4j
            with st.spinner("Đang kết nối Neo4j..."):
                driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pass))
                driver.verify_connectivity()
            
            # 2. Embedding
            with st.spinner("Đang nhúng câu hỏi (Embedding)..."):
                q_emb = embedding_model.encode([question], show_progress_bar=False)[0].tolist()
            
            # 3. Truy vấn Graph RAG
            with st.spinner(f"Đang duyệt đồ thị (Hops = {num_hops})..."):
                context = search_graph_rag(driver, q_emb, num_hops)
                driver.close()
                
            # Hiển thị context
            with st.expander("🔍 Xem chi tiết Ngữ cảnh truy xuất được"):
                if context.strip():
                    st.text(context)
                else:
                    st.warning("Không tìm thấy ngữ cảnh phù hợp.")
            
            # 4. LLM Generation
            if not gemini_api_key:
                st.warning("⚠️ Bạn chưa nhập **Gemini API Key** ở thanh bên. Hệ thống chỉ hiển thị ngữ cảnh trích xuất.")
            else:
                with st.spinner("Đang gọi Gemini AI..."):
                    client = genai.Client(api_key=gemini_api_key)
                    prompt = f"""Bạn là một trợ lý ảo am hiểu pháp luật Việt Nam. Dưới đây là ngữ cảnh trích xuất từ cơ sở dữ liệu đồ thị (Graph RAG).
Ngữ cảnh:\n{context}\n
Dựa vào ngữ cảnh trên, hãy trả lời câu hỏi sau. Nếu ngữ cảnh không có thông tin, hãy nói "Tôi không tìm thấy thông tin".
Câu hỏi: {question}"""
                    response = client.models.generate_content(model=model_choice, contents=prompt)
                    st.markdown(response.text)
                    
        except Exception as e:
            st.error(f"Có lỗi xảy ra: {e}")
