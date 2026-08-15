import os
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

def step9():
    print("--- BƯỚC 9: Kiểm tra Knowledge Graph sau import ---")
    load_dotenv()
    
    uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")
    
    try:
        docs = pd.read_csv('cleaned_documents.csv')
        ents = pd.read_csv('entities.csv')
        rels = pd.read_csv('relationships.csv')
        
        expected_docs = len(docs)
        # Đếm số lượng entity độc nhất theo entity_id (Neo4j gộp theo ID này)
        unique_ents = ents.drop_duplicates(subset=['entity_id'])
        ent_counts = unique_ents['entity_type'].value_counts().to_dict()
        rel_counts = rels['relationship_type'].value_counts().to_dict()
        
    except Exception as e:
        print(f"[FAIL] Lỗi đọc CSV: {e}")
        return
        
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session(database=database) as session:
            # 1. node count theo label
            print("\n1. Node count theo label:")
            res_nodes = session.run("MATCH (n) RETURN labels(n) AS labels, count(*) AS total ORDER BY total DESC")
            actual_nodes = {}
            for rec in res_nodes:
                lbl = rec['labels'][0] if rec['labels'] else 'Unknown'
                actual_nodes[lbl] = rec['total']
                print(f"  - {lbl}: {rec['total']}")
                
            # 2. relationship count theo type
            print("\n2. Relationship count theo type:")
            res_rels = session.run("MATCH ()-[r]->() RETURN type(r) AS relationship_type, count(*) AS total ORDER BY total DESC")
            actual_rels = {}
            for rec in res_rels:
                rtype = rec['relationship_type']
                actual_rels[rtype] = rec['total']
                print(f"  - {rtype}: {rec['total']}")
                
            # 3. một số Document -> NguoiKy
            print("\n3. Mẫu Document -> NguoiKy (3 mẫu):")
            res_dk = session.run("MATCH (d:Document)-[r:KY_BOI]->(p:NguoiKy) RETURN d.id AS doc_id, p.canonical_name AS name LIMIT 3")
            for rec in res_dk:
                print(f"  - Doc {rec['doc_id']} ký bởi {rec['name']}")
                
            # 4. một số Document -> DoiTuongApDung
            print("\n4. Mẫu Document -> DoiTuongApDung (3 mẫu):")
            res_dt = session.run("MATCH (d:Document)-[r:AP_DUNG_CHO]->(o:DoiTuongApDung) RETURN d.id AS doc_id, o.canonical_name AS obj LIMIT 3")
            for rec in res_dt:
                print(f"  - Doc {rec['doc_id']} áp dụng cho {rec['obj']}")
                
            # 5. Document -> Document relations
            print("\n5. Mẫu Document -> Document relations (3 mẫu):")
            res_dd = session.run("MATCH (a:Document)-[r:THAM_CHIEU|SUA_DOI_BO_SUNG|THAY_THE_BOI]->(b:Document) RETURN a.id AS src, type(r) AS rel, b.id AS tgt LIMIT 3")
            for rec in res_dd:
                print(f"  - Doc {rec['src']} -[{rec['rel']}]-> Doc {rec['tgt']}")
                
        # Đối chiếu
        print("\n--- ĐỐI CHIẾU VỚI CSV ---")
        diff_found = False
        if actual_nodes.get('Document', 0) != expected_docs:
            print(f"Chênh lệch Document: Graph={actual_nodes.get('Document', 0)}, CSV={expected_docs}")
            diff_found = True
            
        for k, v in ent_counts.items():
            if actual_nodes.get(k, 0) != v:
                print(f"Chênh lệch {k}: Graph={actual_nodes.get(k, 0)}, CSV={v}")
                diff_found = True
                
        for k, v in rel_counts.items():
            if actual_rels.get(k, 0) != v:
                print(f"Chênh lệch {k}: Graph={actual_rels.get(k, 0)}, CSV={v}")
                diff_found = True
                
        if diff_found:
            print("Nguyên nhân có thể: Các node target của CSV không có trong node CSV (do data bẩn) nên đã bị loại khi import (ở bước 8 không load node lỗi), hoặc missing ID. Chưa tự xóa db.")
            print("\n[FAIL] Có sự chênh lệch bất thường.")
        else:
            print("Toàn bộ số liệu trên Graph khớp chính xác với dữ liệu CSV.")
            print("\n[PASS] BƯỚC 9 hoàn thành.")
            
    except Exception as e:
        print(f"\n[FAIL] Lỗi khi chạy query: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    step9()
