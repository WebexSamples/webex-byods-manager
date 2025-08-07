# Token Management

This project now includes automated token refresh functionality for Webex service app tokens.

## Setup

1. **Create token configuration file:**

   ```bash
   cp token-config.json.template token-config.json
   ```

2. **Edit the configuration file** with your actual values:

   ```json
   {
     "serviceApp": {
       "appId": "your_service_app_id",
       "clientId": "your_service_app_client_id",
       "clientSecret": "your_service_app_client_secret",
       "targetOrgId": "your_target_org_id"
     },
     "tokenManager": {
       "personalAccessToken": "your_personal_access_token_or_integration_token",
       "integration": {
         "clientId": "your_token_manager_integration_client_id",
         "clientSecret": "your_token_manager_integration_client_secret",
         "refreshToken": "your_token_manager_integration_refresh_token"
       }
     }
   }
   ```

   **Note**: The `integration` section is optional and only needed for OAuth-based personal token refresh (Option B2).

## How to get the required values:

The configuration requires two different sets of credentials:

### 1. Service App Information (`serviceApp` section)

These are the credentials for your **existing Webex service app** that manages data sources:

- **appId**: Found in your Webex service app configuration (format: `Y2lzY29zcGFyazovL3VzL0FQUExJQ0FUSU9OL...`)
- **clientId**: Your **service app's** Client ID
- **clientSecret**: Your **service app's** Client Secret
- **targetOrgId**: The organization ID where the service app operates

### 2. Token Manager Authentication (`tokenManager` section)

This is the token used to **refresh** your service app tokens (choose one method):

#### Option A: Quick Start - Developer Portal Token (Temporary)

