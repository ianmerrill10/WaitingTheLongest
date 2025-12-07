#!/bin/bash
###############################################################################
# WAITING THE LONGEST - Rescue Registry Verification Script
# Run this to check the status of your deployment
###############################################################################
set -euo pipefail

echo "=========================================="
echo "WTL RESCUE REGISTRY VERIFICATION"
echo "=========================================="
date

# Find our resources by prefix
echo ""
echo ">>> Looking for WTL resources..."

# Find bucket
BUCKET=$(aws s3api list-buckets --query 'Buckets[?starts_with(Name, `wtl-rescue-registry`)].Name' --output text | head -1)
if [ -z "$BUCKET" ] || [ "$BUCKET" == "None" ]; then
    echo "ERROR: No wtl-rescue-registry bucket found!"
    exit 1
fi
echo "Found bucket: $BUCKET"

# Find orchestrator
ORCHESTRATOR=$(aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `wtl-orchestrator`)].FunctionName' --output text | head -1)
if [ -z "$ORCHESTRATOR" ] || [ "$ORCHESTRATOR" == "None" ]; then
    echo "ERROR: No wtl-orchestrator Lambda found!"
    exit 1
fi
echo "Found orchestrator: $ORCHESTRATOR"

# Find RDS
DB_INSTANCE=$(aws rds describe-db-instances --query 'DBInstances[?starts_with(DBInstanceIdentifier, `wtl-rescue-db`)].DBInstanceIdentifier' --output text | head -1)
if [ -z "$DB_INSTANCE" ] || [ "$DB_INSTANCE" == "None" ]; then
    echo "WARNING: No wtl-rescue-db RDS instance found!"
else
    echo "Found RDS: $DB_INSTANCE"
    DB_STATUS=$(aws rds describe-db-instances --db-instance-identifier "$DB_INSTANCE" --query 'DBInstances[0].DBInstanceStatus' --output text)
    echo "RDS Status: $DB_STATUS"
fi

echo ""
echo "=========================================="
echo "S3 BUCKET CONTENTS"
echo "=========================================="

echo ""
echo ">>> raw/ folder (files waiting to be processed):"
aws s3 ls "s3://$BUCKET/raw/" || echo "  (empty or folder doesn't exist)"

echo ""
echo ">>> processed/ folder (completed files):"
aws s3 ls "s3://$BUCKET/processed/" || echo "  (empty or folder doesn't exist)"

echo ""
echo ">>> failed/ folder (files that had errors):"
aws s3 ls "s3://$BUCKET/failed/" || echo "  (empty or folder doesn't exist)"

echo ""
echo "=========================================="
echo "RECENT ORCHESTRATOR LOGS (last 15 min)"
echo "=========================================="

aws logs tail "/aws/lambda/$ORCHESTRATOR" --since 15m --format short 2>/dev/null || echo "No recent logs found"

echo ""
echo "=========================================="
echo "RECENT EXTRACTOR LOGS (last 15 min)"
echo "=========================================="

EXTRACTOR=$(aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `wtl-contact-extractor`)].FunctionName' --output text | head -1)
if [ -n "$EXTRACTOR" ] && [ "$EXTRACTOR" != "None" ]; then
    aws logs tail "/aws/lambda/$EXTRACTOR" --since 15m --format short 2>/dev/null || echo "No recent logs found"
else
    echo "Extractor Lambda not found"
fi

echo ""
echo "=========================================="
echo "QUICK COMMANDS"
echo "=========================================="
echo ""
echo "Upload a new file:"
echo "  aws s3 cp yourfile.txt s3://$BUCKET/raw/"
echo ""
echo "Run orchestrator:"
echo "  aws lambda invoke --function-name $ORCHESTRATOR --payload '{}' /tmp/result.json && cat /tmp/result.json"
echo ""
echo "View processed JSON:"
echo "  aws s3 cp s3://$BUCKET/processed/yourfile.json - | jq ."
echo ""
echo "Tail logs live:"
echo "  aws logs tail /aws/lambda/$ORCHESTRATOR --follow"
echo ""
date
echo "=========================================="
