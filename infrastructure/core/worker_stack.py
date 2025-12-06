"""
Worker Stack for Email Marketing Serverless Infrastructure.

This stack creates and manages worker resources including:
- Lambda function for sending emails (triggered by SQS)
"""

from typing import Any, Dict, Optional

from aws_cdk import CfnOutput, Duration, Stack, Tags
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_lambda_event_sources as lambda_event_sources
from constructs import Construct

from infrastructure.shared.constants import (
    DEFAULT_ENVIRONMENT,
    DEFAULT_TAGS,
    LAMBDA_MEMORY_SIZE_MB,
    LAMBDA_TIMEOUT_WORKER,
    PROJECT_NAME,
)


class EmailWorkerStack(Stack):
    """
    Worker stack for the email marketing infrastructure.

    This stack creates Lambda functions that consume messages
    from SQS and send emails via SES.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        storage_stack_outputs: Optional[Dict[str, str]] = None,
        security_stack_outputs: Optional[Dict[str, str]] = None,
        processing_stack_outputs: Optional[Dict[str, str]] = None,
        lambda_layer: Optional[_lambda.ILayerVersion] = None,
        environment: str = DEFAULT_ENVIRONMENT,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the worker stack.

        Args:
            scope: The parent construct
            construct_id: Unique identifier for this stack
            storage_stack_outputs: Outputs from the storage stack
            security_stack_outputs: Outputs from the security stack
            processing_stack_outputs: Outputs from the processing stack
            lambda_layer: Lambda Layer object with shared dependencies
            environment: Environment name (dev, staging, prod)
            **kwargs: Additional arguments passed to Stack
        """
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment
        self.storage_outputs = storage_stack_outputs or {}
        self.security_outputs = security_stack_outputs or {}
        self.processing_outputs = processing_stack_outputs or {}
        self.lambda_layer = lambda_layer

        self._create_lambda_functions()
        self._create_outputs()
        self._apply_tags()

    def _create_lambda_functions(self) -> None:
        """
        Create Lambda function for email sending.

        Creates email worker Lambda with SQS event source, grants
        permissions for DynamoDB and Secrets Manager access.
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

        self.email_worker_lambda = _lambda.Function(
            self,
            "EmailWorkerFunction",
            function_name=f"email-worker-{self.env_name}",
            code=_lambda.Code.from_asset("infrastructure/functions/worker"),
            handler="email_worker.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(LAMBDA_TIMEOUT_WORKER),
            memory_size=LAMBDA_MEMORY_SIZE_MB,
            role=lambda_role,
            layers=layers,
            environment={
                "ENVIRONMENT": self.env_name,
                "PROJECT_NAME": PROJECT_NAME,
                "DYNAMODB_TABLE_NAME": self.storage_outputs.get("email_status_table_name", ""),
                "SECRET_NAME": self.security_outputs.get("config_secret_name", ""),
            },
            tracing=_lambda.Tracing.ACTIVE,
        )

        if self.storage_outputs.get("email_status_table_name"):
            from aws_cdk import aws_dynamodb as dynamodb

            status_table = dynamodb.Table.from_table_name(
                self,
                "EmailStatusTableImport",
                self.storage_outputs["email_status_table_name"],
            )
            status_table.grant_write_data(self.email_worker_lambda)

        if self.security_outputs.get("config_secret_arn"):
            from aws_cdk import aws_secretsmanager as secretsmanager

            config_secret = secretsmanager.Secret.from_secret_complete_arn(
                self,
                "ConfigSecretImport",
                self.security_outputs["config_secret_arn"],
            )
            config_secret.grant_read(self.email_worker_lambda)

        if self.processing_outputs.get("email_queue_arn"):
            from aws_cdk import aws_sqs as sqs

            email_queue = sqs.Queue.from_queue_arn(
                self,
                "EmailQueueImport",
                self.processing_outputs["email_queue_arn"],
            )

            self.email_worker_lambda.add_event_source(
                lambda_event_sources.SqsEventSource(
                    email_queue,
                    batch_size=10,
                    max_batching_window=Duration.seconds(5),
                    report_batch_item_failures=True,
                )
            )

    def _create_outputs(self) -> None:
        """
        Create CloudFormation outputs for worker configuration.

        Exports Lambda function identifiers for use by other stacks.
        """
        CfnOutput(
            self,
            "EmailWorkerFunctionArn",
            value=self.email_worker_lambda.function_arn,
            description="Email worker Lambda function ARN",
            export_name=f"{self.stack_name}-EmailWorkerFunctionArn",
        )

        CfnOutput(
            self,
            "EmailWorkerFunctionName",
            value=self.email_worker_lambda.function_name,
            description="Email worker Lambda function name",
            export_name=f"{self.stack_name}-EmailWorkerFunctionName",
        )

    def _apply_tags(self) -> None:
        """
        Apply standard tags to all resources in the stack.

        Applies default tags from constants and adds environment-specific tags.
        """
        for key, value in DEFAULT_TAGS.items():
            Tags.of(self).add(key, value)

        Tags.of(self).add("Environment", self.env_name)
        Tags.of(self).add("StackType", "Worker")

    def get_worker_outputs(self) -> Dict[str, str]:
        """
        Get worker outputs for other stacks.

        Returns:
            Dictionary containing Lambda function identifiers
        """
        return {
            "email_worker_function_arn": self.email_worker_lambda.function_arn,
            "email_worker_function_name": self.email_worker_lambda.function_name,
        }
