import streamlit as st
import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.secure_retriever import SecureBM25Retriever, SecureDenseRetriever, SecureHybridRetriever, get_secure_graph_hints
from src.reranker import Reranker

st.set_page_config(
    page_title="RAG RBAC Security — Buổi 15", 
    page_icon="🛡️",
    layout="wide"
)

corpus_path = 'data/processed/chunks_secure.csv'

@st.cache_resource(show_spinner="Đang tải các mô hình (chỉ chạy lần đầu)...")
def load_retrievers():
    return {
        'bm25': SecureBM25Retriever(corpus_path),
        'dense': SecureDenseRetriever(corpus_path),
        'hybrid': SecureHybridRetriever(corpus_path),
        'reranker': Reranker()
    }

retrievers = load_retrievers()

# ================= SIDEBAR =================
with st.sidebar:
    st.markdown("### 🛡️ Phân quyền (RBAC)")
    user_roles = st.multiselect(
        "Vai trò của bạn (Your Roles):",
        ["Admin", "Staff", "Guest"],
        default=["Guest"]
    )
    
    st.markdown("---")
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
        "Quy định về kỷ luật nhân sự (Admin)",
        "Ai được quyền phê duyệt khoản vay? (Staff, Admin)",
        "Điều 111 của Nghị định 73/2016/NĐ-CP quy định gì? (All)",
        "Việc đóng gói niêm phong kiểm đếm giao nhận vàng kim khí quý đá quý (All)"
    ]
    selected_sample = st.selectbox("Chọn câu hỏi mẫu:", sample_questions)


# ================= MAIN AREA =================
st.title("🛡️ RAG Secure Search — Buổi 15")
st.markdown("<p style='color: gray; font-size: 1.1em;'>Hệ thống Tìm kiếm An toàn có tích hợp Role-Based Access Control (RBAC)</p>", unsafe_allow_html=True)
st.markdown("---")

default_query = ""
if selected_sample != "-- Tùy nhập --":
    default_query = selected_sample

query = st.text_input("🔑 Câu hỏi truy vấn:", value=default_query)

search_pressed = st.button("🔍 Tìm kiếm", type="primary")

if search_pressed:
    if not query.strip():
        st.warning("Vui lòng nhập câu hỏi để tìm kiếm.")
    elif not user_roles:
        st.error("❌ Bạn chưa chọn Vai trò nào! Vui lòng chọn ít nhất 1 vai trò ở thanh bên trái.")
    else:
        results = []
        hybrid_cands = []
        
        with st.spinner("Đang tìm kiếm..."):
            if method == "BM25":
                results = retrievers['bm25'].retrieve(query, user_roles=user_roles, top_k=top_k)
                for r in results: 
                    r['score'] = r.get('retrieval_score', 0)
            elif method == "Dense":
                results = retrievers['dense'].retrieve(query, user_roles=user_roles, top_k=top_k)
                for r in results: 
                    r['score'] = r.get('retrieval_score', 0)
            elif method == "Hybrid":
                results = retrievers['hybrid'].retrieve(query, user_roles=user_roles, candidate_k=candidate_k, top_k=top_k)
                for r in results: 
                    r['score'] = r.get('rrf_score', 0)
            elif method == "Hybrid + Rerank":
                hybrid_cands = retrievers['hybrid'].retrieve(query, user_roles=user_roles, candidate_k=candidate_k, top_k=candidate_k)
                if hybrid_cands:
                    results = retrievers['reranker'].rerank(query, hybrid_cands, top_k=top_k)
                    for r in results:
                        r['retrieval_method'] = 'Hybrid + Rerank'
                        r['score'] = r.get('rerank_score', 0)
        
        st.markdown("---")
        st.subheader(f"📋 Kết Quả Retrieval ({method} | Top-{top_k})")
        
        if not results:
            st.warning("⚠️ Không tìm thấy kết quả nào phù hợp, hoặc bạn không có đủ quyền để xem các tài liệu liên quan!")
        else:
            if method == "Hybrid + Rerank" and results:
                st.markdown("### 🔄 BẢNG SO SÁNH THỨ HẠNG (BEFORE / AFTER RERANK)")
                df_data = []
                cand_map = {c['chunk_id']: {"rank": idx + 1, "rrf": c.get('rrf_score', 0)} for idx, c in enumerate(hybrid_cands)}
                
                for i, r in enumerate(results):
                    chunk_id = r['chunk_id']
                    orig_info = cand_map.get(chunk_id, {"rank": "?", "rrf": 0})
                    
                    df_data.append({
                        "Final Rank (AFTER)": f"🥇 Rank {i+1}" if i==0 else f"🥈 Rank {i+1}" if i==1 else f"🥉 Rank {i+1}" if i==2 else f"🏅 Rank {i+1}",
                        "Hybrid Rank (BEFORE)": f"Rank {orig_info['rank']}",
                        "Rerank Score": f"{r.get('rerank_score', 0):.4f}",
                        "Allowed Roles": r.get('allowed_roles', ''),
                        "Chunk ID": chunk_id
                    })
                
                st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)
                st.markdown("<br>", unsafe_allow_html=True)
            
            chunk_ids = set()
            doc_ids = set()
            
            for i, res in enumerate(results, 1):
                chunk_ids.add(res['chunk_id'])
                doc_ids.add(res['document_id'])
                
                score_val = res['score']
                roles = res.get('allowed_roles', 'Unknown')
                expander_title = f"> **Rank {i}** | {res['chunk_id']} *(Score: {score_val:.4f})* | 🔐 Quyền xem: {roles}"
                
                with st.expander(expander_title, expanded=False):
                    st.markdown(f"**Document ID:** `{res['document_id']}`")
                    st.markdown(f"**Citation:** {res['citation']}")
                    st.markdown("**Text Content:**")
                    st.info(res['text'])

            # Graph hints
            st.markdown("---")
            st.subheader("🌐 GRAPH HINTS (SECURED)")
            hints = get_secure_graph_hints(doc_ids, chunk_ids, user_roles)
            for h in hints:
                st.markdown(h)
