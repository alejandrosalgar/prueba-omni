# PowerShell script to set up environment variables for CDK deployment

# Get AWS account ID
$accountId = (aws sts get-caller-identity --query Account --output text)
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Could not get AWS account ID. Make sure AWS CLI is configured." -ForegroundColor Red
    exit 1
}

# Get AWS region (default to us-east-1)
$region = $env:CDK_DEFAULT_REGION
if (-not $region) {
    $region = "us-east-1"
}

# Set environment variables
$env:CDK_DEFAULT_ACCOUNT = $accountId
$env:CDK_DEFAULT_REGION = $region
$env:ENVIRONMENT = "development"

Write-Host "Environment variables set:" -ForegroundColor Green
Write-Host "  CDK_DEFAULT_ACCOUNT = $accountId" -ForegroundColor Cyan
Write-Host "  CDK_DEFAULT_REGION = $region" -ForegroundColor Cyan
Write-Host "  ENVIRONMENT = development" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now run: cdk bootstrap" -ForegroundColor Yellow

