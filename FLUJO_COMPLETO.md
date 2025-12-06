# Flujo Completo del Sistema

## ¿Qué necesitas hacer además de subir el CSV?

### 1. **Subir el CSV** ✅
El sistema procesa automáticamente:
- ✅ Valida el formato del CSV
- ✅ Crea registros en DynamoDB con status `PENDING`
- ✅ Envía mensajes a SQS para procesamiento
- ✅ El worker Lambda envía los emails automáticamente
- ✅ Actualiza el status a `SENT` o `ERROR` en DynamoDB

### 2. **Verificar el Estado** (Opcional pero recomendado)
Puedes consultar el estado de los emails usando GraphQL:

```powershell
# Ver todos los emails de un batch
$batchId = "tu-batch-id-aqui"
$query = @{
    query = "query { listEmailStatus(batchId: `"$batchId`") { items { email status sentAt errorMessage } total } }"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://e9yczp0zwb.execute-api.us-east-1.amazonaws.com/v1/graphql" `
    -Method POST `
    -ContentType "application/json" `
    -Body $query
```

### 3. **Monitorear en AWS Console** (Opcional)
- **CloudWatch Logs:** Ver logs de las Lambdas
- **DynamoDB:** Ver registros de emails
- **SQS:** Ver mensajes en cola
- **SES:** Ver estadísticas de envío (si no está en dry-run)

## Flujo Automático Completo

```
1. Usuario sube CSV
   ↓
2. API Lambda recibe CSV → Guarda en S3
   ↓
3. API Lambda invoca CSV Processing Lambda
   ↓
4. CSV Processing Lambda:
   - Descarga CSV de S3
   - Valida formato
   - Crea registros en DynamoDB (status: PENDING)
   - Envía mensajes a SQS
   ↓
5. SQS activa Email Worker Lambda
   ↓
6. Email Worker Lambda:
   - Lee mensaje de SQS
   - Envía email via SES (o simula en dry-run)
   - Actualiza DynamoDB (status: SENT o ERROR)
   ↓
7. Usuario consulta estado via GraphQL
```

## No Necesitas Hacer Nada Más

Una vez que subes el CSV, el sistema:
- ✅ Procesa automáticamente
- ✅ Envía emails automáticamente
- ✅ Actualiza estados automáticamente
- ✅ Maneja errores automáticamente (DLQ)

## Verificación Rápida

Para verificar que todo funciona:

1. **Sube un CSV de prueba:**
   ```powershell
   .\upload.ps1
   ```

2. **Consulta el estado:**
   ```powershell
   .\status.ps1
   ```

3. **Revisa logs (opcional):**
   - CloudWatch → Log Groups → `/aws/lambda/email-*-development`

## Configuración Inicial (Solo una vez)

Si es la primera vez:

1. **Configurar variables de entorno:**
   ```powershell
   .\scripts\setup-env.ps1
   ```

2. **Construir el layer:**
   ```powershell
   .\scripts\build-layer.ps1
   ```

3. **Desplegar todo:**
   ```powershell
   cdk deploy --all
   ```

4. **Configurar SES (si quieres enviar emails reales):**
   - Verificar email remitente en SES Console
   - Actualizar secret en Secrets Manager con `dry_run: false`

¡Eso es todo! El sistema está completamente automatizado.

