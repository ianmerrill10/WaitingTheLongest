"""
===============================================================================
Animal Rescue Search Agent - AWS Lambda Function
===============================================================================
Purpose: AI-powered search agent using AWS Bedrock to find and collect
         animal rescue, shelter, and humane society data across US states.

Uses: AWS Bedrock (Claude), DynamoDB, S3, SerpAPI for web search
Triggers: Step Functions orchestration
Schedule: Daily at 2 AM EST via EventBridge

Author: Waiting The Longest Development Team
===============================================================================
"""

import json
import boto3
import os
import re
import csv
import io
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from botocore.config import Config

# AWS Clients with retry configuration
bedrock_config = Config(
    retries={'max_attempts': 3, 'mode': 'adaptive'},
    read_timeout=300,
    connect_timeout=10
)

# Initialize AWS clients
bedrock_runtime = boto3.client(
    'bedrock-runtime',
    region_name=os.environ.get('AWS_REGION', 'us-east-1'),
    config=bedrock_config
)
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
secrets_manager = boto3.client('secretsmanager')

# Environment variables
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'AnimalRescueData')
BUCKET_NAME = os.environ.get('S3_BUCKET', 'animal-rescue-data')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')

# All 50 US states
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming"
}

# Organization types to search for
SEARCH_CATEGORIES = [
    "animal shelter",
    "dog rescue",
    "cat rescue",
    "humane society",
    "SPCA",
    "ASPCA",
    "animal rescue",
    "pet adoption center",
    "animal sanctuary",
    "no-kill shelter",
    "animal foster network",
    "wildlife rescue",
    "exotic animal rescue",
    "rabbit rescue",
    "bird rescue",
    "horse rescue",
    "farm animal sanctuary"
]

# Terms to exclude (for-profit indicators)
EXCLUDE_TERMS = [
    "breeder", "breeding", "for sale", "puppies for sale",
    "kittens for sale", "pet store", "pet shop", "puppy mill",
    "akc breeder", "registered breeder", "champion bloodline"
]


def get_search_api_key() -> str:
    """Retrieve SerpAPI key from Secrets Manager"""
    try:
        response = secrets_manager.get_secret_value(
            SecretId=os.environ.get('SERPAPI_SECRET_ARN', 'animal-rescue-search/serpapi')
        )
        secret = json.loads(response['SecretString'])
        return secret.get('api_key', '')
    except Exception as e:
        print(f"Error retrieving API key: {e}")
        return os.environ.get('SERPAPI_KEY', '')


def search_web(query: str, api_key: str, num_results: int = 100) -> List[Dict]:
    """
    Perform web search using SerpAPI
    Returns list of search results
    """
    import urllib.request
    import urllib.parse

    params = {
        'q': query,
        'api_key': api_key,
        'engine': 'google',
        'num': num_results,
        'gl': 'us',
        'hl': 'en'
    }

    url = f"https://serpapi.com/search?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AnimalRescueAgent/1.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data.get('organic_results', [])
    except Exception as e:
        print(f"Search error: {e}")
        return []


def invoke_bedrock_claude(prompt: str, max_tokens: int = 4096) -> str:
    """
    Invoke AWS Bedrock Claude model for intelligent data extraction
    """
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })

        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=body,
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    except Exception as e:
        print(f"Bedrock invocation error: {e}")
        return ""


def extract_shelter_info(search_results: List[Dict], state: str, state_full: str) -> List[Dict]:
    """
    Use Bedrock Claude to intelligently extract and validate shelter information
    from search results
    """
    if not search_results:
        return []

    # Format search results for Claude
    results_text = ""
    for i, result in enumerate(search_results[:50], 1):  # Limit to top 50 results
        results_text += f"""
Result {i}:
Title: {result.get('title', 'N/A')}
Link: {result.get('link', 'N/A')}
Snippet: {result.get('snippet', 'N/A')}
---
"""

    prompt = f"""You are an expert at identifying legitimate non-profit animal rescue organizations.

Analyze these search results for {state_full} ({state}) and extract information about legitimate animal rescues, shelters, humane societies, SPCAs, and sanctuaries.

IMPORTANT RULES:
1. ONLY include non-profit organizations (501(c)(3) or municipal shelters)
2. EXCLUDE: breeders, pet stores, for-profit businesses, puppy mills, commercial sellers
3. EXCLUDE: organizations that sell animals for profit
4. Include: shelters, rescues, humane societies, SPCA, ASPCA, sanctuaries, foster networks
5. Include organizations that help dogs, cats, and other animals (rabbits, birds, horses, etc.)

For each valid organization, extract:
- name: Official organization name
- type: One of [shelter, rescue, humane_society, spca, aspca, animal_control, sanctuary, foster_network, nonprofit]
- website: Full URL if available
- phone: Phone number if visible in snippet
- email: Email if visible in snippet
- city: City in {state_full}
- description: Brief description of their mission (1-2 sentences)

SEARCH RESULTS:
{results_text}

Return ONLY a valid JSON array of shelter objects. If no valid organizations found, return an empty array [].
Format each object exactly like this:
{{
  "name": "Organization Name",
  "type": "rescue",
  "website": "https://example.org",
  "phone": "(555) 123-4567",
  "email": "info@example.org",
  "city": "City Name",
  "state": "{state}",
  "description": "Brief mission description"
}}

JSON Array:"""

    response = invoke_bedrock_claude(prompt)

    # Parse the response
    try:
        # Find JSON array in response
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            shelters = json.loads(json_match.group())
            # Validate and clean each shelter
            valid_shelters = []
            for shelter in shelters:
                if shelter.get('name') and len(shelter.get('name', '')) > 2:
                    # Ensure state is set correctly
                    shelter['state'] = state
                    # Clean phone number
                    if shelter.get('phone'):
                        shelter['phone'] = re.sub(r'[^\d\-\(\)\s\+]', '', str(shelter['phone']))[:50]
                    valid_shelters.append(shelter)
            return valid_shelters
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")

    return []


