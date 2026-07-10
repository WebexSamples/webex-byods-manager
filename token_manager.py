"""CLI and Lambda adapter for configuring the Webex BYODS SDK."""

import json
import os
from typing import Any, Dict, Optional

from webex_byods import (
    OAuthRefreshTokenProvider,
    ServiceAppCredentials,
    StaticAccessTokenProvider,
    WebexDataSourceClient,
    WebexServiceAppTokenProvider,
)

try:
    import boto3
    from botocore.exceptions import ClientError

    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False


class TokenManager:
    """Build SDK token providers from CLI files or Lambda Secrets Manager data."""

    def __init__(
        self, config_path: str = "token-config.json", secret_name: Optional[str] = None
    ) -> None:
        self.config_path = config_path
        self.secret_name = secret_name
        self.use_aws = "AWS_LAMBDA_FUNCTION_NAME" in os.environ or bool(
            secret_name and AWS_AVAILABLE
        )
        self._config_cache: Optional[Dict[str, Any]] = None
        self._token_provider: Optional[WebexServiceAppTokenProvider] = None

        if self.use_aws:
            if not AWS_AVAILABLE:
                raise RuntimeError("boto3 is required for AWS Secrets Manager support")
            self.secrets_client = boto3.client(
                "secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1")
            )

    def _load_config(self) -> Dict[str, Any]:
        if self._config_cache is not None:
            return self._config_cache

        if self.use_aws:
            try:
                response = self.secrets_client.get_secret_value(SecretId=self.secret_name)
                config = json.loads(response["SecretString"])
            except ClientError as error:
                raise RuntimeError(f"Failed to read AWS secret: {error}") from error
        else:
            try:
                with open(self.config_path, "r", encoding="utf-8") as config_file:
                    config = json.load(config_file)
            except FileNotFoundError as error:
                raise RuntimeError(
                    f"Token config file not found: {self.config_path}"
                ) from error
            except json.JSONDecodeError as error:
                raise RuntimeError("Invalid JSON in token config file") from error

        self._validate_config(config)
        self._config_cache = config
        return config

    @staticmethod
    def _validate_config(config: Dict[str, Any]) -> None:
        service_app = config.get("serviceApp", {})
        token_manager = config.get("tokenManager", {})
        missing_fields = [
            f"serviceApp.{field}"
            for field in ("appId", "clientId", "clientSecret", "targetOrgId")
            if not service_app.get(field)
        ]
        if not token_manager.get("personalAccessToken"):
            missing_fields.append("tokenManager.personalAccessToken")
        if missing_fields:
            raise RuntimeError(f"Missing required fields in config: {missing_fields}")

    @staticmethod
    def _oauth_value(config: Dict[str, Any], primary: str, legacy: str) -> Optional[str]:
        return config.get(primary) or config.get(legacy)

    def get_token_provider(self) -> WebexServiceAppTokenProvider:
        """Build and cache the SDK service-app token provider."""
        if self._token_provider is not None:
            return self._token_provider

        config = self._load_config()
        service_app = config["serviceApp"]
        token_config = config["tokenManager"]
        oauth_client_id = self._oauth_value(token_config, "oauthClientId", "clientId")
        oauth_client_secret = self._oauth_value(
            token_config, "oauthClientSecret", "clientSecret"
        )
        oauth_refresh_token = self._oauth_value(
            token_config, "oauthRefreshToken", "refreshToken"
        )

        if all((oauth_client_id, oauth_client_secret, oauth_refresh_token)):
            personal_token_provider = OAuthRefreshTokenProvider(
                client_id=oauth_client_id,
                client_secret=oauth_client_secret,
                refresh_token=oauth_refresh_token,
            )
        else:
            personal_token_provider = StaticAccessTokenProvider(
                token_config["personalAccessToken"]
            )

        self._token_provider = WebexServiceAppTokenProvider(
            ServiceAppCredentials(
                app_id=service_app["appId"],
                client_id=service_app["clientId"],
                client_secret=service_app["clientSecret"],
                target_org_id=service_app["targetOrgId"],
            ),
            personal_token_provider,
        )
        return self._token_provider

    def get_service_app_token(self, force_refresh: bool = False) -> str:
        """Return a service-app token through the configured SDK provider."""
        return self.get_token_provider().get_access_token(force_refresh=force_refresh)

    def get_client(self) -> WebexDataSourceClient:
        """Return a data-source client that can refresh through this adapter."""
        return WebexDataSourceClient(token_provider=self.get_token_provider())

    def is_token_valid(self) -> bool:
        """Check that the configured credentials can obtain a service-app token."""
        try:
            self.get_service_app_token()
            return True
        except Exception:
            return False

    def refresh_token(self) -> str:
        """Refresh the personal token when OAuth credentials are configured."""
        provider = self.get_token_provider().personal_token_provider
        if not isinstance(provider, OAuthRefreshTokenProvider):
            raise RuntimeError(
                "OAuth refresh is not configured. Update tokenManager credentials "
                "or run setup_oauth.py."
            )
        return provider.get_access_token(force_refresh=True)

    def _get_current_refresh_token(self) -> Optional[str]:
        token_config = self._load_config()["tokenManager"]
        return self._oauth_value(token_config, "oauthRefreshToken", "refreshToken")

    def get_token_refresh_guidance(self) -> str:
        return (
            "Token Refresh Guidance:\n"
            "1. Configure OAuth credentials with setup_oauth.py for automatic refresh.\n"
            "2. Re-authorize the integration if its OAuth refresh token expires.\n"
            "3. Otherwise update tokenManager.personalAccessToken in token-config.json."
        )

    def extend_data_source_token(
        self, data_source_id: str, token_lifetime_minutes: int = 1440
    ) -> Dict[str, Any]:
        """Delegate data-source token extension to the SDK client."""
        return self.get_client().extend_data_source_token(
            data_source_id, token_lifetime_minutes
        )
