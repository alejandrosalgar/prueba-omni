# Architecture Documentation

> 📊 **Para diagramas detallados de servicios AWS con Mermaid, consulta [AWS_ARCHITECTURE_DIAGRAM.md](./AWS_ARCHITECTURE_DIAGRAM.md)**

## System Architecture

### High-Level Overview

The Email Marketing Serverless System is built on AWS using a microservices architecture with serverless components. The system processes CSV files containing email campaigns, queues email sending tasks, and tracks email status through a GraphQL API.

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Application                    │
└────────────────────────┬────────────────────────────────────┘
                          │
                          │ HTTPS/REST
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (REST API)                     │
│  - POST /upload                                               │
│  - POST /graphql                                              │
│  - GET /docs                                                  │
└────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Lambda (api_handler)                    │
│  - Handles file uploads                                       │
│  - Generates pre-signed URLs                                  │
│  - Exposes GraphQL endpoint                                   │
│  - Invokes CSV processing Lambda                              │
└──────┬───────────────────────────────┬───────────────────────┘
       │                               │
       │                               │
       ▼                               ▼
┌──────────────┐              ┌──────────────────────┐
│  S3 Bucket   │              │ CSV Processing      │
│ (CSV Files)  │              │ Lambda              │
└──────────────┘              └──────┬──────────────┘
                                     │
                                     │ SQS Messages
                                     ▼
                            ┌──────────────────┐
                            │   SQS Queue      │
                            │ (Email Tasks)    │
                            └──────┬───────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    │ (Success)                   │ (Failed)
                    ▼                             ▼
            ┌──────────────┐            ┌──────────────┐
            │Email Worker  │            │     DLQ     │
            │   Lambda     │            │  (Failed)   │
            └──────┬───────┘            └──────────────┘
                   │
                   │ SES API
                   ▼
            ┌──────────────┐
            │   AWS SES    │
            │ (Email Send) │
            └──────┬───────┘
                   │
                   │ Status Update
                   ▼
            ┌──────────────┐
            │  DynamoDB    │
            │ (Status)     │
            └──────────────┘
```

## Data Flow

### 1. CSV Upload Flow

1. **Client** uploads CSV file via POST /upload
2. **API Gateway** routes request to FastAPI Lambda
3. **FastAPI Lambda**:
   - Validates file (type, size)
   - Uploads to S3
   - Generates batch ID
   - Invokes CSV processing Lambda (async)
4. **CSV Processing Lambda**:
   - Downloads CSV from S3
   - Validates CSV structure
   - Checks idempotency (file hash)
   - Parses rows
   - Creates DynamoDB records (status: PENDING)
   - Enqueues email tasks to SQS
5. Returns batch ID to client

### 2. Email Sending Flow

1. **SQS** triggers Email Worker Lambda
2. **Email Worker Lambda**:
   - Receives batch of messages (up to 10)
   - For each message:
     - Gets configuration from Secrets Manager
     - Sends email via SES (or simulates in dry-run)
     - Updates DynamoDB status (SENT or ERROR)
   - Handles partial batch failures
3. Failed messages go to DLQ after 3 retries

### 3. Status Query Flow

1. **Client** sends GraphQL query via POST /graphql
2. **API Gateway** routes to FastAPI Lambda
3. **FastAPI Lambda**:
   - Parses GraphQL query
   - Queries DynamoDB (with filters)
   - Returns paginated results
4. **Client** receives email status data

## Idempotency Strategy

### File-Level Idempotency

- Calculate SHA256 hash of CSV file content
- Store hash in DynamoDB with batch metadata
- If hash exists, return existing batch ID
- Prevents duplicate processing of same file

### Email-Level Idempotency

- Check for existing email in batch (batch_id + email)
- Skip if already exists
- Prevents duplicate emails in same batch

## Error Handling

### CSV Processing Errors

- Invalid CSV format → Return error to client
- Missing required columns → Return error to client
- File too large → Return error to client
- Processing errors → Log to CloudWatch, return error

### Email Sending Errors

- SES errors → Update status to ERROR, log error message
- Retry up to 3 times via SQS
- After 3 failures → Move to DLQ
- Partial batch failures → Use SQS batch item failures

### API Errors

- Validation errors → Return 400 with error details
- Internal errors → Return 500, log to CloudWatch
- Timeout errors → Return 504

## Security Architecture

### IAM Roles

- **Lambda Execution Role**: Base role for all Lambdas
  - CloudWatch Logs
  - X-Ray tracing
  - S3 (CSV bucket only)
  - DynamoDB (status table only)
  - SQS (email queue only)
  - SES (send email)
  - Secrets Manager (read config)

### Secrets Management

- Configuration stored in AWS Secrets Manager
- Secrets include:
  - SES from email address
  - Dry-run mode flag
- Secrets rotated manually (can be automated)

### Encryption

- **S3**: Server-side encryption (S3-managed keys)
- **DynamoDB**: Encryption at rest (AWS-managed keys)
- **SQS**: Server-side encryption (SQS-managed keys)
- **Secrets Manager**: Encryption at rest and in transit

## Scalability

### Horizontal Scaling

- **Lambda**: Auto-scales based on request volume
- **SQS**: Handles high message throughput
- **DynamoDB**: On-demand scaling
- **API Gateway**: Auto-scales to handle traffic

### Concurrency Limits

- CSV Processing Lambda: 5 concurrent executions
- Email Worker Lambda: 10 concurrent executions
- API Lambda: No limit (auto-scales)

### Performance Optimization

- SQS batch processing (up to 10 messages)
- DynamoDB GSI for efficient queries
- S3 pre-signed URLs for direct uploads
- X-Ray tracing for performance monitoring

## Cost Optimization

### Serverless Architecture

- Pay only for what you use
- No idle costs
- Automatic scaling

### Resource Optimization

- DynamoDB on-demand billing
- S3 lifecycle policies (delete old files)
- CloudWatch Logs retention (30 days)
- Reserved concurrency limits

### Cost Monitoring

- CloudWatch metrics for usage
- Cost allocation tags
- Monthly cost estimation in README

## Observability

### Logging

- All Lambda functions log to CloudWatch Logs
- Structured logging with context
- Error logging with stack traces

### Metrics

- Lambda invocations and errors
- SQS queue depth
- DynamoDB read/write capacity
- API Gateway request count and latency

### Tracing

- X-Ray tracing enabled for all Lambdas
- Distributed tracing across services
- Performance bottleneck identification

### Alarms

- DLQ message count (alert on failures)
- Lambda error rate (alert on high errors)
- API Gateway 5xx errors (alert on API issues)

## Disaster Recovery

### Backup Strategy

- DynamoDB point-in-time recovery enabled
- S3 versioning enabled
- CloudFormation stacks for infrastructure

### Recovery Procedures

1. Restore DynamoDB from backup if needed
2. Redeploy infrastructure via CDK
3. Replay failed messages from DLQ

## Future Enhancements

### Potential Improvements

1. **CI/CD Pipeline**
   - GitHub Actions for automated deployment
   - Automated testing
   - Staging environment

2. **Enhanced Monitoring**
   - Custom CloudWatch dashboards
   - SNS notifications for alerts
   - Cost anomaly detection

3. **Multi-Region Deployment**
   - Active-passive setup
   - Cross-region replication

4. **API Authentication**
   - API keys or JWT tokens
   - Rate limiting per user

5. **Advanced Features**
   - Email templates
   - Scheduled campaigns
   - A/B testing
   - Analytics dashboard

