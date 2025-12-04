"""
===============================================================================
Animal Rescue Admin Dashboard - API Lambda
===============================================================================
Purpose: Backend API for the admin dashboard with Google OAuth authentication.
         Provides search, view, edit notes, and management capabilities.

Uses: API Gateway, DynamoDB, Cognito (Google OAuth), Lambda
Auth: Google OAuth via Amazon Cognito User Pool

Author: Waiting The Longest Development Team
===============================================================================
"""

import json
import boto3
import os
import re
import base64
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs
import hashlib

# AWS Clients
dynamodb = boto3.resource('dynamodb')
cognito = boto3.client('cognito-idp')

# Environment variables
DATA_TABLE = os.environ.get('DYNAMODB_TABLE', 'AnimalRescueData')
PROGRESS_TABLE = os.environ.get('PROGRESS_TABLE', 'AnimalRescueData_Progress')
USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', '')
ALLOWED_EMAILS = os.environ.get('ALLOWED_ADMIN_EMAILS', '').split(',')

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': os.environ.get('CORS_ORIGIN', '*'),
    'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    'Content-Type': 'application/json'
}


def response(status_code: int, body: Any) -> Dict:
    """Create API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(body, default=str)
    }


def verify_token(event: Dict) -> Optional[Dict]:
    """
    Verify JWT token from Authorization header
    Returns user info if valid, None if invalid
    """
    auth_header = event.get('headers', {}).get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header.replace('Bearer ', '')

    try:
        # Verify token with Cognito
        user_info = cognito.get_user(AccessToken=token)

        # Extract email from user attributes
        email = None
        for attr in user_info.get('UserAttributes', []):
            if attr['Name'] == 'email':
                email = attr['Value']
                break

        if not email:
            return None

        # Check if email is in allowed list (if configured)
        if ALLOWED_EMAILS and ALLOWED_EMAILS[0]:
            if email not in ALLOWED_EMAILS:
                return None

        return {
            'username': user_info.get('Username'),
            'email': email
        }

    except Exception as e:
        print(f"Token verification error: {e}")
        return None


def search_shelters(query: str, state: Optional[str] = None,
                   org_type: Optional[str] = None,
                   limit: int = 50, offset: int = 0) -> Dict:
    """
    Search shelters with optional filters
    """
    table = dynamodb.Table(DATA_TABLE)
    shelters = []

    try:
        # Build filter expression
        filter_parts = []
        expression_values = {}
        expression_names = {}

        if query:
            # Search in name, city, and description
            filter_parts.append(
                '(contains(#name, :query) OR contains(#city, :query) OR contains(#desc, :query))'
            )
            expression_values[':query'] = query.lower()
            expression_names['#name'] = 'name_lower'
            expression_names['#city'] = 'city_lower'
            expression_names['#desc'] = 'description_lower'

        if state:
            filter_parts.append('#state = :state')
            expression_values[':state'] = state.upper()
            expression_names['#state'] = 'state'

        if org_type:
            filter_parts.append('#org_type = :org_type')
            expression_values[':org_type'] = org_type
            expression_names['#org_type'] = 'org_type'

        # Scan with filters
        scan_kwargs = {}
        if filter_parts:
            scan_kwargs['FilterExpression'] = ' AND '.join(filter_parts)
            scan_kwargs['ExpressionAttributeValues'] = expression_values
            scan_kwargs['ExpressionAttributeNames'] = expression_names

        response_db = table.scan(**scan_kwargs)
        shelters.extend(response_db.get('Items', []))

        # Handle pagination
        while 'LastEvaluatedKey' in response_db:
            scan_kwargs['ExclusiveStartKey'] = response_db['LastEvaluatedKey']
            response_db = table.scan(**scan_kwargs)
            shelters.extend(response_db.get('Items', []))

        # Sort by name
        shelters.sort(key=lambda x: x.get('name', '').lower())

        # Apply pagination
        total = len(shelters)
        shelters = shelters[offset:offset + limit]

        return {
            'shelters': shelters,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total
        }

    except Exception as e:
        print(f"Search error: {e}")
        return {'error': str(e), 'shelters': [], 'total': 0}


def get_shelter(shelter_id: str) -> Optional[Dict]:
    """
    Get a single shelter by ID
    """
    table = dynamodb.Table(DATA_TABLE)

    try:
        response_db = table.get_item(Key={'shelter_id': shelter_id})
        return response_db.get('Item')
    except Exception as e:
        print(f"Get shelter error: {e}")
        return None


def update_shelter_notes(shelter_id: str, notes: str, user_email: str) -> Dict:
    """
    Update notes for a shelter
    """
    table = dynamodb.Table(DATA_TABLE)
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        table.update_item(
            Key={'shelter_id': shelter_id},
            UpdateExpression='SET notes = :notes, notes_updated_at = :ts, notes_updated_by = :user',
            ExpressionAttributeValues={
                ':notes': notes,
                ':ts': timestamp,
                ':user': user_email
            }
        )
        return {'status': 'success', 'shelter_id': shelter_id}
    except Exception as e:
        print(f"Update notes error: {e}")
        return {'status': 'error', 'error': str(e)}


def update_shelter_verified(shelter_id: str, verified: bool, user_email: str) -> Dict:
    """
    Update verified status for a shelter
    """
    table = dynamodb.Table(DATA_TABLE)
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        table.update_item(
            Key={'shelter_id': shelter_id},
            UpdateExpression='SET verified = :verified, verified_at = :ts, verified_by = :user',
            ExpressionAttributeValues={
                ':verified': verified,
                ':ts': timestamp,
                ':user': user_email
            }
        )
        return {'status': 'success', 'shelter_id': shelter_id}
    except Exception as e:
        print(f"Update verified error: {e}")
        return {'status': 'error', 'error': str(e)}


def update_shelter(shelter_id: str, updates: Dict, user_email: str) -> Dict:
    """
    Update shelter details
    """
    table = dynamodb.Table(DATA_TABLE)
    timestamp = datetime.now(timezone.utc).isoformat()

    # Allowed fields to update
    allowed_fields = ['name', 'org_type', 'phone', 'email', 'website',
                      'address', 'city', 'zip_code', 'description', 'notes', 'verified']

    try:
        update_parts = ['last_updated = :ts', 'updated_by = :user']
        expression_values = {':ts': timestamp, ':user': user_email}
        expression_names = {}

        for field, value in updates.items():
            if field in allowed_fields:
                placeholder = f":{field}"
                update_parts.append(f"#{field} = {placeholder}")
                expression_values[placeholder] = value
                expression_names[f"#{field}"] = field

        if len(update_parts) > 2:  # More than just timestamp and user
            table.update_item(
                Key={'shelter_id': shelter_id},
                UpdateExpression='SET ' + ', '.join(update_parts),
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names
            )

        return {'status': 'success', 'shelter_id': shelter_id}
    except Exception as e:
        print(f"Update shelter error: {e}")
        return {'status': 'error', 'error': str(e)}


def get_collection_stats() -> Dict:
    """
    Get collection statistics for dashboard
    """
    data_table = dynamodb.Table(DATA_TABLE)
    progress_table = dynamodb.Table(PROGRESS_TABLE)

    stats = {
        'total_shelters': 0,
        'states_completed': 0,
        'states_pending': 0,
        'verified_count': 0,
        'by_state': {},
        'by_type': {},
        'recent_collections': []
    }

    try:
        # Get shelter counts
        response_db = data_table.scan(
            Select='COUNT'
        )
        stats['total_shelters'] = response_db.get('Count', 0)

        # Get full data for statistics
        all_shelters = []
        response_db = data_table.scan()
        all_shelters.extend(response_db.get('Items', []))

        while 'LastEvaluatedKey' in response_db:
            response_db = data_table.scan(ExclusiveStartKey=response_db['LastEvaluatedKey'])
            all_shelters.extend(response_db.get('Items', []))

        # Calculate stats
        for shelter in all_shelters:
            state = shelter.get('state', 'Unknown')
            stats['by_state'][state] = stats['by_state'].get(state, 0) + 1

            org_type = shelter.get('org_type', 'unknown')
            stats['by_type'][org_type] = stats['by_type'].get(org_type, 0) + 1

            if shelter.get('verified'):
                stats['verified_count'] += 1

        # Get progress data
        progress_response = progress_table.scan()
        progress_items = progress_response.get('Items', [])

        stats['states_completed'] = sum(
            1 for p in progress_items if p.get('status') == 'completed'
        )
        stats['states_pending'] = sum(
            1 for p in progress_items if p.get('status') == 'pending'
        )

        # Recent collections
        completed = [p for p in progress_items if p.get('last_collection')]
        completed.sort(key=lambda x: x.get('last_collection', ''), reverse=True)
        stats['recent_collections'] = [
            {
                'state': p['state'],
                'state_full': p.get('state_full', ''),
                'shelter_count': p.get('shelter_count', 0),
                'last_collection': p.get('last_collection')
            }
            for p in completed[:10]
        ]

    except Exception as e:
        print(f"Stats error: {e}")

    return stats


def get_all_states() -> List[Dict]:
    """
    Get all states with their collection status
    """
    table = dynamodb.Table(PROGRESS_TABLE)

    try:
        response_db = table.scan()
        items = response_db.get('Items', [])

        while 'LastEvaluatedKey' in response_db:
            response_db = table.scan(ExclusiveStartKey=response_db['LastEvaluatedKey'])
            items.extend(response_db.get('Items', []))

        # Sort by state name
        items.sort(key=lambda x: x.get('state_full', x.get('state', '')))

        return items
    except Exception as e:
        print(f"Get states error: {e}")
        return []


def lambda_handler(event: Dict[str, Any], context) -> Dict:
    """
    Admin API Lambda Handler

    Routes:
    - GET /admin/shelters - Search shelters
    - GET /admin/shelters/{id} - Get single shelter
    - PUT /admin/shelters/{id} - Update shelter
    - PUT /admin/shelters/{id}/notes - Update shelter notes
    - PUT /admin/shelters/{id}/verify - Toggle verified status
    - GET /admin/stats - Get dashboard statistics
    - GET /admin/states - Get all states with status
    - OPTIONS /* - CORS preflight
    """
    # Handle CORS preflight
    http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', ''))
    if http_method == 'OPTIONS':
        return response(200, {'message': 'OK'})

    # Verify authentication
    user = verify_token(event)
    if not user:
        return response(401, {'error': 'Unauthorized'})

    # Parse path and method
    path = event.get('path', event.get('rawPath', ''))
    path_params = event.get('pathParameters', {}) or {}

    try:
        # Route: GET /admin/stats
        if path == '/admin/stats' and http_method == 'GET':
            stats = get_collection_stats()
            return response(200, stats)

        # Route: GET /admin/states
        elif path == '/admin/states' and http_method == 'GET':
            states = get_all_states()
            return response(200, {'states': states})

        # Route: GET /admin/shelters (search)
        elif path == '/admin/shelters' and http_method == 'GET':
            query_params = event.get('queryStringParameters', {}) or {}
            result = search_shelters(
                query=query_params.get('q', ''),
                state=query_params.get('state'),
                org_type=query_params.get('type'),
                limit=int(query_params.get('limit', 50)),
                offset=int(query_params.get('offset', 0))
            )
            return response(200, result)

        # Route: GET /admin/shelters/{id}
        elif path.startswith('/admin/shelters/') and http_method == 'GET':
            shelter_id = path_params.get('id') or path.split('/')[-1]
            shelter = get_shelter(shelter_id)
            if shelter:
                return response(200, shelter)
            return response(404, {'error': 'Shelter not found'})

        # Route: PUT /admin/shelters/{id}
        elif path.startswith('/admin/shelters/') and http_method == 'PUT':
            shelter_id = path_params.get('id') or path.split('/')[-1].split('/')[0]

            # Check for sub-routes
            if '/notes' in path:
                body = json.loads(event.get('body', '{}'))
                result = update_shelter_notes(
                    shelter_id,
                    body.get('notes', ''),
                    user['email']
                )
                return response(200, result)

            elif '/verify' in path:
                body = json.loads(event.get('body', '{}'))
                result = update_shelter_verified(
                    shelter_id,
                    body.get('verified', False),
                    user['email']
                )
                return response(200, result)

            else:
                body = json.loads(event.get('body', '{}'))
                result = update_shelter(shelter_id, body, user['email'])
                return response(200, result)

        # Route not found
        return response(404, {'error': f'Route not found: {http_method} {path}'})

    except json.JSONDecodeError:
        return response(400, {'error': 'Invalid JSON body'})
    except Exception as e:
        print(f"Handler error: {e}")
        return response(500, {'error': str(e)})


# For local testing
if __name__ == "__main__":
    # Test search
    test_event = {
        'httpMethod': 'GET',
        'path': '/admin/stats',
        'headers': {'Authorization': 'Bearer test-token'}
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
