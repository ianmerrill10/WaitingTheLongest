#!/bin/bash
# ============================================================================
# Animal Rescue Search Agent - AWS Deployment Script
# ============================================================================
# This script deploys the complete infrastructure to AWS
# Run this from AWS CloudShell
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} Animal Rescue Search Agent - Deployment${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check for required tools
check_requirements() {
    echo -e "${YELLOW}Checking requirements...${NC}"

    if ! command -v aws &> /dev/null; then
        echo -e "${RED}Error: AWS CLI not found${NC}"
        exit 1
    fi

    if ! command -v sam &> /dev/null; then
        echo -e "${YELLOW}Installing AWS SAM CLI...${NC}"
        pip3 install aws-sam-cli --quiet
    fi

    echo -e "${GREEN}All requirements met!${NC}"
}

# Get user inputs
get_configuration() {
    echo ""
    echo -e "${YELLOW}Configuration Setup${NC}"
    echo "-------------------"

    # Environment
    read -p "Environment (dev/staging/prod) [prod]: " ENVIRONMENT
    ENVIRONMENT=${ENVIRONMENT:-prod}

    # Region
    read -p "AWS Region [us-east-1]: " AWS_REGION
    AWS_REGION=${AWS_REGION:-us-east-1}

    # SerpAPI Key
    read -sp "SerpAPI Key (for web search): " SERP_API_KEY
    echo ""

    if [ -z "$SERP_API_KEY" ]; then
        echo -e "${RED}Error: SerpAPI key is required${NC}"
        echo "Get a free key at: https://serpapi.com"
        exit 1
    fi

    # Google OAuth Client ID
    read -p "Google OAuth Client ID: " GOOGLE_CLIENT_ID

    if [ -z "$GOOGLE_CLIENT_ID" ]; then
        echo -e "${YELLOW}Warning: Google OAuth not configured. Admin dashboard will not be accessible.${NC}"
        echo "Get credentials at: https://console.cloud.google.com/apis/credentials"
    fi

    # Admin Emails
    read -p "Admin email addresses (comma-separated, or leave empty for any): " ADMIN_EMAILS

    # Stack Name
    STACK_NAME="animal-rescue-${ENVIRONMENT}"

    echo ""
    echo -e "${BLUE}Configuration Summary:${NC}"
    echo "  Environment: $ENVIRONMENT"
    echo "  Region: $AWS_REGION"
    echo "  Stack Name: $STACK_NAME"
    echo "  SerpAPI: [configured]"
    echo "  Google OAuth: ${GOOGLE_CLIENT_ID:-[not configured]}"
    echo ""

    read -p "Proceed with deployment? (y/n) [y]: " CONFIRM
    CONFIRM=${CONFIRM:-y}

    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        echo "Deployment cancelled."
        exit 0
    fi
}

# Create S3 bucket for deployment artifacts
create_deployment_bucket() {
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    DEPLOYMENT_BUCKET="animal-rescue-deploy-${ACCOUNT_ID}"

    echo -e "${YELLOW}Creating deployment bucket: ${DEPLOYMENT_BUCKET}${NC}"

    if aws s3 ls "s3://${DEPLOYMENT_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
        aws s3 mb "s3://${DEPLOYMENT_BUCKET}" --region "$AWS_REGION"
        echo -e "${GREEN}Deployment bucket created${NC}"
    else
        echo -e "${GREEN}Deployment bucket already exists${NC}"
    fi
}

# Package and deploy the stack
deploy_stack() {
    echo ""
    echo -e "${YELLOW}Packaging Lambda functions...${NC}"

    cd "$(dirname "$0")/.."

    # Create a temporary directory for packaging
    TEMP_DIR=$(mktemp -d)
    cp -r lambda/* "$TEMP_DIR/"

    # Package the SAM application
    sam package \
        --template-file cloudformation/animal-rescue-stack.yaml \
        --output-template-file "$TEMP_DIR/packaged.yaml" \
        --s3-bucket "$DEPLOYMENT_BUCKET" \
        --region "$AWS_REGION"

    echo -e "${YELLOW}Deploying CloudFormation stack...${NC}"
    echo -e "${YELLOW}This may take 10-15 minutes...${NC}"

    sam deploy \
        --template-file "$TEMP_DIR/packaged.yaml" \
        --stack-name "$STACK_NAME" \
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
        --region "$AWS_REGION" \
        --parameter-overrides \
            Environment="$ENVIRONMENT" \
            SerpApiKey="$SERP_API_KEY" \
            GoogleClientId="${GOOGLE_CLIENT_ID:-placeholder}" \
            AdminEmails="${ADMIN_EMAILS:-}" \
        --no-fail-on-empty-changeset

    # Cleanup
    rm -rf "$TEMP_DIR"

    echo -e "${GREEN}Stack deployment complete!${NC}"
}

# Deploy admin dashboard
deploy_dashboard() {
    echo ""
    echo -e "${YELLOW}Deploying admin dashboard...${NC}"

    # Get stack outputs
    OUTPUTS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs')

    DASHBOARD_BUCKET=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="DashboardBucketName") | .OutputValue' 2>/dev/null)
    API_ENDPOINT=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="ApiEndpoint") | .OutputValue' 2>/dev/null)
    USER_POOL_ID=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="UserPoolId") | .OutputValue' 2>/dev/null)
    CLIENT_ID=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="UserPoolClientId") | .OutputValue' 2>/dev/null)
    COGNITO_DOMAIN=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="CognitoDomain") | .OutputValue' 2>/dev/null)

    # If we couldn't get the bucket name from outputs, construct it
    if [ -z "$DASHBOARD_BUCKET" ] || [ "$DASHBOARD_BUCKET" = "null" ]; then
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        DASHBOARD_BUCKET="animal-rescue-admin-${ENVIRONMENT}-${ACCOUNT_ID}"
    fi

    cd "$(dirname "$0")/../admin-dashboard"

    # Update config.js with actual values
    cat > config.js << EOF
/**
 * Animal Rescue Admin Dashboard - Configuration
 * Auto-generated by deploy.sh
 */

const CONFIG = {
    COGNITO: {
        REGION: '${AWS_REGION}',
        USER_POOL_ID: '${USER_POOL_ID}',
        CLIENT_ID: '${CLIENT_ID}',
        DOMAIN: '${COGNITO_DOMAIN}'
    },
    GOOGLE: {
        CLIENT_ID: '${GOOGLE_CLIENT_ID}'
    },
    API: {
        BASE_URL: '${API_ENDPOINT}',
        ENDPOINTS: {
            STATS: '/admin/stats',
            STATES: '/admin/states',
            SHELTERS: '/admin/shelters'
        }
    },
    APP: {
        PAGE_SIZE: 25,
        TOAST_DURATION: 3000
    }
};

CONFIG.AUTH = {
    LOGIN_URL: \`https://\${CONFIG.COGNITO.DOMAIN}/oauth2/authorize?\` +
        \`client_id=\${CONFIG.COGNITO.CLIENT_ID}&\` +
        \`response_type=token&\` +
        \`scope=openid+email+profile&\` +
        \`redirect_uri=\${encodeURIComponent(window.location.origin + window.location.pathname)}\`,
    LOGOUT_URL: \`https://\${CONFIG.COGNITO.DOMAIN}/logout?\` +
        \`client_id=\${CONFIG.COGNITO.CLIENT_ID}&\` +
        \`logout_uri=\${encodeURIComponent(window.location.origin + window.location.pathname)}\`
};
EOF

    # Upload dashboard files to S3
    aws s3 sync . "s3://${DASHBOARD_BUCKET}/" \
        --region "$AWS_REGION" \
        --exclude "*.md" \
        --exclude ".git/*"

    echo -e "${GREEN}Dashboard deployed!${NC}"
}

# Start initial collection
start_initial_collection() {
    echo ""
    read -p "Start initial data collection now? (y/n) [y]: " START_COLLECTION
    START_COLLECTION=${START_COLLECTION:-y}

    if [ "$START_COLLECTION" = "y" ] || [ "$START_COLLECTION" = "Y" ]; then
        echo -e "${YELLOW}Starting initial collection...${NC}"

        STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$AWS_REGION" \
            --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' \
            --output text)

        aws stepfunctions start-execution \
            --state-machine-arn "$STATE_MACHINE_ARN" \
            --input '{"mode": "initial_run"}' \
            --region "$AWS_REGION"

        echo -e "${GREEN}Initial collection started!${NC}"
        echo "This will process all 50 states sequentially."
        echo "You can monitor progress in the AWS Step Functions console."
    fi
}

# Display final information
show_summary() {
    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE} Deployment Complete!${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""

    # Get stack outputs
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table

    echo ""
    echo -e "${GREEN}Important URLs:${NC}"

    DASHBOARD_URL=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`DashboardUrl`].OutputValue' \
        --output text 2>/dev/null)

    CSV_LOCATION=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`LatestCsvLocation`].OutputValue' \
        --output text 2>/dev/null)

    echo "  Admin Dashboard: ${DASHBOARD_URL:-[see stack outputs]}"
    echo "  Latest CSV: ${CSV_LOCATION:-[see stack outputs]}"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Configure Google OAuth in Cognito console (if not done)"
    echo "  2. Add your callback URL to Google OAuth settings"
    echo "  3. Monitor collection progress in Step Functions console"
    echo "  4. Access your data via the admin dashboard or S3"
    echo ""
    echo -e "${GREEN}The agent will run automatically every day at 2 AM EST.${NC}"
}

# Main execution
main() {
    check_requirements
    get_configuration
    create_deployment_bucket
    deploy_stack
    deploy_dashboard
    start_initial_collection
    show_summary
}

main "$@"
