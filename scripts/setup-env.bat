@echo off
REM Batch script to set up environment variables for CDK deployment

REM Get AWS account ID
for /f "tokens=*" %%i in ('aws sts get-caller-identity --query Account --output text') do set ACCOUNT_ID=%%i

if errorlevel 1 (
    echo Error: Could not get AWS account ID. Make sure AWS CLI is configured.
    exit /b 1
)

REM Set environment variables
set CDK_DEFAULT_ACCOUNT=%ACCOUNT_ID%
set CDK_DEFAULT_REGION=us-east-1
set ENVIRONMENT=development

echo Environment variables set:
echo   CDK_DEFAULT_ACCOUNT = %ACCOUNT_ID%
echo   CDK_DEFAULT_REGION = us-east-1
echo   ENVIRONMENT = development
echo.
echo You can now run: cdk bootstrap

