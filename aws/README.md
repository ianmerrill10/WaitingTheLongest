# Animal Rescue Search Agent - AWS Deployment

An AI-powered search agent that automatically collects and maintains a comprehensive database of animal rescues, shelters, humane societies, SPCAs, and sanctuaries across all 50 US states.

## Features

- **AI-Powered Search**: Uses AWS Bedrock (Claude) to intelligently search and extract organization data
- **50-State Coverage**: Automatically cycles through all US states
- **Daily Updates**: Runs automatically at 2 AM EST every day
- **CSV Export**: Generates downloadable CSV files for database import
- **Admin Dashboard**: Searchable web interface with Google OAuth authentication
- **Notes System**: Add and save notes about each organization
- **Verification Tracking**: Mark organizations as verified

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   EventBridge   │────▶│  Step Functions  │────▶│ Lambda Functions│
│  (2 AM EST)     │     │  (Orchestrator)  │     │                 │
└─────────────────┘     └──────────────────┘     │  - Search Agent │
                                                  │  - Orchestrator │
                                                  │  - CSV Exporter │
                                                  │  - Admin API    │
                                                  └────────┬────────┘
                                                           │
                        ┌──────────────────────────────────┼───────────────┐
                        │                                  │               │
                        ▼                                  ▼               ▼
                ┌───────────────┐                 ┌───────────────┐ ┌─────────────┐
                │   DynamoDB    │                 │      S3       │ │  Bedrock    │
                │  - Shelter    │                 │  - CSV Files  │ │  (Claude)   │
                │  - Progress   │                 │  - Dashboard  │ └─────────────┘
                └───────────────┘                 └───────────────┘

┌─────────────────┐     ┌──────────────────┐
│  Admin Dashboard│────▶│   API Gateway    │
│  (S3 Static)    │     │   + Cognito      │
│  Google OAuth   │     │   (Google OAuth) │
└─────────────────┘     └──────────────────┘
```

## Prerequisites

Before deploying, you'll need:

1. **AWS Account** with appropriate permissions
2. **SerpAPI Key** (free tier available at https://serpapi.com)
3. **Google OAuth Credentials** (from Google Cloud Console)

### Getting a SerpAPI Key

1. Go to https://serpapi.com
2. Create a free account (100 searches/month free)
3. Get your API key from the dashboard
4. For production, consider a paid plan ($50/month for 5,000 searches)

### Setting Up Google OAuth

1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new project or select existing
3. Go to "OAuth consent screen" and configure:
   - User Type: External
   - App name: "Animal Rescue Admin"
   - Add your email as test user
4. Go to "Credentials" → "Create Credentials" → "OAuth client ID"
5. Application type: Web application
6. Add authorized redirect URIs (after deployment):
   - `https://your-cognito-domain.auth.us-east-1.amazoncognito.com/oauth2/idpresponse`
7. Save your Client ID and Client Secret

## Quick Start - AWS CloudShell Deployment

### Step 1: Open AWS CloudShell

1. Log into the AWS Console
2. Click the CloudShell icon (terminal icon in top navigation)
3. Wait for the shell to initialize

### Step 2: Download the Code

```bash
# Clone the repository
git clone https://github.com/ianmerrill10/WaitingTheLongest.git
cd WaitingTheLongest/aws

# Make scripts executable
chmod +x scripts/*.sh
```

### Step 3: Run the Deployment Script

```bash
./scripts/deploy.sh
```

The script will prompt you for:
- Environment (dev/staging/prod)
- AWS Region
- SerpAPI Key
- Google OAuth Client ID
- Admin email addresses (optional)

### Step 4: Configure Google OAuth (Post-Deployment)

After deployment, update your Google OAuth settings:

1. Get the Cognito Domain from the deployment output
2. Add to Google OAuth redirect URIs:
   ```
   https://{cognito-domain}/oauth2/idpresponse
   ```
3. In AWS Console → Cognito → User Pools:
   - Find your user pool
   - Go to "Sign-in experience" → "Identity providers"
   - Edit Google provider and add your Client Secret

### Step 5: Access Your Dashboard

The deployment script will output your dashboard URL:
```
https://animal-rescue-admin-prod-{account-id}.s3-website-us-east-1.amazonaws.com
```

