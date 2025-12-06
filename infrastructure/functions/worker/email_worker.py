"""
Email Worker Lambda Handler.

This handler consumes messages from SQS and sends emails via SES:
1. Receives email task from SQS
2. Sends email via SES (or simulates in dry-run mode)
3. Updates email status in DynamoDB
4. Handles errors and retries with partial batch failure support
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import boto3
from aws_xray_sdk.core import patch_all
from botocore.exceptions import ClientError

patch_all()

ses_client = boto3.client("ses", region_name=os.getenv("AWS_REGION", "us-east-1"))
dynamodb = boto3.resource("dynamodb")
secretsmanager = boto3.client("secretsmanager")

DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "")
SECRET_NAME = os.getenv("SECRET_NAME", "")

_config_cache: Optional[Dict[str, Any]] = None


def get_config() -> Dict[str, Any]:
    """
    Get configuration from Secrets Manager.

    Caches configuration in memory to avoid repeated Secrets Manager calls.
    Falls back to default configuration if secret retrieval fails.

    Returns:
        Dictionary containing:
            - ses_from_email: Sender email address
            - dry_run: Boolean string indicating if dry-run mode is enabled
    """
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    try:
        if SECRET_NAME:
            response = secretsmanager.get_secret_value(SecretId=SECRET_NAME)
            secret_string = response["SecretString"]
            _config_cache = json.loads(secret_string)
        else:
            _config_cache = {
                "ses_from_email": "noreply@example.com",
                "dry_run": "true",
            }
    except Exception as e:
        print(f"Error getting secret: {e}")
        _config_cache = {
            "ses_from_email": "noreply@example.com",
            "dry_run": "true",
        }

    return _config_cache


def send_email(
    to_email: str,
    subject: str,
    content: str,
    from_email: str,
    dry_run: bool = True,
) -> Tuple[bool, Optional[str]]:
    """
    Send email via SES or simulate in dry-run mode.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        content: Email body content (plain text)
        from_email: Sender email address (must be verified in SES)
        dry_run: If True, simulates sending without actually sending

    Returns:
        Tuple containing:
            - bool: True if email was sent successfully, False otherwise
            - Optional[str]: Error message if sending failed, None if successful
    """
    if dry_run:
        print(f"[DRY RUN] Would send email to {to_email}: {subject}")
        return True, None

    try:
        response = ses_client.send_email(
            Source=from_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": content, "Charset": "UTF-8"}},
            },
        )

        message_id = response.get("MessageId")
        print(f"Email sent successfully: {message_id}")
        return True, None

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        print(f"Error sending email: {error_code} - {error_message}")
        return False, f"{error_code}: {error_message}"

    except Exception as e:
        print(f"Unexpected error sending email: {e}")
        return False, str(e)


def process_email_task(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single email task from SQS.

    Parses message, sends email via SES, and updates status in DynamoDB.

    Args:
        message: SQS message body (dict or JSON string) containing:
            - batch_id: Batch identifier
            - email: Recipient email address
            - subject: Email subject
            - content: Email content

    Returns:
        Dictionary containing:
            - success: Boolean indicating if processing succeeded
            - batch_id: Batch identifier
            - email: Recipient email address
            - status: Email status (SENT or ERROR)
            - error_message: Error message if failed (optional)
            - error: General error message if processing failed (optional)
    """
    try:
        if isinstance(message, str):
            message_body = json.loads(message)
        else:
            message_body = message

        batch_id = message_body.get("batch_id")
        email = message_body.get("email")
        subject = message_body.get("subject")
        content = message_body.get("content")

        if not all([batch_id, email, subject, content]):
            raise ValueError("Missing required fields in message")

        config = get_config()
        from_email = config.get("ses_from_email", "noreply@example.com")
        dry_run = config.get("dry_run", "true").lower() == "true"

        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        current_time = datetime.utcnow().isoformat()

        success, error_message = send_email(
            to_email=email,
            subject=subject,
            content=content,
            from_email=from_email,
            dry_run=dry_run,
        )

        update_expression = "SET #status = :status, updated_at = :updated_at"
        expression_attribute_names = {"#status": "status"}
        expression_attribute_values = {
            ":status": "SENT" if success else "ERROR",
            ":updated_at": current_time,
        }

        if success:
            expression_attribute_values[":sent_at"] = current_time
            update_expression += ", sent_at = :sent_at"
        else:
            expression_attribute_values[":error_message"] = error_message
            update_expression += ", error_message = :error_message"

        table.update_item(
            Key={"batch_id": batch_id, "email": email},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
        )

        return {
            "success": success,
            "batch_id": batch_id,
            "email": email,
            "status": "SENT" if success else "ERROR",
            "error_message": error_message,
        }

    except Exception as e:
        print(f"Error processing email task: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for email worker.

    Processes SQS messages in batch, sending emails and updating status.
    Supports partial batch failure handling for SQS.

    Args:
        event: SQS event containing:
            - Records: List of SQS message records, each with:
                - body: JSON string with email task data
                - messageId: Unique message identifier
        context: Lambda context object

    Returns:
        Dictionary containing:
            - statusCode: HTTP status code (200 or 500)
            - body: JSON string with processing results
            - batchItemFailures: List of failed message IDs (for SQS retry)
    """
    results: List[Dict[str, Any]] = []
    batch_item_failures: List[Dict[str, str]] = []

    try:
        for record in event.get("Records", []):
            try:
                message_body = record.get("body", "{}")
                message_id = record.get("messageId")

                result = process_email_task(message_body)

                if not result.get("success"):
                    batch_item_failures.append({"itemIdentifier": message_id})

                results.append(result)

            except Exception as e:
                print(f"Error processing record: {e}")
                message_id = record.get("messageId", "")
                if message_id:
                    batch_item_failures.append({"itemIdentifier": message_id})

        response: Dict[str, Any] = {
            "statusCode": 200,
            "body": json.dumps({"processed": len(results), "results": results}),
        }

        if batch_item_failures:
            response["batchItemFailures"] = batch_item_failures

        return response

    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }

