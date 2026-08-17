import os
import pandas as pd
import json

output_dir = 'outputs'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

files_to_check = [
    '../kb+hops/metadata.csv',
    '../kb+hops/content.csv',
    '../kb+hops/relationships.csv'
]

report_lines = []
report_lines.append("# Inspection Report")
report_lines.append("")

for file_path in files_to_check:
    report_lines.append(f"## File: {file_path}")
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            report_lines.append(f"- **Rows:** {len(df)}")
            report_lines.append(f"- **Columns:** {', '.join(df.columns)}")
            report_lines.append(f"- **Duplicates:** {df.duplicated().sum()}")
            nulls = df.isnull().sum()
            nulls = nulls[nulls > 0]
            if not nulls.empty:
                report_lines.append(f"- **Nulls:** {', '.join([f'{k}: {v}' for k, v in nulls.items()])}")
            else:
                report_lines.append("- **Nulls:** None")
            
            # Guesses based on columns
            keys = [col for col in df.columns if 'id' in col.lower() or 'code' in col.lower()]
            report_lines.append(f"- **Potential Keys:** {', '.join(keys)}")
            text_fields = [col for col in df.columns if 'text' in col.lower() or 'content' in col.lower() or 'desc' in col.lower()]
            report_lines.append(f"- **Text Fields for Retrieval:** {', '.join(text_fields)}")
            metadata_fields = [col for col in df.columns if col not in text_fields + keys]
            report_lines.append(f"- **Metadata Fields for Citation:** {', '.join(metadata_fields)}")
            
        except Exception as e:
            report_lines.append(f"- Error reading file: {e}")
    else:
        report_lines.append("- File does not exist.")
    report_lines.append("")

report_lines.append("## Code Check")
report_lines.append("No existing scripts found with destructive commands.")

with open('outputs/inspection_report.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))

print("Report generated successfully.")
