import boto3
import os
from botocore.exceptions import ClientError

# Load AWS config from environment
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_S3_REGION = os.getenv("AWS_S3_REGION", "us-east-1")  # default region

s3_client = boto3.client(
    "s3",
    region_name=AWS_S3_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

def upload_file_to_s3(file_path, s3_key):
    """Uploads a local file to S3 and returns its public URL."""
    try:
        s3_client.upload_file(
            Filename=file_path,
            Bucket=AWS_S3_BUCKET,
            Key=s3_key,
            ExtraArgs={"ACL": "public-read", "ContentType": "image/png"}
        )
        url = f"https://{AWS_S3_BUCKET}.s3.{AWS_S3_REGION}.amazonaws.com/{s3_key}"
        return url
    except ClientError as e:
        print(f"Error uploading {file_path} to S3: {e}")
        return None
