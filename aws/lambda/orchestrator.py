"""
===============================================================================
Animal Rescue Search Agent - Orchestrator Lambda
===============================================================================
Purpose: Orchestrates the state-by-state collection process.
         Manages initial full collection and daily update cycles.
         Tracks progress and triggers individual state collectors.

Uses: AWS Step Functions, DynamoDB, EventBridge, SNS
Schedule: Daily at 2 AM EST via EventBridge

Author: Waiting The Longest Development Team
===============================================================================
"""

import json
import boto3
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

# AWS Clients
dynamodb = boto3.resource('dynamodb')
stepfunctions = boto3.client('stepfunctions')
sns = boto3.client('sns')

# Environment variables
PROGRESS_TABLE = os.environ.get('PROGRESS_TABLE', 'AnimalRescueData_Progress')
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN', '')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')

# All 50 US states in collection order (largest population first for initial run)
STATES_BY_PRIORITY = [
    ("CA", "California"), ("TX", "Texas"), ("FL", "Florida"), ("NY", "New York"),
    ("PA", "Pennsylvania"), ("IL", "Illinois"), ("OH", "Ohio"), ("GA", "Georgia"),
    ("NC", "North Carolina"), ("MI", "Michigan"), ("NJ", "New Jersey"),
    ("VA", "Virginia"), ("WA", "Washington"), ("AZ", "Arizona"), ("MA", "Massachusetts"),
    ("TN", "Tennessee"), ("IN", "Indiana"), ("MD", "Maryland"), ("MO", "Missouri"),
    ("WI", "Wisconsin"), ("CO", "Colorado"), ("MN", "Minnesota"), ("SC", "South Carolina"),
    ("AL", "Alabama"), ("LA", "Louisiana"), ("KY", "Kentucky"), ("OR", "Oregon"),
    ("OK", "Oklahoma"), ("CT", "Connecticut"), ("UT", "Utah"), ("IA", "Iowa"),
    ("NV", "Nevada"), ("AR", "Arkansas"), ("MS", "Mississippi"), ("KS", "Kansas"),
    ("NM", "New Mexico"), ("NE", "Nebraska"), ("ID", "Idaho"), ("WV", "West Virginia"),
    ("HI", "Hawaii"), ("NH", "New Hampshire"), ("ME", "Maine"), ("MT", "Montana"),
    ("RI", "Rhode Island"), ("DE", "Delaware"), ("SD", "South Dakota"),
    ("ND", "North Dakota"), ("AK", "Alaska"), ("VT", "Vermont"), ("WY", "Wyoming")
]


def initialize_progress_table():
    """
    Initialize the progress tracking table with all 50 states
    """
    table = dynamodb.Table(PROGRESS_TABLE)
    timestamp = datetime.now(timezone.utc).isoformat()

    for state, state_full in STATES_BY_PRIORITY:
        try:
            # Check if state already exists
            response = table.get_item(Key={'state': state})
            if 'Item' not in response:
                table.put_item(Item={
                    'state': state,
                    'state_full': state_full,
                    'status': 'pending',
                    'shelter_count': 0,
                    'last_collection': None,
                    'created_at': timestamp,
                    'collection_attempts': 0,
                    'priority': STATES_BY_PRIORITY.index((state, state_full))
                })
        except Exception as e:
            print(f"Error initializing {state}: {e}")


def get_collection_status() -> Dict[str, Any]:
    """
    Get current collection status for all states
    """
    table = dynamodb.Table(PROGRESS_TABLE)

    try:
        response = table.scan()
        items = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))

        completed = [i for i in items if i.get('status') == 'completed']
        pending = [i for i in items if i.get('status') == 'pending']
        in_progress = [i for i in items if i.get('status') == 'in_progress']
        errors = [i for i in items if i.get('status') == 'error']

        total_shelters = sum(i.get('shelter_count', 0) for i in items)

        return {
            'total_states': len(items),
            'completed_count': len(completed),
            'pending_count': len(pending),
            'in_progress_count': len(in_progress),
            'error_count': len(errors),
            'total_shelters': total_shelters,
            'completed_states': [i['state'] for i in completed],
            'pending_states': [i['state'] for i in pending],
            'error_states': [i['state'] for i in errors],
            'is_initial_run_complete': len(completed) >= 50
        }
    except Exception as e:
        print(f"Error getting status: {e}")
        return {'error': str(e)}


def get_next_state_to_process() -> Optional[Dict[str, str]]:
    """
    Get the next state that needs to be processed
    Prioritizes: pending states first, then oldest completed states for refresh
    """
    table = dynamodb.Table(PROGRESS_TABLE)

    try:
        response = table.scan()
        items = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))

        # First, find pending states (for initial collection)
        pending = [i for i in items if i.get('status') == 'pending']
        if pending:
            # Sort by priority
            pending.sort(key=lambda x: x.get('priority', 999))
            state = pending[0]
            return {
                'state': state['state'],
                'state_full': state.get('state_full', ''),
                'is_initial': True
            }

        # If all states are done, find the oldest one for daily refresh
        completed = [i for i in items if i.get('status') == 'completed']
        if completed:
            # Sort by last_collection date (oldest first)
            completed.sort(key=lambda x: x.get('last_collection', ''))

            # Only refresh if it's been more than 23 hours since last collection
            oldest = completed[0]
            last_collection = oldest.get('last_collection')
            if last_collection:
                last_dt = datetime.fromisoformat(last_collection.replace('Z', '+00:00'))
                hours_since = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                if hours_since >= 23:
                    return {
                        'state': oldest['state'],
                        'state_full': oldest.get('state_full', ''),
                        'is_initial': False
                    }

        return None

    except Exception as e:
        print(f"Error finding next state: {e}")
        return None


