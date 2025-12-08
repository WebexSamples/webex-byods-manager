#!/usr/bin/env python3
"""
AWS Lambda Function for Webex BYODS Token Extension

This Lambda function automatically extends Webex BYODS (Bring Your Own Data Source)
tokens on a scheduled basis to prevent expiration.

Environment Variables:
    DATA_SOURCE_ID: The ID of the data source to extend
    SECRET_NAME: Name of the AWS Secrets Manager secret containing credentials
    TOKEN_LIFETIME_MINUTES: Token lifetime in minutes (optional, defaults to 1440)

Returns:
    dict: Lambda response with statusCode, body, and execution details
"""

import json
import os
import logging
from datetime import datetime
from token_manager import TokenManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    AWS Lambda handler function for extending BYODS tokens.
    
    Args:
        event: Lambda event object (not used, supports EventBridge scheduled events)
        context: Lambda context object
        
    Returns:
        dict: Response with statusCode and body containing operation result
    """
    logger.info("Starting BYODS token extension Lambda function")
    logger.info(f"Event: {json.dumps(event)}")
    
    # Get configuration from environment variables
    data_source_id = os.environ.get('DATA_SOURCE_ID')
    secret_name = os.environ.get('SECRET_NAME', 'webex-byods-credentials')
    token_lifetime_minutes = int(os.environ.get('TOKEN_LIFETIME_MINUTES', '1440'))
    
    # Validate required environment variables
    if not data_source_id:
        error_msg = "DATA_SOURCE_ID environment variable is required"
        logger.error(error_msg)
        return {
            'statusCode': 400,
            'body': json.dumps({
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })
        }
    
    logger.info(f"Data Source ID: {data_source_id}")
    logger.info(f"Secret Name: {secret_name}")
    logger.info(f"Token Lifetime: {token_lifetime_minutes} minutes")
    
    try:
        # Initialize TokenManager with AWS Secrets Manager support
        logger.info("Initializing TokenManager")
        token_manager = TokenManager(
            config_path='token-config.json',  # Fallback for local testing
            secret_name=secret_name
        )
        
        # Extend the data source token
        logger.info(f"Extending token for data source: {data_source_id}")
        result = token_manager.extend_data_source_token(
            data_source_id, 
            token_lifetime_minutes
        )
        
        if result['success']:
            logger.info("Data source token extended successfully")
            logger.info(f"New nonce: {result.get('nonce_updated')}")
            logger.info(f"Token expiry: {result.get('token_expiry')}")
            logger.info(f"Token lifetime: {result.get('token_lifetime_minutes')} minutes")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': 'Data source token extended successfully',
                    'data_source_id': data_source_id,
                    'nonce_updated': result.get('nonce_updated'),
                    'token_expiry': result.get('token_expiry'),
                    'token_lifetime_minutes': result.get('token_lifetime_minutes'),
                    'timestamp': datetime.now().isoformat()
                })
            }
        else:
            error_msg = result.get('error', 'Unknown error')
            status_code = result.get('status_code', 500)
            logger.error(f"Failed to extend data source token: {error_msg}")
            
            return {
                'statusCode': status_code,
                'body': json.dumps({
                    'success': False,
                    'error': error_msg,
                    'data_source_id': data_source_id,
                    'timestamp': datetime.now().isoformat()
                })
            }
            
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })
        }


# For local testing
if __name__ == "__main__":
    # Mock Lambda event and context for local testing
    class Context:
        def __init__(self):
            self.function_name = "webex-byods-token-extender"
            self.memory_limit_in_mb = 256
            self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:webex-byods-token-extender"
            self.aws_request_id = "local-test-request-id"
    
    # Set environment variables for local testing
    if not os.environ.get('DATA_SOURCE_ID'):
        print("Please set DATA_SOURCE_ID environment variable for local testing")
        print("Example: export DATA_SOURCE_ID=85895e47-3096-4c47-aae8-f5a52f7b7870")
        exit(1)
    
    test_event = {
        "source": "aws.events",
        "detail-type": "Scheduled Event",
        "time": datetime.now().isoformat()
    }
    
    test_context = Context()
    
    print("Running local test...")
    print("-" * 60)
    response = lambda_handler(test_event, test_context)
    print("-" * 60)
    print("Response:")
    print(json.dumps(response, indent=2))

