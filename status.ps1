# Script para consultar estado de emails
param([string]$BatchId)

# Obtener URL del API automáticamente
$API_URL = aws cloudformation describe-stacks --stack-name EmailMarketingApiStack --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text

if (-not $API_URL) {
    Write-Host "ERROR: No se pudo obtener la URL del API. Verifica que el stack esté desplegado." -ForegroundColor Red
    exit 1
}

if (-not $BatchId) {
    Write-Host "Uso: .\status.ps1 -BatchId 'tu-batch-id'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "O consultar todos los emails:" -ForegroundColor Cyan
    $query = @{query = "query { listEmailStatus(limit: 100) { items { batchId email status subject createdAt } total } }"} | ConvertTo-Json
} else {
    $query = @{query = "query { listEmailStatus(batchId: `"$BatchId`", limit: 100) { items { batchId email status subject createdAt sentAt errorMessage } total } }"} | ConvertTo-Json
}

$response = Invoke-WebRequest -Uri "${API_URL}graphql" -Method Post -Body $query -ContentType "application/json" -UseBasicParsing
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10

