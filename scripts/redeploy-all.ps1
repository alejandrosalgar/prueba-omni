# Script para redesplegar todos los stacks
Write-Host "=== Redesplegando todos los stacks ===" -ForegroundColor Cyan

$stacks = @(
    "EmailMarketingStorageStack",
    "EmailMarketingSecurityStack",
    "EmailMarketingProcessingStack",
    "EmailMarketingWorkerStack",
    "EmailMarketingApiStack"
)

foreach ($stack in $stacks) {
    Write-Host "`nDesplegando $stack..." -ForegroundColor Yellow
    cdk deploy $stack --require-approval never
    if ($LASTEXITCODE -eq 0) {
        Write-Host "$stack desplegado exitosamente" -ForegroundColor Green
    } else {
        Write-Host "Error al desplegar $stack" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n=== Todos los stacks desplegados exitosamente ===" -ForegroundColor Green

# Obtener URL del API
Write-Host "`nObteniendo URL del API..." -ForegroundColor Cyan
$apiUrl = aws cloudformation describe-stacks `
    --stack-name EmailMarketingApiStack `
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' `
    --output text

Write-Host "API URL: $apiUrl" -ForegroundColor Green

