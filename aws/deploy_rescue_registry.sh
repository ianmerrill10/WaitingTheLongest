#!/bin/bash
###############################################################################
# WAITING THE LONGEST - Rescue Registry AWS Deployment
# Single-paste CloudShell script - NOISY ON ERRORS
###############################################################################
set -euxo pipefail  # -e: exit on error, -u: unset vars error, -x: print cmds, -o pipefail: pipe errors

echo "=========================================="
echo "WTL RESCUE REGISTRY DEPLOYMENT STARTING"
echo "=========================================="
date

# Generate unique suffix using timestamp
SUFFIX=$(date +%s | tail -c 6)
REGION=${AWS_REGION:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo ">>> Account ID: $ACCOUNT_ID"
echo ">>> Region: $REGION"
echo ">>> Unique Suffix: $SUFFIX"

# Resource names
BUCKET_NAME="wtl-rescue-registry-${SUFFIX}"
DB_INSTANCE="wtl-rescue-db-${SUFFIX}"
DB_NAME="rescueregistry"
DB_USER="wtladmin"
DB_PASS="WtlRescue2025Secure!"  # Change in production!
SECRET_NAME="wtl-rescue-db-url-${SUFFIX}"
ROLE_NAME="wtl-rescue-lambda-role-${SUFFIX}"
LAYER_NAME="wtl-rescue-layer-${SUFFIX}"
ORCHESTRATOR_NAME="wtl-orchestrator-${SUFFIX}"
EXTRACTOR_NAME="wtl-contact-extractor-${SUFFIX}"

echo ""
echo "=========================================="
echo "STEP 1: CREATE S3 BUCKET"
echo "=========================================="

# Create bucket (us-east-1 doesn't need LocationConstraint)
if [ "$REGION" == "us-east-1" ]; then
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION"
else
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" \
        --create-bucket-configuration LocationConstraint="$REGION"
fi

echo ">>> Created bucket: $BUCKET_NAME"

# Create folder structure
aws s3api put-object --bucket "$BUCKET_NAME" --key "raw/" --content-length 0
aws s3api put-object --bucket "$BUCKET_NAME" --key "processed/" --content-length 0
aws s3api put-object --bucket "$BUCKET_NAME" --key "failed/" --content-length 0
echo ">>> Created folder structure in bucket"

echo ""
echo "=========================================="
echo "STEP 2: CREATE RDS POSTGRESQL INSTANCE"
echo "=========================================="

# Create DB subnet group using default VPC
DEFAULT_VPC=$(aws ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text)
echo ">>> Default VPC: $DEFAULT_VPC"

SUBNETS=$(aws ec2 describe-subnets --filters Name=vpc-id,Values="$DEFAULT_VPC" --query 'Subnets[*].SubnetId' --output text | tr '\t' ',')
echo ">>> Subnets: $SUBNETS"

# Check if default subnet group exists, create if not
DB_SUBNET_GROUP="wtl-rescue-subnet-${SUFFIX}"
aws rds create-db-subnet-group \
    --db-subnet-group-name "$DB_SUBNET_GROUP" \
    --db-subnet-group-description "WTL Rescue Registry subnet group" \
    --subnet-ids ${SUBNETS//,/ }

echo ">>> Created DB subnet group: $DB_SUBNET_GROUP"

# Create security group for RDS
SG_NAME="wtl-rescue-db-sg-${SUFFIX}"
SG_ID=$(aws ec2 create-security-group \
    --group-name "$SG_NAME" \
    --description "Security group for WTL Rescue Registry DB" \
    --vpc-id "$DEFAULT_VPC" \
    --query 'GroupId' --output text)

echo ">>> Created security group: $SG_ID"

# Allow PostgreSQL from anywhere (restrict in production!)
aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 5432 \
    --cidr 0.0.0.0/0

echo ">>> Opened port 5432 on security group"

# Create RDS instance (free tier eligible: db.t3.micro, 20GB)
aws rds create-db-instance \
    --db-instance-identifier "$DB_INSTANCE" \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15 \
    --master-username "$DB_USER" \
    --master-user-password "$DB_PASS" \
    --allocated-storage 20 \
    --db-name "$DB_NAME" \
    --db-subnet-group-name "$DB_SUBNET_GROUP" \
    --vpc-security-group-ids "$SG_ID" \
    --publicly-accessible \
    --no-multi-az \
    --storage-type gp2 \
    --backup-retention-period 1

echo ">>> RDS instance creation initiated: $DB_INSTANCE"
echo ">>> WAITING FOR RDS TO BE AVAILABLE (this takes 5-10 minutes)..."

# Wait for RDS to be available
aws rds wait db-instance-available --db-instance-identifier "$DB_INSTANCE"

echo ">>> RDS IS READY!"

# Get RDS endpoint
DB_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier "$DB_INSTANCE" \
    --query 'DBInstances[0].Endpoint.Address' --output text)

echo ">>> RDS Endpoint: $DB_ENDPOINT"

# Build database URL
DATABASE_URL="postgresql://${DB_USER}:${DB_PASS}@${DB_ENDPOINT}:5432/${DB_NAME}"
echo ">>> Database URL constructed"

echo ""
echo "=========================================="
echo "STEP 3: STORE DB URL IN SECRETS MANAGER"
echo "=========================================="

aws secretsmanager create-secret \
    --name "$SECRET_NAME" \
    --description "WTL Rescue Registry database connection string" \
    --secret-string "$DATABASE_URL"

echo ">>> Stored secret: $SECRET_NAME"

echo ""
echo "=========================================="
echo "STEP 4: CREATE IAM ROLE FOR LAMBDAS"
echo "=========================================="

# Trust policy for Lambda
cat > /tmp/trust-policy.json << 'TRUST'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
TRUST

aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document file:///tmp/trust-policy.json

echo ">>> Created IAM role: $ROLE_NAME"

# Attach policies
aws iam attach-role-policy --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam attach-role-policy --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam attach-role-policy --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
aws iam attach-role-policy --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonRDSDataFullAccess

echo ">>> Attached policies to role"

# Get role ARN
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo ">>> Role ARN: $ROLE_ARN"

# Wait for IAM propagation
echo ">>> Waiting 15s for IAM role propagation..."
sleep 15

echo ""
echo "=========================================="
echo "STEP 5: CREATE LAMBDA LAYER (psycopg2)"
echo "=========================================="

# Create layer with psycopg2-binary
mkdir -p /tmp/layer/python
pip3 install psycopg2-binary -t /tmp/layer/python --quiet
cd /tmp/layer && zip -r9 /tmp/psycopg2-layer.zip python
cd -

aws lambda publish-layer-version \
    --layer-name "$LAYER_NAME" \
    --description "psycopg2 for WTL Rescue Registry" \
    --zip-file fileb:///tmp/psycopg2-layer.zip \
    --compatible-runtimes python3.11 python3.12

LAYER_ARN=$(aws lambda list-layer-versions --layer-name "$LAYER_NAME" \
    --query 'LayerVersions[0].LayerVersionArn' --output text)

echo ">>> Created layer: $LAYER_ARN"

echo ""
echo "=========================================="
echo "STEP 6: CREATE CONTACT EXTRACTOR LAMBDA"
echo "=========================================="

# Contact extractor code
cat > /tmp/extractor.py << 'EXTRACTOR'
import json
import re
import boto3
import os

def extract_contacts(text):
    """Extract contact info from raw text."""
    contacts = []

    # Split into lines/records
    lines = text.strip().split('\n')

    # Phone pattern
    phone_re = re.compile(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
    # Email pattern
    email_re = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
    # Website pattern
    website_re = re.compile(r'(https?://)?(www\.)?[\w\.-]+\.(com|org|net|gov|edu)(/\S*)?', re.I)
    # US state codes
    states = r'AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC'
    # Zip code pattern
    zip_re = re.compile(rf'\b({states})\s*(\d{{5}}(?:-\d{{4}})?)\b')

    for line in lines:
        if not line.strip() or 'Organization Name' in line:
            continue

        # Try tab-separated first
        parts = line.split('\t')
        if len(parts) < 3:
            parts = re.split(r'\s{2,}', line)

        if len(parts) >= 2:
            record = {
                'name': parts[0].strip(),
                'raw_line': line,
                'phones': phone_re.findall(line),
                'emails': email_re.findall(line),
                'websites': [m[0] if m[0] else f"www.{m[2]}" for m in website_re.findall(line)],
            }

            # Extract state/zip
            zip_match = zip_re.search(line)
            if zip_match:
                record['state'] = zip_match.group(1)
                record['zip_code'] = zip_match.group(2)

            # Try to identify city from location column if present
            if len(parts) >= 3:
                loc = parts[2] if len(parts) > 2 else ''
                record['location_raw'] = loc
                # Extract city from parentheses like "Warren (Blairstown)"
                city_match = re.search(r'\(([^)]+)\)', loc)
                if city_match:
                    record['city'] = city_match.group(1)

            contacts.append(record)

    return contacts

def lambda_handler(event, context):
    print(f"EVENT: {json.dumps(event)}")

    s3 = boto3.client('s3')

    bucket = event['bucket']
    key = event['key']

    print(f"Processing s3://{bucket}/{key}")

    # Download file
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')

    print(f"Downloaded {len(content)} bytes")

    # Extract contacts
    contacts = extract_contacts(content)

    print(f"Extracted {len(contacts)} contacts")

    # Store processed results
    output_key = key.replace('raw/', 'processed/').replace('.txt', '.json')
    s3.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=json.dumps(contacts, indent=2),
        ContentType='application/json'
    )

    print(f"Saved to s3://{bucket}/{output_key}")

    return {
        'statusCode': 200,
        'bucket': bucket,
        'output_key': output_key,
        'contacts_count': len(contacts),
        'contacts': contacts
    }
EXTRACTOR

cd /tmp && zip -j extractor.zip extractor.py
cd -

aws lambda create-function \
    --function-name "$EXTRACTOR_NAME" \
    --runtime python3.11 \
    --role "$ROLE_ARN" \
    --handler extractor.lambda_handler \
    --zip-file fileb:///tmp/extractor.zip \
    --timeout 60 \
    --memory-size 256

echo ">>> Created extractor Lambda: $EXTRACTOR_NAME"

echo ""
echo "=========================================="
echo "STEP 7: CREATE ORCHESTRATOR LAMBDA"
echo "=========================================="

# Orchestrator code
cat > /tmp/orchestrator.py << ORCHESTRATOR
import json
import boto3
import os
import psycopg2
from datetime import datetime

def get_db_url():
    """Get database URL from Secrets Manager."""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='${SECRET_NAME}')
    return response['SecretString']

