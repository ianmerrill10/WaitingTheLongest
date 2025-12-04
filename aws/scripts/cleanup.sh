#!/bin/bash
# ============================================================================
# Animal Rescue Search Agent - Cleanup Script
# ============================================================================
# Removes all AWS resources created by this stack
# USE WITH CAUTION - This will delete all collected data!
# ============================================================================

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ENVIRONMENT=${ENVIRONMENT:-prod}
AWS_REGION=${AWS_REGION:-us-east-1}
STACK_NAME="animal-rescue-${ENVIRONMENT}"

echo -e "${RED}============================================${NC}"
echo -e "${RED} WARNING: This will delete ALL resources${NC}"
echo -e "${RED}============================================${NC}"
echo ""
echo "Stack: $STACK_NAME"
echo "Region: $AWS_REGION"
echo ""
echo -e "${YELLOW}This will delete:${NC}"
echo "  - All Lambda functions"
echo "  - All DynamoDB tables (including all data)"
echo "  - All S3 buckets (including all CSV files)"
echo "  - The Step Functions state machine"
echo "  - The EventBridge schedule"
echo "  - All Cognito resources"
echo ""

read -p "Type 'DELETE' to confirm: " CONFIRM

if [ "$CONFIRM" != "DELETE" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."

# Get bucket names before deletion
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
DATA_BUCKET="animal-rescue-data-${ENVIRONMENT}-${ACCOUNT_ID}"
DASHBOARD_BUCKET="animal-rescue-admin-${ENVIRONMENT}-${ACCOUNT_ID}"
DEPLOY_BUCKET="animal-rescue-deploy-${ACCOUNT_ID}"

# Empty S3 buckets (required before deletion)
echo "Emptying S3 buckets..."
aws s3 rm "s3://${DATA_BUCKET}" --recursive --region "$AWS_REGION" 2>/dev/null || true
aws s3 rm "s3://${DASHBOARD_BUCKET}" --recursive --region "$AWS_REGION" 2>/dev/null || true
aws s3 rm "s3://${DEPLOY_BUCKET}" --recursive --region "$AWS_REGION" 2>/dev/null || true

# Delete CloudFormation stack
echo "Deleting CloudFormation stack..."
aws cloudformation delete-stack \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION"

echo "Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION"

# Delete deployment bucket
echo "Deleting deployment bucket..."
aws s3 rb "s3://${DEPLOY_BUCKET}" --region "$AWS_REGION" 2>/dev/null || true

echo ""
echo "Cleanup complete!"
