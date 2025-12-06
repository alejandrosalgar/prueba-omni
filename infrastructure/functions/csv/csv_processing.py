"""
CSV Processing Lambda Handler.

This handler processes CSV files uploaded to S3:
1. Downloads CSV from S3
2. Validates and parses CSV
3. Creates email status records in DynamoDB
4. Enqueues email sending tasks to SQS
5. Implements idempotency to prevent duplicates
"""

import csv
import hashlib
import io
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

import boto3
from aws_xray_sdk.core import patch_all
from botocore.exceptions import ClientError

patch_all()

s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")

SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")

REQUIRED_COLUMNS = ["email", "subject", "content"]
MAX_ROWS = 100000
BATCH_SIZE = 100


def calculate_file_hash(content: bytes) -> str:
    """
    Calculate SHA256 hash of file content for idempotency.

    Args:
        content: File content as bytes

    Returns:
        Hexadecimal string representation of SHA256 hash
    """
    return hashlib.sha256(content).hexdigest()


def validate_csv_row(row: Dict[str, str]) -> Tuple[bool, str]:
    """
    Validate a CSV row.

    Checks for required columns and validates email format.

    Args:
        row: CSV row as dictionary with column names as keys

    Returns:
        Tuple containing:
            - bool: True if row is valid, False otherwise
            - str: Error message if invalid, empty string if valid
    """
    for col in REQUIRED_COLUMNS:
        if col not in row or not row[col].strip():
            return False, f"Missing or empty required column: {col}"

    email = row["email"].strip()
    if "@" not in email or "." not in email:
        return False, f"Invalid email format: {email}"

    return True, ""


def process_csv_file(batch_id: str, s3_bucket: str, s3_key: str) -> Dict[str, Any]:
    """
    Process CSV file from S3.

    Downloads CSV, validates structure, creates DynamoDB records,
    and enqueues email tasks to SQS. Implements idempotency at
    both file and email levels.

    Args:
        batch_id: Unique batch identifier
        s3_bucket: S3 bucket name containing the CSV file
        s3_key: S3 object key (path) of the CSV file

    Returns:
        Dictionary containing:
            - batch_id: Batch identifier
            - status: Processing status (completed, duplicate)
            - total: Total number of rows in CSV
            - enqueued: Number of emails successfully enqueued
            - skipped: Number of emails skipped (duplicates/invalid)
            - invalid_rows: List of invalid rows with errors (max 10)
            - message: Status message (if duplicate)
            - existing_batch_id: Original batch ID (if duplicate)

    Raises:
        ValueError: If CSV structure is invalid or exceeds limits
        ClientError: If AWS service calls fail
    """
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        csv_content = response["Body"].read()

        file_hash = calculate_file_hash(csv_content)
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        idempotency_key = f"batch-{file_hash}"

        try:
            response = table.get_item(
                Key={"batch_id": idempotency_key, "email": "__BATCH_METADATA__"}
            )
            if "Item" in response:
                return {
                    "batch_id": batch_id,
                    "status": "duplicate",
                    "message": "This CSV file was already processed",
                    "existing_batch_id": response["Item"].get("original_batch_id"),
                }
        except ClientError:
            pass

        csv_reader = csv.DictReader(io.StringIO(csv_content.decode("utf-8")))
        rows = list(csv_reader)

        if not rows:
            raise ValueError("CSV file is empty")

        csv_columns = set(rows[0].keys())
        required_set = set(REQUIRED_COLUMNS)
        if not required_set.issubset(csv_columns):
            missing = required_set - csv_columns
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        if len(rows) > MAX_ROWS:
            raise ValueError(f"CSV exceeds maximum of {MAX_ROWS} rows")

        valid_rows: List[Dict[str, Any]] = []
        invalid_rows: List[Dict[str, Any]] = []
        enqueued_count = 0
        skipped_count = 0

        current_time = datetime.utcnow().isoformat()
        date_partition = datetime.utcnow().strftime("%Y-%m-%d")

        for i, row in enumerate(rows):
            is_valid, error_msg = validate_csv_row(row)
            if not is_valid:
                invalid_rows.append({"row": i + 1, "error": error_msg})
                skipped_count += 1
                continue

            email = row["email"].strip().lower()

            try:
                existing = table.get_item(Key={"batch_id": batch_id, "email": email})
                if "Item" in existing:
                    skipped_count += 1
                    continue
            except ClientError:
                pass

            item = {
                "batch_id": batch_id,
                "email": email,
                "subject": row["subject"].strip(),
                "content": row["content"].strip(),
                "status": "PENDING",
                "created_at": current_time,
                "updated_at": current_time,
                "date_partition": date_partition,
            }

            try:
                table.put_item(Item=item)
                valid_rows.append(item)
                enqueued_count += 1

                sqs_message = {
                    "batch_id": batch_id,
                    "email": email,
                    "subject": row["subject"].strip(),
                    "content": row["content"].strip(),
                }

                sqs_client.send_message(
                    QueueUrl=SQS_QUEUE_URL,
                    MessageBody=json.dumps(sqs_message),
                    MessageAttributes={
                        "batch_id": {
                            "StringValue": batch_id,
                            "DataType": "String",
                        },
                        "email": {
                            "StringValue": email,
                            "DataType": "String",
                        },
                    },
                )

            except ClientError as e:
                print(f"Error processing row {i+1}: {e}")
                skipped_count += 1

        try:
            table.put_item(
                Item={
                    "batch_id": idempotency_key,
                    "email": "__BATCH_METADATA__",
                    "original_batch_id": batch_id,
                    "file_hash": file_hash,
                    "total_rows": len(rows),
                    "enqueued": enqueued_count,
                    "skipped": skipped_count,
                    "created_at": current_time,
                    "status": "completed",
                }
            )
        except ClientError as e:
            print(f"Error storing batch metadata: {e}")

        return {
            "batch_id": batch_id,
            "status": "completed",
            "total": len(rows),
            "enqueued": enqueued_count,
            "skipped": skipped_count,
            "invalid_rows": invalid_rows[:10],
        }

    except Exception as e:
        print(f"Error processing CSV: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for CSV processing.

    Processes CSV files uploaded to S3 by validating structure,
    creating DynamoDB records, and enqueuing email tasks.

    Args:
        event: Lambda event containing:
            - batch_id: Unique batch identifier
            - s3_bucket: S3 bucket name (optional, defaults to env var)
            - s3_key: S3 object key (required)
            - filename: CSV filename (optional)
        context: Lambda context object

    Returns:
        Dictionary containing:
            - statusCode: HTTP status code (200 or 500)
            - body: JSON string with processing results or error message
    """
    try:
        batch_id = event.get("batch_id")
        s3_bucket = event.get("s3_bucket", S3_BUCKET_NAME)
        s3_key = event.get("s3_key")
        filename = event.get("filename", "unknown.csv")

        if not batch_id or not s3_key:
            raise ValueError("Missing required fields: batch_id or s3_key")

        result = process_csv_file(batch_id, s3_bucket, s3_key)

        return {
            "statusCode": 200,
            "body": json.dumps(result),
        }

    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
