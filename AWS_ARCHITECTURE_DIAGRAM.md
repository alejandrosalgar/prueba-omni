# Diagrama de Arquitectura AWS - Email Marketing Serverless

## Diagrama de Servicios AWS

```mermaid
graph TB
    subgraph "Cliente"
        Client[Cliente/Usuario]
    end

    subgraph "AWS - Capa de API"
        APIGW[API Gateway<br/>REST API<br/>gev0tzxg5j]
        APIGW -->|POST /upload| APILambda
        APIGW -->|POST /graphql| APILambda
        APIGW -->|GET /docs| APILambda
    end

    subgraph "AWS - Compute (Lambda Functions)"
        APILambda[Lambda: email-api-development<br/>FastAPI + GraphQL<br/>Handler: api_handler]
        CSVLambda[Lambda: email-csv-processing-development<br/>CSV Processing<br/>Handler: csv_processing]
        WorkerLambda[Lambda: email-worker-development<br/>Email Sender<br/>Handler: email_worker]
    end

    subgraph "AWS - Storage"
        S3Bucket[S3 Bucket<br/>email-marketing-csv-607136582566-us-east-1<br/>CSV Files Storage]
        DynamoDB[(DynamoDB Table<br/>email-status-development<br/>PK: batch_id<br/>SK: email<br/>GSI: status-index)]
    end

    subgraph "AWS - Messaging"
        SQSQueue[SQS Queue<br/>email-send-queue-development<br/>Email Tasks Queue]
        DLQ[SQS Dead Letter Queue<br/>email-send-dlq-development<br/>Failed Messages]
    end

    subgraph "AWS - Email Service"
        SES[AWS SES<br/>Simple Email Service<br/>Email Sending]
    end

    subgraph "AWS - Security & Configuration"
        SecretsManager[Secrets Manager<br/>email-marketing-config-development<br/>SES Config, Dry-run Mode]
        IAMRole[IAM Role<br/>EmailMarketingLambdaExecution-development<br/>Execution Permissions]
    end

    subgraph "AWS - Observability"
        CloudWatch[CloudWatch Logs<br/>Lambda Logs<br/>Metrics & Alarms]
        XRay[X-Ray<br/>Distributed Tracing<br/>Performance Monitoring]
    end

    %% Flujo de Upload
    Client -->|1. POST /upload<br/>multipart/form-data| APIGW
    APILambda -->|2. Upload CSV| S3Bucket
    APILambda -->|3. Invoke Async| CSVLambda
    CSVLambda -->|4. Download CSV| S3Bucket
    CSVLambda -->|5. Create Records| DynamoDB
    CSVLambda -->|6. Send Messages| SQSQueue
    APILambda -->|7. Return batchId| Client

    %% Flujo de Email Sending
    SQSQueue -->|8. Trigger| WorkerLambda
    WorkerLambda -->|9. Get Config| SecretsManager
    WorkerLambda -->|10. Send Email| SES
    WorkerLambda -->|11. Update Status| DynamoDB
    SQSQueue -.->|After 3 retries| DLQ

    %% Flujo de GraphQL Query
    Client -->|12. POST /graphql<br/>GraphQL Query| APIGW
    APILambda -->|13. Query| DynamoDB
    APILambda -->|14. Return Results| Client

    %% Permisos IAM
    IAMRole -.->|Assume Role| APILambda
    IAMRole -.->|Assume Role| CSVLambda
    IAMRole -.->|Assume Role| WorkerLambda

    %% Observability
    APILambda -.->|Logs| CloudWatch
    CSVLambda -.->|Logs| CloudWatch
    WorkerLambda -.->|Logs| CloudWatch
    APILambda -.->|Traces| XRay
    CSVLambda -.->|Traces| XRay
    WorkerLambda -.->|Traces| XRay

    %% Styling
    classDef awsService fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:#000
    classDef lambda fill:#FF6B6B,stroke:#232F3E,stroke-width:2px,color:#000
    classDef storage fill:#4ECDC4,stroke:#232F3E,stroke-width:2px,color:#000
    classDef messaging fill:#95E1D3,stroke:#232F3E,stroke-width:2px,color:#000
    classDef security fill:#F38181,stroke:#232F3E,stroke-width:2px,color:#000
    classDef observability fill:#AA96DA,stroke:#232F3E,stroke-width:2px,color:#000
    classDef client fill:#C7CEEA,stroke:#232F3E,stroke-width:2px,color:#000

    class APIGW,SES awsService
    class APILambda,CSVLambda,WorkerLambda lambda
    class S3Bucket,DynamoDB storage
    class SQSQueue,DLQ messaging
    class SecretsManager,IAMRole security
    class CloudWatch,XRay observability
    class Client client
```

## Diagrama de Stacks CDK

```mermaid
graph LR
    subgraph "CDK Stacks"
        StorageStack[EmailMarketingStorageStack<br/>S3 + DynamoDB]
        SecurityStack[EmailMarketingSecurityStack<br/>IAM + Secrets Manager]
        ProcessingStack[EmailMarketingProcessingStack<br/>SQS + CSV Lambda]
        WorkerStack[EmailWorkerStack<br/>Email Worker Lambda]
        APIStack[EmailMarketingApiStack<br/>API Gateway + API Lambda]
    end

    StorageStack -->|Dependencies| SecurityStack
    StorageStack -->|Dependencies| ProcessingStack
    SecurityStack -->|Dependencies| ProcessingStack
    SecurityStack -->|Dependencies| WorkerStack
    SecurityStack -->|Dependencies| APIStack
    ProcessingStack -->|Dependencies| WorkerStack
    ProcessingStack -->|Dependencies| APIStack

    classDef stack fill:#FFD93D,stroke:#232F3E,stroke-width:2px,color:#000
    class StorageStack,SecurityStack,ProcessingStack,WorkerStack,APIStack stack
```

