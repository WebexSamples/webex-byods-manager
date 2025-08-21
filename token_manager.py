import json
import requests
import uuid
from typing import Dict, Optional


class TokenManager:
    """Manages Webex service app token refresh and updates.

    Key Features:
    - Smart token refresh (uses refresh tokens when available, falls back to personal tokens)
    - OAuth support for automatic personal token refresh
    - Data source token extension without configuration changes
    - Automatic token validation and refresh
    """

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
            service_app = config["serviceApp"]

            url = "https://webexapis.com/v1/access_token"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {
                "grant_type": "refresh_token",
                "client_id": service_app["clientId"],
                "client_secret": service_app["clientSecret"],
                "refresh_token": refresh_token,
            }

            response = requests.post(url, headers=headers, data=data)

            if response.status_code == 401:
                raise Exception("Refresh token expired or invalid")

            response.raise_for_status()

            token_data = response.json()
            new_access_token = token_data.get("access_token")
            new_refresh_token = token_data.get(
                "refresh_token", refresh_token
            )  # Use new or keep old

            if not new_access_token:
                raise Exception("No access token in refresh response")

            # Update the .env file with the new tokens
            self._update_env_file(new_access_token, new_refresh_token)

            print("Token refreshed successfully using refresh token")
            return new_access_token

        except requests.exceptions.RequestException as e:
            raise Exception(f"Refresh token request failed: {e}")

    def _get_valid_personal_token(self, config: Dict) -> str:
        """
        Get a valid personal access token, refreshing via OAuth if needed.

        Args:
            config: The loaded configuration

        Returns:
            str: A valid personal access token
        """
        token_manager = config["tokenManager"]
        personal_token = token_manager["personalAccessToken"]

        # Check if OAuth integration is configured
        if "integration" in token_manager and all(
            key in token_manager["integration"]
            for key in ["clientId", "clientSecret", "refreshToken"]
        ):
            # Test current personal token
            if not self._is_personal_token_valid(personal_token):
                print("Personal access token expired, refreshing via OAuth...")
                try:
                    personal_token = self._refresh_personal_token_oauth(
                        token_manager["integration"]
                    )
                    # Update the config file with new personal token
                    self._update_personal_token_in_config(personal_token)
                    print("Personal access token refreshed successfully")
                except Exception as e:
                    print(f"Failed to refresh personal token via OAuth: {e}")
                    print("Using existing personal token (may be expired)")

        return personal_token

    def _is_personal_token_valid(self, token: str) -> bool:
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

    def _refresh_personal_token_oauth(self, integration_config: Dict) -> str:
        """
        Refresh the personal access token using OAuth.

        Args:
            integration_config: OAuth integration configuration

        Returns:
            str: New personal access token
        """
        url = "https://webexapis.com/v1/access_token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "refresh_token",
            "client_id": integration_config["clientId"],
            "client_secret": integration_config["clientSecret"],
            "refresh_token": integration_config["refreshToken"],
        }

        response = requests.post(url, headers=headers, data=data)

        if response.status_code == 401:
            raise Exception(
                "OAuth refresh token expired. Please re-authorize your integration."
            )

        response.raise_for_status()

        token_data = response.json()
        new_access_token = token_data.get("access_token")
        new_refresh_token = token_data.get("refresh_token")

        if not new_access_token:
            raise Exception("No access token in OAuth refresh response")

        # Update refresh token if provided
        if new_refresh_token:
            integration_config["refreshToken"] = new_refresh_token
            # Note: This updates the in-memory config, _update_personal_token_in_config will save it

        return new_access_token

    def _update_personal_token_in_config(self, new_personal_token: str) -> None:
        """
        Update the personal access token in the config file.

        Args:
            new_personal_token: The new personal access token
        """
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)

            config["tokenManager"]["personalAccessToken"] = new_personal_token

            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=4)

        except Exception as e:
            raise Exception(f"Failed to update personal token in config: {e}")

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

            # Try to refresh the personal access token first if OAuth is configured
            personal_token = self._get_valid_personal_token(config)

            # Prepare the API request
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

            if response.status_code == 401:
                raise Exception(
                    "Authentication failed. Your personal access token may have expired. "
                    "If using a portal token, get a new one from developer.webex.com. "
                    "If using an integration token, refresh your OAuth token."
                )

            response.raise_for_status()

            token_data = response.json()
            new_access_token = token_data.get("access_token")
            new_refresh_token = token_data.get("refresh_token")

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
            with open(self.config_path, "r") as f:
                config = json.load(f)

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

            # OAuth integration fields are optional
            if "integration" in config["tokenManager"]:
                integration_fields = ["clientId", "clientSecret", "refreshToken"]
                missing_integration_fields = [
                    field
                    for field in integration_fields
                    if field not in config["tokenManager"]["integration"]
                ]
                if missing_integration_fields:
                    print(
                        f"Warning: OAuth integration partially configured. Missing: {missing_integration_fields}"
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

        except FileNotFoundError:
            raise Exception(f"Token config file not found: {self.config_path}")
        except json.JSONDecodeError:
            raise Exception("Invalid JSON in token config file")

    def _update_env_file(
        self, new_access_token: str, new_refresh_token: Optional[str] = None
    ) -> None:
        """
        Update the .env file with the new tokens.

        Args:
            new_access_token: The new access token to write to the file
            new_refresh_token: The new refresh token to write to the file (optional)
        """
        try:
            # Read the current .env file
            with open(self.env_path, "r") as f:
                content = f.read()

            # Replace the existing token lines
            lines = content.split("\n")
            updated_lines = []
            refresh_token_updated = False

            for line in lines:
                if line.startswith("WEBEX_SERVICE_APP_ACCESS_TOKEN="):
                    updated_lines.append(
                        f"WEBEX_SERVICE_APP_ACCESS_TOKEN={new_access_token}"
                    )
                elif line.startswith("WEBEX_SERVICE_APP_REFRESH_TOKEN="):
                    if new_refresh_token:
                        updated_lines.append(
                            f"WEBEX_SERVICE_APP_REFRESH_TOKEN={new_refresh_token}"
                        )
                        refresh_token_updated = True
                    # If no new refresh token, keep the existing line
                    else:
                        updated_lines.append(line)
                else:
                    updated_lines.append(line)

            # Add refresh token if we have one but it wasn't in the file
            if new_refresh_token and not refresh_token_updated:
                updated_lines.append(
                    f"WEBEX_SERVICE_APP_REFRESH_TOKEN={new_refresh_token}"
                )

            # Write the updated content back to the file
            with open(self.env_path, "w") as f:
                f.write("\n".join(updated_lines))

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
            headers = {"Authorization": f"Bearer {current_token}"}
            response = requests.get(
                "https://webexapis.com/v1/dataSources", headers=headers
            )

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
            with open(self.env_path, "r") as f:
                for line in f:
                    if line.startswith("WEBEX_SERVICE_APP_ACCESS_TOKEN="):
                        return line.split("=", 1)[1].strip()
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
            with open(self.env_path, "r") as f:
                for line in f:
                    if line.startswith("WEBEX_SERVICE_APP_REFRESH_TOKEN="):
                        return line.split("=", 1)[1].strip()
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

    def extend_data_source_token(
        self, data_source_id: str, token_lifetime_minutes: int = 1440
    ) -> Dict[str, any]:
        """
        Quickly extend a data source token by updating only the nonce, without changing other values.
        This is useful for extending token expiry without requiring user input for other fields.

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

            # Get current token
            current_token = self._get_current_token()
            if not current_token:
                return {"success": False, "error": "No access token found in .env file"}

            # First, get the current data source configuration
            headers = {"Authorization": f"Bearer {current_token}"}
            get_url = f"https://webexapis.com/v1/dataSources/{data_source_id}"

            response = requests.get(get_url, headers=headers)

            if response.status_code == 401:
                return {
                    "success": False,
                    "error": "Access token expired or invalid. Please refresh your token first.",
                }

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
                # Try to get from current config, but it might not have audience field directly
                audience = current_config.get("audience", "")
            if not subject:
                subject = current_config.get(
                    "subject", "subject"
                )  # Default if not found
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
