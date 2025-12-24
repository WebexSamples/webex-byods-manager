#!/usr/bin/env python3
"""
Get a fresh service app token for external use

Usage:
    python3 get_service_app_token.py              # Print token to stdout
    python3 get_service_app_token.py | pbcopy     # Copy to clipboard (macOS)
    TOKEN=$(python3 get_service_app_token.py)     # Save to variable
"""

from token_manager import TokenManager
import sys

def main():
    try:
        tm = TokenManager()
        token = tm.get_service_app_token()
        
        # Print only the token to stdout (clean output for piping)
        print(token)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

