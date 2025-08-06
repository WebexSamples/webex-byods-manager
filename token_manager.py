import json
import requests
from typing import Dict, Optional


class TokenManager:
    """Manages Webex service app token refresh and updates."""
    
    def __init__(self, env_path: str = ".env", config_path: str = "token-config.json"):
        """
        Initialize TokenManager.
        
        Args:
            env_path: Path to the .env file
            config_path: Path to the token configuration file
        """
        self.env_path = env_path
        self.config_path = config_path
    
    def refresh_token(self) -> str:
        """
        Refresh the Webex service app token using the API.
        Tries to use stored refresh token first, falls back to full refresh if needed.
        
        Returns:
            str: The new access token
            
        Raises:
            Exception: If token refresh fails
        """
        # First try to use the refresh token if available
        current_refresh_token = self._get_current_refresh_token()
        if current_refresh_token:
            try:
                return self._refresh_with_refresh_token(current_refresh_token)
            except Exception as e:
                print(f"Refresh token failed, falling back to full refresh: {e}")
        
        # Fall back to full refresh using personal access token
        return self._refresh_with_personal_token()
    
    def _refresh_with_refresh_token(self, refresh_token: str) -> str:
        """
        Refresh the token using the stored refresh token.
        
        Args:
            refresh_token: The refresh token to use
            
        Returns:
            str: The new access token
        """
        try:
            config = self._load_config()
            service_app = config['serviceApp']
            
            url = "https://webexapis.com/v1/access_token"
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {
                'grant_type': 'refresh_token',
                'client_id': service_app['clientId'],
                'client_secret': service_app['clientSecret'],
                'refresh_token': refresh_token
            }
            
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code == 401:
                raise Exception("Refresh token expired or invalid")
            
            response.raise_for_status()
            
            token_data = response.json()
            new_access_token = token_data.get('access_token')
            new_refresh_token = token_data.get('refresh_token', refresh_token)  # Use new or keep old
            
            if not new_access_token:
                raise Exception("No access token in refresh response")
            
            # Update the .env file with the new tokens
            self._update_env_file(new_access_token, new_refresh_token)
            
            print("Token refreshed successfully using refresh token")
            return new_access_token
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Refresh token request failed: {e}")
    
    def _refresh_with_personal_token(self) -> str:
        """
        Refresh the token using the personal access token (full refresh).
        
        Returns:
            str: The new access token
        """
    def _refresh_with_personal_token(self) -> str:
        """
        Refresh the token using the personal access token (full refresh).
        
        Returns:
            str: The new access token
        """
        try:
            config = self._load_config()
            
            # Prepare the API request
            service_app = config['serviceApp']
            token_manager = config['tokenManager']
            
            url = f"https://webexapis.com/v1/applications/{service_app['appId']}/token"
            headers = {
                'Authorization': f"Bearer {token_manager['personalAccessToken']}",
                'Content-Type': 'application/json'
            }
            payload = {
                'clientId': service_app['clientId'],
                'clientSecret': service_app['clientSecret'],
                'targetOrgId': service_app['targetOrgId']
            }
            
            # Make the API call
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 401:
                raise Exception("Authentication failed. Your personal access token may have expired. "
                               "If using a portal token, get a new one from developer.webex.com. "
                               "If using an integration token, refresh your OAuth token.")
            
            response.raise_for_status()
            
            token_data = response.json()
            new_access_token = token_data.get('access_token')
            new_refresh_token = token_data.get('refresh_token')
            
            if not new_access_token:
                raise Exception("No access token in API response")
            
            # Update the .env file with the new tokens
            self._update_env_file(new_access_token, new_refresh_token)
            
            print("Token refreshed successfully using personal access token")
            return new_access_token
            
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            raise Exception(f"Token refresh failed: {e}")
        except Exception as e:
            print(f"Failed to refresh token: {e}")
            raise
    
    def _load_config(self) -> Dict[str, str]:
        """
        Load configuration from the token config file.
        
        Returns:
            Dict containing the configuration
            
        Raises:
            Exception: If config file is not found or invalid
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            # Validate structure
            if 'serviceApp' not in config:
                raise Exception("Missing 'serviceApp' section in config")
            if 'tokenManager' not in config:
                raise Exception("Missing 'tokenManager' section in config")
            
            # Validate service app fields
            service_app_fields = ['appId', 'clientId', 'clientSecret', 'targetOrgId']
            missing_service_fields = [field for field in service_app_fields if field not in config['serviceApp']]
            
            # Validate token manager fields  
            token_manager_fields = ['personalAccessToken']
            missing_token_fields = [field for field in token_manager_fields if field not in config['tokenManager']]
            
            all_missing = []
            if missing_service_fields:
                all_missing.extend([f"serviceApp.{field}" for field in missing_service_fields])
            if missing_token_fields:
                all_missing.extend([f"tokenManager.{field}" for field in missing_token_fields])
            
            if all_missing:
                raise Exception(f"Missing required fields in config: {all_missing}")
            
            return config
            
        except FileNotFoundError:
            raise Exception(f"Token config file not found: {self.config_path}")
        except json.JSONDecodeError:
            raise Exception("Invalid JSON in token config file")
    
    def _update_env_file(self, new_access_token: str, new_refresh_token: Optional[str] = None) -> None:
        """
        Update the .env file with the new tokens.
        
        Args:
            new_access_token: The new access token to write to the file
            new_refresh_token: The new refresh token to write to the file (optional)
        """
        try:
            # Read the current .env file
            with open(self.env_path, 'r') as f:
                content = f.read()
            
            # Replace the existing token lines
            lines = content.split('\n')
            updated_lines = []
            refresh_token_updated = False
            
            for line in lines:
                if line.startswith('WEBEX_SERVICE_APP_ACCESS_TOKEN='):
                    updated_lines.append(f'WEBEX_SERVICE_APP_ACCESS_TOKEN={new_access_token}')
                elif line.startswith('WEBEX_SERVICE_APP_REFRESH_TOKEN='):
                    if new_refresh_token:
                        updated_lines.append(f'WEBEX_SERVICE_APP_REFRESH_TOKEN={new_refresh_token}')
                        refresh_token_updated = True
                    # If no new refresh token, keep the existing line
                    else:
                        updated_lines.append(line)
                else:
                    updated_lines.append(line)
            
            # Add refresh token if we have one but it wasn't in the file
            if new_refresh_token and not refresh_token_updated:
                updated_lines.append(f'WEBEX_SERVICE_APP_REFRESH_TOKEN={new_refresh_token}')
            
            # Write the updated content back to the file
            with open(self.env_path, 'w') as f:
                f.write('\n'.join(updated_lines))
                
        except Exception as e:
            raise Exception(f"Failed to update .env file: {e}")
    
    def is_token_valid(self) -> bool:
        """
        Check if the current token is valid by making a test API call.
        
        Returns:
            bool: True if token is valid, False otherwise
        """
        try:
            # Get current token from .env
            current_token = self._get_current_token()
            if not current_token:
                return False
            
            # Test the token with the data sources endpoint (service app compatible)
            headers = {'Authorization': f'Bearer {current_token}'}
            response = requests.get('https://webexapis.com/v1/dataSources', headers=headers)
            
            return response.status_code == 200
            
        except Exception:
            return False
    
    def _get_current_token(self) -> Optional[str]:
        """
        Get the current token from the .env file.
        
        Returns:
            The current token or None if not found
        """
        try:
            with open(self.env_path, 'r') as f:
                for line in f:
                    if line.startswith('WEBEX_SERVICE_APP_ACCESS_TOKEN='):
                        return line.split('=', 1)[1].strip()
            return None
        except Exception:
            return None
    
    def _get_current_refresh_token(self) -> Optional[str]:
        """
        Get the current refresh token from the .env file.
        
        Returns:
            The current refresh token or None if not found
        """
        try:
            with open(self.env_path, 'r') as f:
                for line in f:
                    if line.startswith('WEBEX_SERVICE_APP_REFRESH_TOKEN='):
                        return line.split('=', 1)[1].strip()
            return None
        except Exception:
            return None
    
    def get_token_refresh_guidance(self) -> str:
        """
        Provide guidance on how to refresh tokens based on common failure scenarios.
        
        Returns:
            str: Guidance message for token refresh
        """
        return """
Token Refresh Guidance:

If you're using a PORTAL TOKEN (Quick Start - Option A):
1. Go to developer.webex.com
2. Sign in and click your profile (top right)
3. Copy the new "Personal Access Token" 
4. Update the 'personalAccessToken' in your token-config.json
5. Run: python refresh_token.py

If you're using an INTEGRATION TOKEN (Production - Option B):
1. Your integration token may have expired
2. Check your integration's OAuth setup
3. Generate a new access token through the OAuth flow
4. Update the 'personalAccessToken' in your token-config.json
5. Run: python refresh_token.py

For production use, consider Option B (Integration) for longer-lasting tokens.
        """.strip()