## Flujo de Datos Detallado

### 1. Flujo de Upload de CSV

```mermaid
sequenceDiagram
    participant C as Cliente
    participant AG as API Gateway
    participant AL as API Lambda
    participant S3 as S3 Bucket
    participant CL as CSV Processing Lambda
    participant DDB as DynamoDB
    participant SQS as SQS Queue

    C->>AG: POST /upload (CSV file)
    AG->>AL: Invoke Lambda
    AL->>AL: Validate file (size, type)
    AL->>S3: Upload CSV file
    S3-->>AL: Upload success
    AL->>AL: Generate batchId
    AL->>CL: Invoke async (S3 key, batchId)
    AL-->>C: Return {batchId, total, enqueued, skipped}
    
    Note over CL: Process CSV
    CL->>S3: Download CSV
    CL->>CL: Parse CSV rows
    CL->>CL: Check idempotency (file hash)
    loop For each email row
        CL->>DDB: Create record (status: PENDING)
        CL->>SQS: Send message (email task)
    end
```

### 2. Flujo de Envío de Emails

```mermaid
sequenceDiagram
    participant SQS as SQS Queue
    participant WL as Email Worker Lambda
    participant SM as Secrets Manager
    participant SES as AWS SES
    participant DDB as DynamoDB
    participant DLQ as Dead Letter Queue

    SQS->>WL: Trigger (batch of messages)
    WL->>SM: Get configuration
    SM-->>WL: Config (from_email, dry_run)
    
    loop For each message (up to 10)
        WL->>WL: Parse email task
        alt Dry-run mode
            WL->>WL: Simulate email send
        else Real mode
            WL->>SES: Send email
            SES-->>WL: Success/Error
        end
        
        alt Success
            WL->>DDB: Update status = SENT
        else Error
            WL->>DDB: Update status = ERROR
            WL->>SQS: Return failed message ID
        end
    end
    
    alt After 3 retries
        SQS->>DLQ: Move failed messages
    end
```

### 3. Flujo de Consulta GraphQL

```mermaid
sequenceDiagram
    participant C as Cliente
    participant AG as API Gateway
    participant AL as API Lambda
    participant DDB as DynamoDB

    C->>AG: POST /graphql (query)
    AG->>AL: Invoke Lambda
    AL->>AL: Parse GraphQL query
    AL->>AL: Build DynamoDB query
    
    alt Filter by status
        AL->>DDB: Query GSI (status-index)
    else Filter by date range
        AL->>DDB: Scan with filter (created_at)
    else Filter by batchId
        AL->>DDB: Query PK (batch_id)
    end
    
    DDB-->>AL: Results
    AL->>AL: Apply pagination
    AL->>AL: Format GraphQL response
    AL-->>C: Return EmailStatusConnection
```

## Componentes y Servicios AWS

### Servicios Utilizados

| Servicio | Propósito | Configuración |
|----------|-----------|---------------|
| **API Gateway** | REST API endpoint | Stage: v1, CORS habilitado |
| **Lambda** | Serverless compute | 3 funciones, Python 3.11 |
| **S3** | Almacenamiento de CSV | Bucket con versionado |
| **DynamoDB** | Base de datos de estados | On-demand, GSI para queries |
| **SQS** | Cola de mensajes | Queue + DLQ para errores |
| **SES** | Envío de emails | Configurado vía Secrets Manager |
| **Secrets Manager** | Configuración segura | Secret con SES config |
| **IAM** | Permisos y roles | Rol de ejecución para Lambdas |
| **CloudWatch** | Logs y métricas | Logs automáticos, métricas |
| **X-Ray** | Trazado distribuido | Habilitado en todas las Lambdas |

### Permisos IAM por Lambda

#### API Lambda
- `s3:PutObject`, `s3:GetObject` (bucket CSV)
- `dynamodb:Query`, `dynamodb:Scan` (tabla de estados)
- `lambda:InvokeFunction` (CSV processing Lambda)
- `secretsmanager:GetSecretValue` (config)

#### CSV Processing Lambda
- `s3:GetObject` (bucket CSV)
- `dynamodb:PutItem`, `dynamodb:GetItem` (tabla de estados)
- `sqs:SendMessage` (cola de emails)

#### Email Worker Lambda
- `dynamodb:UpdateItem`, `dynamodb:GetItem` (tabla de estados)
- `sqs:ReceiveMessage`, `sqs:DeleteMessage` (cola de emails)
- `ses:SendEmail` (envío de emails)
- `secretsmanager:GetSecretValue` (config)

## Endpoints Disponibles

- **API Base URL**: `https://gev0tzxg5j.execute-api.us-east-1.amazonaws.com/v1/`
- **Upload**: `POST /v1/upload`
- **GraphQL**: `POST /v1/graphql`
- **Documentación**: `GET /v1/docs`
- **OpenAPI Schema**: `GET /v1/openapi.json`

## Observabilidad

### CloudWatch Logs
- `/aws/lambda/email-api-development`
- `/aws/lambda/email-csv-processing-development`
- `/aws/lambda/email-worker-development`

### X-Ray Traces
- Trazado distribuido entre todos los servicios
- Identificación de cuellos de botella
- Análisis de latencia

### Métricas Clave
- Lambda invocations y errores
- SQS queue depth
- DynamoDB read/write units
- API Gateway request count y latency

