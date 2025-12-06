"""
Storage Stack for Email Marketing Serverless Infrastructure.

This stack creates and manages all storage-related resources including:
- S3 bucket for CSV file uploads
- DynamoDB table for email status tracking
"""

from typing import Any, Dict

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack, Tags
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_s3 as s3
from constructs import Construct

from infrastructure.shared.constants import (
    DEFAULT_ENVIRONMENT,
    DEFAULT_TAGS,
    DYNAMODB_POINT_IN_TIME_RECOVERY,
    DYNAMODB_TABLE_NAME,
    S3_BUCKET_PREFIX,
    S3_CSV_PREFIX,
    S3_VERSIONING_ENABLED,
)


class EmailStorageStack(Stack):
    """
    Storage stack for the email marketing infrastructure.

    This stack creates all storage-related resources including S3 bucket
    for CSV uploads and DynamoDB table for email status tracking.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str = DEFAULT_ENVIRONMENT,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the storage stack.

        Args:
            scope: The parent construct
            construct_id: Unique identifier for this stack
            environment: Environment name (dev, staging, prod)
            **kwargs: Additional arguments passed to Stack
        """
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment

        self._create_s3_bucket()
        self._create_dynamodb_table()
        self._create_outputs()
        self._apply_tags()

    def _create_s3_bucket(self) -> None:
        """
        Create S3 bucket for CSV file uploads.

        Creates S3 bucket with versioning, encryption, lifecycle rules,
        and CORS configuration for CSV file storage.
        """
        self.csv_bucket = s3.Bucket(
            self,
            "CsvUploadBucket",
            bucket_name=f"{S3_BUCKET_PREFIX}-csv-{self.account}-{self.region}",
            versioned=S3_VERSIONING_ENABLED,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldCsvFiles",
                    enabled=True,
                    prefix=f"{S3_CSV_PREFIX}/",
                    expiration=Duration.days(90),
                ),
            ],
            cors=[
                s3.CorsRule(
                    allowed_origins=["*"],
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                    ],
                    allowed_headers=["*"],
                    max_age=3000,
                )
            ],
        )

    def _create_dynamodb_table(self) -> None:
        """
        Create DynamoDB table for email status tracking.

        Creates DynamoDB table with composite key (batch_id, email),
        enables Point-in-Time Recovery if configured, and creates
        Global Secondary Indexes for querying by status and date range.
        """
        self.email_status_table = dynamodb.Table(
            self,
            "EmailStatusTable",
            table_name=f"{DYNAMODB_TABLE_NAME}-{self.env_name}",
            partition_key=dynamodb.Attribute(
                name="batch_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )

        if DYNAMODB_POINT_IN_TIME_RECOVERY:
            cfn_table = self.email_status_table.node.default_child
            if cfn_table:
                cfn_table.add_property_override(
                    "PointInTimeRecoverySpecification",
                    {"PointInTimeRecoveryEnabled": True},
                )

        self.email_status_table.add_global_secondary_index(
            index_name="status-created_at-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING,
            ),
        )

        self.email_status_table.add_global_secondary_index(
            index_name="created_at-index",
            partition_key=dynamodb.Attribute(
                name="date_partition",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING,
            ),
        )

    def _create_outputs(self) -> None:
        """
        Create CloudFormation outputs for cross-stack references.

        Exports S3 bucket and DynamoDB table identifiers for use
        by other stacks in the infrastructure.
        """
        CfnOutput(
            self,
            "CsvBucketName",
            value=self.csv_bucket.bucket_name,
            description="Name of the S3 bucket for CSV uploads",
            export_name=f"{self.stack_name}-CsvBucketName",
        )

        CfnOutput(
            self,
            "CsvBucketArn",
            value=self.csv_bucket.bucket_arn,
            description="ARN of the S3 bucket for CSV uploads",
            export_name=f"{self.stack_name}-CsvBucketArn",
        )

        CfnOutput(
            self,
            "EmailStatusTableName",
            value=self.email_status_table.table_name,
            description="Name of the DynamoDB table for email status",
            export_name=f"{self.stack_name}-EmailStatusTableName",
        )

        CfnOutput(
            self,
            "EmailStatusTableArn",
            value=self.email_status_table.table_arn,
            description="ARN of the DynamoDB table for email status",
            export_name=f"{self.stack_name}-EmailStatusTableArn",
        )

        CfnOutput(
            self,
            "EmailStatusTableStreamArn",
            value=self.email_status_table.table_stream_arn or "",
            description="ARN of the DynamoDB stream for email status",
            export_name=f"{self.stack_name}-EmailStatusTableStreamArn",
        )

    def _apply_tags(self) -> None:
        """
        Apply standard tags to all resources in the stack.

        Applies default tags from constants and adds environment-specific tags.
        """
        for key, value in DEFAULT_TAGS.items():
            Tags.of(self).add(key, value)

        Tags.of(self).add("Environment", self.env_name)
        Tags.of(self).add("StackType", "Storage")

    def get_storage_outputs(self) -> Dict[str, str]:
        """
        Get storage outputs for other stacks.

        Returns:
            Dictionary containing S3 bucket and DynamoDB table identifiers
        """
        return {
            "csv_bucket_name": self.csv_bucket.bucket_name,
            "csv_bucket_arn": self.csv_bucket.bucket_arn,
            "email_status_table_name": self.email_status_table.table_name,
            "email_status_table_arn": self.email_status_table.table_arn,
            "email_status_table_stream_arn": self.email_status_table.table_stream_arn or "",
        }