def mark_state_in_progress(state: str):
    """
    Mark a state as currently being processed
    """
    table = dynamodb.Table(PROGRESS_TABLE)
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        table.update_item(
            Key={'state': state},
            UpdateExpression='SET #status = :status, started_at = :ts, collection_attempts = collection_attempts + :one',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'in_progress',
                ':ts': timestamp,
                ':one': 1
            }
        )
    except Exception as e:
        print(f"Error marking in progress: {e}")


def get_daily_run_states() -> List[Dict[str, str]]:
    """
    Get all states for daily run (one complete cycle through all 50 states)
    Returns list of states in priority order
    """
    return [{'state': s[0], 'state_full': s[1]} for s in STATES_BY_PRIORITY]


def send_completion_notification(status: Dict[str, Any]):
    """
    Send SNS notification when collection cycle completes
    """
    if not SNS_TOPIC_ARN:
        return

    try:
        message = f"""
Animal Rescue Collection Status Report
======================================
Timestamp: {datetime.now(timezone.utc).isoformat()}

Collection Status:
- Total States: {status.get('total_states', 0)}
- Completed: {status.get('completed_count', 0)}
- Pending: {status.get('pending_count', 0)}
- Errors: {status.get('error_count', 0)}
- Total Shelters Collected: {status.get('total_shelters', 0)}

Initial Run Complete: {status.get('is_initial_run_complete', False)}

{f"Error States: {', '.join(status.get('error_states', []))}" if status.get('error_states') else ''}
"""

        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject='Animal Rescue Collection Report',
            Message=message
        )
    except Exception as e:
        print(f"SNS error: {e}")


def start_state_machine_execution(state: str, state_full: str) -> str:
    """
    Start Step Functions execution for a single state
    """
    if not STATE_MACHINE_ARN:
        print("No state machine ARN configured")
        return ""

    try:
        execution_name = f"{state}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        response = stepfunctions.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=execution_name,
            input=json.dumps({
                'state': state,
                'state_full': state_full
            })
        )

        return response['executionArn']
    except Exception as e:
        print(f"Error starting execution: {e}")
        return ""


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main orchestrator handler

    Modes:
    1. "initialize" - Set up progress tracking for all 50 states
    2. "status" - Return current collection status
    3. "next_state" - Get and process the next state
    4. "daily_run" - Start full daily collection cycle
    5. "process_state" - Process a specific state

    Event format:
    {
        "mode": "next_state",
        "state": "TX"  // Optional, for process_state mode
    }
    """
    mode = event.get('mode', 'status')

    if mode == 'initialize':
        initialize_progress_table()
        return {
            'status': 'success',
            'message': 'Progress table initialized for all 50 states'
        }

    elif mode == 'status':
        status = get_collection_status()
        return {
            'status': 'success',
            'collection_status': status
        }

    elif mode == 'next_state':
        next_state = get_next_state_to_process()

        if not next_state:
            return {
                'status': 'success',
                'message': 'All states are up to date',
                'next_state': None
            }

        # Mark as in progress
        mark_state_in_progress(next_state['state'])

        # Return state info for Step Functions to process
        return {
            'status': 'success',
            'next_state': next_state,
            'is_initial_run': next_state.get('is_initial', False)
        }

    elif mode == 'daily_run':
        # This is triggered by EventBridge at 2 AM EST
        status = get_collection_status()

        # Check if initial run is still in progress
        if not status.get('is_initial_run_complete', False):
            # Continue initial collection - get next pending state
            next_state = get_next_state_to_process()
            if next_state:
                mark_state_in_progress(next_state['state'])
                execution_arn = start_state_machine_execution(
                    next_state['state'],
                    next_state['state_full']
                )
                return {
                    'status': 'success',
                    'mode': 'initial_run_continue',
                    'next_state': next_state,
                    'execution_arn': execution_arn
                }

        # Start daily refresh cycle
        states = get_daily_run_states()

        return {
            'status': 'success',
            'mode': 'daily_run',
            'states_to_process': states,
            'total_count': len(states)
        }

    elif mode == 'process_state':
        state = event.get('state', '').upper()
        state_dict = dict(STATES_BY_PRIORITY)

        if state not in state_dict:
            return {
                'status': 'error',
                'message': f'Invalid state: {state}'
            }

        mark_state_in_progress(state)

        return {
            'status': 'success',
            'state': state,
            'state_full': state_dict[state]
        }

    elif mode == 'complete_notification':
        # Send completion notification
        status = get_collection_status()
        send_completion_notification(status)

        return {
            'status': 'success',
            'notification_sent': True,
            'collection_status': status
        }

    else:
        return {
            'status': 'error',
            'message': f'Unknown mode: {mode}'
        }


# For local testing
if __name__ == "__main__":
    # Test different modes
    print("Testing status mode:")
    result = lambda_handler({'mode': 'status'}, None)
    print(json.dumps(result, indent=2))
