import pandas as pd
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

data_dir = 'data'
files = {
    'risk_profiles': 'risk_profiles_seed.csv',
    'controls': 'controls_seed.csv',
    'risk_events': 'risk_events_seed.csv',
    'relationships': 'relationships_seed.csv'
}

dfs = {}
for name, filename in files.items():
    path = os.path.join(data_dir, filename)
    dfs[name] = pd.read_csv(path)

print("="*50)
print("INSPECTING DATA")
print("="*50)

for name, df in dfs.items():
    print(f"\n--- {name.upper()} ---")
    print(f"File: {files[name]}")
    print(f"Số dòng: {len(df)}")
    print(f"Tên các cột: {list(df.columns)}")
    
    null_counts = df.isnull().sum()
    null_cols = null_counts[null_counts > 0]
    if len(null_cols) > 0:
        print(f"Số lượng null mỗi cột:\n{null_cols}")
    else:
        print("Số lượng null mỗi cột: 0")
        
    print(f"Số dòng duplicate toàn bộ: {df.duplicated().sum()}")

print("\n" + "="*50)
print("KHÓA CHÍNH (PRIMARY KEYS)")
print("="*50)
print("Giả định 'id' là khóa chính cho các file:")
for name in ['risk_profiles', 'controls', 'risk_events']:
    df = dfs[name]
    if 'id' in df.columns:
        is_unique = df['id'].is_unique
        print(f"{name} - Cột 'id' là duy nhất: {is_unique} (Số dòng duplicate id: {df['id'].duplicated().sum()})")

print("\n" + "="*50)
print("KHÓA THAM CHIẾU (FOREIGN KEYS) VÀ THIẾU THÔNG TIN (MISSING REFERENCES)")
print("="*50)

# Khóa tham chiếu trong risk_profiles: owner_unit_id
rp_df = dfs['risk_profiles']
if 'owner_unit_id' in rp_df.columns:
    print(f"risk_profiles có khóa tham chiếu owner_unit_id: {rp_df['owner_unit_id'].unique()}")

# Khóa tham chiếu trong controls: owner_role_id
ctrl_df = dfs['controls']
if 'owner_role_id' in ctrl_df.columns:
    print(f"controls có khóa tham chiếu owner_role_id: {ctrl_df['owner_role_id'].unique()}")

# Khóa tham chiếu trong risk_events: risk_id tham chiếu đến risk_profiles.id
events_df = dfs['risk_events']
if 'risk_id' in events_df.columns:
    missing_risk_ids = set(events_df['risk_id']) - set(rp_df['id'])
    print(f"risk_events có risk_id tham chiếu đến risk_profiles. Số lượng risk_id bị thiếu: {len(missing_risk_ids)}")
    if len(missing_risk_ids) > 0:
        print(f"Các risk_id bị thiếu: {missing_risk_ids}")

# Khóa tham chiếu trong relationships: source_id, target_id
rel_df = dfs['relationships']
print(f"\nCác loại relationship_type trong relationships_seed: {list(rel_df['relationship_type'].unique())}")

all_ids = set(rp_df['id']).union(set(ctrl_df['id'])).union(set(events_df['id']))

missing_source = set(rel_df['source_id']) - all_ids
missing_target = set(rel_df['target_id']) - all_ids

print(f"relationships source_id bị thiếu tham chiếu: {len(missing_source)}")
if len(missing_source) > 0:
    print(f"Các source_id bị thiếu: {missing_source}")

print(f"relationships target_id bị thiếu tham chiếu: {len(missing_target)}")
if len(missing_target) > 0:
    print(f"Các target_id bị thiếu: {missing_target}")

print("\n" + "="*50)
print("DONE")
print("="*50)