def search_state_shelters(state: str, state_full: str, api_key: str) -> List[Dict]:
    """
    Comprehensive search for all animal rescues in a state
    Uses multiple search queries to maximize coverage
    """
    all_shelters = {}  # Use dict to deduplicate by name

    # Generate search queries for different categories
    for category in SEARCH_CATEGORIES:
        query = f"{category} {state_full} nonprofit -breeder -\"for sale\" -\"puppy mill\""
        print(f"Searching: {query}")

        results = search_web(query, api_key)
        shelters = extract_shelter_info(results, state, state_full)

        for shelter in shelters:
            # Create unique key for deduplication
            name_key = shelter.get('name', '').lower().strip()
            if name_key and name_key not in all_shelters:
                all_shelters[name_key] = shelter

    # Also search by major cities in the state
    major_cities_query = f"animal shelter OR rescue {state_full} major cities nonprofit"
    city_results = search_web(major_cities_query, api_key)
    city_shelters = extract_shelter_info(city_results, state, state_full)

    for shelter in city_shelters:
        name_key = shelter.get('name', '').lower().strip()
        if name_key and name_key not in all_shelters:
            all_shelters[name_key] = shelter

    return list(all_shelters.values())


def enrich_shelter_data(shelters: List[Dict], state: str, state_full: str) -> List[Dict]:
    """
    Use Bedrock to enrich shelter data with additional details
    by searching for more information about each organization
    """
    if not shelters:
        return []

    # Prepare batch for enrichment
    shelter_names = [s.get('name', '') for s in shelters[:30]]  # Limit batch size

    prompt = f"""For each of these {state_full} animal rescue organizations, provide any additional contact information you know:

Organizations:
{json.dumps(shelter_names, indent=2)}

For each organization, provide:
1. Full address if known
2. Phone number if not already provided
3. Email if not already provided
4. Brief description of their mission
5. Types of animals they help (dogs, cats, rabbits, horses, etc.)

Return as JSON array matching the organization order:
[
  {{
    "name": "Organization Name",
    "address": "Full street address",
    "phone": "Phone number",
    "email": "Email address",
    "description": "Brief mission description",
    "animal_types": ["dogs", "cats"]
  }}
]

Only include information you are confident about. Use null for unknown fields.
JSON Array:"""

    response = invoke_bedrock_claude(prompt, max_tokens=8000)

    try:
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            enriched = json.loads(json_match.group())

            # Merge enriched data with original shelters
            for i, shelter in enumerate(shelters[:30]):
                if i < len(enriched):
                    enrichment = enriched[i]
                    # Only update fields that are empty
                    if not shelter.get('address') and enrichment.get('address'):
                        shelter['address'] = enrichment['address']
                    if not shelter.get('phone') and enrichment.get('phone'):
                        shelter['phone'] = enrichment['phone']
                    if not shelter.get('email') and enrichment.get('email'):
                        shelter['email'] = enrichment['email']
                    if not shelter.get('description') and enrichment.get('description'):
                        shelter['description'] = enrichment['description']
    except (json.JSONDecodeError, Exception) as e:
        print(f"Enrichment error: {e}")

    return shelters


