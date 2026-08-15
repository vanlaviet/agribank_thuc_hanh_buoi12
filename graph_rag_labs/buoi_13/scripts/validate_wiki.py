import os
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import pandas as pd

wiki_dir = 'wiki'
entities_path = 'outputs/entities.csv'
relations_path = 'outputs/relations.csv'
report_path = 'outputs/wiki_validation_report.md'

# Đọc entities và relations
entities_df = pd.read_csv(entities_path).astype(str).replace(['nan', 'NaN'], '')
relations_df = pd.read_csv(relations_path).astype(str).replace(['nan', 'NaN'], '')

valid_ids = set(entities_df['id'])

# 4. Entity trùng ID
duplicate_ids = entities_df[entities_df.duplicated('id')]['id'].tolist()

# 6. Relation có source/target không tồn tại
missing_rel_sources = []
missing_rel_targets = []
for _, row in relations_df.iterrows():
    if row['source_id'] not in valid_ids:
        missing_rel_sources.append(row['source_id'])
    if row['target_id'] not in valid_ids:
        missing_rel_targets.append(row['target_id'])

md_files = []
for root, dirs, files in os.walk(wiki_dir):
    for file in files:
        if file.endswith('.md'):
            md_files.append(os.path.join(root, file))

total_md_files = len(md_files)
total_wikilinks = 0
broken_links = []
pages_with_ids = {} # filename (không đuôi .md) -> id

file_links = {}

for fpath in md_files:
    fname = os.path.basename(fpath).replace('.md', '')
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tìm ID trong frontmatter
    id_match = re.search(r'^id:\s*(.+)$', content, re.MULTILINE)
    if id_match:
        file_id = id_match.group(1).strip()
        pages_with_ids[fname] = file_id
        
    # Tìm các wikilinks [[target]]
    links = re.findall(r'\[\[(.*?)(?:\|.*?)?\]\]', content)
    file_links[fname] = links
    total_wikilinks += len(links)

# Tên các trang hợp lệ
valid_pages = set([os.path.basename(f).replace('.md', '') for f in md_files])

# 3. Broken wikilinks
for fname, links in file_links.items():
    for link in links:
        if link not in valid_pages:
            broken_links.append((fname, link))

# 9. Orphan pages
inbound_counts_no_home = {p: 0 for p in valid_pages}
for fname, links in file_links.items():
    if fname == 'Home': continue
    for link in links:
        if link in inbound_counts_no_home:
            inbound_counts_no_home[link] += 1

orphan_pages = []
for p in valid_pages:
    if p != 'Home' and inbound_counts_no_home[p] == 0 and len(file_links[p]) == 0:
        orphan_pages.append(p)

# 5. Trang có ID nhưng không tồn tại trong entities.csv
pages_not_in_entities = []
for fname, pid in pages_with_ids.items():
    if pid not in valid_ids:
        pages_not_in_entities.append((fname, pid))

# 7 & 8. Lỗi nghiệp vụ dữ liệu (RuiRo thiếu KiemSoat hoặc SuKien)
ruiro_ids = set(entities_df[entities_df['type'] == 'RuiRo']['id'])
ruiro_has_kiemsoat = set(relations_df[relations_df['relationship_type'] == 'MITIGATES']['target_id'])
ruiro_has_sukien = set(relations_df[relations_df['relationship_type'] == 'OBSERVED_AS']['source_id'])

missing_kiemsoat = ruiro_ids - ruiro_has_kiemsoat
missing_sukien = ruiro_ids - ruiro_has_sukien

report_lines = []
report_lines.append("# Báo cáo Kiểm tra Wiki Risk Graph")
report_lines.append("\n## 1 & 2. Thống kê chung")
report_lines.append(f"- Tổng số file Markdown: {total_md_files}")
report_lines.append(f"- Tổng số Wikilink: {total_wikilinks}")

report_lines.append("\n## Chi tiết Lỗi Kỹ Thuật (Code Bugs)")

report_lines.append(f"### 3. Broken Wikilinks (Trỏ tới trang không tồn tại)")
if broken_links:
    for src, tgt in broken_links:
        report_lines.append(f"- Trang `[[{src}]]` chứa liên kết gãy tới `[[{tgt}]]`")
else:
    report_lines.append("- (Không có lỗi)")

report_lines.append(f"\n### 4. Entity trùng ID (entities.csv)")
if duplicate_ids:
    report_lines.append(f"- Các ID bị trùng: {duplicate_ids}")
else:
    report_lines.append("- (Không có lỗi)")

report_lines.append(f"\n### 5. Trang có ID nhưng không có trong entities.csv")
if pages_not_in_entities:
    for fname, pid in pages_not_in_entities:
        report_lines.append(f"- Trang `{fname}.md` có ID `{pid}` không nằm trong CSV.")
else:
    report_lines.append("- (Không có lỗi)")

report_lines.append(f"\n### 6. Lỗi Relation (source/target mồ côi)")
if missing_rel_sources:
    report_lines.append(f"- Source ID không tồn tại: {missing_rel_sources}")
if missing_rel_targets:
    report_lines.append(f"- Target ID không tồn tại: {missing_rel_targets}")
if not missing_rel_sources and not missing_rel_targets:
    report_lines.append("- (Không có lỗi)")

report_lines.append(f"\n### 9. Orphan Pages (Trang hoàn toàn cô lập)")
if orphan_pages:
    report_lines.append(f"- Các trang không có link (ngoại trừ từ Home): {orphan_pages}")
else:
    report_lines.append("- (Không có lỗi)")

report_lines.append("\n## Chi tiết Lỗi Dữ Liệu Nghiệp Vụ (Data Missing)")
report_lines.append("> Lưu ý: Các lỗi dưới đây do dữ liệu seed ban đầu thiếu, không phải lỗi hệ thống.")

report_lines.append(f"\n### 7. Rủi ro không có KiemSoat (MITIGATES)")
if missing_kiemsoat:
    for r in missing_kiemsoat:
        report_lines.append(f"- Rủi ro ID: `{r}`")
else:
    report_lines.append("- (Tuyệt vời! Mọi rủi ro đều đã có kiểm soát)")

report_lines.append(f"\n### 8. Rủi ro không có SuKienRuiRo (OBSERVED_AS)")
if missing_sukien:
    for r in missing_sukien:
        report_lines.append(f"- Rủi ro ID: `{r}`")
else:
    report_lines.append("- (Mọi rủi ro đều đã được ghi nhận bằng ít nhất 1 sự kiện)")

with open(report_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(report_lines))

print(f"Validation hoàn tất. Đã lưu báo cáo tại: {report_path}")