## Manual Commands

### Check Collection Progress

```bash
./scripts/manual-run.sh
# Select option 3
```

### Manually Trigger Collection

```bash
./scripts/manual-run.sh
# Select option 1 for full cycle, or 2 for specific state
```

### Download CSV Files

```bash
./scripts/download-csv.sh
```

This creates a local folder with:
- `animal_rescues_all_states.csv` - Master file with all organizations
- `states/` - Individual state CSV files
- `latest_report.json` - Statistics report

## CSV File Format

The exported CSV includes these columns:

| Column | Description |
|--------|-------------|
| shelter_id | Unique identifier |
| name | Organization name |
| org_type | Type (shelter, rescue, humane_society, spca, etc.) |
| state | Two-letter state code |
| city | City name |
| address | Street address |
| zip_code | ZIP/postal code |
| phone | Phone number |
| email | Email address |
| website | Website URL |
| description | Brief description/mission |
| notes | Admin notes |
| verified | Whether verified (Yes/No) |
| source | Data source |
| collected_at | When data was collected |
| last_updated | Last modification date |

## Admin Dashboard Features

### Search & Filter
- Full-text search across name, city, description
- Filter by state
- Filter by organization type
- Show only verified organizations

### Organization Details
- View and edit all contact information
- Add/edit admin notes
- Mark as verified
- See collection metadata

### Security
- Google OAuth authentication
- Optional email whitelist for admin access
- All API calls require valid token

## Costs

Estimated monthly costs (varies by usage):

| Service | Estimated Cost |
|---------|---------------|
| Lambda | ~$5-15 |
| DynamoDB | ~$5-10 |
| S3 | ~$1-5 |
| Bedrock (Claude) | ~$20-50 |
| SerpAPI | $0-50 |
| Step Functions | ~$1-5 |
| **Total** | **~$30-140/month** |

*Costs depend on collection frequency and data volume*

## Cleanup

To remove all resources:

```bash
./scripts/cleanup.sh
```

**Warning**: This deletes all data including collected organizations!

## Troubleshooting

### Lambda Timeout Errors
- Large states may take longer; the default timeout is 10 minutes
- Consider increasing Lambda memory for faster processing

### SerpAPI Rate Limits
- Free tier: 100 searches/month
- Each state uses ~20-30 searches
- Upgrade to paid plan for full 50-state coverage

### Google OAuth Not Working
1. Verify Client ID is correct in config.js
2. Check redirect URIs in Google Console
3. Ensure Client Secret is in Cognito
4. Check Cognito domain is correct

### No Data in Dashboard
1. Check Step Functions execution status
2. Verify DynamoDB tables have data
3. Check Lambda logs in CloudWatch

## Files Structure

```
aws/
├── lambda/
│   ├── shelter_search_agent.py  # AI-powered search
│   ├── orchestrator.py          # State orchestration
│   ├── csv_exporter.py          # CSV generation
│   └── admin_api.py             # Dashboard API
├── admin-dashboard/
│   ├── index.html               # Dashboard HTML
│   ├── styles.css               # Dashboard styles
│   ├── app.js                   # Dashboard logic
│   └── config.js                # Configuration
├── stepfunctions/
│   └── shelter_collection_workflow.json
├── cloudformation/
│   └── animal-rescue-stack.yaml # Infrastructure
├── scripts/
│   ├── deploy.sh                # Main deployment
│   ├── manual-run.sh            # Manual triggers
│   ├── download-csv.sh          # CSV download
│   └── cleanup.sh               # Resource cleanup
└── README.md                    # This file
```

## Data Quality

The agent:
- **Includes**: Non-profit rescues, shelters, humane societies, SPCAs, ASPCAs, sanctuaries, foster networks
- **Excludes**: Breeders, pet stores, puppy mills, for-profit businesses

Use the admin dashboard to:
- Verify organization legitimacy
- Add notes about status
- Mark confirmed organizations as verified

## Support

For issues or questions:
1. Check CloudWatch Logs for Lambda errors
2. Check Step Functions execution history
3. Review this README troubleshooting section

---

*Built for helping animals find forever homes.*
