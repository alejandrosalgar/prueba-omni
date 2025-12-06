"""
Main CDK Application for Email Marketing Serverless Infrastructure

This is the main entry point for the CDK application that orchestrates
the deployment of all infrastructure stacks for the email marketing system.
"""

import os

import aws_cdk as cdk
from aws_cdk import Environment, Tags

from infrastructure.core.api_stack import EmailMarketingApiStack
from infrastructure.core.layer_stack import EmailMarketingLayerStack
from infrastructure.core.processing_stack import EmailProcessingStack
from infrastructure.core.security_stack import EmailSecurityStack
from infrastructure.core.storage_stack import EmailStorageStack
from infrastructure.core.worker_stack import EmailWorkerStack
from infrastructure.shared.constants import (
    API_STACK_NAME,
    DEFAULT_ENVIRONMENT,
    DEFAULT_REGION,
    DEFAULT_TAGS,
    PROCESSING_STACK_NAME,
    PROJECT_NAME,
    SECURITY_STACK_NAME,
    STORAGE_STACK_NAME,
    VERSION,
    WORKER_STACK_NAME,
)


def create_app() -> cdk.App:
    """
    Create and configure the CDK application.

    Returns:
        Configured CDK App instance
    """
    app = cdk.App()

    environment = os.getenv("ENVIRONMENT", DEFAULT_ENVIRONMENT)
    region = os.getenv("CDK_DEFAULT_REGION", DEFAULT_REGION)
    account = os.getenv("CDK_DEFAULT_ACCOUNT")

    if not account:
        raise ValueError("CDK_DEFAULT_ACCOUNT environment variable is required")

    env = Environment(account=account, region=region)

    stacks = _create_stacks(app, env, environment)

    _apply_global_tags(stacks, environment)

    return app


def _create_stacks(app: cdk.App, env: Environment, environment: str) -> list[cdk.Stack]:
    """
    Create all infrastructure stacks.

    Args:
        app: CDK App instance
        env: AWS Environment
        environment: Environment name

    Returns:
        List of created stacks
    """
    stacks = []

    # 1. Storage Stack (S3, DynamoDB)
    storage_stack = EmailStorageStack(
        app,
        STORAGE_STACK_NAME,
        environment=environment,
        env=env,
        description="Storage stack for email marketing (S3, DynamoDB)",
    )
    stacks.append(storage_stack)

    # 2. Layer Stack (Lambda Layer with dependencies)
    layer_stack = EmailMarketingLayerStack(
        app,
        "EmailMarketingLayerStack",
        environment=environment,
        env=env,
        description="Lambda Layer with shared Python dependencies",
    )
    stacks.append(layer_stack)

    # 3. Security Stack (IAM, Secrets Manager)
    security_stack = EmailSecurityStack(
        app,
        SECURITY_STACK_NAME,
        storage_stack_outputs=storage_stack.get_storage_outputs(),
        environment=environment,
        env=env,
        description="Security and permissions stack (IAM, Secrets Manager)",
    )
    stacks.append(security_stack)

    # Get layer object to pass directly to stacks
    lambda_layer = layer_stack.get_layer()

    # 4. Processing Stack (SQS, Lambda for CSV processing)
    processing_stack = EmailProcessingStack(
        app,
        PROCESSING_STACK_NAME,
        storage_stack_outputs=storage_stack.get_storage_outputs(),
        security_stack_outputs=security_stack.get_security_outputs(),
        lambda_layer=lambda_layer,
        environment=environment,
        env=env,
        description="Processing stack for CSV parsing and queueing",
    )
    stacks.append(processing_stack)

    # 5. Worker Stack (Lambda for email sending)
    worker_stack = EmailWorkerStack(
        app,
        WORKER_STACK_NAME,
        storage_stack_outputs=storage_stack.get_storage_outputs(),
        security_stack_outputs=security_stack.get_security_outputs(),
        processing_stack_outputs=processing_stack.get_processing_outputs(),
        lambda_layer=lambda_layer,
        environment=environment,
        env=env,
        description="Worker stack for email sending",
    )
    stacks.append(worker_stack)

    # 6. API Stack (API Gateway, Lambda for FastAPI)
    api_stack = EmailMarketingApiStack(
        app,
        API_STACK_NAME,
        storage_stack_outputs=storage_stack.get_storage_outputs(),
        security_stack_outputs=security_stack.get_security_outputs(),
        processing_stack_outputs=processing_stack.get_processing_outputs(),
        lambda_layer=lambda_layer,
        environment=environment,
        env=env,
        description="API Gateway stack with FastAPI and GraphQL",
    )
    stacks.append(api_stack)

    _setup_stack_dependencies(stacks)

    return stacks


def _setup_stack_dependencies(stacks: list[cdk.Stack]) -> None:
    """
    Set up dependencies between stacks.

    Args:
        stacks: List of created stacks
    """
    storage_stack = stacks[0]
    layer_stack = stacks[1]
    security_stack = stacks[2]
    processing_stack = stacks[3]
    worker_stack = stacks[4]
    api_stack = stacks[5]

    layer_stack.add_dependency(storage_stack)
    security_stack.add_dependency(storage_stack)
    processing_stack.add_dependency(storage_stack)
    processing_stack.add_dependency(security_stack)
    processing_stack.add_dependency(layer_stack)
    worker_stack.add_dependency(storage_stack)
    worker_stack.add_dependency(security_stack)
    worker_stack.add_dependency(processing_stack)
    worker_stack.add_dependency(layer_stack)
    api_stack.add_dependency(storage_stack)
    api_stack.add_dependency(security_stack)
    api_stack.add_dependency(processing_stack)
    api_stack.add_dependency(layer_stack)


def _apply_global_tags(stacks: list[cdk.Stack], environment: str) -> None:
    """
    Apply global tags to all stacks.

    Args:
        stacks: List of stacks to tag
        environment: Environment name
    """
    for stack in stacks:
        for key, value in DEFAULT_TAGS.items():
            Tags.of(stack).add(key, value)

        Tags.of(stack).add("Environment", environment)
        Tags.of(stack).add("ManagedBy", "CDK")
        Tags.of(stack).add("Version", VERSION)
        Tags.of(stack).add("Project", PROJECT_NAME)


def main():
    """Main entry point for the CDK application."""
    app = create_app()
    app.synth()


if __name__ == "__main__":
    main()
