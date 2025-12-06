# Scripts del Proyecto

## Scripts Necesarios

### 1. `build-layer.ps1` ⭐ **NECESARIO**
Construye el Lambda Layer con todas las dependencias Python usando Docker.
```powershell
.\scripts\build-layer.ps1
```
**Cuándo usarlo:** Cada vez que actualices `infrastructure/functions/layer/requirements.txt`

### 2. `deploy.py`
Script Python para desplegar/destruir stacks con CDK.
```powershell
python scripts/deploy.py
```

### 3. `destroy-all.ps1`
Destruye todos los stacks de CloudFormation.
```powershell
.\scripts\destroy-all.ps1
```

### 4. `redeploy-all.ps1`
Reconstruye el layer y despliega todos los stacks.
```powershell
.\scripts\redeploy-all.ps1
```

### 5. `reset-and-redeploy.ps1`
Destruye todo, reconstruye el layer y despliega desde cero.
```powershell
.\scripts\reset-and-redeploy.ps1
```

### 6. `setup-env.ps1` / `setup-env.bat`
Configura las variables de entorno necesarias para CDK.
```powershell
.\scripts\setup-env.ps1
```

### 7. `test_graphql.sh` / `test_upload.sh`
Scripts de prueba para los endpoints (requieren curl).

## Scripts Eliminados (Obsoletos)

Los siguientes scripts fueron eliminados porque ya no son necesarios con Lambda Layers:

- ❌ `build-lambda-deps.ps1` - Ya no instalamos deps directamente en Lambdas
- ❌ `fix-lambda-deps.ps1` - Ya no hay deps que arreglar en Lambdas
- ❌ `fix-all-lambda-deps.ps1` - Obsoleto
- ❌ `install-lambda-deps-docker.ps1` - Obsoleto
- ❌ `deploy-fix-layer.ps1` - Ya no hay problema de exports
- ❌ `clean-lambda-code.ps1` - Ya no es necesario limpiar deps manualmente

## Flujo de Trabajo Normal

1. **Primera vez:**
   ```powershell
   .\scripts\setup-env.ps1
   .\scripts\build-layer.ps1
   cdk deploy --all
   ```

2. **Actualizar dependencias:**
   ```powershell
   .\scripts\build-layer.ps1
   cdk deploy EmailMarketingLayerStack
   ```

3. **Actualizar código Lambda:**
   ```powershell
   cdk deploy --all
   ```

4. **Limpiar todo:**
   ```powershell
   .\scripts\destroy-all.ps1
   ```

