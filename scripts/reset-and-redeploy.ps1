# Script maestro: Elimina todo, corrige dependencias y redesplega
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RESET Y REDEPLOY COMPLETO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Paso 1: Eliminar todos los stacks
Write-Host "`n[PASO 1/3] Eliminando todos los stacks..." -ForegroundColor Yellow
.\scripts\destroy-all.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nADVERTENCIA: Algunos stacks pueden no haberse eliminado correctamente" -ForegroundColor Yellow
    Write-Host "¿Deseas continuar? (S/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne "S" -and $response -ne "s") {
        exit 1
    }
}

# Paso 2: Corregir dependencias Lambda
Write-Host "`n[PASO 2/3] Instalando dependencias Lambda con Docker..." -ForegroundColor Yellow
.\scripts\fix-all-lambda-deps.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nERROR: No se pudieron instalar las dependencias" -ForegroundColor Red
    Write-Host "Asegúrate de que Docker Desktop esté corriendo" -ForegroundColor Yellow
    exit 1
}

# Paso 3: Redesplegar todos los stacks
Write-Host "`n[PASO 3/3] Redesplegando todos los stacks..." -ForegroundColor Yellow
.\scripts\redeploy-all.ps1

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "  PROCESO COMPLETADO EXITOSAMENTE" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "`nERROR: El despliegue falló" -ForegroundColor Red
    exit 1
}

