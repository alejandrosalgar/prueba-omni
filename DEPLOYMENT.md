# Deployment Guide

## Quick Start

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured (`aws configure`)
3. **AWS CDK** installed (`npm install -g aws-cdk`)
4. **Python 3.11+** installed
5. **CDK Bootstrapped** in your AWS account

### Step 1: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Lambda function dependencies
cd infrastructure/functions
pip install --no-user -r requirements.txt -t .
cd ../..
```

### Step 2: Set Environment Variables

**Windows (PowerShell):**
```powershell
.\scripts\setup-env.ps1
```

**Windows (Command Prompt):**
```cmd
scripts\setup-env.bat
```

**Linux/Mac:**
```bash
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=us-east-1
export ENVIRONMENT=development
```

### Step 3: Bootstrap CDK (First Time Only)

```bash
cdk bootstrap
```

### Step 4: Deploy Infrastructure

```bash
# Deploy all stacks
python scripts/deploy.py deploy --environment development

# Or deploy individually
cdk deploy EmailMarketingStorageStack
cdk deploy EmailMarketingSecurityStack
cdk deploy EmailMarketingProcessingStack
cdk deploy EmailMarketingWorkerStack
cdk deploy EmailMarketingApiStack
```

### Step 5: Configure Secrets Manager

```bash
aws secretsmanager put-secret-value \
  --secret-id email-marketing-config-development \
  --secret-string '{"ses_from_email": "your-email@example.com", "dry_run": "true"}'
```

### Step 6: Verify SES Email (If Not in Production)

```bash
aws ses verify-email-identity --email-address your-email@example.com
```

### Step 7: Get API Endpoint

```bash
aws cloudformation describe-stacks \
  --stack-name EmailMarketingApiStack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text
```

## Testing

### Test CSV Upload

```bash
# Make script executable
chmod +x scripts/test_upload.sh

# Run test
./scripts/test_upload.sh
```

### Test GraphQL

```bash
# Make script executable
chmod +x scripts/test_graphql.sh

# Run test
./scripts/test_graphql.sh

# Or with batch ID
./scripts/test_graphql.sh <batch-id>
```

## Environment-Specific Deployment

### Development

```bash
export ENVIRONMENT=development
python scripts/deploy.py deploy --environment development
```

### Staging

```bash
export ENVIRONMENT=staging
python scripts/deploy.py deploy --environment staging
```

### Production

```bash
export ENVIRONMENT=production
python scripts/deploy.py deploy --environment production
```

## Updating Configuration

### Update Secrets Manager

```bash
aws secretsmanager put-secret-value \
  --secret-id email-marketing-config-<environment> \
  --secret-string '{"ses_from_email": "new-email@example.com", "dry_run": "false"}'
```

### Update Lambda Environment Variables

Edit the stack files and redeploy:

```bash
cdk deploy EmailMarketingApiStack
```

## Monitoring

### View Logs

```bash
# API Lambda logs
aws logs tail /aws/lambda/email-api-development --follow

# CSV Processing Lambda logs
aws logs tail /aws/lambda/email-csv-processing-development --follow

# Email Worker Lambda logs
aws logs tail /aws/lambda/email-worker-development --follow
```

### View Metrics

```bash
# Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=email-api-development \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

## Troubleshooting

### Stack Deployment Fails

1. Check CloudFormation events:
   ```bash
   aws cloudformation describe-stack-events --stack-name <stack-name>
   ```

2. Verify IAM permissions
3. Check CDK bootstrap status
4. Review error messages in CloudFormation console

### Lambda Function Errors

1. Check CloudWatch Logs
2. Verify environment variables
3. Check IAM role permissions
4. Review X-Ray traces

### API Gateway Errors

1. Check API Gateway logs
2. Verify Lambda integration
3. Check CORS configuration
4. Review API Gateway metrics

## Cleanup

### Destroy All Stacks

```bash
python scripts/deploy.py destroy --environment development
```

### Destroy Individual Stack

```bash
cdk destroy EmailMarketingApiStack
cdk destroy EmailMarketingWorkerStack
cdk destroy EmailMarketingProcessingStack
cdk destroy EmailMarketingSecurityStack
cdk destroy EmailMarketingStorageStack
```

## Cost Monitoring

### View Monthly Costs

```bash
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

### Set Up Cost Alerts

1. Go to AWS Cost Management Console
2. Create budget with alerts
3. Set threshold (e.g., $50/month)
4. Configure notifications

## Security Best Practices

1. **Rotate Secrets Regularly**
   ```bash
   aws secretsmanager rotate-secret --secret-id email-marketing-config-development
   ```

2. **Enable MFA for AWS Console**
3. **Use IAM roles with least privilege**
4. **Enable CloudTrail for audit logging**
5. **Enable GuardDuty for threat detection**

## Production Checklist

- [ ] Deploy to production environment
- [ ] Configure SES for production (request production access)
- [ ] Set dry_run to false in Secrets Manager
- [ ] Enable API authentication (API keys or JWT)
- [ ] Set up CloudWatch alarms
- [ ] Configure backup strategy
- [ ] Set up monitoring dashboards
- [ ] Document runbooks
- [ ] Set up CI/CD pipeline
- [ ] Configure disaster recovery procedures

