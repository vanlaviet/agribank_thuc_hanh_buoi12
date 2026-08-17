import os
import pandas as pd
import re

def normalize_text(text):
    if pd.isna(text):
        return ""
    # Remove HTML tags if present, keeping the content
    text = re.sub(r'<[^>]+>', ' ', str(text))
    # Replace multiple newlines with a single newline
    text = re.sub(r'\n+', '\n', text)
    # Replace multiple spaces with a single space
    text = re.sub(r' +', ' ', text)
    return text.strip()

def prepare_corpus():
    data_dir = 'data/processed'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Read files
    content_df = pd.read_csv('../kb+hops/content.csv')
    metadata_df = pd.read_csv('../kb+hops/metadata.csv')

    df = pd.merge(content_df, metadata_df, on='id', how='left')
    
    processed_records = []
    for idx, row in df.iterrows():
        text = normalize_text(row.get('content_html', ''))
        if not text:
            continue
            
        doc_id = str(row['id'])
        
        # Split text by Article (Điều)
        parts = re.split(r'(Điều \d+[\.\s])', text)
        chunks = []
        
        # Add the intro part (before the first "Điều") if it's not empty
        if len(parts) > 0 and parts[0].strip():
            chunks.append(parts[0].strip())
            
        # Add the rest of the parts by joining the "Điều X." with its content
        for i in range(1, len(parts)-1, 2):
            chunk_text = parts[i] + parts[i+1]
            chunks.append(chunk_text.strip())
            
        # Process each chunk to assign a proper chunk_id
        for chunk_idx, chunk_text in enumerate(chunks, 1):
            if not chunk_text:
                continue
                
            # Check if this chunk starts with "Điều X" to extract X
            match = re.match(r'^Điều (\d+)', chunk_text)
            if match:
                art_num = match.group(1)
                chunk_id = f"{doc_id}_art_{art_num}"
            else:
                chunk_id = f"{doc_id}_chunk_{chunk_idx}"
                
            record = {
                'chunk_id': chunk_id,
                'document_id': doc_id,
                'text': chunk_text,
                'source_file': 'content.csv',
                'title': row.get('title', ''),
                'document_type': row.get('loai_van_ban', ''),
                'effective_date': row.get('ngay_co_hieu_luc', ''),
                'status': row.get('tinh_trang_hieu_luc', '')
            }
            processed_records.append(record)

    processed_df = pd.DataFrame(processed_records)

    # Validate uniqueness
    is_unique = processed_df['chunk_id'].is_unique
    if not is_unique:
        print("Warning: chunk_id is not unique! Deduping by chunk_id...")
        processed_df.drop_duplicates(subset=['chunk_id'], inplace=True)

    # Save to CSV
    output_path = os.path.join(data_dir, 'chunks_normalized.csv')
    processed_df.to_csv(output_path, index=False, encoding='utf-8')

    # Print stats
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(f"Tổng số chunk: {len(processed_df)}")
    print(f"Số document: {processed_df['document_id'].nunique()}")
    print(f"Số chunk thiếu text: {(processed_df['text'].str.strip() == '').sum()}")
    print(f"Duplicate chunks (same text): {processed_df.duplicated(subset=['text']).sum()}")
    print("\n3 Sample records:")
    for record in processed_df.head(3).to_dict('records'):
        print(f"- {record['chunk_id']}: {record['text'][:50]}...")

if __name__ == '__main__':
    prepare_corpus()
