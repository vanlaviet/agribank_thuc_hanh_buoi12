def generate_citation(row):
    """
    Generates a citation string based on metadata fields.
    Example output: [Nghị định số 73/2016/NĐ-CP | chunk_id]
    """
    title = row.get('title', '')
    if str(title) == 'nan' or not title:
        title = row.get('document_type', 'Unknown Document')
    chunk_id = row.get('chunk_id', '')
    
    parts = []
    if title and str(title) != 'nan':
        parts.append(str(title).strip())
    if chunk_id and str(chunk_id) != 'nan':
        parts.append(str(chunk_id).strip())
        
    return f"[{' | '.join(parts)}]"
