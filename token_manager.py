import json
import os
import requests
import uuid
from typing import Dict, Optional

# AWS SDK import - only used in Lambda environment
try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False


# Standalone utility functions for token validation and refresh
def is_personal_token_valid(token: str) -> bool:
    """
    Check if a personal access token is valid.

    Args:
        token: The personal access token to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            "https://webexapis.com/v1/people/me", headers=headers
        )
        return response.status_code == 200
    except Exception:
        return False


def refresh_personal_token_oauth(config: Dict) -> str:
    """
    Refresh the personal access token using OAuth.

    Args:
        config: Configuration dictionary containing clientId, clientSecret, and refreshToken

    Returns:
        str: New personal access token
        
    Raises:
        Exception: If refresh fails
    """
    url = "https://webexapis.com/v1/access_token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "refresh_token",
        "client_id": config["clientId"],
        "client_secret": config["clientSecret"],
        "refresh_token": config["refreshToken"],
    }

    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 401:
        raise Exception(
            "OAuth refresh token expired. Please re-authorize your integration."
        )

    response.raise_for_status()

    token_data = response.json()
    new_access_token = token_data.get("access_token")

    if not new_access_token:
        raise Exception("No access token in OAuth refresh response")

    return new_access_token


class TokenManager:
    """Manages Webex service app authentication.

    Simplified approach: Always fetches fresh service app tokens on demand.
    Tokens are kept in memory only and never persisted.

    Key Features:
    - Fetches fresh service app tokens using personal access token
    - OAuth support for automatic personal token refresh
    - Data source token extension
    - AWS Secrets Manager support for Lambda deployments
    """

    def __init__(self, config_path: str = "token-config.json", secret_name: Optional[str] = None):
        """
        Initialize TokenManager.

        Args:
            config_path: Path to the token configuration file (used for local execution)
            secret_name: AWS Secrets Manager secret name (used for Lambda execution)
        """
        self.config_path = config_path
        self.secret_name = secret_name
        self.use_aws = self._should_use_aws()
        
        # In-memory token cache (per script execution only)
        self._service_app_token = None
        self._service_app_refresh_token = None
        
        # Initialize AWS Secrets Manager client if needed
        if self.use_aws:
            if not AWS_AVAILABLE:
                raise Exception("boto3 is not installed. Install it with: pip install boto3")
            self.secrets_client = boto3.client('secretsmanager', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
            self._secret_cache = None  # Cache the secret to reduce API calls
    
    def _should_use_aws(self) -> bool:
        """
        Determine if we should use AWS Secrets Manager.
        
        Returns:
            bool: True if running in AWS Lambda environment, False otherwise
        """
        # Check if we're in Lambda environment
        if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
            return True
        # Check if secret_name is provided and AWS is available
        if self.secret_name and AWS_AVAILABLE:
            return True
        return False
    
    def _get_secret_from_aws(self) -> Dict:
        """
        Retrieve secret from AWS Secrets Manager.
        
        Returns:
            Dict: The secret data containing credentials
        """
        if self._secret_cache:
            return self._secret_cache
        
        try:
            response = self.secrets_client.get_secret_value(SecretId=self.secret_name)
            secret_data = json.loads(response['SecretString'])
            self._secret_cache = secret_data
            return secret_data
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                raise Exception(f"Secret '{self.secret_name}' not found in AWS Secrets Manager")
            elif error_code == 'AccessDeniedException':
                raise Exception(f"Access denied to secret '{self.secret_name}'. Check IAM permissions.")
            else:
                raise Exception(f"Failed to retrieve secret from AWS: {e}")
    
    def _update_personal_token_in_config(self, new_personal_token: str) -> None:
        """
        Update the personal access token in the config file or AWS Secrets Manager.

        Args:
            new_personal_token: The new personal access token
        """
        # Use AWS Secrets Manager if in Lambda environment
        if self.use_aws:
            try:
                secret_data = self._get_secret_from_aws()
                if 'tokenManager' not in secret_data:
                    secret_data['tokenManager'] = {}
                secret_data['tokenManager']['personalAccessToken'] = new_personal_token
                
                # Update the secret
                self.secrets_client.update_secret(
                    SecretId=self.secret_name,
                    SecretString=json.dumps(secret_data)
                )
                # Update cache
                self._secret_cache = secret_data
                return
            except Exception as e:
                raise Exception(f"Failed to update personal token in AWS Secrets Manager: {e}")
        
        # Otherwise use local config file
        try:
            import tempfile
            
            with open(self.config_path, "r") as f:
                config = json.load(f)

            config["tokenManager"]["personalAccessToken"] = new_personal_token

            # Write back to file atomically
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                delete=False,
                dir=os.path.dirname(self.config_path) or '.',
                prefix='.token-config-',
                suffix='.tmp'
            )
            try:
                json.dump(config, temp_file, indent=4)
                temp_file.close()
                os.replace(temp_file.name, self.config_path)
            except Exception:
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass
                raise

        except Exception as e:
            raise Exception(f"Failed to update personal token in config: {e}")

    def _load_config(self) -> Dict[str, str]:
        """
        Load configuration from AWS Secrets Manager or local config file.

        Returns:
            Dict containing the configuration

        Raises:
            Exception: If config is not found or invalid
        """
        # Use AWS Secrets Manager if in Lambda environment
        if self.use_aws:
            secret_data = self._get_secret_from_aws()
            config = {
                'serviceApp': secret_data.get('serviceApp', {}),
                'tokenManager': secret_data.get('tokenManager', {})
            }
        else:
            # Load from local file
            try:
                with open(self.config_path, "r") as f:
                    config = json.load(f)
            except FileNotFoundError:
                raise Exception(f"Token config file not found: {self.config_path}")
            except json.JSONDecodeError:
                raise Exception("Invalid JSON in token config file")
        
        try:
            # Validate structure
            if "serviceApp" not in config:
                raise Exception("Missing 'serviceApp' section in config")
            if "tokenManager" not in config:
                raise Exception("Missing 'tokenManager' section in config")

            # Validate service app fields
            service_app_fields = ["appId", "clientId", "clientSecret", "targetOrgId"]
            missing_service_fields = [
                field
                for field in service_app_fields
                if field not in config["serviceApp"]
            ]

            # Validate token manager fields
            token_manager_fields = ["personalAccessToken"]
            missing_token_fields = [
                field
                for field in token_manager_fields
                if field not in config["tokenManager"]
            ]

            # OAuth fields are optional but must all be present together
            oauth_fields = ["clientId", "clientSecret", "refreshToken"]
            oauth_present = [field in config["tokenManager"] for field in oauth_fields]
            
            if any(oauth_present) and not all(oauth_present):
                missing_oauth = [field for field in oauth_fields if field not in config["tokenManager"]]
                print(
                    f"Warning: OAuth partially configured. Missing: {missing_oauth}"
                )
                print("OAuth token refresh will not be available.")

            all_missing = []
            if missing_service_fields:
                all_missing.extend(
                    [f"serviceApp.{field}" for field in missing_service_fields]
                )
            if missing_token_fields:
                all_missing.extend(
                    [f"tokenManager.{field}" for field in missing_token_fields]
                )

            if all_missing:
                raise Exception(f"Missing required fields in config: {all_missing}")

            return config

        except Exception:
            raise

    def is_personal_token_valid(self, token: str) -> bool:
        """
        Check if a personal access token is valid.

        Args:
            token: The personal access token to validate

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                "https://webexapis.com/v1/people/me", headers=headers
            )
            return response.status_code == 200
        except Exception:
            return False

    def refresh_personal_token_oauth(self, config: Dict) -> str:
        """
        Refresh the personal access token using OAuth.

        Args:
            config: Configuration containing OAuth fields

        Returns:
            str: New personal access token
        """
        url = "https://webexapis.com/v1/access_token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "refresh_token",
            "client_id": config["clientId"],
            "client_secret": config["clientSecret"],
            "refresh_token": config["refreshToken"],
        }

        response = requests.post(url, headers=headers, data=data)

        if response.status_code == 401:
            raise Exception(
                "OAuth refresh token expired. Please re-authorize your integration."
            )

        response.raise_for_status()

        token_data = response.json()
        new_access_token = token_data.get("access_token")

        if not new_access_token:
            raise Exception("No access token in OAuth refresh response")

        return new_access_token

    def _try_refresh_personal_token(self, config: Dict) -> str:
        """
        Attempt to refresh the personal access token via OAuth.

        Args:
            config: The loaded configuration

        Returns:
            str: A refreshed personal access token
            
        Raises:
            Exception: If refresh is not configured or fails
        """
        token_manager = config["tokenManager"]

        # Check if OAuth is configured (all three fields must be present)
        oauth_configured = all(
            key in token_manager
            for key in ["clientId", "clientSecret", "refreshToken"]
        )
        
        if not oauth_configured:
            raise Exception(
                "OAuth refresh is not configured. Cannot refresh token automatically. "
                "Please run setup_oauth.py to configure automatic token refresh, "
                "or manually update personalAccessToken in token-config.json"
            )
        
        print("Personal access token expired, refreshing via OAuth...")
        personal_token = self.refresh_personal_token_oauth(token_manager)
        
        # Update the config file with new personal token
        self._update_personal_token_in_config(personal_token)
        print("Personal access token refreshed successfully")
        
        return personal_token

    def get_service_app_token(self) -> str:
        """
        Get a fresh service app access token.
        
        This method fetches a token from the Webex Token Manager API.
        If the personal access token is expired, it will attempt to refresh it
        automatically using OAuth (if configured) and retry.
        
        The token is cached in memory for the duration of the script execution.

        Returns:
            str: Service app access token
            
        Raises:
            Exception: If token request fails
        """
        # Return cached token if we already have one for this execution
        if self._service_app_token:
            return self._service_app_token
        
        config = self._load_config()
        
        # Try to get token with current personal token
        try:
            return self._fetch_service_app_token(config)
        except requests.exceptions.HTTPError as e:
            # If we get a 401, the personal token might be expired
            if e.response.status_code == 401:
                print("Token Manager authentication failed (401), attempting to refresh personal token...")
                try:
                    # Try to refresh the personal token
                    new_personal_token = self._try_refresh_personal_token(config)
                    
                    # Update config in memory with refreshed token
                    config["tokenManager"]["personalAccessToken"] = new_personal_token
                    
                    # Retry fetching service app token with refreshed personal token
                    print("Retrying with refreshed token...")
                    return self._fetch_service_app_token(config)
                    
                except Exception as refresh_error:
                    raise Exception(
                        f"Failed to refresh personal token: {refresh_error}. "
                        "Please run setup_oauth.py to re-authorize."
                    )
            else:
                # Some other HTTP error
                raise Exception(f"Token request failed with status {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get service app token: {e}")
    
    def _fetch_service_app_token(self, config: Dict) -> str:
        """
        Internal method to fetch service app token from the API.
        
        Args:
            config: The loaded configuration
            
        Returns:
            str: Service app access token
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails
        """
        personal_token = config["tokenManager"]["personalAccessToken"]
        service_app = config["serviceApp"]

        url = f"https://webexapis.com/v1/applications/{service_app['appId']}/token"
        headers = {
            "Authorization": f"Bearer {personal_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "clientId": service_app["clientId"],
            "clientSecret": service_app["clientSecret"],
            "targetOrgId": service_app["targetOrgId"],
        }

        # Make the API call
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raises HTTPError for bad status codes

        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        if not access_token:
            raise Exception("No access token in API response")

        # Cache tokens in memory for this execution
        self._service_app_token = access_token
        self._service_app_refresh_token = refresh_token

        return access_token

    def extend_data_source_token(
        self, data_source_id: str, token_lifetime_minutes: int = 1440
    ) -> Dict[str, any]:
        """
        Extend a data source token by updating only the nonce.

        Args:
            data_source_id: The ID of the data source to update
            token_lifetime_minutes: Token lifetime in minutes (default: 1440 = 24 hours, max: 1440)

        Returns:
            Dict containing the result of the operation
        """
        try:
            # Validate token lifetime
            if token_lifetime_minutes > 1440:
                return {
                    "success": False,
                    "error": f"Token lifetime cannot exceed 1440 minutes (24 hours). Requested: {token_lifetime_minutes} minutes",
                }

            if token_lifetime_minutes <= 0:
                return {
                    "success": False,
                    "error": f"Token lifetime must be positive. Requested: {token_lifetime_minutes} minutes",
                }

            # Get fresh service app token
            access_token = self.get_service_app_token()

            # First, get the current data source configuration
            headers = {"Authorization": f"Bearer {access_token}"}
            get_url = f"https://webexapis.com/v1/dataSources/{data_source_id}"

            response = requests.get(get_url, headers=headers)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to retrieve data source: {response.text}",
                    "status_code": response.status_code,
                }

            current_config = response.json()

            # Parse the JWT token to extract audience, subject, and schema info
            jws_token = current_config.get("jwsToken", "")
            audience = None
            subject = None
            schema_uuid = None

            if jws_token:
                try:
                    # Decode JWT without verification to extract claims
                    import jwt

                    decoded = jwt.decode(jws_token, options={"verify_signature": False})
                    audience = decoded.get("aud")
                    subject = decoded.get("sub")
                    schema_uuid = decoded.get("com.cisco.datasource.schema.uuid")
                except Exception as e:
                    print(f"Warning: Could not decode JWT token: {e}")

            # Fallback to current config values if JWT parsing failed
            if not audience:
                audience = current_config.get("audience", "")
            if not subject:
                subject = current_config.get("subject", "subject")
            if not schema_uuid:
                schema_uuid = current_config.get("schemaId", "")

            # Generate a new nonce (this is what triggers the token refresh)
            new_nonce = str(uuid.uuid4())

            # Create update configuration with all required fields
            update_config = {
                "audience": audience,
                "nonce": new_nonce,
                "schemaId": schema_uuid,
                "subject": subject,
                "url": current_config.get("url"),
                "tokenLifetimeMinutes": token_lifetime_minutes,
                "status": current_config.get("status", "active"),
            }

            # Validate that we have all required fields
            required_fields = ["audience", "schemaId", "url"]
            missing_fields = [
                field for field in required_fields if not update_config.get(field)
            ]

            if missing_fields:
                return {
                    "success": False,
                    "error": f"Missing required fields: {missing_fields}. Could not extract from current data source.",
                }

            # Update the data source
            update_url = f"https://webexapis.com/v1/dataSources/{data_source_id}"
            headers["Content-Type"] = "application/json"

            update_response = requests.put(
                update_url, headers=headers, json=update_config
            )

            if update_response.status_code == 200:
                result_data = update_response.json()
                return {
                    "success": True,
                    "data": result_data,
                    "nonce_updated": new_nonce,
                    "token_lifetime_minutes": token_lifetime_minutes,
                    "token_expiry": result_data.get("tokenExpiryTime"),
                    "message": f"Data source token extended successfully. New expiry: {result_data.get('tokenExpiryTime')}",
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to update data source: {update_response.text}",
                    "status_code": update_response.status_code,
                }

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
