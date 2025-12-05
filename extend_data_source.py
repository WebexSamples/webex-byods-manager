#!/usr/bin/env python3
"""
Extend Data Source Token Script

This script provides a quick way to extend a data source token without changing any values.
It only updates the nonce to trigger a new token generation.

Usage:
    python extend_data_source.py <data_source_id> [token_lifetime_minutes]

Examples:
    python extend_data_source.py 85895e47-3096-4c47-aae8-f5a52f7b7870
    python extend_data_source.py 85895e47-3096-4c47-aae8-f5a52f7b7870 1440  # 24 hours (maximum)
"""

import sys
import json
from datetime import datetime
from token_manager import TokenManager


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python extend_data_source.py <data_source_id> [token_lifetime_minutes]"
        )
        print("\nExample:")
        print("  python extend_data_source.py 85895e47-3096-4c47-aae8-f5a52f7b7870")
        print(
            "  python extend_data_source.py 85895e47-3096-4c47-aae8-f5a52f7b7870 1440  # 24 hours (maximum)"
        )
        sys.exit(1)

    data_source_id = sys.argv[1]
    token_lifetime_minutes = (
        int(sys.argv[2]) if len(sys.argv) > 2 else 1440
    )  # Default 24 hours (max allowed)

    # Validate token lifetime
    if token_lifetime_minutes > 1440:
        print("❌ Error: Token lifetime cannot exceed 1440 minutes (24 hours)")
        print(f"   Requested: {token_lifetime_minutes} minutes")
        print("   Maximum allowed: 1440 minutes")
        sys.exit(1)

    if token_lifetime_minutes <= 0:
        print("❌ Error: Token lifetime must be positive")
        print(f"   Requested: {token_lifetime_minutes} minutes")
        sys.exit(1)

    print(f"Extending token for data source: {data_source_id}")
    print(
        f"Token lifetime: {token_lifetime_minutes} minutes ({token_lifetime_minutes / 60:.1f} hours)"
    )
    print()

    # Initialize token manager
    token_manager = TokenManager()
    
    print("Fetching fresh service app token...")
    try:
        token_manager.get_service_app_token()
        print("Service app token retrieved successfully.")
    except Exception as e:
        print(f"Failed to get service app token: {e}")
        print("\nPlease ensure your token configuration is correct.")
        print("Get a fresh personal access token from developer.webex.com")
        print("and update it in token-config.json")
        sys.exit(1)

    # Extend the data source token
    result = token_manager.extend_data_source_token(
        data_source_id, token_lifetime_minutes
    )

    if result["success"]:
        print("✅ Data source token extended successfully!")
        print(f"   New nonce: {result['nonce_updated']}")
        print(f"   Token expiry: {result['token_expiry']}")
        print(f"   Token lifetime: {result['token_lifetime_minutes']} minutes")

        # Save operation log
        log_filename = f"data_source_extend_{data_source_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_data = {
            "operation_timestamp": datetime.now().isoformat(),
            "operation_type": "extend_token",
            "data_source_id": data_source_id,
            "token_lifetime_minutes": token_lifetime_minutes,
            "result": result,
        }

        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2)

        print(f"   Operation logged to: {log_filename}")

    else:
        print("❌ Failed to extend data source token:")
        print(f"   Error: {result['error']}")
        if "status_code" in result:
            print(f"   Status code: {result['status_code']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