def save_to_dynamodb(shelters: List[Dict], state: str) -> int:
    """
    Save shelter data to DynamoDB with upsert logic
    """
    table = dynamodb.Table(TABLE_NAME)
    saved_count = 0
    timestamp = datetime.now(timezone.utc).isoformat()

    for shelter in shelters:
        try:
            # Generate unique ID from name and state
            shelter_id = hashlib.md5(
                f"{shelter.get('name', '')}-{state}".lower().encode()
            ).hexdigest()[:16]

            item = {
                'shelter_id': shelter_id,
                'state': state,
                'name': shelter.get('name', ''),
                'org_type': shelter.get('type', 'nonprofit'),
                'website': shelter.get('website'),
                'phone': shelter.get('phone'),
                'email': shelter.get('email'),
                'address': shelter.get('address'),
                'city': shelter.get('city'),
                'zip_code': shelter.get('zip_code'),
                'description': shelter.get('description'),
                'source': 'bedrock_search_agent',
                'collected_at': timestamp,
                'last_updated': timestamp,
                'verified': False
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            table.put_item(Item=item)
            saved_count += 1
        except Exception as e:
            print(f"DynamoDB error for {shelter.get('name')}: {e}")

    return saved_count


def export_state_to_s3(shelters: List[Dict], state: str, state_full: str) -> str:
    """
    Export state shelter data to S3 as both JSON and CSV
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d')

    # Prepare data
    export_data = {
        'state': state,
        'state_full': state_full,
        'collection_date': datetime.now(timezone.utc).isoformat(),
        'total_count': len(shelters),
        'source': 'bedrock_search_agent',
        'shelters': shelters
    }

    # Save JSON
    json_key = f"states/{state}/{state}_shelters_{timestamp}.json"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=json_key,
        Body=json.dumps(export_data, indent=2),
        ContentType='application/json'
    )

    # Save CSV
    csv_buffer = io.StringIO()
    if shelters:
        fieldnames = ['name', 'type', 'website', 'phone', 'email', 'address',
                      'city', 'state', 'zip_code', 'description']
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(shelters)

    csv_key = f"states/{state}/{state}_shelters_{timestamp}.csv"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=csv_key,
        Body=csv_buffer.getvalue(),
        ContentType='text/csv'
    )

    # Also update the latest version
    latest_json_key = f"states/{state}/{state}_shelters_latest.json"
    latest_csv_key = f"states/{state}/{state}_shelters_latest.csv"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=latest_json_key,
        Body=json.dumps(export_data, indent=2),
        ContentType='application/json'
    )
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=latest_csv_key,
        Body=csv_buffer.getvalue(),
        ContentType='text/csv'
    )

    return f"s3://{BUCKET_NAME}/{csv_key}"


def update_progress_tracker(state: str, shelter_count: int, status: str = 'completed'):
    """
    Update the collection progress in DynamoDB
    """
    table = dynamodb.Table(f"{TABLE_NAME}_Progress")
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        table.update_item(
            Key={'state': state},
            UpdateExpression='SET #status = :status, shelter_count = :count, last_collection = :ts',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': status,
                ':count': shelter_count,
                ':ts': timestamp
            }
        )
    except Exception as e:
        print(f"Progress update error: {e}")


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler for processing a single state

    Event format:
    {
        "state": "TX",
        "state_full": "Texas"
    }

    Returns:
    {
        "state": "TX",
        "state_full": "Texas",
        "shelters_found": 150,
        "status": "success",
        "s3_location": "s3://bucket/path",
        "execution_time_seconds": 120
    }
    """
    import time
    start_time = time.time()

    # Get state from event
    state = event.get('state', '').upper()
    state_full = event.get('state_full') or US_STATES.get(state, '')

    if state not in US_STATES:
        return {
            'state': state,
            'status': 'error',
            'error': f'Invalid state: {state}'
        }

    print(f"Starting collection for {state_full} ({state})")

    try:
        # Get API key
        api_key = get_search_api_key()
        if not api_key:
            raise ValueError("No search API key available")

        # Search for shelters
        shelters = search_state_shelters(state, state_full, api_key)
        print(f"Found {len(shelters)} initial shelters")

        # Enrich with additional data
        shelters = enrich_shelter_data(shelters, state, state_full)
        print(f"Enriched {len(shelters)} shelters")

        # Save to DynamoDB
        saved_count = save_to_dynamodb(shelters, state)
        print(f"Saved {saved_count} shelters to DynamoDB")

        # Export to S3
        s3_location = export_state_to_s3(shelters, state, state_full)
        print(f"Exported to {s3_location}")

        # Update progress
        update_progress_tracker(state, len(shelters), 'completed')

        execution_time = round(time.time() - start_time, 2)

        return {
            'state': state,
            'state_full': state_full,
            'shelters_found': len(shelters),
            'shelters_saved': saved_count,
            'status': 'success',
            's3_location': s3_location,
            'execution_time_seconds': execution_time
        }

    except Exception as e:
        print(f"Error processing {state}: {str(e)}")
        update_progress_tracker(state, 0, 'error')

        return {
            'state': state,
            'state_full': state_full,
            'status': 'error',
            'error': str(e),
            'execution_time_seconds': round(time.time() - start_time, 2)
        }


# For local testing
if __name__ == "__main__":
    test_event = {
        "state": "ME",
        "state_full": "Maine"
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
