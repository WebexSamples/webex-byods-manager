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


def setup_oauth_flow():
    """Set up OAuth flow for token manager integration."""
    print("OAuth Setup for Token Manager Integration")
    print("=" * 50)
    print()

    config = load_config()

    # Get OAuth credentials
    print("First, you need the OAuth credentials from your Token Manager Integration:")
    print("(This is DIFFERENT from your service app credentials)")
    print()

    client_id = input("Enter your Token Manager Integration Client ID: ").strip()
    if not client_id:
        print("Client ID is required")
        return

    client_secret = input(
        "Enter your Token Manager Integration Client Secret: "
    ).strip()
    if not client_secret:
        print("Client Secret is required")
        return

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
    print("-" * 30)
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
        print("Authorization code is required")
        return

    # Exchange code for tokens
    print("Exchanging authorization code for tokens...")

    import requests

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
            print("Error: Did not receive both access and refresh tokens")
            return

        # Update configuration with flat structure
        config["tokenManager"]["oauthClientId"] = client_id
        config["tokenManager"]["oauthClientSecret"] = client_secret
        config["tokenManager"]["oauthRefreshToken"] = refresh_token
        config["tokenManager"]["personalAccessToken"] = access_token

        save_config(config)

        print()
        print("✅ OAuth setup completed successfully!")
        print("Your token manager now supports automatic personal token refresh.")
        print()
        print("Updated configuration:")
        print(f"- Personal Access Token: {access_token[:20]}...")
        print(f"- Refresh Token: {refresh_token[:20]}...")
        print("- OAuth credentials saved to token-config.json")

    except requests.exceptions.RequestException as e:
        print(f"Error exchanging authorization code: {e}")
        return
    except Exception as e:
        print(f"Unexpected error: {e}")
        return


def main():
    """Main function."""
    print("Token Manager OAuth Setup")
    print("This will help you set up automatic refresh for your personal access token.")
    print()
    print("Prerequisites:")
    print("1. You have created a Token Manager Integration at developer.webex.com")
    print("2. Your integration has the 'spark:applications_token' scope")
    print("3. Your integration has 'http://localhost:3000/callback' as a redirect URI")
    print()

    proceed = input("Do you want to continue? (y/N): ").strip().lower()
    if proceed not in ["y", "yes"]:
        print("Setup cancelled.")
        return

    setup_oauth_flow()


if __name__ == "__main__":
    main()
