#!/usr/bin/env python3
"""
OAuth Setup Helper for Token Manager Integration

This script helps you set up OAuth authorization for your token manager integration.
Use this when you want to enable automatic refresh of your personal access token.
"""

import json
import urllib.parse
import webbrowser
from typing import Dict
import requests


def load_config() -> Dict:
    """Load the token configuration."""
    try:
        with open("token-config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(
            "Error: token-config.json not found. Please create it from the template first."
        )
        exit(1)
    except json.JSONDecodeError:
        print("Error: Invalid JSON in token-config.json")
        exit(1)


def save_config(config: Dict) -> None:
    """Save the updated configuration."""
    with open("token-config.json", "w") as f:
        json.dump(config, f, indent=4)


def is_token_manager_token_valid(token: str, service_app_config: Dict) -> bool:
    """
    Check if a Token Manager integration token is valid by using it
    to fetch a service app token.

    Args:
        token: The Token Manager integration token to validate
        service_app_config: The serviceApp section from config

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        url = f"https://webexapis.com/v1/applications/{service_app_config['appId']}/token"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "clientId": service_app_config["clientId"],
            "clientSecret": service_app_config["clientSecret"],
            "targetOrgId": service_app_config["targetOrgId"],
        }

        response = requests.post(url, headers=headers, json=payload)

        # 200 = valid token, 401 = invalid/expired token
        return response.status_code == 200
    except Exception:
        return False


def refresh_personal_token_oauth(token_config: Dict) -> str:
    """
    Refresh the personal access token using OAuth.

    Args:
        token_config: Configuration dictionary containing clientId, clientSecret, and refreshToken

    Returns:
        str: New personal access token

    Raises:
        Exception: If refresh fails
    """
    url = "https://webexapis.com/v1/access_token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "refresh_token",
        "client_id": token_config["clientId"],
        "client_secret": token_config["clientSecret"],
        "refresh_token": token_config["refreshToken"],
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


def can_refresh_oauth(config: Dict) -> bool:
    """Check if OAuth refresh credentials exist."""
    return all(k in config for k in ["clientId", "clientSecret", "refreshToken"])


def has_oauth_credentials(config: Dict) -> bool:
    """Check if OAuth client credentials exist (without refresh token)."""
    return all(k in config for k in ["clientId", "clientSecret"])


def try_refresh_token(token_config: Dict, full_config: Dict, service_app_config: Dict) -> bool:
    """
    Attempt to refresh using OAuth refresh token.
    
    Args:
        token_config: The tokenManager section of the config
        full_config: The complete config dictionary
        service_app_config: The serviceApp section for validation
        
    Returns:
        bool: True if refresh succeeded, False otherwise
    """
    try:
        print("Attempting to refresh token using OAuth...")
        new_token = refresh_personal_token_oauth(token_config)
        
        # Validate the new token if we have service app config
        if service_app_config.get("appId"):
            print("Validating refreshed token...")
            if not is_token_manager_token_valid(new_token, service_app_config):
                print("✗ Refreshed token is not valid for Token Manager API")
                return False
        
        full_config["tokenManager"]["personalAccessToken"] = new_token
        save_config(full_config)
        print("✓ Token refreshed successfully!")
        print(f"  New token: {new_token[:20]}...")
        return True
    except Exception as e:
        print(f"✗ Refresh failed: {e}")
        return False


def prompt_for_credential_method() -> str:
    """
    Ask user to choose between PAT or OAuth flow.
    
    Returns:
        str: "pat" or "oauth"
    """
    print()
    print("=" * 60)
    print("No valid token manager credentials found.")
    print("=" * 60)
    print()
    print("How would you like to proceed?")
    print()
    print("  1. Paste a Personal Access Token from developer.webex.com")
    print("     (Quick setup, but requires manual renewal)")
    print()
    print("  2. Provide OAuth credentials for automatic refresh")
    print("     (Recommended: enables automatic token renewal)")
    print()
    
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice == "1":
            return "pat"
        elif choice == "2":
            return "oauth"
        else:
            print("Invalid choice. Please enter 1 or 2.")


def handle_pat_input(config: Dict) -> None:
    """
    Handle manual PAT input from user.
    
    Args:
        config: The configuration dictionary
    """
    print()
    print("Manual Personal Access Token Setup")
    print("-" * 40)
    print()
    print("To get a Personal Access Token:")
    print("1. Go to https://developer.webex.com/docs/getting-started")
    print("2. Log in with your Webex account")
    print("3. Copy your Personal Access Token")
    print()
    
    pat = input("Paste your Personal Access Token: ").strip()
    if not pat:
        print("✗ No token provided. Setup cancelled.")
        return
    
    # Validate the token by trying to use it
    print("Validating token...")
    service_app_config = config.get("serviceApp", {})
    
    if not service_app_config.get("appId"):
        print("⚠️  Warning: Cannot validate token - serviceApp config missing.")
        print("   Token will be saved but may not work correctly.")
    elif not is_token_manager_token_valid(pat, service_app_config):
        print("✗ Invalid token or token doesn't have required permissions.")
        print("  Make sure this is a Token Manager Integration token with")
        print("  'spark:applications_token' scope.")
        return
    
    # Save to config
    if "tokenManager" not in config:
        config["tokenManager"] = {}
    
    config["tokenManager"]["personalAccessToken"] = pat
    save_config(config)
    
    print()
    print("✓ Personal Access Token saved successfully!")
    print(f"  Token: {pat[:20]}...")
    print()
    print("⚠️  Note: This token will need to be manually renewed when it expires.")
    print("   Consider running this script again with OAuth credentials for automatic renewal.")


def confirm_use_existing_credentials() -> bool:
    """
    Ask user if they want to use existing OAuth credentials.
    
    Returns:
        bool: True if user wants to use existing credentials
    """
    print()
    print("OAuth credentials found in configuration.")
    response = input("Do you want to use these credentials? (Y/n): ").strip().lower()
    return response in ["", "y", "yes"]


def do_oauth_flow_with_credentials(client_id: str, client_secret: str, config: Dict) -> None:
    """
    Execute the OAuth authorization flow with provided credentials.
    
    Args:
        client_id: OAuth client ID
        client_secret: OAuth client secret
        config: The configuration dictionary
    """
    # Use localhost as redirect URI
    redirect_uri = "http://localhost:3000/callback"

    # Build authorization URL
    auth_params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": "spark:applications_token",
        "state": "token_manager_setup",
    }

    auth_url = "https://webexapis.com/v1/authorize?" + urllib.parse.urlencode(
        auth_params
    )

    print()
    print("OAuth Authorization Setup")
    print("-" * 40)
    print("1. Opening authorization URL in your browser...")
    print("2. Log in and authorize the application")
    print("3. You'll be redirected to localhost (which will fail)")
    print("4. Copy the 'code' parameter from the URL")
    print()
    print(f"Authorization URL: {auth_url}")
    print()

    # Open browser
    try:
        webbrowser.open(auth_url)
    except Exception:
        print("Could not open browser automatically. Please copy the URL above.")

    print("After authorization, you'll see a URL like:")
    print("http://localhost:3000/callback?code=ABC123...&state=token_manager_setup")
    print()

    auth_code = input("Enter the authorization code from the URL: ").strip()
    if not auth_code:
        print("✗ Authorization code is required. Setup cancelled.")
        return

    # Exchange code for tokens
    print("Exchanging authorization code for tokens...")

    token_url = "https://webexapis.com/v1/access_token"
    token_data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }

    try:
        response = requests.post(token_url, data=token_data)
        response.raise_for_status()

        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        if not access_token or not refresh_token:
            print("✗ Error: Did not receive both access and refresh tokens")
            return

        # Update configuration with flat structure
        if "tokenManager" not in config:
            config["tokenManager"] = {}
            
        config["tokenManager"]["clientId"] = client_id
        config["tokenManager"]["clientSecret"] = client_secret
        config["tokenManager"]["refreshToken"] = refresh_token
        config["tokenManager"]["personalAccessToken"] = access_token

        save_config(config)

        print()
        print("✓ OAuth setup completed successfully!")
        print("  Your token manager now supports automatic personal token refresh.")
        print()
        print("Updated configuration:")
        print(f"  - Personal Access Token: {access_token[:20]}...")
        print(f"  - Refresh Token: {refresh_token[:20]}...")
        print("  - OAuth credentials saved to token-config.json")

    except requests.exceptions.RequestException as e:
        print(f"✗ Error exchanging authorization code: {e}")
        return
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return


def handle_oauth_credential_input(config: Dict) -> None:
    """
    Handle OAuth credential input from user and start OAuth flow.
    
    Args:
        config: The configuration dictionary
    """
    print()
    print("OAuth Credential Setup")
    print("-" * 40)
    print()
    print("You need OAuth credentials from your Token Manager Integration:")
    print("(This is DIFFERENT from your service app credentials)")
    print()
    print("To get these credentials:")
    print("1. Go to https://developer.webex.com/my-apps")
    print("2. Create or select your Token Manager Integration")
    print("3. Ensure it has 'spark:applications_token' scope")
    print("4. Add 'http://localhost:3000/callback' as a redirect URI")
    print()

    client_id = input("Enter your Token Manager Integration Client ID: ").strip()
    if not client_id:
        print("✗ Client ID is required. Setup cancelled.")
        return

    client_secret = input(
        "Enter your Token Manager Integration Client Secret: "
    ).strip()
    if not client_secret:
        print("✗ Client Secret is required. Setup cancelled.")
        return

    do_oauth_flow_with_credentials(client_id, client_secret, config)


def smart_setup_oauth_flow():
    """
    Smart OAuth flow that checks existing tokens before prompting user.
    
    This follows a cascade:
    1. Check if PAT exists and is valid -> Done
    2. Try to refresh using OAuth if refresh token exists -> Done if successful
    3. Use existing OAuth credentials for new auth flow if they exist
    4. Prompt user to choose between PAT or OAuth setup
    """
    print("Token Manager OAuth Setup")
    print("=" * 60)
    print()

    config = load_config()
    token_manager_config = config.get("tokenManager", {})
    service_app_config = config.get("serviceApp", {})

    # Step 1: Check if PAT exists and is valid
    personal_token = token_manager_config.get("personalAccessToken")
    if personal_token and service_app_config.get("appId"):
        print("Checking existing personal access token...")
        if is_token_manager_token_valid(personal_token, service_app_config):
            print("✓ Existing personal access token is valid!")
            print(f"  Token: {personal_token[:20]}...")
            print()
            print("No further setup needed. Your token is ready to use.")
            return
        
        print("✗ Existing token is expired or invalid.")

    # Step 2: Try OAuth refresh if available
    if can_refresh_oauth(token_manager_config):
        if try_refresh_token(token_manager_config, config, service_app_config):
            print()
            print("No further setup needed. Your token has been refreshed.")
            return

    # Step 3: Try OAuth flow with existing credentials
    if has_oauth_credentials(token_manager_config):
        if confirm_use_existing_credentials():
            do_oauth_flow_with_credentials(
                token_manager_config["clientId"],
                token_manager_config["clientSecret"],
                config
            )
            return
        else:
            print("Proceeding with manual setup...")

    # Step 4: Prompt user for input method
    choice = prompt_for_credential_method()
    if choice == "pat":
        handle_pat_input(config)
    else:
        handle_oauth_credential_input(config)


def main():
    """Main function."""
    print()
    print("This script will help you set up token manager credentials.")
    print("It supports both manual PAT entry and OAuth with automatic refresh.")
    print()
    
    smart_setup_oauth_flow()
    
    print()
    print("Setup complete!")


if __name__ == "__main__":
    main()
