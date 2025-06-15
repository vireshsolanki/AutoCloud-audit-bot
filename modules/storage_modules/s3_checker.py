import boto3
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError

def get_cloudtrail_access(cloudtrail_client, bucket_name):
    """Query CloudTrail for recent S3 access events for a given bucket."""
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=30)
    events_found = False

    try:
        response = cloudtrail_client.lookup_events(
            LookupAttributes=[
                {
                    'AttributeKey': 'ResourceName',
                    'AttributeValue': bucket_name
                }
            ],
            StartTime=start_time,
            EndTime=now,
            MaxResults=50
        )
        for event in response.get('Events', []):
            if any(op in event['EventName'] for op in ['GetObject', 'PutObject']):
                events_found = True
                break
    except ClientError as e:
        print(f"Error querying CloudTrail for bucket {bucket_name}: {e}")
    
    return events_found

def analyze_s3_buckets(s3_client, cloudtrail_client):
    report = []
    try:
        buckets = s3_client.list_buckets().get('Buckets', [])
    except ClientError as e:
        print("Error listing buckets:", e)
        return []

    for bucket in buckets:
        bucket_name = bucket['Name']
        region = s3_client.get_bucket_location(Bucket=bucket_name).get('LocationConstraint', 'us-east-1') or 'us-east-1'
        bucket_data = {
            "Bucket Name": bucket_name,
            "Region": region,
            "Last Object Upload": "N/A",
            "Total Objects": 0,
            "Total Size (GB)": 0,
            "Public?": "Unknown",
            "Versioning": "Disabled",
            "Lifecycle": "None",
            "Access Frequency": "Unknown",
            "Notes": []
        }

        try:
            versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
            bucket_data["Versioning"] = versioning.get('Status', 'Disabled')

            acl = s3_client.get_bucket_acl(Bucket=bucket_name)
            for grant in acl['Grants']:
                if grant['Grantee'].get('URI', '').endswith('AllUsers'):
                    bucket_data["Public?"] = "Yes"
                    bucket_data["Notes"].append("Bucket is publicly accessible.")
                    break
            else:
                bucket_data["Public?"] = "No"

            try:
                s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                bucket_data["Lifecycle"] = "Enabled"
            except ClientError:
                bucket_data["Lifecycle"] = "None"

            logging = s3_client.get_bucket_logging(Bucket=bucket_name)
            if "LoggingEnabled" in logging:
                bucket_data["Access Frequency"] = "Logs enabled"
            else:
                # No access logs enabled, fallback to CloudTrail
                access_detected = get_cloudtrail_access(cloudtrail_client, bucket_name)
                if access_detected:
                    bucket_data["Access Frequency"] = "Accessed (via CloudTrail)"
                    bucket_data["Notes"].append("Activity detected via CloudTrail.")
                else:
                    bucket_data["Access Frequency"] = "Unknown"
                    bucket_data["Notes"].append("No access logs or CloudTrail activity detected.")

            # Object listing
            objects = []
            paginator = s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket_name):
                contents = page.get('Contents', [])
                for obj in contents:
                    objects.append(obj)

            bucket_data["Total Objects"] = len(objects)
            total_size = sum(obj['Size'] for obj in objects)
            bucket_data["Total Size (GB)"] = round(total_size / (1024 ** 3), 2)

            if objects:
                latest_upload = max(obj['LastModified'] for obj in objects)
                bucket_data["Last Object Upload"] = latest_upload.strftime('%Y-%m-%d')

                if (datetime.now(timezone.utc) - latest_upload).days > 30:
                    bucket_data["Notes"].append("No objects added in last 30 days.")

                oldest_upload = min(obj['LastModified'] for obj in objects)
                if (datetime.now(timezone.utc) - oldest_upload).days > 365:
                    bucket_data["Notes"].append("Contains data older than 1 year.")
            else:
                bucket_data["Notes"].append("Bucket is empty.")

        except ClientError as e:
            bucket_data["Notes"].append(f"Error analyzing bucket: {e}")

        report.append(bucket_data)
    return report
