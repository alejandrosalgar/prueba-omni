# Script simple para consultar estado
param([string]$BatchId)

$API_URL = "https://e9yczp0zwb.execute-api.us-east-1.amazonaws.com/v1/"

if (-not $BatchId) {
    Write-Host "Uso: .\status.ps1 -BatchId 'tu-batch-id'" -ForegroundColor Yellow
    exit
}

$query = @{query = "query { listEmailStatus(batchId: `"$BatchId`", limit: 100) { items { email status subject } total } }"} | ConvertTo-Json
$response = Invoke-WebRequest -Uri "${API_URL}graphql" -Method Post -Body $query -ContentType "application/json" -UseBasicParsing
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10

