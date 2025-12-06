# Script para formatear código automáticamente
Write-Host "=== Formateando Código ===" -ForegroundColor Cyan

# Verificar que las herramientas estén instaladas
$tools = @("black", "isort", "ruff")
$missing = @()

foreach ($tool in $tools) {
    try {
        & $tool --version | Out-Null
        Write-Host "✓ $tool encontrado" -ForegroundColor Green
    } catch {
        Write-Host "✗ $tool no encontrado" -ForegroundColor Red
        $missing += $tool
    }
}

if ($missing.Count -gt 0) {
    Write-Host "`nInstalando herramientas faltantes..." -ForegroundColor Yellow
    pip install black isort ruff mypy
}

Write-Host "`nFormateando con black..." -ForegroundColor Cyan
black .

Write-Host "Ordenando imports con isort..." -ForegroundColor Cyan
isort .

Write-Host "Linting con ruff..." -ForegroundColor Cyan
ruff check . --fix

Write-Host "`n✓ Formateo completado!" -ForegroundColor Green
Write-Host "`nPara verificar tipos (opcional):" -ForegroundColor Yellow
Write-Host "mypy . --ignore-missing-imports" -ForegroundColor Gray

