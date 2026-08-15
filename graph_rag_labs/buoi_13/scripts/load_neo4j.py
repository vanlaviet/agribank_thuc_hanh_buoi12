import os
import sys
import pandas as pd
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

# Load biến môi trường từ .env
load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

ENTITIES_PATH = 'outputs/entities.csv'
RELATIONS_PATH = 'outputs/relations.csv'

def load_data(driver):
    if not os.path.exists(ENTITIES_PATH) or not os.path.exists(RELATIONS_PATH):
        print(f"Lỗi: Không tìm thấy {ENTITIES_PATH} hoặc {RELATIONS_PATH}")
        return

    entities_df = pd.read_csv(ENTITIES_PATH).astype(str).replace(['nan', 'NaN'], '')
    relations_df = pd.read_csv(RELATIONS_PATH).astype(str).replace(['nan', 'NaN'], '')

    # Chuẩn bị truy vấn tạo node (dùng MERGE để không trùng lặp)
    query_ruiro = """
    UNWIND $rows AS row
    MERGE (n:RuiRo {id: row.id})
    SET n.name = row.name,
        n.description = row.description,
        n.category = row.category,
        n.cause = row.cause,
        n.event = row.event,
        n.impact = row.impact,
        n.inherent_level = row.inherent_level,
        n.residual_level = row.residual_level,
        n.owner_unit_id = row.owner_unit_id,
        n.verification_status = row.verification_status,
        n.data_origin = row.data_origin
    """
    
    query_kiemsoat = """
    UNWIND $rows AS row
    MERGE (n:KiemSoat {id: row.id})
    SET n.name = row.name,
        n.description = row.description,
        n.control_type = row.control_type,
        n.frequency = row.frequency,
        n.owner_role_id = row.owner_role_id,
        n.effectiveness = row.effectiveness,
        n.verification_status = row.verification_status,
        n.data_origin = row.data_origin
    """
    
    query_sukien = """
    UNWIND $rows AS row
    MERGE (n:SuKienRuiRo {id: row.id})
    SET n.name = row.name,
        n.description = row.description,
        n.occurred_at = row.occurred_at,
        n.discovered_at = row.discovered_at,
        n.severity = row.severity,
        n.loss_amount_vnd = row.loss_amount_vnd,
        n.verification_status = row.verification_status,
        n.data_origin = row.data_origin
    """
    
    # Tạo relations (dùng MERGE để không trùng lặp quan hệ)
    query_rel_mitigates = """
    UNWIND $rows AS row
    MATCH (source:KiemSoat {id: row.source_id})
    MATCH (target:RuiRo {id: row.target_id})
    MERGE (source)-[r:MITIGATES]->(target)
    SET r.evidence_quote = row.evidence_quote,
        r.confidence = row.confidence,
        r.verification_status = row.verification_status,
        r.data_origin = row.data_origin
    """
    
    query_rel_observed = """
    UNWIND $rows AS row
    MATCH (source:RuiRo {id: row.source_id})
    MATCH (target:SuKienRuiRo {id: row.target_id})
    MERGE (source)-[r:OBSERVED_AS]->(target)
    SET r.evidence_quote = row.evidence_quote,
        r.confidence = row.confidence,
        r.verification_status = row.verification_status,
        r.data_origin = row.data_origin
    """

    ruiro_data = entities_df[entities_df['type'] == 'RuiRo'].to_dict('records')
    kiemsoat_data = entities_df[entities_df['type'] == 'KiemSoat'].to_dict('records')
    sukien_data = entities_df[entities_df['type'] == 'SuKienRuiRo'].to_dict('records')
    
    mitigates_data = relations_df[relations_df['relationship_type'] == 'MITIGATES'].to_dict('records')
    observed_data = relations_df[relations_df['relationship_type'] == 'OBSERVED_AS'].to_dict('records')

    try:
        # Nếu database là default (neo4j) có thể truyền thẳng driver.session() nếu version neo4j driver cũ
        with driver.session(database=DATABASE) as session:
            # 1. Load schema constraint (chạy file schema.cypher hoặc trực tiếp ở đây)
            # (Người dùng có thể chạy schema.cypher thủ công, nhưng ở đây có thể tự động luôn)
            pass 
        
        with driver.session(database=DATABASE) as session:
            print(f"Đang nạp {len(ruiro_data)} nodes RuiRo...")
            session.run(query_ruiro, rows=ruiro_data)
            
            print(f"Đang nạp {len(kiemsoat_data)} nodes KiemSoat...")
            session.run(query_kiemsoat, rows=kiemsoat_data)
            
            print(f"Đang nạp {len(sukien_data)} nodes SuKienRuiRo...")
            session.run(query_sukien, rows=sukien_data)
            
            print(f"Đang nạp {len(mitigates_data)} edges MITIGATES...")
            session.run(query_rel_mitigates, rows=mitigates_data)
            
            print(f"Đang nạp {len(observed_data)} edges OBSERVED_AS...")
            session.run(query_rel_observed, rows=observed_data)
            
        print("HOÀN TẤT: Tải dữ liệu lên Neo4j thành công!")
    except Exception as e:
        print(f"Lỗi khi thực thi truy vấn nạp dữ liệu: {e}")

if __name__ == "__main__":
    try:
        driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
        # Kiểm tra kết nối trước khi tiếp tục
        driver.verify_connectivity()
        print(f"Đã kết nối thành công tới Neo4j tại {URI}")
        load_data(driver)
        driver.close()
    except ServiceUnavailable:
        print("="*50)
        print("LỖI KẾT NỐI NEO4J (ServiceUnavailable)")
        print("="*50)
        print(f"Không thể kết nối đến cơ sở dữ liệu Neo4j tại: {URI}.")
        print("Neo4j có thể chưa được bật. Vui lòng kiểm tra:")
        print("1. Neo4j Desktop hoặc Docker đã được khởi động chưa?")
        print("2. Thông tin kết nối trong file .env có chính xác không?")
        print("\n=> Không cần lo lắng, các bước trước đó (Obsidian Wiki) KHÔNG BỊ ẢNH HƯỞNG.")
    except AuthError:
        print("="*50)
        print("LỖI XÁC THỰC NEO4J (AuthError)")
        print("="*50)
        print("Thông tin User hoặc Password không chính xác.")
        print("Vui lòng cập nhật NEO4J_USER và NEO4J_PASSWORD trong file .env.")
    except Exception as e:
        print(f"Đã xảy ra lỗi không xác định: {e}")