1. Go to [developer.webex.com](https://developer.webex.com)
2. Sign in and click on your profile in the top right
3. Copy your "Personal Access Token"
4. Use this token in the `personalAccessToken` field

⚠️ **Note**: Portal tokens expire every 12 hours and are meant for testing only.

#### Option B: Production - Create a Dedicated Integration (Recommended)

1. Go to [developer.webex.com](https://developer.webex.com)
2. Click "Create a New App" → "Create an Integration"
3. Fill in the details:
   - **Integration name**: "Token Refresh Helper" (or your preferred name)
   - **Description**: "Integration for refreshing service app tokens"
   - **Redirect URI**: `http://localhost:3000/callback`
   - **Scopes**: Select `spark:applications_token`
4. Save the integration and copy the **Client ID** and **Client Secret**
5. **Option B1 - Manual Setup**: Use the test token provided in the `personalAccessToken` field
6. **Option B2 - OAuth Setup (Recommended)**: Run `python setup_oauth.py` for automated OAuth flow

✅ **Recommended**: The OAuth setup (B2) provides automatic refresh of your personal access token and is suitable for production use.

## OAuth Setup (Advanced)

For production environments, you can set up OAuth to automatically refresh your personal access token:

### Prerequisites

- Token Manager Integration created with:
  - Scope: `spark:applications_token`
  - Redirect URI: `http://localhost:3000/callback`

### Setup Process

```bash
# Activate virtual environment
source venv/bin/activate

# Run OAuth setup helper
python setup_oauth.py
```

This will:

1. Open your browser for authorization
2. Exchange the authorization code for tokens
3. Update your `token-config.json` with OAuth credentials
4. Enable automatic personal token refresh

## Development Approaches

### Quick Start Approach (Option A)

- **Time to setup**: ~2 minutes
- **Token lifespan**: 12 hours
- **Best for**: Testing, proof of concept, development
- **Maintenance**: Manual token refresh every 12 hours from developer portal

### Production Approach (Option B)

- **Time to setup**: ~10 minutes (includes OAuth setup)
- **Token lifespan**: Much longer (typically months)
- **Best for**: Production deployments, automated systems
- **Maintenance**: Minimal - tokens refresh automatically
- **Variants**:
  - **B1 (Manual)**: Use integration test token (needs periodic manual refresh)
  - **B2 (OAuth)**: Fully automated with personal token auto-refresh

## Usage

### Automatic Token Refresh

The main `data-sources.py` script will automatically check token validity and refresh if needed when run.

**Smart Refresh Strategy:**

1. **First**: Tries to use the stored refresh token (faster, no personal token needed)
2. **Fallback**: Uses personal access token if refresh token fails or is unavailable
3. **Validation**: Uses the `/v1/dataSources` endpoint to check service app token validity

### Manual Token Refresh

You can manually refresh tokens anytime:

```bash
# Activate virtual environment first
source venv/bin/activate

# Then run the refresh script
python refresh_token.py
```

### Token Manager API

You can also use the TokenManager class directly in your code:

```python
# Activate virtual environment first
source venv/bin/activate

from token_manager import TokenManager

# Initialize the token manager
token_manager = TokenManager()

# Check if current token is valid
if not token_manager.is_token_valid():
    # Refresh the token
    new_token = token_manager.refresh_token()
    print(f"New token: {new_token}")
```

## Security Notes

- The `token-config.json` file is automatically excluded from git
- Keep your personal access token secure and never commit it to version control
- **Portal tokens** (Option A): Expire every 12 hours, good for development only
- **Integration tokens** (Option B): Last much longer, suitable for production
- The personal access token must have `spark:applications_token` scope
- Service app tokens are automatically updated in the `.env` file as:
  - `WEBEX_SERVICE_APP_ACCESS_TOKEN`: The active service app token
  - `WEBEX_SERVICE_APP_REFRESH_TOKEN`: Used for automatic token refresh
- **Refresh tokens** are automatically stored and used for efficient token refresh
- Consider using environment variables for the token config in production environments

## How Refresh Tokens Work

The system manages multiple types of tokens for maximum efficiency:

### Service App Tokens

- **Access Token**: Used for data source API calls → `WEBEX_SERVICE_APP_ACCESS_TOKEN`
- **Refresh Token**: Used to get new service app access tokens → `WEBEX_SERVICE_APP_REFRESH_TOKEN`

### Token Manager Tokens (for refreshing service app tokens)

- **Personal Access Token**: Used to authenticate service app token refresh requests
- **OAuth Refresh Token**: Used to automatically refresh the personal access token (optional)

**Multi-Level Refresh Strategy:**

1. **Service App Token Expired**: Use service app refresh token → New service app access token
2. **Service App Refresh Token Expired**: Use personal access token → New service app tokens
3. **Personal Access Token Expired**: Use OAuth refresh token → New personal access token
4. **OAuth Refresh Token Expired**: Manual re-authorization required

**Benefits:**

- Faster refresh (service app refresh tokens used first)
- Automatic personal token refresh (with OAuth setup)
- Minimal manual intervention required
- Production-ready automation

## API Reference

The token refresh uses the Webex Applications API:

```
POST https://webexapis.com/v1/applications/{serviceApp.appId}/token
Authorization: Bearer {tokenManager.personalAccessToken}
```

With the following payload (using **service app** credentials):

```json
{
  "clientId": "serviceApp.clientId",
  "clientSecret": "serviceApp.clientSecret",
  "targetOrgId": "serviceApp.targetOrgId"
}
```

**Note**: The API call is authenticated with your `tokenManager.personalAccessToken` but requests a new token for your `serviceApp` credentials.

## Troubleshooting

### "Authentication failed" or 401 errors

Your **token manager** personal access token has likely expired:

**If using Portal Token (Option A):**

1. Go to [developer.webex.com](https://developer.webex.com)
2. Sign in and get a fresh token from your profile
3. Update `tokenManager.personalAccessToken` in `token-config.json`

**If using Integration Token (Option B):**

1. Your integration's OAuth token has expired
2. Generate a new access token through your OAuth flow
3. Update `tokenManager.personalAccessToken` in `token-config.json`

### "No access token in API response"

- Verify your **service app** credentials in the `serviceApp` section are correct:
  - `serviceApp.appId`, `serviceApp.clientId`, `serviceApp.clientSecret`
- Ensure the `serviceApp.targetOrgId` matches your service app's organization
- Check that your **token manager** `personalAccessToken` has `spark:applications_token` scope

### Script fails to find config file

- Ensure `token-config.json` exists in the same directory as the scripts
- Copy from `token-config.json.template` if needed
- Check file permissions
