# Script para construir Lambda Layer con dependencias
Write-Host "=== Construyendo Lambda Layer ===" -ForegroundColor Cyan

$layerPath = "infrastructure/functions/layer"
$pythonPath = "$layerPath/python/lib/python3.11/site-packages"

# Verificar Docker
try {
    docker --version | Out-Null
    Write-Host "Docker encontrado!" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker no está instalado o no está corriendo" -ForegroundColor Red
    exit 1
}

# Limpiar directorio del layer
Write-Host "`nLimpiando directorio del layer..." -ForegroundColor Yellow
if (Test-Path $pythonPath) {
    Remove-Item -Path $pythonPath -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path $pythonPath -Force | Out-Null

# Instalar dependencias en la estructura del layer
Write-Host "Instalando dependencias en estructura de layer..." -ForegroundColor Cyan
$currentDir = (Get-Location).Path
$layerDir = Join-Path $currentDir $layerPath

docker run --rm `
    --entrypoint /bin/sh `
    -v "${layerDir}:/var/task" `
    -w /var/task `
    python:3.11-slim `
    -c "pip install --no-user -r requirements.txt -t python/lib/python3.11/site-packages"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nLayer construido exitosamente!" -ForegroundColor Green
    Write-Host "Ubicación: $layerPath" -ForegroundColor Cyan
    Write-Host "Ahora puedes desplegar el stack del layer:" -ForegroundColor Yellow
    Write-Host "cdk deploy EmailMarketingLayerStack" -ForegroundColor Yellow
} else {
    Write-Host "`nERROR: Error al construir el layer" -ForegroundColor Red
    exit 1
}

