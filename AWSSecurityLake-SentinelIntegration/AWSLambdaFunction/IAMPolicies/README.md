# IAM Policies — Lambda Execution Role

This folder contains the four IAM policies required for the AWS Lambda execution role used in the AWS Security Lake to Microsoft Sentinel integration.

Each policy follows the principle of least privilege and is scoped to only the permissions the Lambda function requires to operate.

---

## Policies

### `lambda-s3-security-lake.json`

Grants the Lambda function read access to Parquet files stored in the AWS Security Lake S3 bucket, and write access to update S3 object metadata used for idempotency tracking (to prevent duplicate processing of the same file).

**Actions:** `s3:GetObject`, `s3:HeadObject`, `s3:CopyObject`

---

### `lambda-secrets-manager.json`

Grants the Lambda function permission to retrieve the Azure Event Hub connection strings stored in AWS Secrets Manager. Connection strings are stored as a single JSON secret with one key per log type, and retrieved at Lambda cold start.

**Actions:** `secretsmanager:GetSecretValue`

---

### `lambda-sqs-security-lake.json`

Grants the Lambda function permission to consume messages from the Amazon SQS queue that receives S3 event notifications from AWS Security Lake. The condition ensures the queue must belong to the same AWS account as the Lambda function.

**Actions:** `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes`

---

### `lambda-cloudwatch-logs.json`

Grants the Lambda function permission to create and write to its CloudWatch Log Group. This is required for Lambda execution logging and is scoped to the specific Lambda function's log group.

**Actions:** `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

---

## How to Attach These Policies to the Lambda Execution Role

1. Open the [AWS IAM Console](https://console.aws.amazon.com/iam/)
2. Navigate to **Roles** and select the execution role attached to your Lambda function
3. Click **Add permissions** → **Create inline policy**
4. Select the **JSON** tab and paste the content of each policy file
5. Name the policy consistently — for example:
   - `lambda-securitylake-sentinel-s3`
   - `lambda-securitylake-sentinel-secrets`
   - `lambda-securitylake-sentinel-sqs`
   - `lambda-securitylake-sentinel-logs`
6. Click **Create policy**
7. Repeat for each of the four policy files

> **Note:** Do not use `AmazonS3FullAccess` or other broad AWS managed policies in place of the scoped S3 policy. The Lambda function only requires access to the Security Lake bucket and should not have write or delete permissions on S3.

---

## Placeholders

Before applying these policies, replace the following placeholders in each JSON file with values from your environment:

| Placeholder | Description | Example |
| --- | --- | --- |
| `<YOUR_ACCOUNT_ID>` | Your 12-digit AWS account ID | `123456789012` |
| `<YOUR_REGION>` | AWS region where Security Lake and Lambda are deployed | `us-east-1` |
| `<YOUR_SECRET_NAME>` | The name prefix of your Secrets Manager secret | `sentinel-eventhub-secret` |
| `<YOUR_LAMBDA_FUNCTION_NAME>` | The name of your Lambda function | `SecurityLakeToSentinel` |

> **Important:** Never commit real account IDs, secret ARNs, or credentials to a public repository. The placeholder values above are intentionally generic and must be replaced only in your local AWS environment, not in version-controlled files.
