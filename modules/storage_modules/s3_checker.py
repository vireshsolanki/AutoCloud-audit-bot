import boto3
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError

def analyze_s3_buckets(s3_client):
    report = []
    try:
        buckets = s3_client.list_buckets().get('Buckets', [])
    except ClientError as e:
        print("Error listing buckets:", e)
        return []

    for bucket in buckets:
        bucket_name = bucket['Name']
        region = s3_client.get_bucket_location(Bucket=bucket_name).get('LocationConstraint', 'us-east-1')
        bucket_data = {
            "Bucket Name": bucket_name,
            "Region": region or 'us-east-1',
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
            # Versioning
            versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
            bucket_data["Versioning"] = versioning.get('Status', 'Disabled')

            # ACL/Public access
            acl = s3_client.get_bucket_acl(Bucket=bucket_name)
            for grant in acl['Grants']:
                if grant['Grantee'].get('URI', '').endswith('AllUsers'):
                    bucket_data["Public?"] = "Yes"
                    bucket_data["Notes"].append("Bucket is publicly accessible.")
                    break
            else:
                bucket_data["Public?"] = "No"

            # Lifecycle
            try:
                lifecycle = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                bucket_data["Lifecycle"] = "Enabled"
            except ClientError:
                bucket_data["Lifecycle"] = "None"

            # Logging
            logging = s3_client.get_bucket_logging(Bucket=bucket_name)
            if "LoggingEnabled" in logging:
                bucket_data["Access Frequency"] = "Logs enabled"
            else:
                bucket_data["Access Frequency"] = "Unknown"
                bucket_data["Notes"].append("Access frequency unknown. Enable access logs.")

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

                # Check idle > 30 days
                if (datetime.now(timezone.utc) - latest_upload).days > 30:
                    bucket_data["Notes"].append("No objects added in last 30 days.")

                # Check oldest data > 1 year
                oldest_upload = min(obj['LastModified'] for obj in objects)
                if (datetime.now(timezone.utc) - oldest_upload).days > 365:
                    bucket_data["Notes"].append("Contains data older than 1 year.")
            else:
                bucket_data["Notes"].append("Bucket is empty.")

        except ClientError as e:
            bucket_data["Notes"].append(f"Error analyzing bucket: {e}")

        report.append(bucket_data)
    return report
