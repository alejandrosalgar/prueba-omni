"""
Lambda Layer Stack for Email Marketing Serverless Infrastructure.

This stack creates a shared Lambda Layer containing all Python dependencies
used by the Lambda functions, reducing package size and improving deployment speed.
"""

from typing import Any, Dict, Optional

from aws_cdk import Stack, Tags
from aws_cdk import aws_lambda as _lambda
from constructs import Construct

from infrastructure.shared.constants import (
    DEFAULT_ENVIRONMENT,
    DEFAULT_TAGS,
    PROJECT_NAME,
)


class EmailMarketingLayerStack(Stack):
    """
    Lambda Layer stack for the email marketing infrastructure.

    This stack creates a shared Lambda Layer containing all Python dependencies
    that can be reused across all Lambda functions.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str = DEFAULT_ENVIRONMENT,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the Lambda Layer stack.

        Args:
            scope: Parent construct
            construct_id: Unique identifier for this stack
            environment: Environment name (development, staging, production)
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment

        self._create_lambda_layer()
        self._apply_tags()

    def _create_lambda_layer(self) -> None:
        """
        Create Lambda Layer with Python dependencies.

        Creates a Lambda Layer containing all Python packages from
        infrastructure/functions/layer/requirements.txt.
        """
        self.dependencies_layer = _lambda.LayerVersion(
            self,
            "DependenciesLayer",
            layer_version_name=f"email-marketing-dependencies-{self.env_name}",
            code=_lambda.Code.from_asset("infrastructure/functions/layer"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="Shared Python dependencies for email marketing Lambdas",
        )

    def _apply_tags(self) -> None:
        """Apply tags to the stack resources."""
        for key, value in DEFAULT_TAGS.items():
            Tags.of(self).add(key, value)

        Tags.of(self).add("Environment", self.env_name)
        Tags.of(self).add("ManagedBy", "CDK")
        Tags.of(self).add("Project", PROJECT_NAME)
        Tags.of(self).add("Component", "LambdaLayer")

    def get_layer(self) -> _lambda.ILayerVersion:
        """
        Get the Lambda Layer object.

        Returns:
            Lambda Layer object that can be attached to functions
        """
        return self.dependencies_layer

    def get_layer_arn(self) -> str:
        """
        Get the ARN of the dependencies layer.

        Returns:
            ARN of the Lambda Layer
        """
        return self.dependencies_layer.layer_version_arn
