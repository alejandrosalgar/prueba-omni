# Script para eliminar todos los stacks de CDK
Write-Host "=== Eliminando todos los stacks ===" -ForegroundColor Red

$stacks = @(
    "EmailMarketingApiStack",
    "EmailMarketingWorkerStack",
    "EmailMarketingProcessingStack",
    "EmailMarketingSecurityStack",
    "EmailMarketingStorageStack"
)

foreach ($stack in $stacks) {
    Write-Host "`nEliminando $stack..." -ForegroundColor Yellow
    cdk destroy $stack --force
    if ($LASTEXITCODE -eq 0) {
        Write-Host "$stack eliminado exitosamente" -ForegroundColor Green
    } else {
        Write-Host "Error al eliminar $stack" -ForegroundColor Red
    }
}

Write-Host "`n=== Proceso completado ===" -ForegroundColor Cyan

