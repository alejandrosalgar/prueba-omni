"""
FastAPI Lambda Handler for Email Marketing API.

This handler provides:
- POST /upload - CSV file upload endpoint
- POST /graphql - GraphQL endpoint for querying email status
- GET /docs - API documentation
"""

import json
import os
import uuid
from typing import Any, Dict, Optional

import boto3
from aws_xray_sdk.core import patch_all
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from graphql_schema import Query
from mangum import Mangum
from strawberry.fastapi import GraphQLRouter
from strawberry.schema import Schema

patch_all()

app = FastAPI(
    title="Email Marketing API",
    description="Serverless Email Marketing System API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

lambda_client = boto3.client("lambda")
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")
CSV_PROCESSING_FUNCTION_NAME = os.getenv("CSV_PROCESSING_FUNCTION_NAME", "")
SECRET_NAME = os.getenv("SECRET_NAME", "")


@app.get("/")
async def root() -> Dict[str, Any]:
    """
    Root endpoint providing API information.

    Returns:
        Dictionary containing API metadata and available endpoints.
    """
    return {
        "message": "Email Marketing API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload",
            "graphql": "/graphql",
            "docs": "/docs",
        },
    }


@app.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    use_presigned_url: Optional[bool] = Form(False),
) -> Dict[str, Any]:
    """
    Upload CSV file endpoint.

    Supports two modes:
    1. Direct upload (multipart/form-data): File is uploaded directly to S3
    2. Pre-signed URL upload: Returns a pre-signed URL for client-side upload

    Args:
        file: CSV file to upload
        use_presigned_url: If True, returns pre-signed URL instead of uploading

    Returns:
        Dictionary containing:
            - batchId: Unique identifier for this batch
            - presignedUrl: Pre-signed URL (if use_presigned_url=True)
            - s3Key: S3 key where file is/will be stored
            - message: Status message
            - status: Processing status (if direct upload)

    Raises:
        HTTPException: If file validation fails or upload error occurs
    """
    try:
        if not file.filename or not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="File must be a CSV file")

        batch_id = str(uuid.uuid4())

        if use_presigned_url:
            s3_key = f"csv-uploads/{batch_id}/{file.filename}"
            presigned_url = s3_client.generate_presigned_url(
                "put_object",
                Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
                ExpiresIn=3600,
            )

            return {
                "batchId": batch_id,
                "presignedUrl": presigned_url,
                "s3Key": s3_key,
                "message": "Use the presigned URL to upload your CSV file",
            }

        content = await file.read()
        max_size = 100 * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(
                status_code=400, detail=f"File size exceeds maximum of {max_size} bytes"
            )

        s3_key = f"csv-uploads/{batch_id}/{file.filename}"
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=content,
            ContentType="text/csv",
        )

        lambda_client.invoke(
            FunctionName=CSV_PROCESSING_FUNCTION_NAME,
            InvocationType="Event",
            Payload=json.dumps(
                {
                    "batch_id": batch_id,
                    "s3_bucket": S3_BUCKET_NAME,
                    "s3_key": s3_key,
                    "filename": file.filename,
                }
            ),
        )

        return {
            "batchId": batch_id,
            "message": "CSV file uploaded and processing started",
            "status": "processing",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@app.post("/upload/presigned-url")
async def get_presigned_url(filename: str = Form(...)) -> Dict[str, Any]:
    """
    Get pre-signed URL for CSV upload.

    Generates a pre-signed S3 URL that allows direct client-side upload
    without going through the API Gateway.

    Args:
        filename: Name of the CSV file to upload

    Returns:
        Dictionary containing:
            - batchId: Unique identifier for this batch
            - presignedUrl: Pre-signed URL for uploading (valid for 1 hour)
            - s3Key: S3 key where file will be stored
            - expiresIn: URL expiration time in seconds

    Raises:
        HTTPException: If URL generation fails
    """
    try:
        batch_id = str(uuid.uuid4())
        s3_key = f"csv-uploads/{batch_id}/{filename}"

        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=3600,
        )

        return {
            "batchId": batch_id,
            "presignedUrl": presigned_url,
            "s3Key": s3_key,
            "expiresIn": 3600,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating presigned URL: {str(e)}")


schema = Schema(query=Query)
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for FastAPI application.

    Args:
        event: Lambda event object from API Gateway
        context: Lambda context object

    Returns:
        Dictionary containing HTTP response with statusCode and body
    """
    handler = Mangum(app, lifespan="off")
    return handler(event, context)
