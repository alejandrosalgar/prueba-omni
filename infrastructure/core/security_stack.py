"""
Security Stack for Email Marketing Serverless Infrastructure.

This stack creates and manages all security-related resources including:
- IAM roles for Lambda functions
- Secrets Manager for sensitive configuration
"""

from typing import Any

from aws_cdk import CfnOutput, Stack, Tags
from aws_cdk import aws_iam as iam
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

from infrastructure.shared.constants import (
    DEFAULT_ENVIRONMENT,
    DEFAULT_TAGS,
    SECRETS_MANAGER_SECRET_NAME,
)


class EmailSecurityStack(Stack):
    """
    Security stack for the email marketing infrastructure.

    This stack creates IAM roles and Secrets Manager resources
    for secure configuration management.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        storage_stack_outputs: dict[str, str] | None = None,
        environment: str = DEFAULT_ENVIRONMENT,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the security stack.

        Args:
            scope: The parent construct
            construct_id: Unique identifier for this stack
            storage_stack_outputs: Outputs from the storage stack
            environment: Environment name (dev, staging, prod)
            **kwargs: Additional arguments passed to Stack
        """
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment
        self.storage_outputs = storage_stack_outputs or {}

        self._create_iam_roles()
        self._create_secrets_manager()
        self._create_outputs()
        self._apply_tags()

    def _create_iam_roles(self) -> None:
        """
        Create IAM roles for Lambda functions.

        Creates base execution role with permissions for CloudWatch Logs,
        X-Ray tracing, S3, DynamoDB, SQS, SES, and Secrets Manager.
        Permissions are scoped to specific resources where possible.
        """
        self.lambda_execution_role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=f"EmailMarketingLambdaExecution-{self.env_name}",
            description="Base execution role for Lambda functions",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        self.lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            )
        )

        self.lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                ],
                resources=["*"],
            )
        )

        if self.storage_outputs:
            csv_bucket_name = self.storage_outputs.get("csv_bucket_name", "")
            if csv_bucket_name:
                self.lambda_execution_role.add_to_policy(
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject",
                            "s3:ListBucket",
                        ],
                        resources=[
                            f"arn:aws:s3:::{csv_bucket_name}",
                            f"arn:aws:s3:::{csv_bucket_name}/*",
                        ],
                    )
                )

        if self.storage_outputs:
            table_arn = self.storage_outputs.get("email_status_table_arn", "")
            if table_arn:
                self.lambda_execution_role.add_to_policy(
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "dynamodb:PutItem",
                            "dynamodb:GetItem",
                            "dynamodb:UpdateItem",
                            "dynamodb:Query",
                            "dynamodb:Scan",
                            "dynamodb:BatchWriteItem",
                        ],
                        resources=[table_arn, f"{table_arn}/index/*"],
                    )
                )

        self.lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sqs:SendMessage",
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                ],
                resources=["*"],
            )
        )

        self.lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ses:SendEmail",
                    "ses:SendRawEmail",
                ],
                resources=["*"],
            )
        )

        self.lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret",
                ],
                resources=["*"],
            )
        )

    def _create_secrets_manager(self) -> None:
        """
        Create Secrets Manager secret for configuration.

        Creates secret with default configuration template and grants
        read access to Lambda execution role.
        """
        self.config_secret = secretsmanager.Secret(
            self,
            "EmailMarketingConfigSecret",
            secret_name=f"{SECRETS_MANAGER_SECRET_NAME}-{self.env_name}",
            description="Configuration secret for email marketing system",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"ses_from_email": "noreply@example.com", "dry_run": "true"}',
                generate_string_key="dummy",
                exclude_characters='{}"',
            ),
        )

        self.config_secret.grant_read(self.lambda_execution_role)

    def _create_outputs(self) -> None:
        """
        Create CloudFormation outputs for security configuration.

        Exports IAM role and Secrets Manager identifiers for use
        by other stacks in the infrastructure.
        """
        CfnOutput(
            self,
            "LambdaExecutionRoleArn",
            value=self.lambda_execution_role.role_arn,
            description="Lambda execution role ARN",
            export_name=f"{self.stack_name}-LambdaExecutionRoleArn",
        )

        CfnOutput(
            self,
            "LambdaExecutionRoleName",
            value=self.lambda_execution_role.role_name,
            description="Lambda execution role name",
            export_name=f"{self.stack_name}-LambdaExecutionRoleName",
        )

        CfnOutput(
            self,
            "ConfigSecretArn",
            value=self.config_secret.secret_arn,
            description="Configuration secret ARN",
            export_name=f"{self.stack_name}-ConfigSecretArn",
        )

        CfnOutput(
            self,
            "ConfigSecretName",
            value=self.config_secret.secret_name,
            description="Configuration secret name",
            export_name=f"{self.stack_name}-ConfigSecretName",
        )

    def _apply_tags(self) -> None:
        """
        Apply standard tags to all resources in the stack.

        Applies default tags from constants and adds environment-specific tags.
        """
        for key, value in DEFAULT_TAGS.items():
            Tags.of(self).add(key, value)

        Tags.of(self).add("Environment", self.env_name)
        Tags.of(self).add("StackType", "Security")
        Tags.of(self).add("SecurityLevel", "High")

    def get_security_outputs(self) -> dict[str, str]:
        """
        Get security outputs for other stacks.

        Returns:
            Dictionary containing IAM role and Secrets Manager identifiers
        """
        return {
            "lambda_execution_role_arn": self.lambda_execution_role.role_arn,
            "lambda_execution_role_name": self.lambda_execution_role.role_name,
            "config_secret_arn": self.config_secret.secret_arn,
            "config_secret_name": self.config_secret.secret_name,
        }
