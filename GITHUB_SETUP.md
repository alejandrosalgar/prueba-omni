# Configuración de GitHub

## ✅ Repositorio Configurado

- **URL**: https://github.com/alejandrosalgar/prueba-omni
- **Branch principal**: `main` (production)
- **Branch desarrollo**: `develop` (development)

## 🔐 Configurar Secrets para CI/CD

Para que el CI/CD funcione, necesitas configurar los siguientes secrets en GitHub:

### Pasos:

1. Ve a tu repositorio en GitHub
2. Click en **Settings** → **Secrets and variables** → **Actions**
3. Click en **New repository secret**

### Secrets Requeridos:

#### Para Development:
- **Name**: `AWS_ACCESS_KEY_ID`
  - **Value**: Tu AWS Access Key ID para desarrollo

- **Name**: `AWS_SECRET_ACCESS_KEY`
  - **Value**: Tu AWS Secret Access Key para desarrollo

- **Name**: `AWS_ACCOUNT_ID`
  - **Value**: Tu AWS Account ID (puedes obtenerlo con: `aws sts get-caller-identity --query Account --output text`)

#### Para Production (Opcional):
- **Name**: `AWS_ACCESS_KEY_ID_PROD`
- **Name**: `AWS_SECRET_ACCESS_KEY_PROD`
- **Name**: `AWS_ACCOUNT_ID_PROD`

### Crear IAM User para CI/CD

Si no tienes un usuario IAM para CI/CD, créalo:

```bash
# Crear usuario
aws iam create-user --user-name github-actions-cicd

# Crear política (ajusta según necesites)
aws iam attach-user-policy \
  --user-name github-actions-cicd \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# Crear access keys
aws iam create-access-key --user-name github-actions-cicd
```

**⚠️ Importante**: Guarda las credenciales de forma segura. Solo se mostrarán una vez.

## 🚀 Flujo de Trabajo

### Desarrollo:
```bash
# Trabajar en develop
git checkout develop
# ... hacer cambios ...
git add .
git commit -m "feat: nueva funcionalidad"
git push origin develop
# → GitHub Actions despliega automáticamente a development
```

### Producción:
```bash
# Merge develop → main
git checkout main
git merge develop
git push origin main
# → GitHub Actions despliega automáticamente a production
```

## 📋 Verificar CI/CD

1. Ve a **Actions** en GitHub
2. Deberías ver los workflows:
   - **Deploy Email Marketing System** (deploy.yml)
   - **Test and Lint** (test.yml)

3. Los workflows se ejecutarán automáticamente cuando:
   - Haces push a `develop` o `main`
   - Creas un Pull Request
   - Ejecutas manualmente desde **Actions** → **Run workflow**

## 🔍 Verificar que Todo Está Subido

```bash
# Ver branches remotos
git branch -r

# Ver commits
git log --oneline --graph --all

# Ver archivos en el repo
git ls-files
```

## ✅ Checklist

- [x] Repositorio creado en GitHub
- [x] Código subido a `main`
- [x] Branch `develop` creado y subido
- [ ] Secrets configurados en GitHub
- [ ] IAM user creado para CI/CD
- [ ] Probar workflow de CI/CD

## 🎯 Próximos Pasos

1. **Configurar secrets** en GitHub (ver arriba)
2. **Hacer un cambio pequeño** y hacer push a `develop` para probar CI/CD
3. **Verificar** que el despliegue automático funcione
4. **Revisar logs** en GitHub Actions si hay errores

¡Listo para usar CI/CD! 🚀

