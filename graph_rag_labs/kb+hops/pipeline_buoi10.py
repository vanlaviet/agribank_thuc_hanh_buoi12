import os
import pandas as pd
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase

# ==========================================
# Cấu hình
# ==========================================
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "abcd1234" # ĐỔI MẬT KHẨU NÀY NẾU CẦN

# Mô hình Embedding tiếng Việt (dùng CPU)
MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"

# ==========================================
# Bước 1 & 2: Phân tách HTML và nhúng vector
# ==========================================
def parse_html_to_chunks(html_content, doc_id):
    """Làm sạch HTML và chia đoạn phân cấp (Chunking)"""
    soup = BeautifulSoup(html_content, 'html.parser')
    chunks = []
    
    current_chuong = None
    current_muc = None
    current_dieu = None
    
    seq_id = 0
    # Lấy các thẻ p và table theo thứ tự xuất hiện
    for element in soup.find_all(['p', 'table']):
        text = element.get_text(separator=' ', strip=True)
        if not text: 
            continue
            
        level = "Đoạn văn"
        parent_id = str(doc_id)
        
        if element.name == 'p':
            # Tìm thẻ b/strong để xác định tiêu đề
            bold_text = " ".join([b.get_text(strip=True) for b in element.find_all(['b', 'strong', 'span'])])
            if not bold_text:
                bold_text = text
                
            upper_text = bold_text.upper().strip()
            
            if upper_text.startswith('CHƯƠNG'):
                level = "Chương"
                parent_id = str(doc_id)
            elif upper_text.startswith('MỤC'):
                level = "Mục"
                parent_id = current_chuong if current_chuong else str(doc_id)
            elif upper_text.startswith('ĐIỀU'):
                level = "Điều"
                parent_id = current_muc if current_muc else (current_chuong if current_chuong else str(doc_id))
            else:
                level = "Đoạn văn"
                parent_id = current_dieu if current_dieu else (current_muc if current_muc else (current_chuong if current_chuong else str(doc_id)))
        elif element.name == 'table':
            level = "Bảng biểu"
            parent_id = current_dieu if current_dieu else (current_muc if current_muc else (current_chuong if current_chuong else str(doc_id)))
            
        chunk_id = f"{doc_id}_{seq_id}"
        
        chunks.append({
            'chunk_id': chunk_id,
            'doc_id': str(doc_id),
            'text': text,
            'level': level,
            'parent_id': parent_id,
            'seq_id': seq_id
        })
        
        # Cập nhật ID cha hiện tại
        if level == "Chương": current_chuong = chunk_id
        elif level == "Mục": current_muc = chunk_id
        elif level == "Điều": current_dieu = chunk_id
        
        seq_id += 1
        
    return chunks

# ==========================================
# Bước 4: Nạp dữ liệu vào Neo4j
# ==========================================
def setup_database(driver):
    """Tạo constraints"""
    with driver.session() as session:
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE")
        # Xóa dữ liệu cũ nếu chạy lại
        session.run("MATCH (n) DETACH DELETE n")

