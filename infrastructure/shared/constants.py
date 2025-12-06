"""
Constants and Configuration for Email Marketing Serverless Infrastructure

This module contains all the constants, default values, and configuration
parameters used across the email marketing infrastructure.
"""

# Project Configuration
PROJECT_NAME = "email-marketing"
PROJECT_DESCRIPTION = "Serverless Email Marketing System"
VERSION = "1.0.0"

# Environment Configuration
DEFAULT_ENVIRONMENT = "development"
SUPPORTED_ENVIRONMENTS = ["development", "staging", "production"]

# AWS Configuration
DEFAULT_REGION = "us-east-1"
DEFAULT_ACCOUNT = "123456789012"  # Placeholder, will be replaced at runtime

# Stack Names
STORAGE_STACK_NAME = "EmailMarketingStorageStack"
SECURITY_STACK_NAME = "EmailMarketingSecurityStack"
PROCESSING_STACK_NAME = "EmailMarketingProcessingStack"
WORKER_STACK_NAME = "EmailMarketingWorkerStack"
API_STACK_NAME = "EmailMarketingApiStack"

# S3 Configuration
S3_BUCKET_PREFIX = "email-marketing"
S3_VERSIONING_ENABLED = True
S3_ENCRYPTION = "S3_MANAGED"
S3_BLOCK_PUBLIC_ACCESS = True
S3_MAX_FILE_SIZE_MB = 100  # Maximum CSV file size: 100MB
S3_CSV_PREFIX = "csv-uploads"
S3_PRESIGNED_URL_EXPIRATION_SECONDS = 3600  # 1 hour

# DynamoDB Configuration
DYNAMODB_TABLE_NAME = "email-status"
DYNAMODB_BILLING_MODE = "PAY_PER_REQUEST"  # On-demand for cost optimization
DYNAMODB_POINT_IN_TIME_RECOVERY = True

# SQS Configuration
SQS_QUEUE_NAME = "email-send-queue"
SQS_VISIBILITY_TIMEOUT_SECONDS = 300  # 5 minutes
SQS_MESSAGE_RETENTION_SECONDS = 1209600  # 14 days
SQS_DLQ_NAME = "email-send-dlq"
SQS_DLQ_MAX_RECEIVE_COUNT = 3

# Lambda Configuration
LAMBDA_RUNTIME = "python3.11"
LAMBDA_TIMEOUT_UPLOAD = 60  # seconds
LAMBDA_TIMEOUT_PROCESSING = 300  # 5 minutes
LAMBDA_TIMEOUT_WORKER = 60  # seconds
LAMBDA_TIMEOUT_API = 30  # seconds
LAMBDA_MEMORY_SIZE_MB = 512
LAMBDA_RESERVED_CONCURRENCY = 10  # Limit concurrent executions

# API Gateway Configuration
API_GATEWAY_STAGE_NAME = "v1"
API_GATEWAY_THROTTLE_RATE = 100  # requests per second
API_GATEWAY_THROTTLE_BURST = 200  # burst capacity

# SES Configuration
SES_REGION = "us-east-1"
SES_DRY_RUN_MODE = True  # Set to False for production
SES_FROM_EMAIL = "noreply@example.com"  # Must be verified in SES

# Email Status Values
EMAIL_STATUS_PENDING = "PENDING"
EMAIL_STATUS_SENT = "SENT"
EMAIL_STATUS_ERROR = "ERROR"

# CSV Configuration
CSV_REQUIRED_COLUMNS = ["email", "subject", "content"]
CSV_MAX_ROWS = 100000  # Maximum rows per CSV file
CSV_BATCH_SIZE = 100  # Process in batches

# Idempotency Configuration
IDEMPOTENCY_TTL_SECONDS = 86400  # 24 hours
IDEMPOTENCY_KEY_PREFIX = "batch-"

# CloudWatch Configuration
CLOUDWATCH_LOG_RETENTION_DAYS = 30
CLOUDWATCH_METRICS_NAMESPACE = "EmailMarketing"
CLOUDWATCH_ALARM_EVALUATION_PERIODS = 2
CLOUDWATCH_ALARM_DATAPOINTS_TO_ALARM = 1

# Secrets Manager Configuration
SECRETS_MANAGER_SECRET_NAME = "email-marketing-config"

# Tags Configuration
DEFAULT_TAGS = {
    "Project": PROJECT_NAME,
    "Environment": DEFAULT_ENVIRONMENT,
    "ManagedBy": "CDK",
    "Owner": "Engineering",
    "CostCenter": "Marketing",
    "Application": "EmailMarketing",
}

# GraphQL Configuration
GRAPHQL_PAGE_SIZE_DEFAULT = 50
GRAPHQL_PAGE_SIZE_MAX = 1000

# Cost Estimation (monthly, approximate)
COST_ESTIMATION = {
    "lambda": "~$5-10 (1M requests)",
    "dynamodb": "~$1-5 (on-demand)",
    "s3": "~$0.50-2 (storage + requests)",
    "sqs": "~$0.40 (1M requests)",
    "api_gateway": "~$3.50 (1M requests)",
    "ses": "~$0.10 (1000 emails)",
    "cloudwatch": "~$1-3 (logs + metrics)",
    "total": "~$12-25/month (low traffic)",
}
