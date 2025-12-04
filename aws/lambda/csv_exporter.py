"""
===============================================================================
Animal Rescue Search Agent - CSV Exporter Lambda
===============================================================================
Purpose: Exports all collected shelter data to a consolidated CSV file.
         Creates master CSV with all organizations from all 50 states.
         Generates daily and cumulative reports.

Uses: DynamoDB, S3
Triggers: After daily collection cycle completes

Author: Waiting The Longest Development Team
===============================================================================
"""

import json
import boto3
import os
import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List

# AWS Clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Environment variables
DATA_TABLE = os.environ.get('DYNAMODB_TABLE', 'AnimalRescueData')
BUCKET_NAME = os.environ.get('S3_BUCKET', 'animal-rescue-data')

# CSV field definitions
CSV_FIELDS = [
    'shelter_id',
    'name',
    'org_type',
    'state',
    'city',
    'address',
    'zip_code',
    'phone',
    'email',
    'website',
    'description',
    'notes',
    'verified',
    'source',
    'collected_at',
    'last_updated'
]


def get_all_shelters() -> List[Dict]:
    """
    Retrieve all shelter records from DynamoDB
    """
    table = dynamodb.Table(DATA_TABLE)
    shelters = []

    try:
        response = table.scan()
        shelters.extend(response.get('Items', []))

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            shelters.extend(response.get('Items', []))

    except Exception as e:
        print(f"DynamoDB scan error: {e}")

    return shelters


def get_shelters_by_state(state: str) -> List[Dict]:
    """
    Retrieve shelter records for a specific state
    """
    table = dynamodb.Table(DATA_TABLE)
    shelters = []

    try:
        response = table.query(
            IndexName='state-index',
            KeyConditionExpression='#state = :state',
            ExpressionAttributeNames={'#state': 'state'},
            ExpressionAttributeValues={':state': state}
        )
        shelters.extend(response.get('Items', []))

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.query(
                IndexName='state-index',
                KeyConditionExpression='#state = :state',
                ExpressionAttributeNames={'#state': 'state'},
                ExpressionAttributeValues={':state': state},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            shelters.extend(response.get('Items', []))

    except Exception as e:
        print(f"DynamoDB query error: {e}")

    return shelters


def shelters_to_csv(shelters: List[Dict]) -> str:
    """
    Convert shelter list to CSV string
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction='ignore')
    writer.writeheader()

    for shelter in shelters:
        # Ensure all fields exist
        row = {field: shelter.get(field, '') for field in CSV_FIELDS}
        # Convert boolean to string
        if 'verified' in row:
            row['verified'] = 'Yes' if row['verified'] else 'No'
        writer.writerow(row)

    return output.getvalue()


def export_master_csv() -> Dict[str, Any]:
    """
    Export all shelters to master CSV files
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')

    # Get all shelters
    shelters = get_all_shelters()

    if not shelters:
        return {
            'status': 'error',
            'message': 'No shelters found in database'
        }

    # Sort by state then name
    shelters.sort(key=lambda x: (x.get('state', ''), x.get('name', '')))

    # Generate CSV
    csv_content = shelters_to_csv(shelters)

    # Upload dated version
    dated_key = f"exports/master/animal_rescues_all_states_{timestamp}.csv"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=dated_key,
        Body=csv_content,
        ContentType='text/csv'
    )

    # Upload latest version (always updated)
    latest_key = "exports/master/animal_rescues_all_states_LATEST.csv"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=latest_key,
        Body=csv_content,
        ContentType='text/csv'
    )

    # Generate summary statistics
    states_covered = len(set(s.get('state', '') for s in shelters))
    by_type = {}
    for s in shelters:
        org_type = s.get('org_type', 'unknown')
        by_type[org_type] = by_type.get(org_type, 0) + 1

    return {
        'status': 'success',
        'total_shelters': len(shelters),
        'states_covered': states_covered,
        'by_type': by_type,
        'dated_file': f"s3://{BUCKET_NAME}/{dated_key}",
        'latest_file': f"s3://{BUCKET_NAME}/{latest_key}"
    }


