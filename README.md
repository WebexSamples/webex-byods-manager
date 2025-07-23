# Webex BYO Data Source Management

This script manages [Webex BYODS (Bring Your Own Data Source)](https://developer.webex.com/create/docs/bring-your-own-datasource) system using the Webex Admin API.

## Main Script

**`data-sources.py`** - Unified interface for all data source operations including:

- Listing and viewing existing data sources
- Registering new data sources
- Updating existing data source configurations
- Interactive menu-driven interface

## Requirements

- Python 3.6 or higher
- A Webex Service App with appropriate scopes:
  - `spark-admin:datasource_write` (for registration and updates)
  - `spark-admin:datasource_read` (for listing/viewing)
- Access token from your Service App

## Setup

1. Create and activate a virtual environment (recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure your access token:
   - Copy the sample environment file: `cp .env.sample .env`
   - Edit the `.env` file and replace `your_service_app_token_here` with your actual Service App access token

## Usage

Run the data source manager:

```bash
python data-sources.py
```

**Features:**

- Automatically loads and displays all your data sources on startup
- Interactive menu to view/update existing data sources or register new ones
- **Schema-aware interface**: Automatically fetches and displays available schemas with friendly service type names
- Real-time refresh capability
- Unified interface for all operations
- Saves operation records automatically
- JWT token decoding for enhanced data source details

**Menu Options:**

1. **View/Update Data Sources**: Select any data source to view details and optionally update
2. **Register New Data Source**: Create a new data source with guided prompts
3. **Refresh Data Sources List**: Reload the current list from the API
4. **Quit**: Exit the application

**Optional Flags:**

```bash
# Save the initial data sources list to a JSON file
python data-sources.py --save-list
```

### Registration Process

When registering a new data source, the script will prompt for:

- **Audience**: The audience field in the JWT token (default: "BYODS")
- **Nonce**: Unique nonce used in the encryption of the JWT token (default: auto-generated UUID)
- **Schema Selection**: Interactive menu showing available schemas with service type names and descriptions (default schema provided)
- **Subject**: The subject field in the JWT token (default: "BYODS")
- **URL**: The URL of the endpoint where Webex will send the data (required, no default)
- **Token Lifetime Minutes**: The validity of the created token in minutes (default: 1440, max 1440)

**Note**: You can press Enter to accept the default values shown in brackets, or type a custom value to override the defaults.

### Update Process

When updating data sources, the process:

- Pre-fills current values as defaults (press Enter to keep)
- **Shows current schema with friendly service type name**
- Requires a new nonce for security (auto-generated UUID provided)
- Allows updating token lifetime, URL, audience, subject, schema selection, and status
- **Interactive schema selection** with numbered menu of available options
- Confirms changes before applying
- Saves operation records to JSON files automatically

## Documentation and Resources

### Comprehensive BYODS Guide

- [Bring Your Own Data Source - Complete Developer Guide](https://developer.webex.com/create/docs/bring-your-own-datasource) - Comprehensive guide covering the entire BYODS framework

### Getting Started

- [Service Apps Guide](https://developer.webex.com/docs/service-apps) - Learn how to create and configure Service Apps
- [Webex Developer Portal](https://developer.webex.com/) - Create your Service App here
- [Developer Sandbox Guide](https://developer.webex.com/docs/developer-sandbox-guide) - Set up a sandbox environment for testing
- [Contact Center Sandbox](https://developer.webex-cx.com/sandbox) - For Contact Center specific use cases

### API Documentation

- [Register a Data Source](https://developer.webex.com/admin/docs/api/v1/data-sources/register-a-data-source)
- [Retrieve All Data Sources](https://developer.webex.com/admin/docs/api/v1/data-sources/retrieve-all-data-sources)
- [Retrieve Data Source Details](https://developer.webex.com/admin/docs/api/v1/data-sources/retrieve-data-source-details)
- [Update a Data Source](https://developer.webex.com/admin/docs/api/v1/data-sources/update-a-data-source)
- [Retrieve Data Source Schemas](https://developer.webex.com/admin/docs/api/v1/data-sources/retrieve-data-source-schemas) - Browse available schemas with service types and descriptions

### Security and Authentication

- [JWT Debugger](https://jwt.io) - Tool for inspecting JWS tokens
- [JWS Token Verification Example (Java)](https://github.com/ralfschiffert/byodsJws) - Reference implementation for token validation
- [Cisco Public Key Endpoints](https://idbroker.webex.com/idb/oauth2/v2/keys/verificationjwk/) - US endpoint for JWS verification
- [EU Public Key Endpoint](https://idbroker-eu.webex.com/idb/oauth2/v2/keys/verificationjwk) - EU endpoint for JWS verification

## Response and Output

Upon successful operations, you'll receive:

- Data Source ID (for registrations)
- Status (active/disabled)
- All configured parameters
- Any error messages (if applicable)
- Enhanced JWT token information (audience, subject, expiration)

The script automatically saves all operation details to JSON files:

- **Successful registrations**: `data_source_registration_{ID}_{timestamp}.json`
- **Successful updates**: `data_source_update_{ID}_{timestamp}.json`
- **Failed operations**: `data_source_{operation}_failed_{timestamp}.json`
- **Data source lists**: `data_sources_list_{timestamp}.json` (when using --save-list flag)

These files contain:

- Operation timestamp
- Original configuration used
- Complete API response
- Success/failure status

**Note**: All JSON files are automatically excluded from git via `.gitignore` to protect sensitive information.

## Authentication

The script requires a Service App access token with the following scopes:

- **Registration and Updates**: `spark-admin:datasource_write`
- **Listing/Viewing**: `spark-admin:datasource_read`

For full functionality, use a token that has both read and write scopes.

## Error Handling

The script includes comprehensive error handling for:

- Missing or invalid access tokens
- Network connection issues
- API validation errors
- Invalid input parameters
