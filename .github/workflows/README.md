# GitHub Actions Workflows

Este directorio contiene los workflows de CI/CD para el proyecto.

## Workflows Disponibles

### 1. `deploy.yml` - Despliegue Automático

Despliega automáticamente el sistema en diferentes ambientes según el branch:

- **`develop` branch** → Despliega a `development`
- **`main` branch** → Despliega a `production`
- **Manual dispatch** → Permite elegir el ambiente

**Jobs:**
- `validate`: Valida el código y sintetiza CDK
- `build-layer`: Construye el Lambda Layer con Docker
- `deploy-dev`: Despliega a desarrollo
- `deploy-prod`: Despliega a producción

### 2. `test.yml` - Tests y Validación

Ejecuta validaciones de código en Pull Requests:

- **Linting**: black, isort, ruff, mypy
- **CDK Validation**: Valida la síntesis de CDK
- **Layer Build Test**: Prueba la construcción del layer

## Configuración Requerida

### Secrets de GitHub

Configura los siguientes secrets en GitHub Settings → Secrets and variables → Actions:

#### Para Development:
- `AWS_ACCESS_KEY_ID` - AWS Access Key para desarrollo
- `AWS_SECRET_ACCESS_KEY` - AWS Secret Key para desarrollo
- `AWS_ACCOUNT_ID` - AWS Account ID para desarrollo

#### Para Production:
- `AWS_ACCESS_KEY_ID_PROD` - AWS Access Key para producción
- `AWS_SECRET_ACCESS_KEY_PROD` - AWS Secret Key para producción
- `AWS_ACCOUNT_ID_PROD` - AWS Account ID para producción

### IAM Permissions

El usuario de AWS necesita los siguientes permisos:
- CloudFormation (crear/actualizar/eliminar stacks)
- S3 (subir assets de CDK)
- Lambda (crear/actualizar funciones y layers)
- IAM (crear roles y políticas)
- API Gateway (crear APIs)
- DynamoDB (crear tablas)
- SQS (crear colas)
- Secrets Manager (crear/leer secrets)
- X-Ray (habilitar tracing)

## Uso

### Despliegue Automático

1. **Push a `develop`** → Despliega automáticamente a development
2. **Push a `main`** → Despliega automáticamente a production
3. **Pull Request** → Solo ejecuta validaciones, no despliega

### Despliegue Manual

1. Ve a **Actions** en GitHub
2. Selecciona **Deploy Email Marketing System**
3. Click en **Run workflow**
4. Elige el ambiente (development/production)
5. Click en **Run workflow**

## Flujo de Trabajo Recomendado

```
1. Crear feature branch desde develop
   git checkout -b feature/nueva-funcionalidad develop

2. Hacer cambios y commits
   git commit -m "feat: nueva funcionalidad"

3. Crear Pull Request a develop
   → GitHub Actions ejecuta tests y validaciones

4. Merge a develop
   → GitHub Actions despliega automáticamente a development

5. Cuando esté listo, merge develop → main
   → GitHub Actions despliega automáticamente a production
```

## Troubleshooting

### Error: "AWS credentials not configured"
- Verifica que los secrets estén configurados en GitHub
- Verifica que los nombres de los secrets sean correctos

### Error: "CDK bootstrap required"
- El workflow intenta hacer bootstrap automáticamente
- Si falla, ejecuta manualmente: `cdk bootstrap aws://ACCOUNT/REGION`

### Error: "Layer build failed"
- Verifica que Docker esté disponible en el runner
- Verifica que `requirements.txt` del layer sea válido

