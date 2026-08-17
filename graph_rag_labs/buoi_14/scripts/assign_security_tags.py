import pandas as pd
import json
import os

def assign_roles(text, title):
    text_lower = str(text).lower()
    title_lower = str(title).lower()
    combined = text_lower + " " + title_lower
    
    # HR / High security
    if any(keyword in combined for keyword in ["nhân sự", "lương thưởng", "tuyển dụng", "bổ nhiệm", "kỷ luật"]):
        return json.dumps(["Admin"])
        
    # Operations / Medium security
    if any(keyword in combined for keyword in ["tín dụng", "rủi ro", "hạn mức", "phê duyệt", "cho vay"]):
        return json.dumps(["Admin", "Staff"])
        
    # General / Low security
    return json.dumps(["Admin", "Staff", "Guest"])

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_file = os.path.join(base_dir, "data", "processed", "chunks_normalized.csv")
    output_file = os.path.join(base_dir, "data", "processed", "chunks_secure.csv")
    
    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)
    
    print("Assigning security tags...")
    df["allowed_roles"] = df.apply(lambda row: assign_roles(row["text"], row["title"]), axis=1)
    
    print(f"Saving to {output_file}...")
    df.to_csv(output_file, index=False)
    
    print("\n--- SECURITY TAGGING REPORT ---")
    print("Total chunks:", len(df))
    print("\nDistribution of roles:")
    print(df["allowed_roles"].value_counts())
    
    print("\nSample rows:")
    for role_set in df["allowed_roles"].unique():
        sample = df[df["allowed_roles"] == role_set].head(1)
        print(f"\nRole: {role_set}")
        print(f"Text snippet: {sample['text'].values[0][:100]}...")

if __name__ == "__main__":
    main()