def load_data_to_neo4j(driver, df_meta, df_content, df_rel, model):
    with driver.session() as session:
        # Nạp Document Metadata
        print("Nạp Metadata (Documents)...")
        for _, row in df_meta.iterrows():
            session.run("""
                MERGE (d:Document {id: $id})
                SET d.title = $title,
                    d.so_ky_hieu = $so_ky_hieu,
                    d.ngay_ban_hanh = $ngay_ban_hanh,
                    d.loai_van_ban = $loai_van_ban
            """, 
            id=str(row['id']),
            title=str(row['title']) if pd.notna(row['title']) else "",
            so_ky_hieu=str(row['so_ky_hieu']) if pd.notna(row['so_ky_hieu']) else "",
            ngay_ban_hanh=str(row['ngay_ban_hanh']) if pd.notna(row['ngay_ban_hanh']) else "",
            loai_van_ban=str(row['loai_van_ban']) if pd.notna(row['loai_van_ban']) else ""
            )
            
        # Nạp Chunk & Embeddings
        print("Phân tách HTML và nạp Chunks...")
        first_doc_chunks = []
        
        for _, row in df_content.iterrows():
            doc_id = row['id']
            html_content = row['content_html']
            if pd.isna(html_content): continue
            
            chunks = parse_html_to_chunks(html_content, doc_id)
            if not first_doc_chunks:
                first_doc_chunks = chunks[:5] # Lưu lại để in mẫu
                
            # Tạo Embeddings
            texts = [c['text'] for c in chunks]
            if not texts: continue
            embeddings = model.encode(texts, show_progress_bar=False)
            
            # Đẩy vào Neo4j
            for i, chunk in enumerate(chunks):
                chunk['embedding'] = embeddings[i].tolist()
                
                # Tạo Chunk node và quan hệ PART_OF document
                session.run("""
                    MATCH (d:Document {id: $doc_id})
                    MERGE (c:Chunk {id: $chunk_id})
                    SET c.text = $text,
                        c.level = $level,
                        c.seq_id = $seq_id,
                        c.embedding = $embedding
                    MERGE (c)-[:PART_OF]->(d)
                """, 
                doc_id=chunk['doc_id'],
                chunk_id=chunk['chunk_id'],
                text=chunk['text'],
                level=chunk['level'],
                seq_id=chunk['seq_id'],
                embedding=chunk['embedding']
                )
                
                # Quan hệ PARENT_OF
                # Nếu parent_id == doc_id, nó là top-level chunk, không cần PARENT_OF trỏ tới Document (đã có PART_OF)
                # Nhưng để truy vấn đồ thị rõ ràng, ta có thể tạo PARENT_OF từ Node Cha tới Node Con
                if chunk['parent_id'] != chunk['doc_id']:
                    session.run("""
                        MATCH (parent:Chunk {id: $parent_id})
                        MATCH (child:Chunk {id: $chunk_id})
                        MERGE (parent)-[:PARENT_OF]->(child)
                    """, parent_id=chunk['parent_id'], chunk_id=chunk['chunk_id'])
                else:
                    session.run("""
                        MATCH (parent:Document {id: $parent_id})
                        MATCH (child:Chunk {id: $chunk_id})
                        MERGE (parent)-[:PARENT_OF]->(child)
                    """, parent_id=chunk['parent_id'], chunk_id=chunk['chunk_id'])
                    
                # Quan hệ NEXT
                if i > 0:
                    prev_chunk_id = chunks[i-1]['chunk_id']
                    session.run("""
                        MATCH (prev:Chunk {id: $prev_id})
                        MATCH (curr:Chunk {id: $curr_id})
                        MERGE (prev)-[:NEXT]->(curr)
                    """, prev_id=prev_chunk_id, curr_id=chunk['chunk_id'])
                    
        # In mẫu chunking
        print("\n--- KẾT QUẢ PHÂN TÁCH MẪU (BƯỚC 1) ---")
        for c in first_doc_chunks:
            print(f"ID: {c['chunk_id']} | Level: {c['level']} | Parent: {c['parent_id']}")
            print(f"Text: {c['text'][:100]}...\n")
            
        # Nạp quan hệ Document
        print("Nạp các mối quan hệ văn bản...")
        for _, row in df_rel.iterrows():
            rel_type = str(row['relationship_type'])
            # Chỉ cho phép các ký tự hợp lệ trong Tên Quan Hệ
            if not rel_type.isalnum() and "_" not in rel_type: continue
            
            cypher = f"""
                MATCH (d1:Document {{id: $doc_id}})
                MATCH (d2:Document {{id: $other_doc_id}})
                MERGE (d1)-[:{rel_type}]->(d2)
            """
            session.run(cypher, doc_id=str(row['doc_id']), other_doc_id=str(row['other_doc_id']))

def main():
    print("Khởi tạo mô hình Embedding (Pytorch CPU)...")
    # Bước 2: Tải mô hình
    model = SentenceTransformer(MODEL_NAME, device='cpu')
    
    print("Đọc dữ liệu CSV...")
    df_meta = pd.read_csv('metadata.csv')
    df_content = pd.read_csv('content.csv')
    df_rel = pd.read_csv('relationships.csv')
    
    print("Kết nối Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        setup_database(driver)
        load_data_to_neo4j(driver, df_meta, df_content, df_rel, model)
        
        # Bước 5: Kiểm tra xác minh (Verification)
        print("\n--- XÁC MINH KẾT QUẢ (BƯỚC 5) ---")
        with driver.session() as session:
            doc_count = session.run("MATCH (d:Document) RETURN count(d)").single()[0]
            print(f"Số lượng nút Document: {doc_count} (Kỳ vọng: 15)")
            
            rel_count = session.run("MATCH (d1:Document)-[r]->(d2:Document) RETURN count(r)").single()[0]
            print(f"Số lượng quan hệ giữa các tài liệu Document: {rel_count} (Kỳ vọng: 8)")
            
            chunk_count = session.run("MATCH (c:Chunk) RETURN count(c)").single()[0]
            print(f"Số lượng nút Chunk: {chunk_count}")
            
    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")
    finally:
        driver.close()
        print("Hoàn thành!")

if __name__ == "__main__":
    main()
