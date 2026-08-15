import streamlit as st
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from google import genai

# Load config
load_dotenv(dotenv_path='../kb+hops/.env')
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_GENERATION_MODEL", "gemini-3.5-flash-lite")
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "abcd1234"
MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"

# Khởi tạo clients
@st.cache_resource
def get_models_and_db():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    embed_model = SentenceTransformer(MODEL_NAME, device='cpu')
    llm_client = genai.Client(api_key=GEMINI_API_KEY)
    return driver, embed_model, llm_client

driver, embed_model, llm_client = get_models_and_db()

def get_graph_rag_context(driver, question_embedding, limit=5):
    cypher_query = """
    CALL db.index.vector.queryNodes('chunk_embedding', $limit, $embedding)
    YIELD node AS chunk, score
    MATCH (chunk)-[:PART_OF]->(doc:Document)
    OPTIONAL MATCH (doc)-[r]->(other_doc:Document)
    RETURN chunk.text AS text, doc.so_ky_hieu AS so_ky_hieu, doc.title AS title, 
           score, type(r) AS rel_type, other_doc.so_ky_hieu AS linked_doc
    ORDER BY score DESC
    """
    contexts = []
    with driver.session(database=os.environ.get("NEO4J_DATABASE", "kb-hops")) as session:
        result = session.run(cypher_query, embedding=question_embedding.tolist(), limit=limit)
        for record in result:
            context_str = f"[Tài liệu: {record['so_ky_hieu']} - {record['title']}] (Độ tương đồng: {record['score']:.4f})\nTrích dẫn: {record['text']}"
            if record['rel_type'] and record['linked_doc']:
                context_str += f"\nLưu ý: Có quan hệ {record['rel_type']} với tài liệu {record['linked_doc']}"
            contexts.append(context_str)
    return contexts

def generate_answer(client, question, contexts):
    context_str = "\n\n".join(contexts)
    prompt = f"""
Bạn là trợ lý ảo AI chuyên về pháp luật và quy định ngân hàng.
Dựa vào ngữ cảnh (Context) sau đây lấy từ Đồ thị tri thức, hãy trả lời câu hỏi của người dùng.

Context:
{context_str}

Câu hỏi: {question}

Nếu trong ngữ cảnh không có thông tin để trả lời, hãy nói "Tôi không tìm thấy thông tin trong cơ sở dữ liệu để trả lời câu hỏi này."
"""
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )
    return response.text

st.set_page_config(page_title="Neo4j GraphRAG Legal Assistant", layout="wide")
st.title("🧠 Trợ lý Ảo Pháp lý GraphRAG")
st.markdown("Tra cứu văn bản pháp luật sử dụng Vector Search kết hợp Đồ thị Tri thức Neo4j và Gemini LLM.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Nhập câu hỏi pháp lý của bạn vào đây..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang nhúng câu hỏi & truy vấn Neo4j..."):
            question_embedding = embed_model.encode([prompt], show_progress_bar=False)[0]
            contexts = get_graph_rag_context(driver, question_embedding)
            
        if not contexts:
            st.warning("Không tìm thấy đoạn văn nào liên quan.")
            st.session_state.messages.append({"role": "assistant", "content": "Không tìm thấy thông tin phù hợp trong CSDL.", "contexts": []})
        else:
            with st.expander("📚 Ngữ cảnh tìm thấy từ Neo4j", expanded=False):
                for c in contexts:
                    st.markdown(c)
                    st.markdown("---")
                    
            with st.spinner("Đang gọi Gemini để tổng hợp câu trả lời..."):
                answer = generate_answer(llm_client, prompt, contexts)
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer, "contexts": contexts})
