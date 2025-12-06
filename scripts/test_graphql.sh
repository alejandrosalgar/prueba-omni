#!/bin/bash
# Test script for GraphQL endpoint

set -e

# Get API URL from CloudFormation
API_URL=$(aws cloudformation describe-stacks \
  --stack-name EmailMarketingApiStack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

if [ -z "$API_URL" ]; then
  echo "Error: Could not get API URL. Make sure the stack is deployed."
  exit 1
fi

echo "API URL: $API_URL"
echo ""

# Test 1: Query all email statuses
echo "Test 1: Query all email statuses"
curl -s -X POST "${API_URL}graphql" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { listEmailStatus(limit: 10) { items { batchId email status createdAt } total } }"
  }' | jq '.'
echo ""

# Test 2: Query by status
echo "Test 2: Query by status (SENT)"
curl -s -X POST "${API_URL}graphql" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { listEmailStatus(status: [\"SENT\"], limit: 10) { items { batchId email status sentAt } total } }"
  }' | jq '.'
echo ""

# Test 3: Query by date range
echo "Test 3: Query by date range"
TODAY=$(date -u +"%Y-%m-%d")
curl -s -X POST "${API_URL}graphql" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"query { listEmailStatus(fromDate: \\\"${TODAY}T00:00:00\\\", toDate: \\\"${TODAY}T23:59:59\\\", limit: 10) { items { batchId email status createdAt } total } }\"
  }" | jq '.'
echo ""

# Test 4: Query by batch ID (if provided)
if [ -n "$1" ]; then
  BATCH_ID=$1
  echo "Test 4: Query by batch ID: $BATCH_ID"
  curl -s -X POST "${API_URL}graphql" \
    -H "Content-Type: application/json" \
    -d "{
      \"query\": \"query { listEmailStatus(batchId: \\\"${BATCH_ID}\\\", limit: 10) { items { batchId email status subject createdAt } total } }\"
    }" | jq '.'
  echo ""
fi

echo "GraphQL tests completed!"