def save_to_db(contacts, source_file):
    """Save extracted contacts to PostgreSQL."""
    db_url = get_db_url()
    print(f"Connecting to database...")

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Create table if not exists
    cur.execute('''
        CREATE TABLE IF NOT EXISTS shelters (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            source VARCHAR(50),
            external_id VARCHAR(100),
            email VARCHAR(200),
            phone VARCHAR(50),
            website TEXT,
            description TEXT,
            address VARCHAR(300),
            city VARCHAR(100),
            state VARCHAR(50),
            zip_code VARCHAR(20),
            latitude FLOAT,
            longitude FLOAT,
            total_animals INTEGER DEFAULT 0,
            facebook_url TEXT,
            instagram_url TEXT,
            twitter_url TEXT,
            last_verified_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    inserted = 0
    updated = 0

    for contact in contacts:
        name = contact.get('name', '').strip()
        if not name:
            continue

        email = contact['emails'][0] if contact.get('emails') else None
        phone = contact['phones'][0] if contact.get('phones') else None
        website = contact['websites'][0] if contact.get('websites') else None
        city = contact.get('city')
        state = contact.get('state')
        zip_code = contact.get('zip_code')

        # Check if exists
        cur.execute('SELECT id FROM shelters WHERE name = %s AND state = %s', (name, state))
        existing = cur.fetchone()

        if existing:
            cur.execute('''
                UPDATE shelters SET
                    email = COALESCE(%s, email),
                    phone = COALESCE(%s, phone),
                    website = COALESCE(%s, website),
                    city = COALESCE(%s, city),
                    zip_code = COALESCE(%s, zip_code),
                    last_verified_at = %s,
                    updated_at = %s
                WHERE id = %s
            ''', (email, phone, website, city, zip_code, datetime.utcnow(), datetime.utcnow(), existing[0]))
            updated += 1
        else:
            cur.execute('''
                INSERT INTO shelters (name, source, email, phone, website, city, state, zip_code, last_verified_at, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (name, source_file, email, phone, website, city, state, zip_code, datetime.utcnow(), datetime.utcnow(), datetime.utcnow()))
            inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    return inserted, updated

def lambda_handler(event, context):
    print(f"ORCHESTRATOR EVENT: {json.dumps(event)}")

    s3 = boto3.client('s3')
    lambda_client = boto3.client('lambda')

    bucket = event.get('bucket', '${BUCKET_NAME}')

    # List raw files
    response = s3.list_objects_v2(Bucket=bucket, Prefix='raw/')
    files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'] != 'raw/']

    print(f"Found {len(files)} files in raw/")

    results = []
    total_inserted = 0
    total_updated = 0

    for file_key in files:
        print(f"Processing: {file_key}")

        # Call extractor
        extract_response = lambda_client.invoke(
            FunctionName='${EXTRACTOR_NAME}',
            InvocationType='RequestResponse',
            Payload=json.dumps({'bucket': bucket, 'key': file_key})
        )

        payload = json.loads(extract_response['Payload'].read())
        print(f"Extractor response: {payload}")

        if payload.get('statusCode') == 200:
            contacts = payload.get('contacts', [])

            # Save to database
            try:
                inserted, updated = save_to_db(contacts, file_key)
                total_inserted += inserted
                total_updated += updated

                results.append({
                    'file': file_key,
                    'status': 'success',
                    'contacts': len(contacts),
                    'inserted': inserted,
                    'updated': updated
                })

                # Move to processed
                s3.copy_object(
                    Bucket=bucket,
                    CopySource={'Bucket': bucket, 'Key': file_key},
                    Key=file_key.replace('raw/', 'processed/')
                )
                s3.delete_object(Bucket=bucket, Key=file_key)

            except Exception as e:
                print(f"DB ERROR: {e}")
                results.append({
                    'file': file_key,
                    'status': 'db_error',
                    'error': str(e)
                })
                # Move to failed
                s3.copy_object(
                    Bucket=bucket,
                    CopySource={'Bucket': bucket, 'Key': file_key},
                    Key=file_key.replace('raw/', 'failed/')
                )
        else:
            results.append({
                'file': file_key,
                'status': 'extract_error',
                'error': payload
            })

    return {
        'statusCode': 200,
        'files_processed': len(files),
        'total_inserted': total_inserted,
        'total_updated': total_updated,
        'results': results
    }
ORCHESTRATOR

cd /tmp && zip -j orchestrator.zip orchestrator.py
cd -

aws lambda create-function \
    --function-name "$ORCHESTRATOR_NAME" \
    --runtime python3.11 \
    --role "$ROLE_ARN" \
    --handler orchestrator.lambda_handler \
    --zip-file fileb:///tmp/orchestrator.zip \
    --timeout 300 \
    --memory-size 512 \
    --layers "$LAYER_ARN" \
    --environment "Variables={SECRET_NAME=$SECRET_NAME}"

echo ">>> Created orchestrator Lambda: $ORCHESTRATOR_NAME"

echo ""
echo "=========================================="
echo "STEP 8: UPLOAD SAMPLE DATA"
echo "=========================================="

# Create sample NJ shelters file
cat > /tmp/nj_shelters.txt << 'NJDATA'
Comprehensive New Jersey Animal Adoption Directory
Organization Name	Type	County / Area	Contact Info	Description
A Helping Wing Parrot Rescue	Rescue (Birds)	Warren (Blairstown)	ahelpingwing.org	Volunteer-run rescue dedicated to parrots and exotic birds.
A Pathway to Hope	Rescue	Passaic (Hawthorne)	apathwaytohope.org	Foster-based rescue focusing on special needs dogs.
All Fur Love Animal Rescue	Rescue	Monmouth (Freehold)	allfurlove.org	Volunteer organization for cats and kittens.
Almost Home Animal Shelter	Shelter	Camden (Pennsauken)	(856) 663-3058	Shelter for stray and unwanted animals.
Animal Welfare Association (AWA)	Shelter	Camden (Voorhees)	(856) 424-2288	South Jersey's oldest private shelter.
Bergen County Animal Shelter	Municipal	Bergen (Teterboro)	(201) 229-4600	County facility for animal control and adoptions.
Eleventh Hour Rescue	Rescue	Morris (Randolph)	ehrdogs.org	Saves dogs and cats from death row.
Home for Good Dog Rescue	Rescue	Union (Berkeley Heights)	(908) 598-8212	Rescues dogs from the South.
Liberty Humane Society	Shelter	Hudson (Jersey City)	(201) 547-4147	Major urban shelter.
St. Hubert's Animal Welfare Center	Shelter	Morris (Madison)	(973) 377-2295	Major hub for animal welfare.
NJDATA

aws s3 cp /tmp/nj_shelters.txt "s3://${BUCKET_NAME}/raw/nj_shelters.txt"

echo ">>> Uploaded sample data to s3://${BUCKET_NAME}/raw/nj_shelters.txt"

echo ""
echo "=========================================="
echo "STEP 9: INVOKE ORCHESTRATOR"
echo "=========================================="

aws lambda invoke \
    --function-name "$ORCHESTRATOR_NAME" \
    --payload '{"bucket":"'"$BUCKET_NAME"'"}' \
    --cli-binary-format raw-in-base64-out \
    /tmp/invoke-result.json

echo ">>> Orchestrator invocation result:"
cat /tmp/invoke-result.json
echo ""

echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "RESOURCES CREATED:"
echo "  S3 Bucket:        $BUCKET_NAME"
echo "  RDS Instance:     $DB_INSTANCE"
echo "  RDS Endpoint:     $DB_ENDPOINT"
echo "  Secret:           $SECRET_NAME"
echo "  IAM Role:         $ROLE_NAME"
echo "  Lambda Layer:     $LAYER_NAME"
echo "  Extractor Lambda: $EXTRACTOR_NAME"
echo "  Orchestrator:     $ORCHESTRATOR_NAME"
echo ""
echo "TO ADD MORE DATA:"
echo "  aws s3 cp your_file.txt s3://$BUCKET_NAME/raw/"
echo "  aws lambda invoke --function-name $ORCHESTRATOR_NAME --payload '{}' result.json"
echo ""
echo "TO VERIFY:"
echo "  aws s3 ls s3://$BUCKET_NAME/raw/"
echo "  aws s3 ls s3://$BUCKET_NAME/processed/"
echo "  aws logs tail /aws/lambda/$ORCHESTRATOR_NAME --since 10m"
echo ""
date
echo "=========================================="
