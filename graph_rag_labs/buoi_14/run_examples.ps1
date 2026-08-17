$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8

$queries = @(
    "Điều 111 của Nghị định 73/2016/NĐ-CP quy định gì?",
    "Trách nhiệm của các bộ và cơ quan ngang bộ là gì?",
    "Điều 112 quy định trách nhiệm của Ủy ban nhân dân như thế nào?"
)

$outputFile = "outputs\retrieval_examples.md"
"# Retrieval Examples" | Out-File -FilePath $outputFile -Encoding utf8

foreach ($q in $queries) {
    "## Query: $q`n" | Out-File -FilePath $outputFile -Encoding utf8 -Append
    .\.venv\Scripts\python.exe scripts\baseline_retrieval.py --query $q --top-k 3 | Out-File -FilePath $outputFile -Encoding utf8 -Append
}

Write-Host "Examples generated in $outputFile"
