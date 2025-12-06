#!/usr/bin/env python3
"""
Deployment Script for Email Marketing Serverless Infrastructure

This script provides utilities for deploying and managing the email marketing infrastructure.
"""

import argparse
import os
import subprocess
import sys

import boto3
from botocore.exceptions import ClientError


class EmailMarketingDeployer:
    """Deployment manager for the email marketing infrastructure."""

    def __init__(self, environment: str = "development", region: str = "us-east-1"):
        """
        Initialize the deployer.

        Args:
            environment: Environment name
            region: AWS region
        """
        self.environment = environment
        self.region = region
        self.session = boto3.Session(region_name=region)
        self.cloudformation = self.session.client("cloudformation")

    def deploy_all(self) -> bool:
        """
        Deploy all stacks.

        Returns:
            True if successful, False otherwise
        """
        print(f"DEPLOY Deploying email marketing infrastructure for {self.environment}")

        stacks = [
            "EmailMarketingStorageStack",
            "EmailMarketingSecurityStack",
            "EmailMarketingProcessingStack",
            "EmailMarketingWorkerStack",
            "EmailMarketingApiStack",
        ]

        success = True
        for stack in stacks:
            if not self.deploy_stack(stack):
                success = False
                break

        if success:
            print("OK All stacks deployed successfully!")
        else:
            print("ERROR Deployment failed!")

        return success

    def deploy_stack(self, stack_name: str) -> bool:
        """
        Deploy a specific stack.

        Args:
            stack_name: Name of the stack to deploy

        Returns:
            True if successful, False otherwise
        """
        print(f"STACK Deploying {stack_name}...")

        try:
            result = subprocess.run(
                ["cdk", "deploy", stack_name, "--require-approval", "never"],
                capture_output=True,
                text=True,
                check=True,
                shell=True,
                encoding="utf-8",
                errors="replace",
            )
            print(f"OK {stack_name} deployed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"ERROR Failed to deploy {stack_name}")
            print(f"Error: {e.stderr}")
            return False

    def destroy_all(self) -> bool:
        """
        Destroy all stacks.

        Returns:
            True if successful, False otherwise
        """
        print(f"DESTROY Destroying email marketing infrastructure for {self.environment}")

        # Destroy in reverse order
        stacks = [
            "EmailMarketingApiStack",
            "EmailMarketingWorkerStack",
            "EmailMarketingProcessingStack",
            "EmailMarketingSecurityStack",
            "EmailMarketingStorageStack",
        ]

        success = True
        for stack in stacks:
            if self.stack_exists(stack):
                if not self.destroy_stack(stack):
                    success = False
                    break

        if success:
            print("OK All stacks destroyed successfully!")
        else:
            print("ERROR Destruction failed!")

        return success

    def destroy_stack(self, stack_name: str) -> bool:
        """
        Destroy a specific stack.

        Args:
            stack_name: Name of the stack to destroy

        Returns:
            True if successful, False otherwise
        """
        print(f"DESTROY Destroying {stack_name}...")

        try:
            result = subprocess.run(
                ["cdk", "destroy", stack_name, "--force"],
                capture_output=True,
                text=True,
                check=True,
                shell=True,
                encoding="utf-8",
                errors="replace",
            )
            print(f"OK {stack_name} destroyed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"ERROR Failed to destroy {stack_name}")
            print(f"Error: {e.stderr}")
            return False

    def stack_exists(self, stack_name: str) -> bool:
        """
        Check if a stack exists.

        Args:
            stack_name: Name of the stack

        Returns:
            True if stack exists, False otherwise
        """
        try:
            self.cloudformation.describe_stacks(StackName=stack_name)
            return True
        except ClientError:
            return False

    def get_stack_outputs(self, stack_name: str) -> dict:
        """
        Get stack outputs.

        Args:
            stack_name: Name of the stack

        Returns:
            Dictionary of stack outputs
        """
        try:
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            outputs = {}
            for output in response["Stacks"][0].get("Outputs", []):
                outputs[output["OutputKey"]] = output["OutputValue"]
            return outputs
        except ClientError as e:
            print(f"Error getting outputs for {stack_name}: {e}")
            return {}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Deploy email marketing infrastructure")
    parser.add_argument(
        "action", choices=["deploy", "destroy"], help="Action to perform"
    )
    parser.add_argument(
        "--environment",
        default="development",
        help="Environment name (default: development)",
    )
    parser.add_argument(
        "--region", default="us-east-1", help="AWS region (default: us-east-1)"
    )
    parser.add_argument("--stack", help="Specific stack to deploy/destroy")

    args = parser.parse_args()

    deployer = EmailMarketingDeployer(args.environment, args.region)

    if args.action == "deploy":
        if args.stack:
            success = deployer.deploy_stack(args.stack)
        else:
            success = deployer.deploy_all()
        sys.exit(0 if success else 1)

    elif args.action == "destroy":
        if args.stack:
            success = deployer.destroy_stack(args.stack)
        else:
            success = deployer.destroy_all()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

