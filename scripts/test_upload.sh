#!/bin/bash
# Test script for CSV upload endpoint

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

# Create test CSV file
cat > /tmp/test_emails.csv << EOF
email,subject,content
test1@example.com,Welcome Email,Welcome to our platform!
test2@example.com,Promo Email,Get 20% off this week!
test3@example.com,Newsletter,Check out our latest updates.
EOF

echo "Created test CSV file"

# Upload CSV
echo "Uploading CSV file..."
RESPONSE=$(curl -s -X POST "${API_URL}upload" \
  -F "file=@/tmp/test_emails.csv")

echo "Response:"
echo "$RESPONSE" | jq '.'

# Extract batch ID
BATCH_ID=$(echo "$RESPONSE" | jq -r '.batchId')

if [ -z "$BATCH_ID" ] || [ "$BATCH_ID" == "null" ]; then
  echo "Error: Could not get batch ID from response"
  exit 1
fi

echo ""
echo "Batch ID: $BATCH_ID"
echo ""
echo "Waiting 10 seconds for processing..."
sleep 10

# Query status via GraphQL
echo "Querying email status..."
curl -s -X POST "${API_URL}graphql" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"query { listEmailStatus(batchId: \\\"$BATCH_ID\\\", limit: 10) { items { batchId email status createdAt } total } }\"
  }" | jq '.'

echo ""
echo "Test completed!"

