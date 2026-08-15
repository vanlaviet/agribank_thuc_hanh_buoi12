import pandas as pd
from bs4 import BeautifulSoup
import re
import os

def clean_html(html_text):
    if pd.isna(html_text):
        return ""
    # Parse with BeautifulSoup
    soup = BeautifulSoup(str(html_text), 'html.parser')
    # Get text
    text = soup.get_text(separator=' ', strip=True)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def step1():
    print("--- BƯỚC 1: Kiểm tra dữ liệu và làm sạch HTML ---")
    
    # 1. Đọc dữ liệu
    try:
        metadata = pd.read_csv('metadata.csv')
        content = pd.read_csv('content.csv')
    except Exception as e:
        print(f"[FAIL] Lỗi đọc file: {e}")
        return
        
    # 2. Kiểm tra số dòng, số cột
    print(f"Metadata: {metadata.shape[0]} dòng, {metadata.shape[1]} cột")
    print(f"Content: {content.shape[0]} dòng, {content.shape[1]} cột")
    
    # 3. Kiểm tra duplicate id
    meta_dups = metadata['id'].duplicated().sum()
    content_dups = content['id'].duplicated().sum()
    print(f"Duplicate IDs trong metadata.csv: {meta_dups}")
    print(f"Duplicate IDs trong content.csv: {content_dups}")
    
    # 4. Kiểm tra id mismatch
    meta_ids = set(metadata['id'])
    content_ids = set(content['id'])
    only_in_meta = meta_ids - content_ids
    only_in_content = content_ids - meta_ids
    print(f"IDs chỉ có trong metadata: {len(only_in_meta)}")
    print(f"IDs chỉ có trong content: {len(only_in_content)}")
    
    # 5. Merge
    df = pd.merge(metadata, content, on='id', how='inner')
    print(f"Số document sau khi merge: {len(df)}")
    
    # 6 & 7. Missing values, NULL, Rỗng, 'Chưa phân loại'
    print("\n--- Missing Values & Anomalies (Metadata) ---")
    for col in metadata.columns:
        if col == 'id': continue
        nulls = df[col].isna().sum()
        empty = (df[col] == "").sum()
        unclassified = (df[col] == "Chưa phân loại").sum()
        print(f"- Cột '{col}': {nulls} NULL/NaN, {empty} chuỗi rỗng, {unclassified} 'Chưa phân loại'")
        
    # 8-11. Làm sạch content_html
    print("\nĐang làm sạch HTML...")
    if 'content_html' not in df.columns:
        # Giả sử cột chứa HTML có tên khác nếu không tìm thấy content_html
        html_col = 'content' if 'content' in df.columns else df.columns[-1]
        df['content_clean'] = df[html_col].apply(clean_html)
    else:
        df['content_clean'] = df['content_html'].apply(clean_html)
    
    # 12. Lưu file
    output_path = 'cleaned_documents.csv'
    df.to_csv(output_path, index=False)
    print(f"Đã lưu kết quả ra: {output_path}")
    
    # 13. In mẫu
    print("\n--- 2 Mẫu content_html vs content_clean ---")
    for i in range(min(2, len(df))):
        print(f"\nMẫu {i+1} (ID: {df.iloc[i]['id']})")
        
        html_val = df.iloc[i].get('content_html', df.iloc[i].get('content', ''))
        
        print("HTML (đoạn đầu 100 ký tự):", str(html_val)[:100].replace('\n', '\\n'), "...")
        print("Clean (đoạn đầu 100 ký tự):", df.iloc[i]['content_clean'][:100].replace('\n', '\\n'), "...")
        
    # Validation check
    if os.path.exists(output_path) and len(df) > 0 and 'content_clean' in df.columns:
        empty_clean = (df['content_clean'] == "").sum()
        if empty_clean == len(df):
            print("\n[FAIL] Tất cả content_clean đều rỗng.")
        else:
            print("\n[PASS] BƯỚC 1 hoàn thành thành công.")
    else:
        print("\n[FAIL] BƯỚC 1 thất bại (không tạo được cleaned_documents.csv).")

if __name__ == "__main__":
    step1()
