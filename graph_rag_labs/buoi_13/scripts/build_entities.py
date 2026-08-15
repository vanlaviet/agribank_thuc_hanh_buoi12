import pandas as pd
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

data_dir = 'data'
out_dir = 'outputs'
os.makedirs(out_dir, exist_ok=True)

# 1. Đọc dữ liệu
rp_df = pd.read_csv(os.path.join(data_dir, 'risk_profiles_seed.csv'))
ctrl_df = pd.read_csv(os.path.join(data_dir, 'controls_seed.csv'))
ev_df = pd.read_csv(os.path.join(data_dir, 'risk_events_seed.csv'))
rel_df = pd.read_csv(os.path.join(data_dir, 'relationships_seed.csv'))

# 3. Mapping Type & Source file
rp_df['type'] = 'RuiRo'
rp_df['source_file'] = 'risk_profiles_seed.csv'

ctrl_df['type'] = 'KiemSoat'
ctrl_df['source_file'] = 'controls_seed.csv'

ev_df['type'] = 'SuKienRuiRo'
ev_df['source_file'] = 'risk_events_seed.csv'

# risk_events_seed.csv không có cột 'name', bổ sung để đáp ứng schema tối thiểu
if 'name' not in ev_df.columns:
    ev_df['name'] = 'Sự kiện ' + ev_df['id']

# 4. Gộp dữ liệu
entities_df = pd.concat([rp_df, ctrl_df, ev_df], ignore_index=True)

# Đảm bảo các cột tối thiểu
required_cols = ['id', 'type', 'name', 'description', 'source_file', 'data_origin', 'verification_status']
for col in required_cols:
    if col not in entities_df.columns:
        entities_df[col] = None

# Sắp xếp cột: cột required trước, cột nghiệp vụ sau
other_cols = [c for c in entities_df.columns if c not in required_cols]
final_cols = required_cols + other_cols
entities_df = entities_df[final_cols]

# Xuất ra entities.csv
entities_csv_path = os.path.join(out_dir, 'entities.csv')
entities_df.to_csv(entities_csv_path, index=False)

# 5. Xuất relations.csv
# Phải giữ tối thiểu các cột
rel_required_cols = ['source_id', 'relationship_type', 'target_id', 'source', 'evidence_quote', 'confidence', 'verification_status', 'data_origin']
for col in rel_required_cols:
    if col not in rel_df.columns:
        rel_df[col] = None

relations_csv_path = os.path.join(out_dir, 'relations.csv')
rel_df.to_csv(relations_csv_path, index=False)

# 6. Kiểm tra orphan references
valid_ids = set(entities_df['id'])
missing_sources = set(rel_df['source_id']) - valid_ids
missing_targets = set(rel_df['target_id']) - valid_ids

# Báo cáo
print("="*50)
print("BÁO CÁO KẾT QUẢ CHUẨN HÓA DỮ LIỆU")
print("="*50)

print("\n--- SỐ LƯỢNG ENTITY THEO TYPE ---")
type_counts = entities_df['type'].value_counts()
for t, count in type_counts.items():
    print(f"Type '{t}': {count} nodes")

print("\n--- SỐ LƯỢNG RELATION THEO LOẠI ---")
rel_counts = rel_df['relationship_type'].value_counts()
for r, count in rel_counts.items():
    print(f"Relationship '{r}': {count} edges")

print("\n--- KIỂM TRA ORPHAN REFERENCES ---")
has_error = False
if missing_sources:
    print(f"LỖI: Có source_id không tồn tại trong entities.csv: {missing_sources}")
    has_error = True
if missing_targets:
    print(f"LỖI: Có target_id không tồn tại trong entities.csv: {missing_targets}")
    has_error = True

if not has_error:
    print("THÀNH CÔNG: Tất cả source_id và target_id đều tồn tại trong entities.csv.")

print("\n--- CÁC FILE ĐÃ XUẤT ---")
print(f" - {entities_csv_path} (Tổng: {len(entities_df)} dòng)")
print(f" - {relations_csv_path} (Tổng: {len(rel_df)} dòng)")
print("="*50)
