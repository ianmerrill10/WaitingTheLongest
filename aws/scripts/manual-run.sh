#!/bin/bash
# ============================================================================
# Animal Rescue Search Agent - Manual Run Script
# ============================================================================
# Use this to manually trigger collection for a specific state or all states
# ============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
ENVIRONMENT=${ENVIRONMENT:-prod}
AWS_REGION=${AWS_REGION:-us-east-1}
STACK_NAME="animal-rescue-${ENVIRONMENT}"

echo -e "${BLUE}Animal Rescue Search Agent - Manual Run${NC}"
echo ""

# Get State Machine ARN
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' \
    --output text 2>/dev/null)

if [ -z "$STATE_MACHINE_ARN" ]; then
    echo "Error: Could not find State Machine ARN. Is the stack deployed?"
    exit 1
fi

# Show menu
echo "Options:"
echo "  1. Run collection for all states (full cycle)"
echo "  2. Run collection for a specific state"
echo "  3. Check collection progress"
echo "  4. Export master CSV"
echo ""

read -p "Select option (1-4): " OPTION

case $OPTION in
    1)
        echo -e "${YELLOW}Starting full collection cycle...${NC}"
        EXECUTION_ARN=$(aws stepfunctions start-execution \
            --state-machine-arn "$STATE_MACHINE_ARN" \
            --input '{"mode": "full_run"}' \
            --region "$AWS_REGION" \
            --query 'executionArn' \
            --output text)
        echo -e "${GREEN}Execution started: $EXECUTION_ARN${NC}"
        ;;
    2)
        read -p "Enter state abbreviation (e.g., TX, CA, NY): " STATE
        STATE=$(echo "$STATE" | tr '[:lower:]' '[:upper:]')
        echo -e "${YELLOW}Starting collection for $STATE...${NC}"

        SEARCH_FUNCTION=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$AWS_REGION" \
            --query 'Stacks[0].Outputs[?OutputKey==`ShelterSearchFunctionArn`].OutputValue' \
            --output text)

        aws lambda invoke \
            --function-name "$SEARCH_FUNCTION" \
            --payload "{\"state\": \"$STATE\"}" \
            --region "$AWS_REGION" \
            --cli-binary-format raw-in-base64-out \
            /tmp/lambda-response.json

        echo -e "${GREEN}Collection complete!${NC}"
        cat /tmp/lambda-response.json
        ;;
    3)
        echo -e "${YELLOW}Checking collection progress...${NC}"
        ORCHESTRATOR_FUNCTION="AnimalRescue-Orchestrator-${ENVIRONMENT}"

        aws lambda invoke \
            --function-name "$ORCHESTRATOR_FUNCTION" \
            --payload '{"mode": "status"}' \
            --region "$AWS_REGION" \
            --cli-binary-format raw-in-base64-out \
            /tmp/lambda-response.json

        cat /tmp/lambda-response.json | python3 -m json.tool
        ;;
    4)
        echo -e "${YELLOW}Exporting master CSV...${NC}"
        EXPORTER_FUNCTION="AnimalRescue-CsvExporter-${ENVIRONMENT}"

        aws lambda invoke \
            --function-name "$EXPORTER_FUNCTION" \
            --payload '{"mode": "full_export"}' \
            --region "$AWS_REGION" \
            --cli-binary-format raw-in-base64-out \
            /tmp/lambda-response.json

        echo -e "${GREEN}Export complete!${NC}"
        cat /tmp/lambda-response.json | python3 -m json.tool
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac
