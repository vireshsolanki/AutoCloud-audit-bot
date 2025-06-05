from datetime import datetime, timezone, timedelta
import boto3

def check_idle_ec2_instances(session, region, idle_days=7, cpu_threshold=5, network_threshold=1000):
    ec2 = session.client('ec2', region_name=region)
    cloudwatch = session.client('cloudwatch', region_name=region)
    now = datetime.now(timezone.utc)
    idle_instances = []

    try:
        response = ec2.describe_instances()
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                state = instance['State']['Name']
                launch_time = instance['LaunchTime']
                name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'N/A')

                if state == 'terminated':
                    continue  # Skip terminated instances
                
                # If instance is stopped, consider it idle immediately
                if state == 'stopped':
                    idle_instances.append({
                        'Resource ID': instance_id,
                        'Name': name,
                        'State': state,
                        'Launch Time': str(launch_time),
                        'Idle Days': idle_days,
                        'CPU Avg (%)': 0.0,
                        'NetworkOut Avg (Bytes)': 0.0,
                        'Used?': 'No',
                        'Suggestion': 'Instance is stopped. Consider terminating if not needed.'
                    })
                    continue

                # For running or other states, check CloudWatch metrics
                cpu_util = get_average_metric(cloudwatch, instance_id, 'CPUUtilization', idle_days, now)
                network_out = get_average_metric(cloudwatch, instance_id, 'NetworkOut', idle_days, now)

                is_idle = cpu_util < cpu_threshold and network_out < network_threshold

                if is_idle:
                    idle_instances.append({
                        'Resource ID': instance_id,
                        'Name': name,
                        'State': state,
                        'Launch Time': str(launch_time),
                        'Idle Days': idle_days,
                        'CPU Avg (%)': cpu_util,
                        'NetworkOut Avg (Bytes)': network_out,
                        'Used?': 'No',
                        'Suggestion': 'Review and consider stopping or terminating due to low usage.'
                    })

    except Exception as e:
        print(f"[Error] EC2 Check: {e}")

    return idle_instances


def get_average_metric(cloudwatch_client, instance_id, metric_name, days, end_time):
    start_time = end_time - timedelta(days=days)
    try:
        response = cloudwatch_client.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName=metric_name,
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # 1 day in seconds
            Statistics=['Average']
        )
        datapoints = response.get('Datapoints', [])
        if not datapoints:
            return 0.0
        # Calculate average across datapoints
        avg = sum(dp['Average'] for dp in datapoints) / len(datapoints)
        return avg
    except Exception as e:
        print(f"[Error] CloudWatch metric {metric_name} for {instance_id}: {e}")
        return 0.0


def check_available_volumes(session, region):
    ec2 = session.client('ec2', region_name=region)
    available_volumes = []

    try:
        volumes = ec2.describe_volumes(Filters=[{'Name': 'status', 'Values': ['available']}])
        for vol in volumes['Volumes']:
            available_volumes.append({
                'Resource ID': vol['VolumeId'],
                'Size (GiB)': vol['Size'],
                'State': vol['State'],
                'Created Time': str(vol['CreateTime']),
                'Used?': 'No',
                'Suggestion': 'Delete if not needed.'
            })
    except Exception as e:
        print(f"[Error] Volume Check: {e}")

    return available_volumes


def check_old_amis(session, region, ami_days=30):
    ec2 = session.client('ec2', region_name=region)
    now = datetime.now(timezone.utc)
    threshold = timedelta(days=ami_days)
    old_amis = []

    try:
        images = ec2.describe_images(Owners=['self'])['Images']
        for image in images:
            creation_time = datetime.strptime(image['CreationDate'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            age = now - creation_time
            if age > threshold:
                old_amis.append({
                    'Resource ID': image['ImageId'],
                    'Name': image.get('Name', 'N/A'),
                    'Creation Date': image['CreationDate'],
                    'Snapshot IDs': ", ".join([bdm.get('Ebs', {}).get('SnapshotId', 'N/A') for bdm in image.get('BlockDeviceMappings', [])]),
                    'Idle Days': age.days,
                    'Used?': 'Unknown',
                    'Suggestion': 'Deregister AMI and manually delete snapshots if unused.'
                })
    except Exception as e:
        print(f"[Error] AMI Check: {e}")

    return old_amis


def check_unassociated_elastic_ips(session, region):
    ec2 = session.client('ec2', region_name=region)
    unassoc_ips = []

    try:
        addresses = ec2.describe_addresses()
        for addr in addresses['Addresses']:
            if 'InstanceId' not in addr and 'NetworkInterfaceId' not in addr:
                unassoc_ips.append({
                    'Resource ID': addr.get('AllocationId', 'N/A'),
                    'Public IP': addr.get('PublicIp'),
                    'Domain': addr.get('Domain'),
                    'Used?': 'No',
                    'Suggestion': 'Release unused Elastic IP to avoid charges.'
                })
    except Exception as e:
        print(f"[Error] EIP Check: {e}")

    return unassoc_ips


def check_orphan_snapshots(session, region):
    ec2 = session.client('ec2', region_name=region)
    orphan_snapshots = []

    try:
        snapshots = ec2.describe_snapshots(OwnerIds=['self'])['Snapshots']
        for snap in snapshots:
            orphan_snapshots.append({
                'Resource ID': snap['SnapshotId'],
                'Volume ID': snap.get('VolumeId', 'N/A'),
                'Start Time': str(snap['StartTime']),
                'Size (GiB)': snap['VolumeSize'],
                'Description': snap.get('Description', 'N/A'),
                'Used?': 'Unknown',
                'Suggestion': 'Delete if snapshot is orphan and not used by AMI or restore point.'
            })
    except Exception as e:
        print(f"[Error] Snapshot Check: {e}")

    return orphan_snapshots