def export_state_csv(state: str) -> Dict[str, Any]:
    """
    Export shelters for a single state
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

    shelters = get_shelters_by_state(state)

    if not shelters:
        return {
            'status': 'warning',
            'message': f'No shelters found for state: {state}'
        }

    # Sort by name
    shelters.sort(key=lambda x: x.get('name', ''))

    # Generate CSV
    csv_content = shelters_to_csv(shelters)

    # Upload dated version
    dated_key = f"exports/states/{state}/animal_rescues_{state}_{timestamp}.csv"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=dated_key,
        Body=csv_content,
        ContentType='text/csv'
    )

    # Upload latest version
    latest_key = f"exports/states/{state}/animal_rescues_{state}_LATEST.csv"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=latest_key,
        Body=csv_content,
        ContentType='text/csv'
    )

    return {
        'status': 'success',
        'state': state,
        'total_shelters': len(shelters),
        'dated_file': f"s3://{BUCKET_NAME}/{dated_key}",
        'latest_file': f"s3://{BUCKET_NAME}/{latest_key}"
    }


def export_all_states_individually() -> Dict[str, Any]:
    """
    Export separate CSV files for each state
    """
    from orchestrator import STATES_BY_PRIORITY

    results = []
    success_count = 0
    error_count = 0

    for state, state_full in STATES_BY_PRIORITY:
        result = export_state_csv(state)
        results.append({
            'state': state,
            'state_full': state_full,
            'result': result
        })

        if result.get('status') == 'success':
            success_count += 1
        else:
            error_count += 1

    return {
        'status': 'success',
        'states_exported': success_count,
        'states_failed': error_count,
        'details': results
    }


def generate_daily_report() -> Dict[str, Any]:
    """
    Generate daily summary report
    """
    shelters = get_all_shelters()

    # Calculate statistics
    by_state = {}
    by_type = {}
    verified_count = 0
    with_email = 0
    with_phone = 0
    with_website = 0

    for shelter in shelters:
        state = shelter.get('state', 'Unknown')
        by_state[state] = by_state.get(state, 0) + 1

        org_type = shelter.get('org_type', 'unknown')
        by_type[org_type] = by_type.get(org_type, 0) + 1

        if shelter.get('verified'):
            verified_count += 1
        if shelter.get('email'):
            with_email += 1
        if shelter.get('phone'):
            with_phone += 1
        if shelter.get('website'):
            with_website += 1

    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_organizations': len(shelters),
        'states_covered': len(by_state),
        'verified_organizations': verified_count,
        'contact_coverage': {
            'with_email': with_email,
            'with_phone': with_phone,
            'with_website': with_website,
            'email_percentage': round(with_email / len(shelters) * 100, 1) if shelters else 0,
            'phone_percentage': round(with_phone / len(shelters) * 100, 1) if shelters else 0,
            'website_percentage': round(with_website / len(shelters) * 100, 1) if shelters else 0
        },
        'by_state': dict(sorted(by_state.items())),
        'by_type': dict(sorted(by_type.items(), key=lambda x: -x[1]))
    }

    # Save report to S3
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d')
    report_key = f"reports/daily/report_{timestamp}.json"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=report_key,
        Body=json.dumps(report, indent=2),
        ContentType='application/json'
    )

    # Also save as latest
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key="reports/daily/report_LATEST.json",
        Body=json.dumps(report, indent=2),
        ContentType='application/json'
    )

    return {
        'status': 'success',
        'report': report,
        'report_location': f"s3://{BUCKET_NAME}/{report_key}"
    }


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    CSV Exporter Lambda Handler

    Modes:
    - "master" - Export all shelters to master CSV
    - "state" - Export single state (requires state parameter)
    - "all_states" - Export each state to individual CSV
    - "report" - Generate daily statistics report
    - "full_export" - Run master + all_states + report

    Event format:
    {
        "mode": "master",
        "state": "TX"  // Optional, for state mode
    }
    """
    mode = event.get('mode', 'master')
    state = event.get('state', '').upper()

    if mode == 'master':
        return export_master_csv()

    elif mode == 'state':
        if not state:
            return {
                'status': 'error',
                'message': 'State parameter required for state export'
            }
        return export_state_csv(state)

    elif mode == 'all_states':
        return export_all_states_individually()

    elif mode == 'report':
        return generate_daily_report()

    elif mode == 'full_export':
        # Run complete export process
        master_result = export_master_csv()
        states_result = export_all_states_individually()
        report_result = generate_daily_report()

        return {
            'status': 'success',
            'master_export': master_result,
            'states_export': states_result,
            'report': report_result
        }

    else:
        return {
            'status': 'error',
            'message': f'Unknown mode: {mode}'
        }


# For local testing
if __name__ == "__main__":
    result = lambda_handler({'mode': 'report'}, None)
    print(json.dumps(result, indent=2))
