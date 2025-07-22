#!/usr/bin/env python3
"""
Webex Data Source Management Script

This script provides a unified interface for managing Webex BYODS (Bring Your Own Data Source) system.
It can register new data sources, list existing ones, view details, and update configurations.

It requires a Service App access token with appropriate scopes:
- 'spark-admin:datasource_read' (for listing/viewing)
- 'spark-admin:datasource_write' (for registration and updates)

Usage:
    python data-sources.py
"""

import os
import sys
import json
import requests
import argparse
import uuid
import jwt
from typing import Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv


class WebexDataSourceManager:
    """Handle Webex Data Source operations via API"""
    
    BASE_URL = "https://webexapis.com/v1"
    
    def __init__(self, access_token: str):
        """Initialize with access token"""
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def list_all_data_sources(self) -> Dict[str, Any]:
        """Retrieve all data sources"""
        url = f"{self.BASE_URL}/dataSources"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "status_code": None
            }
    
    def get_data_source_details(self, data_source_id: str) -> Dict[str, Any]:
        """Retrieve details for a specific data source"""
        url = f"{self.BASE_URL}/dataSources/{data_source_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "status_code": None
            }
    
    def register_data_source(self, data_source_config: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new data source"""
        url = f"{self.BASE_URL}/dataSources"
        
        try:
            response = requests.post(
                url, 
                headers=self.headers, 
                json=data_source_config,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "status_code": None
            }
    
    def update_data_source(self, data_source_id: str, update_config: Dict[str, Any]) -> Dict[str, Any]:
        """Update a data source"""
        url = f"{self.BASE_URL}/dataSources/{data_source_id}"
        
        try:
            response = requests.put(
                url, 
                headers=self.headers,
                json=update_config,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "status_code": None
            }


def load_env_token() -> str:
    """Load the service app access token from .env file"""
    # Load .env file from the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, '.env')
    
    load_dotenv(env_path)
    
    token = os.getenv('WEBEX_ACCESS_TOKEN')
    if not token:
        print("Error: WEBEX_ACCESS_TOKEN not found in .env file")
        print(f"Please create a .env file in {script_dir} with:")
        print("WEBEX_ACCESS_TOKEN=your_service_app_token_here")
        sys.exit(1)
    
    return token


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode JWT token to extract audience and subject"""
    try:
        # Decode without verification since we just need to read the payload
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        print(f"Warning: Could not decode JWT token: {str(e)}")
        return {}


def enhance_data_source_with_jwt(data_source: Dict[str, Any]) -> Dict[str, Any]:
    """Enhance data source data by decoding JWT token if present"""
    enhanced = data_source.copy()
    
    # Check if there's a JWT token field
    jwt_token = data_source.get('jwtToken') or data_source.get('jwsToken')
    
    if jwt_token:
        jwt_claims = decode_jwt_token(jwt_token)
        
        # Extract audience and subject from JWT if not present in main data
        if not enhanced.get('audience') and jwt_claims.get('aud'):
            enhanced['audience'] = jwt_claims['aud']
        
        if not enhanced.get('subject') and jwt_claims.get('sub'):
            enhanced['subject'] = jwt_claims['sub']
        
        # Store JWT claims for reference
        enhanced['jwt_claims'] = jwt_claims
    
    return enhanced


def display_data_sources_list(data_sources: List[Dict[str, Any]]) -> None:
    """Display a formatted list of data sources"""
    if not data_sources:
        print("No data sources found.")
        return
    
    print(f"\nFound {len(data_sources)} data source(s):")
    print("=" * 70)
    print(f"{'#':<3} {'ID':<36} {'Status':<10} {'Audience':<15} {'URL':<15}")
    print("-" * 70)
    
    for i, ds in enumerate(data_sources, 1):
        # Enhance with JWT data
        enhanced_ds = enhance_data_source_with_jwt(ds)
        
        ds_id = enhanced_ds.get('id', 'N/A')[:36]
        status = enhanced_ds.get('status', 'N/A')
        audience = enhanced_ds.get('audience', 'N/A')[:15]
        url = enhanced_ds.get('url', 'N/A')[:15] + ('...' if len(enhanced_ds.get('url', '')) > 15 else '')
        print(f"{i:<3} {ds_id:<36} {status:<10} {audience:<15} {url:<15}")
    
    print("-" * 70)


def display_data_source_details(data_source: Dict[str, Any]) -> None:
    """Display detailed information about a data source"""
    # Enhance with JWT data
    enhanced_ds = enhance_data_source_with_jwt(data_source)
    
    print("\n" + "=" * 60)
    print("DATA SOURCE DETAILS")
    print("=" * 60)
    
    details = [
        ("ID", enhanced_ds.get('id', 'N/A')),
        ("Status", enhanced_ds.get('status', 'N/A')),
        ("Audience", enhanced_ds.get('audience', 'N/A')),
        ("Subject", enhanced_ds.get('subject', 'N/A')),
        ("Schema ID", enhanced_ds.get('schemaId', 'N/A')),
        ("URL", enhanced_ds.get('url', 'N/A')),
        ("Token Lifetime (min)", enhanced_ds.get('tokenLifetimeMinutes', 'N/A')),
        ("Token Expiry", enhanced_ds.get('tokenExpiryTime', 'N/A')),
        ("Nonce", enhanced_ds.get('nonce', 'N/A')),
        ("Created At", enhanced_ds.get('createdAt', 'N/A')),
        ("Updated At", enhanced_ds.get('updatedAt', 'N/A')),
    ]
    
    for label, value in details:
        if label == "Nonce" and value != 'N/A' and len(str(value)) > 16:
            # Mask nonce for security
            masked_value = f"{str(value)[:8]}...{str(value)[-8:]}"
            print(f"{label:<20}: {masked_value}")
        else:
            print(f"{label:<20}: {value}")
    
    # Show error message if present
    if 'errorMessage' in enhanced_ds and enhanced_ds['errorMessage']:
        print(f"{'Error Message':<20}: {enhanced_ds['errorMessage']}")
    
    # Show JWT token info if available
    if 'jwt_claims' in enhanced_ds and enhanced_ds['jwt_claims']:
        jwt_claims = enhanced_ds['jwt_claims']
        print(f"\n{'JWT Token Claims':<20}:")
        if jwt_claims.get('aud'):
            print(f"{'  Audience (aud)':<20}: {jwt_claims['aud']}")
        if jwt_claims.get('sub'):
            print(f"{'  Subject (sub)':<20}: {jwt_claims['sub']}")
        if jwt_claims.get('iss'):
            print(f"{'  Issuer (iss)':<20}: {jwt_claims['iss']}")
        if jwt_claims.get('exp'):
            exp_time = datetime.fromtimestamp(jwt_claims['exp'])
            print(f"{'  Expires (exp)':<20}: {exp_time.isoformat()}")
        if jwt_claims.get('iat'):
            iat_time = datetime.fromtimestamp(jwt_claims['iat'])
            print(f"{'  Issued (iat)':<20}: {iat_time.isoformat()}")


def get_registration_config() -> Dict[str, Any]:
    """Collect registration input from user via command line"""
    print("\n" + "=" * 50)
    print("REGISTER NEW DATA SOURCE")
    print("=" * 50)
    print("Press Enter to use default values shown in [brackets]")
    print()
    
    config = {}
    
    # Default values
    default_audience = "BYODS"
    default_nonce = str(uuid.uuid4())
    default_subject = "BYODS"
    default_schema_id = "5397013b-7920-4ffc-807c-e8a3e0a18f43"
    default_token_lifetime = 1440
    
    # Required fields with defaults
    audience_input = input(f"Audience (JWT token audience, usually DAPs app name) [{default_audience}]: ").strip()
    config['audience'] = audience_input if audience_input else default_audience
    
    nonce_input = input(f"Nonce (unique nonce for JWT encryption) [{default_nonce}]: ").strip()
    config['nonce'] = nonce_input if nonce_input else default_nonce
    
    schema_input = input(f"Schema ID (data exchange schema ID) [{default_schema_id}]: ").strip()
    config['schemaId'] = schema_input if schema_input else default_schema_id
    
    subject_input = input(f"Subject (JWT token subject, app function indication) [{default_subject}]: ").strip()
    config['subject'] = subject_input if subject_input else default_subject
    
    # URL is required and has no sensible default
    config['url'] = input("URL (endpoint where Webex will send data): ").strip()
    if not config['url']:
        print("Error: URL is required")
        return {}
    
    # Validate URL format
    if not config['url'].startswith(('http://', 'https://')):
        print("Error: URL must start with http:// or https://")
        return {}
    
    # Token lifetime with default
    lifetime_input = input(f"Token Lifetime Minutes (1-1440) [{default_token_lifetime}]: ").strip()
    if lifetime_input:
        try:
            config['tokenLifetimeMinutes'] = int(lifetime_input)
            if not (1 <= config['tokenLifetimeMinutes'] <= 1440):
                print("Error: Token lifetime must be between 1 and 1440 minutes")
                return {}
        except ValueError:
            print("Error: Please enter a valid number")
            return {}
    else:
        config['tokenLifetimeMinutes'] = default_token_lifetime
    
    return config


def get_update_config(current_data: Dict[str, Any]) -> Dict[str, Any]:
    """Get updated configuration from user input"""
    # Enhance with JWT data first
    enhanced_data = enhance_data_source_with_jwt(current_data)
    
    print("\n" + "=" * 50)
    print("UPDATE DATA SOURCE")
    print("=" * 50)
    print("Press Enter to keep current values shown in [brackets]")
    print("Note: A new nonce is required for security purposes")
    print()
    
    config = {}
    
    # Generate new nonce (required for security)
    default_nonce = str(uuid.uuid4())
    
    # Required fields with current values as defaults
    current_audience = enhanced_data.get('audience', '')
    audience_input = input(f"Audience [{current_audience}]: ").strip()
    config['audience'] = audience_input if audience_input else current_audience
    
    # New nonce is required
    nonce_input = input(f"New Nonce (required) [{default_nonce}]: ").strip()
    config['nonce'] = nonce_input if nonce_input else default_nonce
    
    current_schema = enhanced_data.get('schemaId', '')
    schema_input = input(f"Schema ID [{current_schema}]: ").strip()
    config['schemaId'] = schema_input if schema_input else current_schema
    
    current_subject = enhanced_data.get('subject', '')
    subject_input = input(f"Subject [{current_subject}]: ").strip()
    config['subject'] = subject_input if subject_input else current_subject
    
    current_url = enhanced_data.get('url', '')
    url_input = input(f"URL [{current_url}]: ").strip()
    config['url'] = url_input if url_input else current_url
    
    # Validate URL format if provided
    if config['url'] and not config['url'].startswith(('http://', 'https://')):
        print("Error: URL must start with http:// or https://")
        return {}
    
    # Token lifetime
    current_lifetime = enhanced_data.get('tokenLifetimeMinutes', 1440)
    lifetime_input = input(f"Token Lifetime Minutes (1-1440) [{current_lifetime}]: ").strip()
    if lifetime_input:
        try:
            config['tokenLifetimeMinutes'] = int(lifetime_input)
            if not (1 <= config['tokenLifetimeMinutes'] <= 1440):
                print("Error: Token lifetime must be between 1 and 1440 minutes")
                return {}
        except ValueError:
            print("Error: Please enter a valid number")
            return {}
    else:
        config['tokenLifetimeMinutes'] = current_lifetime
    
    # Status update (optional)
    current_status = enhanced_data.get('status', 'active')
    print(f"\nCurrent Status: {current_status}")
    if current_status == 'active':
        disable_input = input("Disable this data source? (y/N): ").strip().lower()
        if disable_input in ['y', 'yes']:
            config['status'] = 'disabled'
            error_msg = input("Error message for Control Hub (required when disabling): ").strip()
            if not error_msg:
                print("Error: Error message is required when disabling a data source")
                return {}
            config['errorMessage'] = error_msg
        else:
            config['status'] = 'active'
    else:
        enable_input = input("Enable this data source? (y/N): ").strip().lower()
        if enable_input in ['y', 'yes']:
            config['status'] = 'active'
            config['errorMessage'] = ""
        else:
            config['status'] = current_status
            if enhanced_data.get('errorMessage'):
                config['errorMessage'] = enhanced_data.get('errorMessage')
    
    return config


def display_main_menu(data_sources: List[Dict[str, Any]]) -> None:
    """Display the main menu options"""
    print("\n" + "=" * 60)
    print("WEBEX DATA SOURCE MANAGER")
    print("=" * 60)
    
    if data_sources:
        for i, ds in enumerate(data_sources, 1):
            enhanced_ds = enhance_data_source_with_jwt(ds)
            audience = enhanced_ds.get('audience', 'N/A')
            status = enhanced_ds.get('status', 'N/A')
            print(f"{i}. View/Update: {audience} ({status})")
        print()
    
    print(f"{len(data_sources) + 1}. Register New Data Source")
    print(f"{len(data_sources) + 2}. Refresh Data Sources List")
    print("q. Quit")


def get_main_menu_choice(data_sources: List[Dict[str, Any]]) -> str:
    """Get user's main menu choice"""
    max_option = len(data_sources) + 2
    while True:
        choice = input(f"\nEnter your choice (1-{max_option} or 'q'): ").strip().lower()
        
        if choice == 'q' or choice == 'quit':
            return 'quit'
        
        if choice == str(len(data_sources) + 1):
            return 'register'
        
        if choice == str(len(data_sources) + 2):
            return 'refresh'
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(data_sources):
                return str(choice_num - 1)  # Return 0-based index
        except ValueError:
            pass
        
        print(f"Please enter a number between 1 and {max_option}, or 'q' to quit")


def save_operation_record(operation_type: str, config: Dict[str, Any], result: Dict[str, Any]) -> str:
    """Save operation record to JSON file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create operation record
    operation_record = {
        "operation_timestamp": datetime.now().isoformat(),
        "operation_type": operation_type,
        "configuration": config,
        "api_response": result,
        "success": result['success']
    }
    
    # Generate filename based on operation and result
    if result['success'] and 'data' in result and 'id' in result['data']:
        ds_id = result['data']['id']
        filename = f"data_source_{operation_type}_{ds_id}_{timestamp}.json"
    else:
        filename = f"data_source_{operation_type}_failed_{timestamp}.json"
    
    filepath = os.path.join(script_dir, filename)
    
    try:
        with open(filepath, 'w') as f:
            json.dump(operation_record, f, indent=2)
        
        print(f"\n📄 Operation record saved to: {os.path.basename(filepath)}")
        return filepath
    except Exception as e:
        print(f"Warning: Could not save operation record to file: {str(e)}")
        return ""


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Webex Data Source Manager")
    parser.add_argument('--save-list', action='store_true', 
                       help='Save the data sources list to a JSON file on startup')
    
    args = parser.parse_args()
    
    try:
        # Load access token
        access_token = load_env_token()
        
        # Create manager instance
        manager = WebexDataSourceManager(access_token)
        
        print("Webex Data Source Manager")
        print("=" * 30)
        print("Loading data sources...")
        
        # Get all data sources initially
        result = manager.list_all_data_sources()
        
        if not result['success']:
            print("❌ Failed to retrieve data sources!")
            print(f"Status Code: {result.get('status_code', 'Unknown')}")
            print(f"Error: {result['error']}")
            sys.exit(1)
        
        data_sources = result['data'].get('items', [])
        
        # Save list if requested
        if args.save_list and data_sources:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data_sources_list_{timestamp}.json"
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
            
            data_record = {
                "retrieved_timestamp": datetime.now().isoformat(),
                "count": len(data_sources),
                "data_sources": data_sources
            }
            
            with open(filepath, 'w') as f:
                json.dump(data_record, f, indent=2)
            print(f"📄 Data sources list saved to: {filename}")
        
        # Main interactive loop
        while True:
            display_data_sources_list(data_sources)
            display_main_menu(data_sources)
            
            choice = get_main_menu_choice(data_sources)
            
            if choice == 'quit':
                print("Goodbye!")
                break
            elif choice == 'refresh':
                print("Refreshing data sources...")
                result = manager.list_all_data_sources()
                if result['success']:
                    data_sources = result['data'].get('items', [])
                    print("✅ Data sources refreshed!")
                else:
                    print("❌ Failed to refresh data sources!")
                    print(f"Error: {result['error']}")
                continue
            elif choice == 'register':
                # Register new data source
                config = get_registration_config()
                if config:
                    # Show configuration summary
                    print("\n" + "=" * 40)
                    print("REGISTRATION SUMMARY:")
                    print("=" * 40)
                    for key, value in config.items():
                        if key == 'nonce':
                            masked_value = f"{str(value)[:8]}...{str(value)[-8:]}" if len(str(value)) > 16 else str(value)
                            print(f"{key}: {masked_value}")
                        else:
                            print(f"{key}: {value}")
                    
                    confirm = input("\nProceed with registration? (y/N): ").strip().lower()
                    if confirm in ['y', 'yes']:
                        print("Registering data source...")
                        reg_result = manager.register_data_source(config)
                        
                        if reg_result['success']:
                            print("✅ Data Source Registration Successful!")
                            print(f"Data Source ID: {reg_result['data'].get('id', 'N/A')}")
                            save_operation_record('registration', config, reg_result)
                            
                            # Refresh the list
                            result = manager.list_all_data_sources()
                            if result['success']:
                                data_sources = result['data'].get('items', [])
                        else:
                            print("❌ Data Source Registration Failed!")
                            print(f"Status Code: {reg_result.get('status_code', 'Unknown')}")
                            print(f"Error: {reg_result['error']}")
                            save_operation_record('registration', config, reg_result)
                    else:
                        print("Registration cancelled.")
                continue
            else:
                # View/update existing data source
                try:
                    ds_index = int(choice)
                    selected_ds = data_sources[ds_index]
                    ds_id = selected_ds['id']
                    
                    print(f"Retrieving details for data source: {ds_id}")
                    details_result = manager.get_data_source_details(ds_id)
                    
                    if details_result['success']:
                        display_data_source_details(details_result['data'])
                        
                        # Ask if user wants to update
                        update_choice = input("\nUpdate this data source? (y/N): ").strip().lower()
                        if update_choice in ['y', 'yes']:
                            update_config = get_update_config(details_result['data'])
                            
                            if update_config:
                                # Show update summary
                                print("\n" + "=" * 40)
                                print("UPDATE SUMMARY:")
                                print("=" * 40)
                                for key, value in update_config.items():
                                    if key == 'nonce':
                                        masked_value = f"{str(value)[:8]}...{str(value)[-8:]}" if len(str(value)) > 16 else str(value)
                                        print(f"{key}: {masked_value}")
                                    else:
                                        print(f"{key}: {value}")
                                
                                confirm_update = input("\nProceed with update? (y/N): ").strip().lower()
                                if confirm_update in ['y', 'yes']:
                                    print(f"Updating data source: {ds_id}")
                                    update_result = manager.update_data_source(ds_id, update_config)
                                    
                                    if update_result['success']:
                                        print("✅ Data Source Update Successful!")
                                        display_data_source_details(update_result['data'])
                                        save_operation_record('update', update_config, update_result)
                                        
                                        # Refresh the list
                                        result = manager.list_all_data_sources()
                                        if result['success']:
                                            data_sources = result['data'].get('items', [])
                                    else:
                                        print("❌ Data Source Update Failed!")
                                        print(f"Status Code: {update_result.get('status_code', 'Unknown')}")
                                        print(f"Error: {update_result['error']}")
                                        save_operation_record('update', update_config, update_result)
                                else:
                                    print("Update cancelled.")
                            else:
                                print("Update cancelled due to invalid input.")
                    else:
                        print(f"❌ Failed to retrieve details for data source {ds_id}")
                        print(f"Status Code: {details_result.get('status_code', 'Unknown')}")
                        print(f"Error: {details_result['error']}")
                        
                except (ValueError, IndexError):
                    print("Invalid selection.")
                
                input("\nPress Enter to continue...")
                
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
