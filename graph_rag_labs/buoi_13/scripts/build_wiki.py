import pandas as pd
import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

entities_path = 'outputs/entities.csv'
relations_path = 'outputs/relations.csv'

if not os.path.exists(entities_path) or not os.path.exists(relations_path):
    print("Không tìm thấy outputs/entities.csv hoặc outputs/relations.csv")
    sys.exit(1)

entities_df = pd.read_csv(entities_path)
relations_df = pd.read_csv(relations_path)
entities_df = entities_df.astype(str).replace(['nan', 'NaN'], '')
relations_df = relations_df.astype(str).replace(['nan', 'NaN'], '')

wiki_dir = 'wiki'
dirs = {
    'RuiRo': 'risks',
    'KiemSoat': 'controls',
    'SuKienRuiRo': 'events'
}

for d in dirs.values():
    os.makedirs(os.path.join(wiki_dir, d), exist_ok=True)

def safe_filename(name):
    s = str(name).strip()
    # Loại bỏ các ký tự không an toàn cho tên file hệ điều hành
    s = re.sub(r'[\\/*?:"<>|]', "", s)
    return s

# Map id to safe name and other properties
entity_dict = {}
for _, row in entities_df.iterrows():
    name = row['name']
    sname = safe_filename(name)
    entity_dict[row['id']] = {
        'row': row,
        'safe_name': sname,
        'filename': f"{sname}.md",
        'type': row['type'],
        'name': name
    }

# Map quan hệ (Relations)
source_to_targets = {}
target_to_sources = {}

for _, row in relations_df.iterrows():
    s = row['source_id']
    t = row['target_id']
    if s not in source_to_targets:
        source_to_targets[s] = []
    source_to_targets[s].append(row)
    
    if t not in target_to_sources:
        target_to_sources[t] = []
    target_to_sources[t].append(row)

wiki_link_count = 0

def format_relation(rel_row, target_id):
    global wiki_link_count
    if target_id not in entity_dict:
        return f"- Liên kết đến {target_id} (Không tìm thấy node)"
    
    t_name = entity_dict[target_id]['safe_name']
    wiki_link_count += 1
    rel_type = rel_row['relationship_type']
    quote = rel_row['evidence_quote']
    status = rel_row['verification_status']
    quote_str = f" - Evidence: {quote}" if quote else ""
    return f"- [[{t_name}]] ({rel_type}) [Status: {status}]{quote_str}"

pages_created = 0

