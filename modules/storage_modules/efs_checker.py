
import boto3
import datetime
from botocore.exceptions import ClientError

def get_efs_write_activity(cloudwatch, fs_id, days=30):
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(days=days)

    try:
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/EFS',
            MetricName='DataWriteIOBytes',
            Dimensions=[{'Name': 'FileSystemId', 'Value': fs_id}],
            StartTime=start,
            EndTime=end,
            Period=86400,
            Statistics=['Sum']
        )
        datapoints = response.get('Datapoints', [])
        return sum(dp['Sum'] for dp in datapoints) > 0  # True if any write happened
    except ClientError as e:
        print(f"Error fetching CloudWatch metrics for {fs_id}: {e}")
        return False

def check_efs_usage(session, region):
    efs = session.client('efs', region_name=region)
    cw = session.client('cloudwatch', region_name=region)
    results = []

    try:
        file_systems = efs.describe_file_systems().get('FileSystems', [])

        for fs in file_systems:
            fs_id = fs['FileSystemId']
            name_tag = next((t['Value'] for t in efs.describe_tags(FileSystemId=fs_id)['Tags'] if t['Key'] == 'Name'), 'N/A')
            mount_targets = efs.describe_mount_targets(FileSystemId=fs_id).get('MountTargets', [])
            lifecycle = efs.describe_lifecycle_configuration(FileSystemId=fs_id).get('LifecyclePolicies', [])
            ia_enabled = any('TransitionToIA' in policy.get('TransitionToIA', '') for policy in lifecycle)
            has_activity = get_efs_write_activity(cw, fs_id)

            suggestion = []
            if not has_activity:
                suggestion.append("No write activity in last 30 days.")
            if not ia_enabled:
                suggestion.append("Enable lifecycle policy to move to Infrequent Access.")
            if fs.get('AvailabilityZoneName'):
                suggestion.append("Consider moving to One Zone if high durability not needed.")

            results.append({
                "File System ID": fs_id,
                "Name Tag": name_tag,
                "Mount Targets": len(mount_targets),
                "Encrypted": fs.get('Encrypted'),
                "Performance Mode": fs.get('PerformanceMode'),
                "Throughput Mode": fs.get('ThroughputMode'),
                "Lifecycle Policies": ", ".join(p.get('TransitionToIA', '') for p in lifecycle) or "None",
                "Used in Last 30 Days": "Yes" if has_activity else "No",
                "Suggestion": " | ".join(suggestion) if suggestion else "None"
            })

    except ClientError as e:
        print(f"Error describing EFS: {e}")

    return results
