# Data Ingestion

This directory contains data ingestion modules for the Cloud Cost Optimizer.

## Modules

### Synthetic Ingestion (`synthetic_ingest.py`)

Generates synthetic EC2 instances and metrics for local development and demos.

**Usage:**
```bash
python -m app.ingestion.synthetic_ingest
```

### AWS CloudWatch Ingestion (`aws_cloudwatch_ingest.py`)

Pulls real EC2 instance metrics from AWS CloudWatch and stores them in the database.

## AWS CloudWatch Ingestion Setup

### Prerequisites

1. **AWS Credentials**: Configure AWS credentials using one of these methods:
   - Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - AWS credentials file: `~/.aws/credentials`
   - IAM role (if running on EC2)

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Set the following environment variables:

```bash
# Required: AWS region
export AWS_REGION=us-west-2

# Required: Comma-separated EC2 instance IDs to monitor
export AWS_INSTANCE_IDS=i-0123456789abcdef0,i-0fedcba9876543210
```

### Usage

```bash
cd backend

# Configure AWS credentials and instance IDs
export AWS_REGION=us-west-2
export AWS_INSTANCE_IDS=i-0123456789abcdef0,i-0fedcba9876543210

# Run ingestion (pulls last 24 hours of metrics)
python -m app.ingestion.aws_cloudwatch_ingest
```

### What It Does

1. **Connects to AWS CloudWatch** using boto3
2. **Fetches metrics** for each specified EC2 instance:
   - `CPUUtilization` (Average per hour)
   - `NetworkIn` (Sum per hour, in bytes)
   - `NetworkOut` (Sum per hour, in bytes)
3. **Time range**: Last 24 hours by default (configurable in code)
4. **Storage**: Metrics are stored in the `metrics` table
5. **Instance creation**: If an EC2 instance ID doesn't exist in the `instances` table, a new row is automatically created

### Metrics Retrieved

- **CPUUtilization**: Percentage (0-100)
- **NetworkIn**: Total bytes received in the hour
- **NetworkOut**: Total bytes sent in the hour
- **Memory**: Not available via CloudWatch for EC2 (set to NULL)

### Example Output

```
============================================================
📊 AWS CloudWatch Metrics Ingestion
============================================================
Region: us-west-2
Instance IDs: i-0123456789abcdef0, i-0fedcba9876543210
Lookback: 24 hours
============================================================

✅ CloudWatch client initialized

📦 Processing instance: i-0123456789abcdef0
   🔄 Fetching metrics from CloudWatch...
   ✅ Retrieved 24 datapoints
   💾 Writing metrics to database...
   ✅ Inserted/updated 24 metrics

📦 Processing instance: i-0fedcba9876543210
   ⚠️  No Instance row found for i-0fedcba9876543210, creating new entry...
   ✅ Created Instance row (id: 42)
   🔄 Fetching metrics from CloudWatch...
   ✅ Retrieved 24 datapoints
   💾 Writing metrics to database...
   ✅ Inserted/updated 24 metrics

============================================================
✅ Ingested CloudWatch metrics for 2 instance(s) (last 24h)
   Total metrics inserted/updated: 48
============================================================
```

### Notes

- **Duplicate handling**: If a metric already exists for the same (instance_id, timestamp), it will be updated
- **Missing metrics**: If CloudWatch doesn't have data for a metric, it will be set to 0 or None
- **Error handling**: Gracefully handles missing instances, API errors, and network issues
- **Performance**: Uses hourly aggregation (Period=3600) to reduce API calls and data volume

### Troubleshooting

**Error: "AWS credentials not found"**
- Ensure AWS credentials are configured via environment variables or `~/.aws/credentials`
- Verify credentials have CloudWatch read permissions

**Error: "No metrics found"**
- Check that the instance IDs are correct
- Verify instances are running and have CloudWatch metrics enabled
- CloudWatch metrics may take a few minutes to appear after instance launch

**Error: "Access Denied"**
- Ensure your AWS credentials have `cloudwatch:GetMetricStatistics` permission
- Required IAM policy: `AmazonCloudWatchReadOnlyAccess` or custom policy with CloudWatch read permissions





