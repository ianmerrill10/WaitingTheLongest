#!/bin/bash
###############################################################################
# WAITING THE LONGEST - Rescue Registry CLEANUP Script
# WARNING: This will DELETE all WTL rescue registry resources!
###############################################################################
set -euo pipefail

echo "=========================================="
echo "WTL RESCUE REGISTRY CLEANUP"
echo "=========================================="
echo ""
echo "WARNING: This will DELETE all wtl-rescue-* resources!"
echo "Press Ctrl+C within 10 seconds to cancel..."
sleep 10

echo ""
echo ">>> Starting cleanup..."

# Delete Lambdas
echo ""
echo ">>> Deleting Lambdas..."
for fn in $(aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `wtl-`)].FunctionName' --output text); do
    echo "  Deleting Lambda: $fn"
    aws lambda delete-function --function-name "$fn" || true
done

# Delete Lambda layers
echo ""
echo ">>> Deleting Lambda layers..."
for layer in $(aws lambda list-layers --query 'Layers[?starts_with(LayerName, `wtl-`)].LayerName' --output text); do
    for version in $(aws lambda list-layer-versions --layer-name "$layer" --query 'LayerVersions[*].Version' --output text); do
        echo "  Deleting layer: $layer version $version"
        aws lambda delete-layer-version --layer-name "$layer" --version-number "$version" || true
    done
done

# Delete S3 buckets (must empty first)
echo ""
echo ">>> Deleting S3 buckets..."
for bucket in $(aws s3api list-buckets --query 'Buckets[?starts_with(Name, `wtl-rescue`)].Name' --output text); do
    echo "  Emptying bucket: $bucket"
    aws s3 rm "s3://$bucket" --recursive || true
    echo "  Deleting bucket: $bucket"
    aws s3api delete-bucket --bucket "$bucket" || true
done

# Delete Secrets
echo ""
echo ">>> Deleting Secrets..."
for secret in $(aws secretsmanager list-secrets --query 'SecretList[?starts_with(Name, `wtl-`)].Name' --output text); do
    echo "  Deleting secret: $secret"
    aws secretsmanager delete-secret --secret-id "$secret" --force-delete-without-recovery || true
done

# Delete RDS instances
echo ""
echo ">>> Deleting RDS instances (this may take several minutes)..."
for db in $(aws rds describe-db-instances --query 'DBInstances[?starts_with(DBInstanceIdentifier, `wtl-rescue-db`)].DBInstanceIdentifier' --output text); do
    echo "  Deleting RDS: $db"
    aws rds delete-db-instance --db-instance-identifier "$db" --skip-final-snapshot --delete-automated-backups || true
done

# Wait for RDS deletion
for db in $(aws rds describe-db-instances --query 'DBInstances[?starts_with(DBInstanceIdentifier, `wtl-rescue-db`)].DBInstanceIdentifier' --output text 2>/dev/null); do
    echo "  Waiting for RDS $db to be deleted..."
    aws rds wait db-instance-deleted --db-instance-identifier "$db" 2>/dev/null || true
done

# Delete DB subnet groups
echo ""
echo ">>> Deleting DB subnet groups..."
for sg in $(aws rds describe-db-subnet-groups --query 'DBSubnetGroups[?starts_with(DBSubnetGroupName, `wtl-`)].DBSubnetGroupName' --output text 2>/dev/null); do
    echo "  Deleting subnet group: $sg"
    aws rds delete-db-subnet-group --db-subnet-group-name "$sg" || true
done

# Delete security groups
echo ""
echo ">>> Deleting security groups..."
for sg in $(aws ec2 describe-security-groups --query 'SecurityGroups[?starts_with(GroupName, `wtl-`)].GroupId' --output text); do
    echo "  Deleting security group: $sg"
    aws ec2 delete-security-group --group-id "$sg" || true
done

# Detach and delete IAM roles
echo ""
echo ">>> Cleaning up IAM roles..."
for role in $(aws iam list-roles --query 'Roles[?starts_with(RoleName, `wtl-`)].RoleName' --output text); do
    echo "  Detaching policies from: $role"
    for policy in $(aws iam list-attached-role-policies --role-name "$role" --query 'AttachedPolicies[*].PolicyArn' --output text); do
        aws iam detach-role-policy --role-name "$role" --policy-arn "$policy" || true
    done
    echo "  Deleting role: $role"
    aws iam delete-role --role-name "$role" || true
done

echo ""
echo "=========================================="
echo "CLEANUP COMPLETE"
echo "=========================================="
echo ""
echo "Note: CloudWatch log groups are retained for debugging."
echo "To delete them manually:"
echo "  aws logs describe-log-groups --log-group-name-prefix '/aws/lambda/wtl-' --query 'logGroups[*].logGroupName' --output text"
echo ""
date
