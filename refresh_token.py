#!/usr/bin/env python3
"""
Script to manually refresh Webex service app tokens.
"""

import sys
from token_manager import TokenManager


def main():
    """Main function to refresh the token."""
    token_manager = TokenManager()
    
    try:
        print("Checking current token validity...")
        if token_manager.is_token_valid():
            print("Current token is still valid.")
            response = input("Do you want to refresh it anyway? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Token refresh cancelled.")
                return
        
        print("Refreshing token...")
        new_token = token_manager.refresh_token()
        print("Token refreshed successfully!")
        print(f"New token starts with: {new_token[:20]}...")
        
        # Show which refresh method was used
        if token_manager._get_current_refresh_token():
            print("Note: Future refreshes will use the stored refresh token for better efficiency.")
        
    except Exception as e:
        print(f"Token refresh failed: {e}")
        
        # Provide guidance on how to fix token issues
        if "Authentication failed" in str(e) or "401" in str(e):
            print("\n" + "="*60)
            print(token_manager.get_token_refresh_guidance())
            print("="*60)
        
        sys.exit(1)


if __name__ == "__main__":
    main()
