# Lambda Function — Packaging and Deployment

This guide covers how to package the Lambda dependencies as an AWS Lambda Layer, build the function deployment package, and deploy both to AWS.

All commands are written for **AWS CloudShell** or any Linux bash environment.

---

## Prerequisites

- AWS CLI configured with sufficient permissions
- An S3 bucket in the same region as your Lambda function (created in Step 1)
- The Lambda execution role already created and attached (see [`IAMPolicies/`](./IAMPolicies/))

---

## Step 1 — Build and Publish the Lambda Layer

The Lambda Layer packages `pyarrow` and `pandas`, which are too large to include in the function deployment package directly.

> **Architecture note:** If your Lambda function is configured for `arm64`, replace the platform flag `manylinux_2_28_x86_64` with `manylinux_2_28_aarch64` (fallback: `manylinux2014_aarch64`).

```bash
# Create the layer build directory
mkdir -p layer_build/python
cd layer_build

# Upgrade pip
python3 -m pip install --upgrade pip

# Install pyarrow and pandas with Lambda-compatible wheels
# Primary platform (x86_64)
python3 -m pip install \
  --target python \
  --only-binary=:all: \
  --implementation cp \
  --python-version <YOUR_PYTHON_VERSION> \
  --platform manylinux_2_28_x86_64 \
  --no-cache-dir \
  pyarrow pandas \
|| python3 -m pip install \
  --target python \
  --only-binary=:all: \
  --implementation cp \
  --python-version <YOUR_PYTHON_VERSION> \
  --platform manylinux2014_x86_64 \
  --no-cache-dir \
  pyarrow pandas

# Remove unnecessary files to reduce layer size
find python -name "*.pyc" -delete
find python -name "__pycache__" -type d -exec rm -rf {} +
find python -name "tests" -type d -exec rm -rf {} +

# Create the layer zip (must contain a top-level python/ folder)
zip -r ../layer.zip python
cd ..
ls -lh layer.zip

# Set your bucket name, region, and layer name
BUCKET=<YOUR_S3_BUCKET_NAME>
REGION=<YOUR_REGION>
LAYER_NAME=<YOUR_LAYER_NAME>

# Create the S3 bucket to store the layer zip
# NOTE: If your region is us-east-1, remove the --create-bucket-configuration flag
# It is not required for us-east-1 and will cause an error if included
aws s3api create-bucket \
  --bucket $BUCKET \
  --region $REGION \
  --create-bucket-configuration LocationConstraint=$REGION

# Upload the layer zip to S3 (required for zips larger than 50 MB)
aws s3 cp layer.zip "s3://${BUCKET}/lambda-layers/${LAYER_NAME}.zip" --region $REGION

# Publish the layer from S3
aws lambda publish-layer-version \
  --layer-name $LAYER_NAME \
  --content "S3Bucket=${BUCKET},S3Key=lambda-layers/${LAYER_NAME}.zip" \
  --compatible-runtimes python<YOUR_PYTHON_VERSION> \
  --region $REGION
```

> Save the **LayerVersionArn** from the output. You will need it in Step 3.
> Example format: `arn:aws:lambda:<YOUR_REGION>:<YOUR_ACCOUNT_ID>:layer:<YOUR_LAYER_NAME>:1`

---

## Step 2 — Build the Function Deployment Package

The function package includes only `azure-eventhub` and its dependencies. `pyarrow` and `pandas` are provided by the Layer attached in Step 3.

Run the following from the directory containing `ParquetLambda.py`:

```bash
# Create the function package directory
mkdir lambda_package
cd lambda_package

# Install azure-eventhub with a urllib3 version compatible with the Lambda runtime
# urllib3 is pinned to avoid conflicts with botocore bundled in the Lambda runtime
pip3 install "urllib3==1.26.18" -t . --no-cache-dir
pip3 install azure-eventhub -t . --no-cache-dir

# Remove unnecessary files to reduce package size
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -r {} +
find . -name "tests" -type d -exec rm -r {} +
find . -name "*.dist-info" -type d -exec rm -r {} +

# Copy the Lambda function code into the package
cp ../ParquetLambda.py .

# Verify size before zipping (should be well under 250 MB unzipped)
du -sh .

# Create the deployment zip
zip -r ../ParquetLambda.zip .

# Verify final zip size (typically under 50 MB)
cd ..
du -sh ParquetLambda.zip
```

---

## Step 3 — Deploy the Function and Attach the Layer

Set `LAYER_ARN` to the **LayerVersionArn** saved from Step 1.

```bash
FUNCTION_NAME=<YOUR_LAMBDA_FUNCTION_NAME>
REGION=<YOUR_REGION>
LAYER_ARN=<YOUR_LAYER_VERSION_ARN>

# Upload the function deployment package
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://ParquetLambda.zip \
  --region $REGION

# Attach the Layer to the function
aws lambda update-function-configuration \
  --function-name $FUNCTION_NAME \
  --layers $LAYER_ARN \
  --region $REGION
```

---

## Step 4 — Configure AWS Secrets Manager

The function retrieves Azure Event Hub connection strings from AWS Secrets Manager at cold start. The secret must be structured as a JSON object with one key per log type.

The key names must match the `LOG_TYPES` defined in `ParquetLambda.py`:

```python
LOG_TYPES = [
    'cloudfront',
    'LAMBDA_EXECUTION',
    'CLOUD_TRAIL_MGMT',
    'EKS_AUDIT',
    'ROUTE53',
    'S3_DATA',
    'SH_FINDINGS',
    'VPC_FLOW',
    'WAF',
]
```

The secret value should follow this structure:

```json
{
    "cloudfront": "<Azure Event Hub primary connection string>",
    "LAMBDA_EXECUTION": "<Azure Event Hub primary connection string>",
    "CLOUD_TRAIL_MGMT": "<Azure Event Hub primary connection string>",
    "EKS_AUDIT": "<Azure Event Hub primary connection string>",
    "ROUTE53": "<Azure Event Hub primary connection string>",
    "S3_DATA": "<Azure Event Hub primary connection string>",
    "SH_FINDINGS": "<Azure Event Hub primary connection string>",
    "VPC_FLOW": "<Azure Event Hub primary connection string>",
    "WAF": "<Azure Event Hub primary connection string>"
}
```

Once the secret is created, add the secret ARN as a Lambda environment variable named `SECRET_ARN`.

> **Important:** Never store connection strings as plaintext Lambda environment variables. Always use Secrets Manager.

---

## Placeholders

Replace the following placeholders before running any commands:

| Placeholder | Description | Example |
| --- | --- | --- |
| `<YOUR_PYTHON_VERSION>` | Python version matching your Lambda runtime | `3.12` |
| `<YOUR_S3_BUCKET_NAME>` | Name of the new S3 bucket to store the layer zip | `my-lambda-layers-bucket` |
| `<YOUR_REGION>` | AWS region where Lambda is deployed | `us-east-1` |
| `<YOUR_ACCOUNT_ID>` | Your 12-digit AWS account ID | `123456789012` |
| `<YOUR_LAYER_NAME>` | Name for your Lambda Layer | `pyarrow-pandas-layer` |
| `<YOUR_LAMBDA_FUNCTION_NAME>` | Name of your Lambda function | `SecurityLakeToSentinel` |
| `<YOUR_LAYER_VERSION_ARN>` | Full ARN of the published layer from Step 1 | `arn:aws:lambda:us-east-1:123456789012:layer:pyarrow-layer:1` |
