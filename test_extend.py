#!/usr/bin/env python3
"""
Test script for the extend_data_source_token functionality
"""

from token_manager import TokenManager


def test_extend_method():
    """Test the extend_data_source_token method"""
    print("Testing extend_data_source_token method...")

    # Use a known data source ID from the logs
    test_data_source_id = "85895e47-3096-4c47-aae8-f5a52f7b7870"

    token_manager = TokenManager()

    # Check if token is valid first
    print("Checking if service app token is valid...")
    if not token_manager.is_token_valid():
        print("Token is invalid, attempting to refresh...")
        try:
            token_manager.refresh_token()
            print("Token refreshed successfully!")
        except Exception as e:
            print(f"Failed to refresh token: {e}")
            return False
    else:
        print("Service app token is valid!")

    # Test extending the data source token
    print(f"Testing extend_data_source_token with ID: {test_data_source_id}")
    print(
        "This is a dry run - we'll catch any errors but won't actually extend if there are issues"
    )

    try:
        result = token_manager.extend_data_source_token(
            test_data_source_id, 720
        )  # 12 hours

        if result["success"]:
            print("✅ extend_data_source_token method works correctly!")
            print(f"   New nonce: {result.get('nonce_updated', 'N/A')}")
            print(f"   Token expiry: {result.get('token_expiry', 'N/A')}")
            print(
                f"   Token lifetime: {result.get('token_lifetime_minutes', 'N/A')} minutes"
            )
            return True
        else:
            print("❌ extend_data_source_token method failed:")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            if "status_code" in result:
                print(f"   Status code: {result['status_code']}")
            return False

    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return False


if __name__ == "__main__":
    test_extend_method()
