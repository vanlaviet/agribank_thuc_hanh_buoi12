import streamlit as st
import pandas as pd
import os
import sys
from neo4j import GraphDatabase

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.bm25_retriever import BM25Retriever
from src.dense_retriever import DenseRetriever
from src.hybrid_retriever import HybridRetriever
from src.reranker import Reranker

st.set_page_config(
    page_title="RAG Hybrid Search — Buổi 14", 
    page_icon="🔍",
    layout="wide"
)

corpus_path = 'data/processed/chunks_normalized.csv'

@st.cache_resource(show_spinner="Đang tải các mô hình (chỉ chạy lần đầu)...")
def load_retrievers():
    return {
        'bm25': BM25Retriever(corpus_path),
        'dense': DenseRetriever(corpus_path),
        'hybrid': HybridRetriever(corpus_path),
        'reranker': Reranker()
    }

retrievers = load_retrievers()

def get_graph_hints(doc_ids, chunk_ids):
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    
    uri = os.environ.get("NEO4J_URI", "neo4j://127.0.0.1:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "abcd1234")
    database = os.environ.get("NEO4J_DATABASE", "kb-hops")

    hints = []
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
    except Exception:
        return ["*Neo4j chưa sẵn sàng hoặc không thể kết nối.*"]

    with driver.session(database=database) as session:
        if doc_ids:
            doc_query = """
            MATCH (v1:VanBan)-[r]->(v2:VanBan)
            WHERE v1.id IN $doc_ids AND v1.lab_session = 'buoi_14' AND v2.lab_session = 'buoi_14'
            RETURN v1.id AS source, type(r) AS rel, v2.id AS target
            LIMIT 10
            """
            doc_rels = session.run(doc_query, doc_ids=list(doc_ids)).data()
            if doc_rels:
                hints.append("**Document Relationships (Neo4j):**")
                for row in doc_rels:
                    hints.append(f"- `[{row['source']}] --{row['rel']}--> [{row['target']}]`")
            
        if chunk_ids:
            chunk_query = """
            MATCH (d1:DieuKhoan)-[r:NEXT]->(d2:DieuKhoan)
            WHERE d1.id IN $chunk_ids AND d1.lab_session = 'buoi_14' AND d2.lab_session = 'buoi_14'
            RETURN d1.id AS source, type(r) AS rel, d2.id AS target
            LIMIT 10
            """
            chunk_rels = session.run(chunk_query, chunk_ids=list(chunk_ids)).data()
            if chunk_rels:
                hints.append("**Chunk Context (Neo4j NEXT):**")
                for row in chunk_rels:
                    hints.append(f"- `[{row['source']}] --{row['rel']}--> [{row['target']}]`")
                    
    if not hints:
        hints.append("Không tìm thấy direct relations nào trong Neo4j cho các Node này.")
        
    return hints

# ================= SIDEBAR =================
with st.sidebar:
    st.markdown("### ⚙️ Cấu Hình Tìm Kiếm")
    method = st.radio(
        "Phương thức Retrieval (Method):", 
        ["BM25", "Dense", "Hybrid", "Hybrid + Rerank"],
        index=3
    )
    
    st.markdown("---")
    top_k = st.slider("Số lượng kết quả (Top-K):", min_value=1, max_value=20, value=5, step=1)
    candidate_k = st.slider("Candidate Pool (Candidate-K):", min_value=10, max_value=100, value=20, step=5)
    
    st.markdown("---")
    st.markdown("### 💡 Mẫu Câu Hỏi Gợi Ý")
    
    sample_questions = [
        "-- Tùy nhập --",
        "Quy định niêm phong tiền mặt theo Điều 5 Thông tư 01/2014/TT-NHNN",
        "Trách nhiệm của các bộ và cơ quan ngang bộ là gì?",
        "Ai được quyền phê duyệt khoản vay?",
        "Điều 111 của Nghị định 73/2016/NĐ-CP quy định gì?",
        "Việc đóng gói niêm phong kiểm đếm giao nhận vàng kim khí quý đá quý"
    ]
    selected_sample = st.selectbox("Chọn câu hỏi mẫu:", sample_questions)


# ================= MAIN AREA =================
st.title("🔍 RAG Hybrid Search — Buổi 14")
st.markdown("<p style='color: gray; font-size: 1.1em;'>Hệ thống Tìm kiếm Lai (Hybrid Lexical - Dense) kết hợp Neural Cross-Encoder Reranking & Knowledge Graph Hints</p>", unsafe_allow_html=True)
st.markdown("---")

# Determine default query text
default_query = ""
if selected_sample != "-- Tùy nhập --":
    default_query = selected_sample

query = st.text_input("🔑 Câu hỏi truy vấn:", value=default_query)

search_pressed = st.button("🔍 Tìm kiếm", type="primary")

if search_pressed:
    if not query.strip():
        st.warning("Vui lòng nhập câu hỏi để tìm kiếm.")
    else:
        results = []
        hybrid_cands = []
        
        with st.spinner("Đang tìm kiếm..."):
            if method == "BM25":
                results = retrievers['bm25'].retrieve(query, top_k=top_k)
                for r in results: 
                    r['retrieval_method'] = 'BM25'
                    r['score'] = r.get('retrieval_score', 0)
            elif method == "Dense":
                results = retrievers['dense'].retrieve(query, top_k=top_k)
                for r in results: 
                    r['retrieval_method'] = 'Dense'
                    r['score'] = r.get('retrieval_score', 0)
            elif method == "Hybrid":
                results = retrievers['hybrid'].retrieve(query, candidate_k=candidate_k, top_k=top_k)
                for r in results: 
                    r['retrieval_method'] = 'Hybrid'
                    r['score'] = r.get('rrf_score', 0)
            elif method == "Hybrid + Rerank":
                hybrid_cands = retrievers['hybrid'].retrieve(query, candidate_k=candidate_k, top_k=candidate_k)
                results = retrievers['reranker'].rerank(query, hybrid_cands, top_k=top_k)
                for r in results:
                    r['retrieval_method'] = 'Hybrid + Rerank'
                    r['score'] = r.get('rerank_score', 0)
        
        st.markdown("---")
        st.subheader(f"📋 Kết Quả Retrieval ({method} | Top-{top_k})")
        
        # Bảng so sánh cho Hybrid + Rerank
        if method == "Hybrid + Rerank":
            st.markdown("### 🔄 BẢNG SO SÁNH THỨ HẠNG (BEFORE / AFTER RERANK)")
            
            # Prepare data for DataFrame
            df_data = []
            
            # Map original candidate ranks
            cand_map = {c['chunk_id']: {"rank": idx + 1, "rrf": c.get('rrf_score', 0)} for idx, c in enumerate(hybrid_cands)}
            
            for i, r in enumerate(results):
                chunk_id = r['chunk_id']
                orig_info = cand_map.get(chunk_id, {"rank": "?", "rrf": 0})
                
                df_data.append({
                    "Final Rank (AFTER)": f"🥇 Rank {i+1}" if i==0 else f"🥈 Rank {i+1}" if i==1 else f"🥉 Rank {i+1}" if i==2 else f"🏅 Rank {i+1}",
                    "Hybrid Rank (BEFORE)": f"Rank {orig_info['rank']}",
                    "Rerank Score": f"{r.get('rerank_score', 0):.4f}",
                    "Hybrid RRF Score": f"{orig_info['rrf']:.6f}",
                    "Chunk ID": chunk_id,
                    "Citation": r['citation']
                })
            
            st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)
            st.markdown("<br>", unsafe_allow_html=True)
        
        chunk_ids = set()
        doc_ids = set()
        
        for i, res in enumerate(results, 1):
            chunk_ids.add(res['chunk_id'])
            doc_ids.add(res['document_id'])
            
            score_val = res['score']
            expander_title = f"> **Rank {i}** | {res['chunk_id']} *(Score: {score_val:.4f})*"
            
            with st.expander(expander_title, expanded=False):
                st.markdown(f"**Document ID:** `{res['document_id']}`")
                
                if method in ["Hybrid", "Hybrid + Rerank"] and 'bm25_rank' in res:
                    st.markdown(f"**Hybrid Info:** BM25 Rank: `{res.get('bm25_rank', 'N/A')}` | Dense Rank: `{res.get('dense_rank', 'N/A')}`")
                
                st.markdown(f"**Citation:** {res['citation']}")
                st.markdown("**Text Content:**")
                st.info(res['text'])

        # Graph hints
        st.markdown("---")
        st.subheader("🌐 GRAPH HINTS")
        hints = get_graph_hints(doc_ids, chunk_ids)
        for h in hints:
            st.markdown(h)
