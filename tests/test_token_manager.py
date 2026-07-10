import json

from webex_byods import OAuthRefreshTokenProvider, StaticAccessTokenProvider

from token_manager import TokenManager


def write_config(path, token_manager):
    path.write_text(
        json.dumps(
            {
                "serviceApp": {
                    "appId": "app-id",
                    "clientId": "service-client-id",
                    "clientSecret": "service-client-secret",
                    "targetOrgId": "org-id",
                },
                "tokenManager": token_manager,
            }
        )
    )


def test_token_manager_builds_service_provider_from_json_config(tmp_path):
    config_path = tmp_path / "token-config.json"
    write_config(config_path, {"personalAccessToken": "personal-token"})

    provider = TokenManager(config_path=str(config_path)).get_token_provider()

    assert provider.credentials.app_id == "app-id"
    assert provider.credentials.client_id == "service-client-id"
    assert isinstance(provider.personal_token_provider, StaticAccessTokenProvider)
    assert provider.personal_token_provider.get_access_token() == "personal-token"
    assert TokenManager(config_path=str(config_path)).get_client().token_provider.credentials.app_id == "app-id"


def test_token_manager_uses_oauth_refresh_credentials_from_config(tmp_path):
    config_path = tmp_path / "token-config.json"
    write_config(
        config_path,
        {
            "personalAccessToken": "personal-token",
            "oauthClientId": "oauth-client-id",
            "oauthClientSecret": "oauth-client-secret",
            "oauthRefreshToken": "oauth-refresh-token",
        },
    )

    provider = TokenManager(config_path=str(config_path)).get_token_provider()

    assert isinstance(provider.personal_token_provider, OAuthRefreshTokenProvider)
    assert provider.personal_token_provider.client_id == "oauth-client-id"
    assert provider.personal_token_provider.client_secret == "oauth-client-secret"
    assert provider.personal_token_provider.refresh_token == "oauth-refresh-token"
