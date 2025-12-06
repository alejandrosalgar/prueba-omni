"""
Processing Stack for Email Marketing Serverless Infrastructure.

This stack creates and manages processing resources including:
- SQS queue for email sending tasks
- Dead Letter Queue (DLQ) for failed messages
- Lambda function for CSV processing
"""

from typing import Any, Dict, Optional

from aws_cdk import CfnOutput, Duration, Stack, Tags
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_sqs as sqs
from constructs import Construct

from infrastructure.shared.constants import (
    DEFAULT_ENVIRONMENT,
    DEFAULT_TAGS,
    LAMBDA_MEMORY_SIZE_MB,
    LAMBDA_TIMEOUT_PROCESSING,
    PROJECT_NAME,
    SQS_DLQ_MAX_RECEIVE_COUNT,
    SQS_DLQ_NAME,
    SQS_MESSAGE_RETENTION_SECONDS,
    SQS_QUEUE_NAME,
    SQS_VISIBILITY_TIMEOUT_SECONDS,
)


class EmailProcessingStack(Stack):
    """
    Processing stack for the email marketing infrastructure.

    This stack creates SQS queues and Lambda functions for
    processing CSV files and queueing email sending tasks.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        storage_stack_outputs: Optional[Dict[str, str]] = None,
        security_stack_outputs: Optional[Dict[str, str]] = None,
        lambda_layer: Optional[_lambda.ILayerVersion] = None,
        environment: str = DEFAULT_ENVIRONMENT,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the processing stack.

        Args:
            scope: The parent construct
            construct_id: Unique identifier for this stack
            storage_stack_outputs: Outputs from the storage stack
            security_stack_outputs: Outputs from the security stack
            lambda_layer: Lambda Layer object with shared dependencies
            environment: Environment name (dev, staging, prod)
            **kwargs: Additional arguments passed to Stack
        """
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment
        self.storage_outputs = storage_stack_outputs or {}
        self.security_outputs = security_stack_outputs or {}
        self.lambda_layer = lambda_layer

        self._create_sqs_queues()
        self._create_lambda_functions()
        self._create_outputs()
        self._apply_tags()

    def _create_sqs_queues(self) -> None:
        """
        Create SQS queue and DLQ for email sending tasks.

        Creates main queue with Dead Letter Queue for failed messages
        after maximum receive count is exceeded.
        """
        self.dlq = sqs.Queue(
            self,
            "EmailSendDLQ",
            queue_name=f"{SQS_DLQ_NAME}-{self.env_name}",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
        )

        self.email_queue = sqs.Queue(
            self,
            "EmailSendQueue",
            queue_name=f"{SQS_QUEUE_NAME}-{self.env_name}",
            visibility_timeout=Duration.seconds(SQS_VISIBILITY_TIMEOUT_SECONDS),
            retention_period=Duration.seconds(SQS_MESSAGE_RETENTION_SECONDS),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=SQS_DLQ_MAX_RECEIVE_COUNT,
                queue=self.dlq,
            ),
        )

    def _create_lambda_functions(self) -> None:
        """
        Create Lambda function for CSV processing.

        Creates CSV processing Lambda with permissions for SQS,
        S3, and DynamoDB. Grants appropriate read/write permissions.
        """
        from aws_cdk import aws_iam as iam

        lambda_role_arn = self.security_outputs.get("lambda_execution_role_arn", "")
        lambda_role: Optional[iam.IRole] = None
        if lambda_role_arn:
            lambda_role = iam.Role.from_role_arn(self, "LambdaExecutionRoleImport", lambda_role_arn)

        # Use layer if provided
        layers = []
        if self.lambda_layer:
            layers.append(self.lambda_layer)

        self.csv_processing_lambda = _lambda.Function(
            self,
            "CsvProcessingFunction",
            function_name=f"email-csv-processing-{self.env_name}",
            code=_lambda.Code.from_asset("infrastructure/functions/csv"),
            handler="csv_processing.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(LAMBDA_TIMEOUT_PROCESSING),
            memory_size=LAMBDA_MEMORY_SIZE_MB,
            role=lambda_role,
            layers=layers,
            environment={
                "ENVIRONMENT": self.env_name,
                "PROJECT_NAME": PROJECT_NAME,
                "SQS_QUEUE_URL": self.email_queue.queue_url,
                "DYNAMODB_TABLE_NAME": self.storage_outputs.get("email_status_table_name", ""),
                "S3_BUCKET_NAME": self.storage_outputs.get("csv_bucket_name", ""),
            },
            tracing=_lambda.Tracing.ACTIVE,
        )

        self.email_queue.grant_send_messages(self.csv_processing_lambda)

        if self.storage_outputs.get("csv_bucket_name"):
            from aws_cdk import aws_s3 as s3

            csv_bucket = s3.Bucket.from_bucket_name(
                self, "CsvBucketImport", self.storage_outputs["csv_bucket_name"]
            )
            csv_bucket.grant_read(self.csv_processing_lambda)

        if self.storage_outputs.get("email_status_table_name"):
            from aws_cdk import aws_dynamodb as dynamodb

            status_table = dynamodb.Table.from_table_name(
                self,
                "EmailStatusTableImport",
                self.storage_outputs["email_status_table_name"],
            )
            status_table.grant_write_data(self.csv_processing_lambda)

    def _create_outputs(self) -> None:
        """
        Create CloudFormation outputs for processing configuration.

        Exports SQS queue and Lambda function identifiers for use
        by other stacks in the infrastructure.
        """
        CfnOutput(
            self,
            "EmailQueueUrl",
            value=self.email_queue.queue_url,
            description="SQS queue URL for email sending tasks",
            export_name=f"{self.stack_name}-EmailQueueUrl",
        )

        CfnOutput(
            self,
            "EmailQueueArn",
            value=self.email_queue.queue_arn,
            description="SQS queue ARN for email sending tasks",
            export_name=f"{self.stack_name}-EmailQueueArn",
        )

        CfnOutput(
            self,
            "DlqUrl",
            value=self.dlq.queue_url,
            description="Dead Letter Queue URL",
            export_name=f"{self.stack_name}-DlqUrl",
        )

        CfnOutput(
            self,
            "DlqArn",
            value=self.dlq.queue_arn,
            description="Dead Letter Queue ARN",
            export_name=f"{self.stack_name}-DlqArn",
        )

        CfnOutput(
            self,
            "CsvProcessingFunctionArn",
            value=self.csv_processing_lambda.function_arn,
            description="CSV processing Lambda function ARN",
            export_name=f"{self.stack_name}-CsvProcessingFunctionArn",
        )

        CfnOutput(
            self,
            "CsvProcessingFunctionName",
            value=self.csv_processing_lambda.function_name,
            description="CSV processing Lambda function name",
            export_name=f"{self.stack_name}-CsvProcessingFunctionName",
        )

    def _apply_tags(self) -> None:
        """
        Apply standard tags to all resources in the stack.

        Applies default tags from constants and adds environment-specific tags.
        """
        for key, value in DEFAULT_TAGS.items():
            Tags.of(self).add(key, value)

        Tags.of(self).add("Environment", self.env_name)
        Tags.of(self).add("StackType", "Processing")

    def get_processing_outputs(self) -> Dict[str, str]:
        """
        Get processing outputs for other stacks.

        Returns:
            Dictionary containing SQS queue and Lambda function identifiers
        """
        return {
            "email_queue_url": self.email_queue.queue_url,
            "email_queue_arn": self.email_queue.queue_arn,
            "dlq_url": self.dlq.queue_url,
            "dlq_arn": self.dlq.queue_arn,
            "csv_processing_function_arn": self.csv_processing_lambda.function_arn,
            "csv_processing_function_name": self.csv_processing_lambda.function_name,
        }
