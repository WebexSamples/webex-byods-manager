# AWS Lambda Deployment Guide

This guide provides step-by-step instructions for deploying the Webex BYODS Token Manager as an AWS Lambda function with automatic hourly execution.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [OAuth Setup (REQUIRED)](#oauth-setup-required)
3. [AWS Secrets Manager Setup](#aws-secrets-manager-setup)
4. [Create IAM Role](#create-iam-role)
5. [Create Lambda Function](#create-lambda-function)
6. [Configure EventBridge Trigger](#configure-eventbridge-trigger)
7. [Testing](#testing)
8. [Set Up Monitoring and Alerts](#set-up-monitoring-and-alerts)
9. [Monitoring Dashboard](#monitoring-dashboard)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have:

- AWS Account with appropriate permissions
- AWS CLI installed and configured (optional, but recommended)
- Your Webex service app credentials:
  - Service App ID
  - Service App Client ID
  - Service App Client Secret
  - Target Organization ID
- **OAuth Integration configured** (REQUIRED for automated Lambda deployment)
  - Without this, personal access tokens expire every 12 hours and Lambda will fail
  - Run `python setup_oauth.py` locally to set this up
  - See [OAuth Setup](#oauth-setup-required) below
- Your Webex data source ID to manage

## OAuth Setup (REQUIRED)

### Before Creating AWS Resources

⚠️ **IMPORTANT**: Lambda requires OAuth to run unattended. Without it, your personal access token expires every 12 hours and Lambda will fail.

**On your local machine, run:**

```bash
# Activate virtual environment
source venv/bin/activate

# Run OAuth setup
python setup_oauth.py
```

This will:

1. Open your browser for OAuth authorization
2. Exchange authorization code for tokens
3. Save OAuth credentials to `token-config.json`

**What you'll get:**

- `oauthClientId` - Integration client ID
- `oauthClientSecret` - Integration client secret
- `oauthRefreshToken` - Long-lived refresh token (months/years)

**Why this is required:**

- Personal access tokens from developer.webex.com expire every 12 hours
- OAuth refresh tokens last months/years
- Lambda automatically refreshes personal tokens using OAuth
- Enables true "set and forget" operation

**See [TOKEN_MANAGEMENT.md](../TOKEN_MANAGEMENT.md) for detailed OAuth setup instructions.**

## AWS Secrets Manager Setup

### Step 1: Create Secret in AWS Secrets Manager

1. Navigate to **AWS Secrets Manager** in the AWS Console
2. Click **Store a new secret**
3. Select **Other type of secret**
4. Choose **Plaintext** tab
5. **Copy and paste the entire contents of your local `token-config.json` file**

After running `setup_oauth.py`, your `token-config.json` will look like this:

```json
{
  "serviceApp": {
    "appId": "Y2lzY29zcGFyazovL3VzL0FQUExJQ0FUSU9OL...",
    "clientId": "C1a2b3c4d5e6f7g8h9i0...",
    "clientSecret": "a1b2c3d4e5f6g7h8i9j0...",
    "targetOrgId": "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8..."
  },
  "tokenManager": {
    "personalAccessToken": "ZDYxNjc5MzgtNjE2Yy00...",
    "oauthClientId": "C9z8y7x6w5v4u3t2s1r0...",
    "oauthClientSecret": "z9y8x7w6v5u4t3s2r1q0...",
    "oauthRefreshToken": "MmY0ZjBjMzMtYzA5Yy00..."
  }
}
```

**✅ Just copy this entire file and paste it into Secrets Manager - no manual editing needed!**

**Field Descriptions:**

- **serviceApp**: Credentials for your Webex service app

  - `appId`: Your service app's application ID
  - `clientId`: Service app client ID
  - `clientSecret`: Service app client secret
  - `targetOrgId`: Organization ID where the service app operates

- **tokenManager**: Credentials for refreshing service app tokens
  - `personalAccessToken`: Current personal access token (will auto-refresh)
  - `oauthClientId`: OAuth integration client ID (from setup_oauth.py)
  - `oauthClientSecret`: OAuth integration client secret (from setup_oauth.py)
  - `oauthRefreshToken`: OAuth refresh token (from setup_oauth.py)

**Important Notes:**

- ⚠️ **All OAuth fields are REQUIRED** for production Lambda deployment
- Without OAuth, personal tokens expire every 12 hours causing Lambda to fail
- Run `setup_oauth.py` locally first, then copy values from `token-config.json`
- Service app tokens are NOT stored - they're fetched fresh on every Lambda execution

6. Click **Next**
7. Set **Secret name**: `webex-byods-credentials` (or your preferred name)
8. Add description: "Webex BYODS Token Manager credentials"
9. Click **Next** through the remaining steps
10. Click **Store**

**Important:** Copy the **Secret ARN** - you'll need it for the IAM policy.

## Create IAM Role

### Step 2: Create IAM Policy for Secrets Manager Access

1. Navigate to **IAM** → **Policies** in the AWS Console
2. Click **Create policy**
3. Select **JSON** tab
4. Paste the following policy (**replace `YOUR_SECRET_ARN` with the ARN from Step 1**):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "YOUR_SECRET_ARN"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

**Example**: If your secret ARN is `arn:aws:secretsmanager:us-east-1:123456789012:secret:webex-byods-credentials-AbCdEf`, use that full ARN.

5. Click **Next**
6. Set **Policy name**: `WebexBYODSLambdaPolicy`
7. Add description: "Allows Lambda to access Webex BYODS credentials and write logs"
8. Click **Create policy**

### Step 3: Create IAM Role for Lambda

1. Navigate to **IAM** → **Roles**
2. Click **Create role**
3. Select **AWS service** as trusted entity type
4. Choose **Lambda** as the use case
5. Click **Next**
6. Attach the policy you just created: `WebexBYODSLambdaPolicy`
7. Click **Next**
8. Set **Role name**: `WebexBYODSLambdaRole`
9. Add description: "Execution role for Webex BYODS token manager Lambda"
10. Click **Create role**

## Create Lambda Function

### Step 4: Create the Deployment Package

On your local machine, run the packaging script:

```bash
cd deploy
chmod +x package_lambda.sh
./package_lambda.sh
```

This creates `lambda_deployment.zip` containing all necessary code and dependencies.

### Step 5: Create Lambda Function

1. Navigate to **AWS Lambda** in the AWS Console
2. Click **Create function**
3. Choose **Author from scratch**
4. Configure the function:
   - **Function name**: `webex-byods-token-extender`
   - **Runtime**: Python 3.14
   - **Architecture**: x86_64
   - **Execution role**: Use an existing role → `WebexBYODSLambdaRole`
5. Click **Create function**

### Step 6: Upload Deployment Package

1. In the **Code** tab, click **Upload from** → **.zip file**
2. Click **Upload** and select `lambda_deployment.zip`
3. Click **Save**

### Step 7: Configure Environment Variables

1. Navigate to **Configuration** → **Environment variables**
2. Click **Edit** → **Add environment variable**
3. Add the following variables:

| Key                      | Value                     | Description                                            |
| ------------------------ | ------------------------- | ------------------------------------------------------ |
| `DATA_SOURCE_ID`         | Your data source ID       | The Webex BYODS data source to manage                  |
| `SECRET_NAME`            | `webex-byods-credentials` | Name of the secret in Secrets Manager                  |
| `TOKEN_LIFETIME_MINUTES` | `1440`                    | Token lifetime in minutes (optional, defaults to 1440) |

**Note**: `AWS_REGION` is automatically set by Lambda to match the region where your function is deployed. Do not set it manually.

4. Click **Save**

#### Memory and Timeout

1. Navigate to **Configuration** → **General configuration**
2. Click **Edit**
3. Set:
   - **Memory**: 256 MB
   - **Timeout**: 1 minute
4. Click **Save**

## Configure EventBridge Trigger

### Step 9: Create Hourly Schedule

1. In your Lambda function, click **Add trigger**
2. Select **EventBridge (CloudWatch Events)**
3. Choose **Create a new rule**
4. Configure the rule:
   - **Rule name**: `webex-byods-hourly-refresh`
   - **Rule description**: "Triggers BYODS token refresh every hour"
   - **Rule type**: Schedule expression
   - **Schedule expression**: `cron(0 * * * ? *)`
     - This runs at the top of every hour (00:00, 01:00, 02:00, etc.)
5. Click **Add**

**Alternative Schedules:**

- Every 30 minutes: `cron(0,30 * * * ? *)`
- Every 12 hours: `cron(0 0,12 * * ? *)`
- Once daily at midnight UTC: `cron(0 0 * * ? *)`
- Custom: See [AWS Cron Expressions](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html#eb-cron-expressions)

## Testing

### Step 10: Test the Lambda Function

Before setting up monitoring, test the Lambda function to ensure it works and to create the CloudWatch log group.

1. In your Lambda function, click the **Test** tab
2. Click **Create new event**
3. Set:
   - **Event name**: `test-event`
   - **Template**: `hello-world`
4. Keep the default JSON (the event data is not used)
5. Click **Save**
6. Click **Test**

#### Expected Success Response

```json
{
  "statusCode": 200,
  "body": "{\"success\": true, \"message\": \"Data source token extended successfully\", ...}"
}
```

#### Check CloudWatch Logs

1. Navigate to **Monitor** → **Logs** → **View logs in CloudWatch**
2. Click the latest log stream
3. Look for:
   - "Starting BYODS token extension Lambda function"
   - "Data source token extended successfully"
   - Token expiry time and new nonce

✅ **Your Lambda function is now working!** The test also created the CloudWatch log group needed for monitoring.

## Set Up Monitoring and Alerts

### Step 11: Create SNS Topic for Alerts

Critical failures (like OAuth refresh token expiration) can prevent token extension. Set up alerts to be notified when issues occur.

#### Create SNS Topic

**Via AWS Console:**

1. Navigate to **Amazon SNS** in the AWS Console
2. Click **Topics** → **Create topic**
3. Configure:
   - **Type**: Standard
   - **Name**: `webex-byods-alerts`
   - **Display name**: `Webex BYODS Alerts`
4. Click **Create topic**
5. Copy the **Topic ARN** (you'll need it for alarms)

**Via AWS CLI:**

```bash
aws sns create-topic --name webex-byods-alerts
```

#### Subscribe to Alerts

**Via AWS Console:**

1. In your SNS topic, click **Create subscription**
2. Configure:
   - **Protocol**: Email
   - **Endpoint**: `your-email@example.com`
3. Click **Create subscription**
4. **Check your email** and click the confirmation link

**Via AWS CLI:**

```bash
# Create subscription
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:webex-byods-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Check your email and confirm the subscription
```

### Step 12: Create CloudWatch Alarm for Lambda Errors

Monitor all Lambda execution failures.

**Via AWS Console:**

1. Navigate to **CloudWatch** → **Alarms** → **Create alarm**
2. Click **Select metric**
3. Choose **Lambda** → **By Function Name**
4. Find your function `webex-byods-token-extender`
5. Select the **Errors** metric
6. Click **Select metric**
7. Configure the metric:
   - **Statistic**: Sum
   - **Period**: 5 minutes
8. Configure conditions:
   - **Threshold type**: Static
   - **Whenever Errors is...**: Greater than
   - **than...**: 0
9. Click **Next**
10. Configure actions:
    - **Alarm state trigger**: In alarm
    - **Select an SNS topic**: webex-byods-alerts
11. Click **Next**
12. Set alarm name:
    - **Alarm name**: `webex-byods-lambda-errors`
    - **Alarm description**: `Alert when Webex BYODS Lambda function fails`
13. Click **Next** → **Create alarm**

**Via AWS CLI (works even before first invocation):**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name webex-byods-lambda-errors \
  --alarm-description "Alert when Webex BYODS Lambda function fails" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=webex-byods-token-extender \
  --alarm-actions arn:aws:sns:YOUR_REGION:YOUR_ACCOUNT_ID:webex-byods-alerts
```

Replace `YOUR_REGION` and `YOUR_ACCOUNT_ID` with your actual values.

### Step 13: Create Log Metric Filter for OAuth Failures

Monitor for OAuth refresh token expiration specifically.

**Via AWS Console:**

1. Navigate to **CloudWatch** → **Log groups**
2. Find `/aws/lambda/webex-byods-token-extender`
3. Click on the log group
4. Go to **Metric filters** tab
5. Click **Create metric filter**
6. Configure filter pattern:
   - **Filter pattern**: `"OAuth refresh token expired"`
7. Click **Test pattern** to verify (optional)
8. Click **Next**
9. Configure metric:
   - **Filter name**: `OAuthRefreshTokenExpired`
   - **Metric namespace**: `WebexBYODS`
   - **Metric name**: `OAuthRefreshFailures`
   - **Metric value**: `1`
   - **Default value**: Leave blank
10. Click **Next** → **Create metric filter**

**Via AWS CLI:**

```bash
aws logs put-metric-filter \
  --log-group-name /aws/lambda/webex-byods-token-extender \
  --filter-name OAuthRefreshTokenExpired \
  --filter-pattern '"OAuth refresh token expired"' \
  --metric-transformations \
    metricName=OAuthRefreshFailures,metricNamespace=WebexBYODS,metricValue=1
```

### Step 14: Create Alarm for OAuth Failures

**Via AWS Console:**

1. Navigate to **CloudWatch** → **Alarms** → **Create alarm**
2. Click **Select metric**
3. Choose **Custom namespaces** → **WebexBYODS**
4. Select **Metrics with no dimensions**
5. Select **OAuthRefreshFailures**
6. Click **Select metric**
7. Configure the metric:
   - **Statistic**: Sum
   - **Period**: 5 minutes
8. Configure conditions:
   - **Threshold type**: Static
   - **Whenever OAuthRefreshFailures is...**: Greater than
   - **than...**: 0
9. Click **Next**
10. Configure actions:
    - **Alarm state trigger**: In alarm
    - **Select an SNS topic**: webex-byods-alerts
11. Click **Next**
12. Set alarm name:
    - **Alarm name**: `webex-byods-oauth-expired`
    - **Alarm description**: `CRITICAL: OAuth refresh token has expired - manual action required`
13. Click **Next** → **Create alarm**

**Via AWS CLI:**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name webex-byods-oauth-expired \
  --alarm-description "CRITICAL: OAuth refresh token expired - requires manual re-authorization" \
  --metric-name OAuthRefreshFailures \
  --namespace WebexBYODS \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:webex-byods-alerts
```

### Monitoring Summary

You now have the following alerts configured:

| Alert             | Trigger                      | Action Required                                         |
| ----------------- | ---------------------------- | ------------------------------------------------------- |
| **Lambda Errors** | Any Lambda execution failure | Check CloudWatch Logs for details                       |
| **OAuth Expired** | OAuth refresh token expired  | Run `setup_oauth.py` locally and update Secrets Manager |

**Expected Notifications:**

- **Immediate action**: OAuth refresh token expired (every few months/years)
- **Investigation**: Lambda errors (check logs for root cause)
- **No alerts**: Normal operation ✅

**Additional Cost:**

- SNS: First 1,000 emails/month FREE
- CloudWatch Alarms: $0.10/alarm/month × 2 = **$0.20/month**

## Monitoring Dashboard

### CloudWatch Metrics

Monitor your Lambda function:

1. Navigate to **CloudWatch** → **Metrics** → **Lambda**
2. Key metrics to watch:
   - **Invocations**: Should match your schedule (24/day for hourly)
   - **Errors**: Should be 0
   - **Duration**: Typically 1-3 seconds
   - **Throttles**: Should be 0

### CloudWatch Alarms

Set up alarms for failures:

1. Navigate to **CloudWatch** → **Alarms** → **Create alarm**
2. Select **Lambda** → **By Function Name** → **Errors**
3. Set condition: **Greater than** 0
4. Configure SNS notification to email you on failures

### Logs Insights Queries

Useful CloudWatch Logs Insights queries:

**Find all successful executions:**

```sql
fields @timestamp, @message
| filter @message like /successfully/
| sort @timestamp desc
```

**Find all errors:**

```sql
fields @timestamp, @message
| filter @message like /error/ or @message like /failed/
| sort @timestamp desc
```

**Check token expiry times:**

```sql
fields @timestamp, @message
| filter @message like /token_expiry/
| parse @message /token_expiry": "(?<expiry>[^"]+)"/
| sort @timestamp desc
```

## Troubleshooting

### Common Issues

#### Error: "Unable to import module 'lambda_function'"

**Cause:** The deployment ZIP is missing `lambda_function.py` or dependencies

**Solution:**

1. Verify you ran `./deploy/package_lambda.sh` successfully
2. Check that `lambda_deployment.zip` contains `lambda_function.py`
3. Re-upload the ZIP file to Lambda
4. Test again

#### Error: "Secret 'webex-byods-credentials' not found"

**Cause:** Secret name mismatch or wrong region

**Solution:**

- Verify `SECRET_NAME` environment variable matches the actual secret name
- Ensure `AWS_REGION` matches where you created the secret
- Check IAM role has permission to access the secret

#### Error: "Access denied to secret"

**Cause:** IAM role lacks permissions

**Solution:**

- Verify the Lambda execution role has `secretsmanager:GetSecretValue` permission
- Check the secret ARN in the IAM policy is correct
- Ensure the policy is attached to the Lambda execution role

#### Error: "Failed to refresh service app token"

**Cause:** Expired personal access token or invalid credentials

**Solution:**

- Get a fresh personal access token from developer.webex.com
- Update the secret in Secrets Manager:
  1. Go to Secrets Manager → Your secret → **Retrieve secret value**
  2. Click **Edit**
  3. Update `tokenManager.personalAccessToken`
  4. Click **Save**

#### Alert: "OAuth refresh token expired"

**Cause:** The OAuth refresh token has expired (typically after months/years)

**Solution:**

1. On your local machine, run: `python setup_oauth.py`
2. Complete the OAuth flow in your browser
3. Copy the new refresh token from `token-config.json`
4. Update Secrets Manager:
   - Navigate to your secret `webex-byods-credentials`
   - Click **Retrieve secret value** → **Edit**
   - Update `tokenManager.oauthRefreshToken` with the new value
   - Click **Save**
5. Test the Lambda function to verify it works

**Prevention:**

- OAuth refresh tokens typically last months to years
- When you receive this alert, it's a routine maintenance task
- The alert ensures you're notified before data source tokens fail to extend

#### Error: "DATA_SOURCE_ID environment variable is required"

**Cause:** Missing environment variable

**Solution:**

- Add `DATA_SOURCE_ID` environment variable in Lambda configuration
- Set it to your Webex BYODS data source ID

#### Lambda times out

**Cause:** Network issues or API slowness

**Solution:**

- Increase timeout to 2-3 minutes in Lambda configuration
- Check CloudWatch logs for specific error
- Verify VPC configuration if Lambda is in a VPC

#### Token not being refreshed

**Cause:** Schedule not configured or disabled

**Solution:**

- Check EventBridge rule is enabled
- Verify the rule target points to your Lambda function
- Check CloudWatch metrics for invocations

### Debug Mode

To get more detailed logs, you can temporarily modify the Lambda handler:

1. Go to Lambda function → **Code** tab
2. Temporarily change logging level (if you add this capability)
3. Re-test and check CloudWatch logs
4. Remember to revert changes

### Validate Secret Structure

Use AWS CLI to verify your secret format:

```bash
aws secretsmanager get-secret-value \
    --secret-id webex-byods-credentials \
    --query SecretString \
    --output text | jq .
```

Should show the complete JSON structure with all required fields.

## Cost Estimation

**Monthly costs (approximate, us-east-1 region):**

- **Lambda**: ~$0.00

  - 720 invocations/month (hourly)
  - ~2 seconds duration @ 256MB
  - Well within free tier (1M requests/month)

- **Secrets Manager**: ~$0.40/month

  - $0.40 per secret per month
  - API calls included in secret cost

- **CloudWatch Logs**: ~$0.01/month

  - Minimal log data
  - Free tier: 5GB ingestion

- **CloudWatch Alarms**: ~$0.20/month
  - $0.10 per alarm per month
  - 2 alarms (Lambda errors + OAuth failures)

### Total estimated cost: ~$0.61/month

## Security Best Practices

1. **Rotate Credentials Regularly**

   - Update personal access token every 90 days
   - Use OAuth integration for automatic rotation when possible

2. **Least Privilege IAM**

   - Grant only necessary permissions
   - Use specific secret ARNs, not wildcards

3. **Enable CloudTrail**

   - Monitor secret access
   - Track Lambda invocations

4. **Use VPC (Optional)**

   - For additional network isolation
   - Requires VPC endpoints for Secrets Manager

5. **Enable Encryption**
   - Secrets Manager encrypts by default with AWS KMS
   - Consider using customer-managed KMS key for compliance

## Updating the Lambda Function

To update the code:

1. Make changes locally to `lambda_function.py` or `token_manager.py`
2. Run the packaging script: `./deploy/package_lambda.sh`
3. Upload new `lambda_deployment.zip` to Lambda
4. Test the function

## Cleanup / Removal

To remove the Lambda function:

1. Delete EventBridge rule: `webex-byods-hourly-refresh`
2. Delete Lambda function: `webex-byods-token-extender`
3. Delete IAM role: `WebexBYODSLambdaRole`
4. Delete IAM policy: `WebexBYODSLambdaPolicy`
5. Delete Secrets Manager secret: `webex-byods-credentials` (30-day recovery period)

## Support and Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [EventBridge Schedules](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html)
- [Webex BYODS Documentation](https://developer.webex.com/create/docs/bring-your-own-datasource)
- Project README: [../README.md](../README.md)
- Token Management Guide: [../TOKEN_MANAGEMENT.md](../TOKEN_MANAGEMENT.md)
