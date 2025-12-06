from typing import Any, Dict, Optional

from aws_cdk import CfnOutput, Duration, Stack, Tags
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_lambda as _lambda
from constructs import Construct

from infrastructure.shared.constants import (
    API_GATEWAY_STAGE_NAME,
    API_GATEWAY_THROTTLE_BURST,
    API_GATEWAY_THROTTLE_RATE,
    DEFAULT_ENVIRONMENT,
    DEFAULT_TAGS,
    LAMBDA_MEMORY_SIZE_MB,
    LAMBDA_TIMEOUT_API,
    PROJECT_NAME,
)


class EmailMarketingApiStack(Stack):
    """
    API stack for the email marketing infrastructure.

    This stack creates API Gateway and Lambda function for
    FastAPI application with GraphQL endpoint.
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
        Initialize the API stack.

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

        self._create_lambda_function()
        self._create_api_gateway()
        self._create_outputs()
        self._apply_tags()

    def _create_lambda_function(self) -> None:
        """
        Create Lambda function for FastAPI application.

        Creates the API Lambda function with appropriate permissions
        for S3, DynamoDB, Lambda invocation, and Secrets Manager access.
        """
        from aws_cdk import aws_iam as iam

        lambda_role_arn = self.security_outputs.get("lambda_execution_role_arn", "")
        lambda_role: Optional[iam.IRole] = None
        if lambda_role_arn:
            lambda_role = iam.Role.from_role_arn(
                self, "LambdaExecutionRoleImport", lambda_role_arn
            )

        # Use layer if provided
        layers = []
        if self.lambda_layer:
            layers.append(self.lambda_layer)

        self.api_lambda = _lambda.Function(
            self,
            "ApiFunction",
            function_name=f"email-api-{self.env_name}",
            code=_lambda.Code.from_asset("infrastructure/functions/api"),
            handler="api_handler.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(LAMBDA_TIMEOUT_API),
            memory_size=LAMBDA_MEMORY_SIZE_MB,
            role=lambda_role,
            layers=layers,
            environment={
                "ENVIRONMENT": self.env_name,
                "PROJECT_NAME": PROJECT_NAME,
                "DYNAMODB_TABLE_NAME": self.storage_outputs.get(
                    "email_status_table_name", ""
                ),
                "S3_BUCKET_NAME": self.storage_outputs.get("csv_bucket_name", ""),
                "CSV_PROCESSING_FUNCTION_NAME": self.processing_outputs.get(
                    "csv_processing_function_name", ""
                ),
                "SECRET_NAME": self.security_outputs.get("config_secret_name", ""),
            },
            tracing=_lambda.Tracing.ACTIVE,
        )

        if self.storage_outputs.get("csv_bucket_name"):
            from aws_cdk import aws_s3 as s3

            csv_bucket = s3.Bucket.from_bucket_name(
                self, "CsvBucketImport", self.storage_outputs["csv_bucket_name"]
            )
            csv_bucket.grant_read_write(self.api_lambda)

        if self.storage_outputs.get("email_status_table_name"):
            from aws_cdk import aws_dynamodb as dynamodb

            status_table = dynamodb.Table.from_table_name(
                self,
                "EmailStatusTableImport",
                self.storage_outputs["email_status_table_name"],
            )
            status_table.grant_read_data(self.api_lambda)

        if self.processing_outputs.get("csv_processing_function_arn"):
            self.api_lambda.add_to_role_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["lambda:InvokeFunction"],
                    resources=[
                        self.processing_outputs["csv_processing_function_arn"],
                    ],
                )
            )

        if self.security_outputs.get("config_secret_arn"):
            from aws_cdk import aws_secretsmanager as secretsmanager

            config_secret = secretsmanager.Secret.from_secret_complete_arn(
                self,
                "ConfigSecretImport",
                self.security_outputs["config_secret_arn"],
            )
            config_secret.grant_read(self.api_lambda)

    def _create_api_gateway(self) -> None:
        """
        Create API Gateway REST API.

        Creates REST API with Lambda integration, CORS support,
        and routes for upload, GraphQL, docs, and OpenAPI schema.
        """
        api_lambda_integration = apigateway.LambdaIntegration(
            self.api_lambda,
            proxy=True,
        )

        self.api = apigateway.RestApi(
            self,
            "EmailMarketingApi",
            rest_api_name=f"email-marketing-api-{self.env_name}",
            description="Email Marketing API with FastAPI and GraphQL",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization"],
            ),
            deploy_options=apigateway.StageOptions(
                stage_name=API_GATEWAY_STAGE_NAME,
                throttling_rate_limit=API_GATEWAY_THROTTLE_RATE,
                throttling_burst_limit=API_GATEWAY_THROTTLE_BURST,
                tracing_enabled=True,
            ),
        )

        upload_resource = self.api.root.add_resource("upload")
        upload_resource.add_method(
            "POST",
            api_lambda_integration,
            api_key_required=False,
        )

        graphql_resource = self.api.root.add_resource("graphql")
        graphql_resource.add_method(
            "POST",
            api_lambda_integration,
            api_key_required=False,
        )

        docs_resource = self.api.root.add_resource("docs")
        docs_resource.add_method("GET", api_lambda_integration)

        openapi_resource = self.api.root.add_resource("openapi.json")
        openapi_resource.add_method("GET", api_lambda_integration)

    def _create_outputs(self) -> None:
        """
        Create CloudFormation outputs for API configuration.

        Exports API URL, API ID, and Lambda function ARN/name
        for cross-stack references.
        """
        CfnOutput(
            self,
            "ApiUrl",
            value=self.api.url,
            description="API Gateway URL",
            export_name=f"{self.stack_name}-ApiUrl",
        )

        CfnOutput(
            self,
            "ApiId",
            value=self.api.rest_api_id,
            description="API Gateway ID",
            export_name=f"{self.stack_name}-ApiId",
        )

        CfnOutput(
            self,
            "ApiLambdaFunctionArn",
            value=self.api_lambda.function_arn,
            description="API Lambda function ARN",
            export_name=f"{self.stack_name}-ApiLambdaFunctionArn",
        )

        CfnOutput(
            self,
            "ApiLambdaFunctionName",
            value=self.api_lambda.function_name,
            description="API Lambda function name",
            export_name=f"{self.stack_name}-ApiLambdaFunctionName",
        )

    def _apply_tags(self) -> None:
        """
        Apply standard tags to all resources in the stack.

        Applies default tags from constants and adds environment-specific tags.
        """
        for key, value in DEFAULT_TAGS.items():
            Tags.of(self).add(key, value)

        Tags.of(self).add("Environment", self.env_name)
        Tags.of(self).add("StackType", "API")

    def get_api_outputs(self) -> Dict[str, str]:
        """
        Get API outputs for other stacks.

        Returns:
            Dictionary containing API URL, ID, and Lambda function identifiers
        """
        return {
            "api_url": self.api.url,
            "api_id": self.api.rest_api_id,
            "api_lambda_function_arn": self.api_lambda.function_arn,
            "api_lambda_function_name": self.api_lambda.function_name,
        }
