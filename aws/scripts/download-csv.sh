#!/bin/bash
# ============================================================================
# Animal Rescue Search Agent - Download CSV Script
# ============================================================================
# Downloads the latest CSV files from S3
# ============================================================================

set -e

# Default values
ENVIRONMENT=${ENVIRONMENT:-prod}
AWS_REGION=${AWS_REGION:-us-east-1}
OUTPUT_DIR=${OUTPUT_DIR:-./animal-rescue-data}

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
DATA_BUCKET="animal-rescue-data-${ENVIRONMENT}-${ACCOUNT_ID}"

echo "Downloading Animal Rescue Data from S3..."
echo "Bucket: $DATA_BUCKET"
echo "Output: $OUTPUT_DIR"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Download master CSV
echo "Downloading master CSV..."
aws s3 cp "s3://${DATA_BUCKET}/exports/master/animal_rescues_all_states_LATEST.csv" \
    "${OUTPUT_DIR}/animal_rescues_all_states.csv" \
    --region "$AWS_REGION" 2>/dev/null || echo "Master CSV not available yet"

# Download individual state CSVs
echo "Downloading state CSVs..."
aws s3 sync "s3://${DATA_BUCKET}/exports/states/" \
    "${OUTPUT_DIR}/states/" \
    --exclude "*" \
    --include "*_LATEST.csv" \
    --region "$AWS_REGION" 2>/dev/null || echo "Some state CSVs not available"

# Download latest report
echo "Downloading latest report..."
aws s3 cp "s3://${DATA_BUCKET}/reports/daily/report_LATEST.json" \
    "${OUTPUT_DIR}/latest_report.json" \
    --region "$AWS_REGION" 2>/dev/null || echo "Report not available yet"

echo ""
echo "Download complete!"
echo "Files saved to: $OUTPUT_DIR"

# Show file count
if [ -f "${OUTPUT_DIR}/animal_rescues_all_states.csv" ]; then
    LINE_COUNT=$(wc -l < "${OUTPUT_DIR}/animal_rescues_all_states.csv")
    echo "Total organizations in master CSV: $((LINE_COUNT - 1))"
fi
