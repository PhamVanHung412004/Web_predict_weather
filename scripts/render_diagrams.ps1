# Script PowerShell để xuất mermaid (.mmd) thành PNG bằng mermaid-cli
# Yêu cầu: Node.js + mermaid-cli (@mermaid-js/mermaid-cli)
# Cách 1 (dùng npx, không cần cài global):
# npx @mermaid-js/mermaid-cli -i diagrams\architecture.mmd -o backend\results\architecture.png
# npx @mermaid-js/mermaid-cli -i diagrams\data_pipeline.mmd -o backend\results\data_pipeline.png

# Cách 2 (cài global):
# npm i -g @mermaid-js/mermaid-cli
# mmdc -i diagrams\architecture.mmd -o backend\results\architecture.png
# mmdc -i diagrams\data_pipeline.mmd -o backend\results\data_pipeline.png

Write-Host "Sử dụng lệnh npx ở trên để xuất các sơ đồ thành PNG (hoặc dùng mermaid.live để render online)."