# 🔐 Configurar Secrets de AWS en GitHub

## 🎯 ¿Qué es esto?

Este documento te guía paso a paso para configurar las credenciales de AWS en GitHub Actions, permitiendo que el pipeline CI/CD despliegue automáticamente tu aplicación a AWS cuando hagas push a `develop` o `main`.

**En resumen**: Necesitas copiar tus credenciales de AWS (Access Key ID y Secret Access Key) y guardarlas como "secrets" en GitHub para que el pipeline pueda usarlas de forma segura.

## ⚡ Inicio Rápido

Si ya tienes tus credenciales de AWS (como en la imagen que viste):

1. **Ve a GitHub**: https://github.com/alejandrosalgar/prueba-omni → **Settings** → **Secrets and variables** → **Actions**
2. **Crea 3 secrets**:
   - `AWS_ACCESS_KEY_ID` = Tu Access Key ID (ej: `AKIAIOSFODNN7EXAMPLE`)
   - `AWS_SECRET_ACCESS_KEY` = Tu Secret Access Key (ej: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`)
   - `AWS_ACCOUNT_ID` = Tu Account ID (12 dígitos, solo números)
3. **Haz push a `develop`** y el pipeline se ejecutará automáticamente

---

## 📋 Requisitos Previos

Antes de configurar los secrets, necesitas:

1. **AWS Account ID**: Tu ID de cuenta de AWS
2. **AWS Access Key ID**: Clave de acceso de AWS
3. **AWS Secret Access Key**: Clave secreta de AWS

## 🔍 Paso 1: Obtener tu AWS Account ID

Ejecuta este comando en tu terminal (si tienes AWS CLI configurado):

```powershell
aws sts get-caller-identity --query Account --output text
```

O puedes verlo en la consola de AWS:
- Ve a **AWS Console** → Click en tu nombre de usuario (arriba derecha)
- El **Account ID** aparece en el menú desplegable

## 🔑 Paso 2: Crear o Usar Credenciales de AWS

### Opción A: Usar credenciales existentes (Tu caso)

Si ya tienes un Access Key ID y Secret Access Key (como en la imagen de AWS Console que viste), puedes usarlas directamente:

1. **Copia el Access Key ID**: 
   - Ejemplo de formato: `AKIAIOSFODNN7EXAMPLE` (reemplaza con tu Access Key ID real)
   - O desde AWS Console → IAM → Security credentials

2. **Copia el Secret Access Key**:
   - Ejemplo de formato: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` (reemplaza con tu Secret Access Key real)
   - ⚠️ **Importante**: Copia el valor completo, incluyendo el símbolo `+` al inicio si lo tiene
   - ⚠️ **Solo se muestra una vez**: Si no lo guardaste, tendrás que crear nuevas credenciales

3. **Guarda estas credenciales de forma segura** antes de continuar (las necesitarás en el Paso 3)

**Nota**: Si estas credenciales son de tu cuenta personal, considera crear un usuario IAM específico para CI/CD (ver Opción B).

### Opción B: Crear nuevas credenciales para CI/CD (Recomendado)

Es mejor crear un usuario IAM específico para CI/CD:

1. **Ve a AWS Console** → **IAM** → **Users**
2. Click en **Create user**
3. Nombre: `github-actions-cicd`
4. Click en **Next**
5. En **Set permissions**, selecciona:
   - **Attach policies directly**
   - Busca y selecciona: `PowerUserAccess` (o crea una política más restrictiva)
6. Click en **Next** → **Create user**
7. Click en el usuario creado
8. Ve a la pestaña **Security credentials**
9. Click en **Create access key**
10. Selecciona **Application running outside AWS**
11. Click en **Next** → **Create access key**
12. **⚠️ IMPORTANTE**: Copia y guarda:
    - **Access key ID**
    - **Secret access key** (solo se muestra una vez)

## 📝 Paso 3: Configurar Secrets en GitHub

### 3.1. Acceder a la Configuración de Secrets

1. **Abre tu navegador** y ve a tu repositorio en GitHub:
   ```
   https://github.com/alejandrosalgar/prueba-omni
   ```

2. **Click en la pestaña "Settings"** (arriba del repositorio, junto a "Code", "Issues", etc.)

3. **En el menú lateral izquierdo**, busca y click en:
   ```
   Secrets and variables → Actions
   ```

4. Verás una página con dos secciones:
   - **Repository secrets**: Secrets para este repositorio
   - **Environment secrets**: Secrets específicos por ambiente (development/production)

### 3.2. Crear los Secrets para Development

**Click en el botón "New repository secret"** (arriba a la derecha) y crea estos 3 secrets uno por uno:

#### 🔑 Secret 1: AWS_ACCESS_KEY_ID

1. **Name**: Escribe exactamente: `AWS_ACCESS_KEY_ID`
   - ⚠️ **Importante**: Debe ser exactamente así, con mayúsculas y guiones bajos
   
2. **Secret**: Pega tu **Access Key ID** de AWS
   - Ejemplo de formato: `AKIAIOSFODNN7EXAMPLE` (usa tu Access Key ID real)
   
3. **Click en "Add secret"**

#### 🔐 Secret 2: AWS_SECRET_ACCESS_KEY

1. **Name**: Escribe exactamente: `AWS_SECRET_ACCESS_KEY`
   
2. **Secret**: Pega tu **Secret Access Key** de AWS
   - Ejemplo de formato: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` (usa tu Secret Access Key real)
   - ⚠️ **Importante**: Copia todo el valor completo, incluyendo el símbolo `+` al inicio
   
3. **Click en "Add secret"**

#### 🆔 Secret 3: AWS_ACCOUNT_ID

1. **Name**: Escribe exactamente: `AWS_ACCOUNT_ID`
   
2. **Secret**: Pega tu **AWS Account ID**
   - Solo números, sin guiones ni espacios
   - Ejemplo: `123456789012`
   - Si no lo tienes, ejecuta: `aws sts get-caller-identity --query Account --output text`
   
3. **Click en "Add secret"**

### 3.3. Crear Secrets para Production (Opcional pero Recomendado)

Si quieres desplegar a producción desde GitHub, repite el proceso anterior pero con estos nombres:

1. **Click en "New repository secret"** nuevamente

2. Crea estos 3 secrets adicionales:

   - **Name**: `AWS_ACCESS_KEY_ID_PROD`
     - **Secret**: Access Key ID para producción
   
   - **Name**: `AWS_SECRET_ACCESS_KEY_PROD`
     - **Secret**: Secret Access Key para producción
   
   - **Name**: `AWS_ACCOUNT_ID_PROD`
     - **Secret**: AWS Account ID para producción (puede ser el mismo si usas la misma cuenta)

### 3.4. Verificar que los Secrets Están Creados

Después de crear todos los secrets, deberías ver en la lista:

```
Repository secrets (3)
├── AWS_ACCESS_KEY_ID          ••••••••
├── AWS_SECRET_ACCESS_KEY      ••••••••
└── AWS_ACCOUNT_ID             ••••••••
```

**Nota**: Los valores aparecen como `••••••••` por seguridad. No podrás verlos nuevamente después de crearlos.

## ✅ Paso 4: Verificar la Configuración

1. En **Secrets and variables** → **Actions**, deberías ver tus 3 secrets listados
2. Los secrets aparecen como `••••••••` (no puedes ver sus valores por seguridad)
3. Verifica que los nombres sean **exactamente**:
   - `AWS_ACCESS_KEY_ID` (no `aws_access_key_id` ni `AWS_ACCESS_KEY`)
   - `AWS_SECRET_ACCESS_KEY` (no `aws_secret_access_key`)
   - `AWS_ACCOUNT_ID` (no `AWS_ACCOUNT` ni `aws_account_id`)

### 📋 Checklist de Verificación

Antes de probar el pipeline, asegúrate de tener:

- [ ] `AWS_ACCESS_KEY_ID` creado en GitHub Secrets
- [ ] `AWS_SECRET_ACCESS_KEY` creado en GitHub Secrets  
- [ ] `AWS_ACCOUNT_ID` creado en GitHub Secrets
- [ ] Los nombres de los secrets son exactos (case-sensitive)
- [ ] Tienes las credenciales guardadas de forma segura (por si necesitas recrearlas)

## 🚀 Paso 5: Probar el CI/CD

Una vez configurados los secrets, puedes probar el pipeline de dos formas:

### Opción A: Despliegue Automático (Push a develop)

1. Haz un commit y push a la rama `develop`:
   ```bash
   git checkout develop
   git add .
   git commit -m "test: probar pipeline"
   git push origin develop
   ```

2. Ve a **Actions** en GitHub (pestaña en la parte superior del repositorio)

3. Verás que el workflow **"Deploy Email Marketing System"** se ejecuta automáticamente

### Opción B: Despliegue Manual (Workflow Dispatch)

1. Ve a **Actions** en GitHub

2. En el menú lateral izquierdo, click en **"Deploy Email Marketing System"**

3. Click en el botón **"Run workflow"** (arriba a la derecha)

4. Selecciona:
   - **Branch**: `develop` (o `main` para producción)
   - **Environment**: `development` (o `production`)
   
5. Click en el botón verde **"Run workflow"**

6. El workflow comenzará a ejecutarse. Puedes ver el progreso en tiempo real

### 📊 Monitorear la Ejecución

Durante la ejecución verás:

1. **Jobs ejecutándose**:
   - ✅ `validate` - Valida el código
   - ✅ `build-layer` - Construye el Lambda Layer
   - ✅ `deploy-dev` o `deploy-prod` - Despliega a AWS

2. **Logs en tiempo real**: Click en cada job para ver los logs detallados

3. **Resultado**: 
   - ✅ Verde = Éxito
   - ❌ Rojo = Error (revisa los logs para ver qué falló)

## 🔒 Seguridad

- ✅ Los secrets están encriptados en GitHub
- ✅ Solo se pueden ver en los workflows (no en el código)
- ✅ No se muestran en los logs de GitHub Actions
- ⚠️ **Nunca** compartas tus Access Keys públicamente
- ⚠️ Si comprometes una key, revócala inmediatamente en AWS IAM

## 🛠️ Troubleshooting

### ❌ Error: "AWS_ACCESS_KEY_ID not found" o "Secret not found"

**Causa**: El secret no existe o tiene un nombre incorrecto

**Solución**:
1. Ve a **Settings** → **Secrets and variables** → **Actions**
2. Verifica que el secret exista con el nombre **exacto** (case-sensitive)
3. Asegúrate de estar en **Repository secrets**, no en **Environment secrets**
4. Si no existe, créalo siguiendo el Paso 3.2

### ❌ Error: "Invalid credentials" o "Access Denied"

**Causa**: Las credenciales son incorrectas o el usuario IAM no tiene permisos

**Solución**:
1. Verifica que copiaste correctamente el **Access Key ID** y **Secret Access Key**
   - ⚠️ Asegúrate de copiar el Secret Access Key completo (incluye el símbolo `+` si lo tiene)
2. Verifica que el usuario IAM tenga los permisos necesarios:
   - CloudFormation (crear/actualizar stacks)
   - S3 (subir assets)
   - Lambda (crear/actualizar funciones)
   - IAM (crear roles)
   - API Gateway, DynamoDB, SQS, Secrets Manager, X-Ray
3. Prueba las credenciales localmente:
   ```bash
   aws configure set aws_access_key_id TU_ACCESS_KEY_ID
   aws configure set aws_secret_access_key TU_SECRET_ACCESS_KEY
   aws sts get-caller-identity
   ```

### ❌ Error: "Account ID mismatch"

**Causa**: El AWS Account ID es incorrecto o tiene formato incorrecto

**Solución**:
1. Verifica que el `AWS_ACCOUNT_ID` sea solo números (12 dígitos)
2. No debe tener guiones, espacios o letras
3. Obtén el Account ID correcto:
   ```bash
   aws sts get-caller-identity --query Account --output text
   ```

### ❌ Error: "Bootstrap failed" o "CDK bootstrap error"

**Causa**: El CDK no está bootstrapeado en la cuenta/región

**Solución**:
- El workflow intenta hacer bootstrap automáticamente, pero si falla:
  ```bash
  cdk bootstrap aws://TU_ACCOUNT_ID/us-east-1
  ```

### ❌ Error: "Workflow no se ejecuta automáticamente"

**Causa**: El workflow solo se ejecuta en push a `develop` o `main`

**Solución**:
- Asegúrate de hacer push a la rama correcta (`develop` para dev, `main` para prod)
- O usa **Run workflow** manualmente desde la pestaña Actions

### 📝 Cómo Ver los Logs Detallados

1. Ve a **Actions** → Click en el workflow que falló
2. Click en el **job** que falló (aparece con ❌)
3. Click en el **step** específico que falló
4. Revisa los logs para ver el error exacto

## 📚 Recursos

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [CDK Bootstrap](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html)

---

**¿Necesitas ayuda?** Revisa los logs en **Actions** → [nombre del workflow] → [nombre del job] para ver errores específicos.

