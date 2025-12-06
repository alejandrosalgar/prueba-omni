"""
GraphQL Schema for Email Marketing API.

Provides query interface for email status tracking with filtering
and pagination support.
"""

import base64
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key
from strawberry import field, type

dynamodb = boto3.resource("dynamodb")
table_name: Optional[str] = None


def get_table() -> Any:
    """
    Get DynamoDB table instance.

    Lazy-loads table name from environment variable on first call.

    Returns:
        DynamoDB Table resource instance

    Raises:
        ValueError: If DYNAMODB_TABLE_NAME environment variable is not set
    """
    global table_name
    if table_name is None:
        table_name = os.getenv("DYNAMODB_TABLE_NAME", "")
    if not table_name:
        raise ValueError("DYNAMODB_TABLE_NAME environment variable not set")
    return dynamodb.Table(table_name)


@type
class EmailStatus:
    """
    Email status type.

    Represents the status of an email in the system.
    """

    batch_id: str
    email: str
    subject: str
    content: str
    status: str
    created_at: str
    updated_at: str
    error_message: Optional[str] = None
    sent_at: Optional[str] = None


@type
class EmailStatusConnection:
    """
    Paginated email status connection.

    Provides pagination support for email status queries.
    """

    items: List[EmailStatus]
    next_token: Optional[str] = None
    total: int


@type
class Query:
    """
    GraphQL query root.

    Entry point for all GraphQL queries.
    """

    @field
    def list_email_status(
        self,
        status: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        batch_id: Optional[str] = None,
        limit: Optional[int] = 50,
        next_token: Optional[str] = None,
    ) -> EmailStatusConnection:
        """
        List email status with filters.

        Supports filtering by status, date range, and batch ID.
        Results are paginated using cursor-based pagination.

        Args:
            status: List of statuses to filter by (PENDING, SENT, ERROR)
            from_date: Start date in ISO 8601 format (YYYY-MM-DD)
            to_date: End date in ISO 8601 format (YYYY-MM-DD)
            batch_id: Filter by specific batch ID
            limit: Maximum number of results (default: 50, max: 1000)
            next_token: Pagination token from previous query

        Returns:
            EmailStatusConnection containing paginated results
        """
        return list_email_status(
            status=status,
            from_date=from_date,
            to_date=to_date,
            batch_id=batch_id,
            limit=limit,
            next_token=next_token,
        )


def list_email_status(
    status: Optional[List[str]] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    batch_id: Optional[str] = None,
    limit: Optional[int] = 50,
    next_token: Optional[str] = None,
) -> EmailStatusConnection:
    """
    Query DynamoDB for email status with filtering and pagination.

    Supports multiple query strategies based on provided filters:
    - batch_id: Query by partition key (most efficient)
    - status: Query using GSI (status-created_at-index)
    - date range: Query using date partition GSI
    - no filters: Scan table (least efficient, use sparingly)

    Args:
        status: List of statuses to filter by (PENDING, SENT, ERROR)
        from_date: Start date in ISO 8601 format (YYYY-MM-DD)
        to_date: End date in ISO 8601 format (YYYY-MM-DD)
        batch_id: Filter by specific batch ID
        limit: Maximum number of results (default: 50, max: 1000, min: 1)
        next_token: Base64-encoded pagination token from previous query

    Returns:
        EmailStatusConnection containing:
            - items: List of EmailStatus objects
            - next_token: Pagination token for next page (if available)
            - total: Total number of items in current page

    Note:
        Returns empty result on any error to prevent GraphQL query failures.
    """
    table = get_table()

    if limit is None:
        limit = 50
    if limit > 1000:
        limit = 1000
    if limit < 1:
        limit = 1

    items: List[Dict[str, Any]] = []
    last_evaluated_key: Optional[Dict[str, Any]] = None

    try:
        exclusive_start_key: Optional[Dict[str, Any]] = None
        if next_token:
            try:
                exclusive_start_key = json.loads(base64.b64decode(next_token).decode())
            except Exception:
                pass

        if batch_id:
            query_params: Dict[str, Any] = {
                "KeyConditionExpression": Key("batch_id").eq(batch_id),
                "Limit": limit,
            }
            if exclusive_start_key:
                query_params["ExclusiveStartKey"] = exclusive_start_key
            response = table.query(**query_params)
            items = response.get("Items", [])
            last_evaluated_key = response.get("LastEvaluatedKey")

        elif status and len(status) > 0:
            all_items: List[Dict[str, Any]] = []
            for stat in status:
                response = table.query(
                    IndexName="status-created_at-index",
                    KeyConditionExpression=Key("status").eq(stat),
                    Limit=limit,
                )
                all_items.extend(response.get("Items", []))

            if from_date or to_date:
                filtered_items: List[Dict[str, Any]] = []
                for item in all_items:
                    created_at = item.get("created_at", "")
                    if from_date and created_at < from_date:
                        continue
                    if to_date and created_at > to_date:
                        continue
                    filtered_items.append(item)
                all_items = filtered_items

            all_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            items = all_items[:limit]

        elif from_date or to_date:
            date_partition = from_date[:10] if from_date else datetime.now().strftime("%Y-%m-%d")
            response = table.query(
                IndexName="created_at-index",
                KeyConditionExpression=Key("date_partition").eq(date_partition),
                Limit=limit,
            )
            items = response.get("Items", [])

            if from_date or to_date:
                filtered_items = []
                for item in items:
                    created_at = item.get("created_at", "")
                    if from_date and created_at < from_date:
                        continue
                    if to_date and created_at > to_date:
                        continue
                    filtered_items.append(item)
                items = filtered_items

        else:
            scan_params: Dict[str, Any] = {"Limit": limit}
            if exclusive_start_key:
                scan_params["ExclusiveStartKey"] = exclusive_start_key
            response = table.scan(**scan_params)
            items = response.get("Items", [])
            last_evaluated_key = response.get("LastEvaluatedKey")

        email_statuses: List[EmailStatus] = []
        for item in items:
            email_statuses.append(
                EmailStatus(
                    batch_id=item.get("batch_id", ""),
                    email=item.get("email", ""),
                    subject=item.get("subject", ""),
                    content=item.get("content", ""),
                    status=item.get("status", "PENDING"),
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                    error_message=item.get("error_message"),
                    sent_at=item.get("sent_at"),
                )
            )

        next_token_str: Optional[str] = None
        if last_evaluated_key:
            next_token_str = base64.b64encode(json.dumps(last_evaluated_key).encode()).decode()

        return EmailStatusConnection(
            items=email_statuses,
            next_token=next_token_str,
            total=len(email_statuses),
        )

    except Exception as e:
        print(f"Error querying email status: {e}")
        return EmailStatusConnection(items=[], next_token=None, total=0)