for eid, edata in entity_dict.items():
    row = edata['row']
    etype = edata['type']
    fname = edata['filename']
    sub_dir = dirs.get(etype, 'other')
    fpath = os.path.join(wiki_dir, sub_dir, fname)
    
    lines = []
    lines.append("---")
    lines.append(f"id: {row['id']}")
    lines.append(f"type: {row['type']}")
    lines.append(f"verification_status: {row['verification_status']}")
    lines.append(f"data_origin: {row['data_origin']}")
    lines.append("---")
    lines.append(f"# {row['name']}")
    lines.append(f"\n**Mô tả:** {row['description']}\n")
    
    if etype == 'RuiRo':
        lines.append(f"- **Category:** {row.get('category', '')}")
        lines.append(f"- **Cause:** {row.get('cause', '')}")
        lines.append(f"- **Event:** {row.get('event', '')}")
        lines.append(f"- **Impact:** {row.get('impact', '')}")
        lines.append(f"- **Inherent Level:** {row.get('inherent_level', '')}")
        lines.append(f"- **Residual Level:** {row.get('residual_level', '')}")
        lines.append(f"- **Owner Unit ID:** {row.get('owner_unit_id', '')}")
        
        lines.append("\n## Kiểm soát liên quan")
        # Kiểm soát là source, RuiRo là target
        rels = target_to_sources.get(eid, [])
        for r in rels:
            if r['relationship_type'] == 'MITIGATES':
                lines.append(format_relation(r, r['source_id']))
                
        lines.append("\n## Sự kiện liên quan")
        # RuiRo là source, SuKienRuiRo là target
        rels = source_to_targets.get(eid, [])
        for r in rels:
            if r['relationship_type'] == 'OBSERVED_AS':
                lines.append(format_relation(r, r['target_id']))

    elif etype == 'KiemSoat':
        lines.append(f"- **Control Type:** {row.get('control_type', '')}")
        lines.append(f"- **Frequency:** {row.get('frequency', '')}")
        lines.append(f"- **Owner Role ID:** {row.get('owner_role_id', '')}")
        lines.append(f"- **Effectiveness:** {row.get('effectiveness', '')}")
        
        lines.append("\n## Rủi ro được giảm thiểu")
        rels = source_to_targets.get(eid, [])
        for r in rels:
            if r['relationship_type'] == 'MITIGATES':
                lines.append(format_relation(r, r['target_id']))
                
    elif etype == 'SuKienRuiRo':
        lines.append(f"- **Occurred At:** {row.get('occurred_at', '')}")
        lines.append(f"- **Discovered At:** {row.get('discovered_at', '')}")
        lines.append(f"- **Severity:** {row.get('severity', '')}")
        lines.append(f"- **Loss Amount (VND):** {row.get('loss_amount_vnd', '')}")
        
        lines.append("\n## Rủi ro liên quan")
        rels = target_to_sources.get(eid, [])
        for r in rels:
            if r['relationship_type'] == 'OBSERVED_AS':
                lines.append(format_relation(r, r['source_id']))
                
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    pages_created += 1

# Tạo Home.md
home_path = os.path.join(wiki_dir, 'Home.md')
home_lines = []
home_lines.append("# Wiki Risk Graph Home\n")
home_lines.append("## Thống kê")
home_lines.append(f"- Tổng số Node (Entities): {len(entity_dict)}")
home_lines.append(f"- Tổng số Edge (Relations): {len(relations_df)}")

home_lines.append("\n## Danh sách Rủi ro")
for eid, edata in entity_dict.items():
    if edata['type'] == 'RuiRo':
        home_lines.append(f"- [[{edata['safe_name']}]]")

home_lines.append("\n## Danh sách Kiểm soát")
for eid, edata in entity_dict.items():
    if edata['type'] == 'KiemSoat':
        home_lines.append(f"- [[{edata['safe_name']}]]")

home_lines.append("\n## Danh sách Sự kiện Rủi ro")
for eid, edata in entity_dict.items():
    if edata['type'] == 'SuKienRuiRo':
        home_lines.append(f"- [[{edata['safe_name']}]]")

with open(home_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(home_lines))
pages_created += 1

print("="*50)
print("BÁO CÁO SINH WIKI MARKDOWN")
print("="*50)
print(f"Số trang Wiki đã tạo: {pages_created}")
print(f"Số wikilink đã tạo (giữa các node): {wiki_link_count}")

print("\nVí dụ đường đi: KiemSoat -> RuiRo -> SuKienRuiRo")
path_found = False
for ctrl_id, ctrl_data in entity_dict.items():
    if ctrl_data['type'] == 'KiemSoat':
        mitigates_rels = source_to_targets.get(ctrl_id, [])
        for m_rel in mitigates_rels:
            if m_rel['relationship_type'] == 'MITIGATES':
                risk_id = m_rel['target_id']
                obs_rels = source_to_targets.get(risk_id, [])
                for o_rel in obs_rels:
                    if o_rel['relationship_type'] == 'OBSERVED_AS':
                        event_id = o_rel['target_id']
                        print(f"[{ctrl_data['name']}] \n  -> (MITIGATES) -> [{entity_dict[risk_id]['name']}] \n  -> (OBSERVED_AS) -> [{entity_dict[event_id]['name']}]")
                        path_found = True
                        break
            if path_found: break
    if path_found: break

if not path_found:
    print("Không tìm thấy đường đi hoàn chỉnh nào.")
    
print("="*50)
