from datetime import datetime, timezone, timedelta
import boto3
import botocore


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
                    continue

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
            Period=86400,
            Statistics=['Average']
        )
        datapoints = response.get('Datapoints', [])
        if not datapoints:
            return 0.0
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


def check_unattached_enis(session, region):
    ec2 = session.client('ec2', region_name=region)
    results = []
    try:
        enis = ec2.describe_network_interfaces(Filters=[{'Name': 'status', 'Values': ['available']}])
        for eni in enis['NetworkInterfaces']:
            results.append({
                'Resource ID': eni['NetworkInterfaceId'],
                'Description': eni.get('Description', 'N/A'),
                'Used?': 'No',
                'Suggestion': 'Delete unattached ENI to avoid unnecessary charges.'
            })
    except Exception as e:
        print(f"[Error] ENI Check: {e}")
    return results


def check_reserved_instance_utilization(session, region):
    ec2 = session.client('ec2', region_name=region)
    report = []
    try:
        reserved = ec2.describe_reserved_instances(Filters=[{'Name': 'state', 'Values': ['active']}])
        instances = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])

        reserved_counts = {}
        for ri in reserved['ReservedInstances']:
            key = (ri['InstanceType'], ri['AvailabilityZone'])
            reserved_counts[key] = reserved_counts.get(key, 0) + ri['InstanceCount']

        running_counts = {}
        for res in instances['Reservations']:
            for inst in res['Instances']:
                key = (inst['InstanceType'], inst['Placement']['AvailabilityZone'])
                running_counts[key] = running_counts.get(key, 0) + 1

        for key in reserved_counts:
            used = running_counts.get(key, 0)
            available = reserved_counts[key]
            if used < available:
                report.append({
                    'Instance Type': key[0],
                    'AZ': key[1],
                    'Reserved Count': available,
                    'Used Count': used,
                    'Suggestion': 'Underutilized reserved instances. Consider modifying or reducing.'
                })
    except Exception as e:
        print(f"[Error] Reserved Instance Check: {e}")
    return report


def check_instance_store_backed_amis(session, region):
    ec2 = session.client('ec2', region_name=region)
    results = []
    try:
        images = ec2.describe_images(Owners=['self'])['Images']
        for image in images:
            for bdm in image.get('BlockDeviceMappings', []):
                if 'Ebs' not in bdm:
                    results.append({
                        'Resource ID': image['ImageId'],
                        'Name': image.get('Name', 'N/A'),
                        'Used?': 'Unknown',
                        'Suggestion': 'Instance store-backed AMI. Check for leftover snapshots or data.'
                    })
                    break
    except Exception as e:
        print(f"[Error] Instance Store-backed AMI Check: {e}")
    return results


def report_running_instance_costs(session, region):
    ec2 = session.client('ec2', region_name=region)
    pricing = session.client('pricing', region_name='us-east-1')
    costs = []
    try:
        reservations = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        for res in reservations['Reservations']:
            for inst in res['Instances']:
                instance_type = inst['InstanceType']
                az = inst['Placement']['AvailabilityZone']
                region_name = region
                try:
                    price_resp = pricing.get_products(
                        ServiceCode='AmazonEC2',
                        Filters=[
                            {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_region_name(region)}
                        ],
                        MaxResults=1
                    )
                    price = 'N/A'
                    for offer in price_resp['PriceList']:
                        price = offer
                        break
                except botocore.exceptions.ClientError:
                    price = 'Unknown'

                costs.append({
                    'Resource ID': inst['InstanceId'],
                    'Instance Type': instance_type,
                    'AZ': az,
                    'Estimated Cost Info': price,
                    'Suggestion': 'Review usage if not fully utilized.'
                })
    except Exception as e:
        print(f"[Error] Running Instance Cost Report: {e}")
    return costs

def get_region_name(region_code):
    region_map = {
        'us-east-1': 'US East (N. Virginia)',
        'us-east-2': 'US East (Ohio)',
        'us-west-1': 'US West (N. California)',
        'us-west-2': 'US West (Oregon)',
        'af-south-1': 'Africa (Cape Town)',
        'ap-east-1': 'Asia Pacific (Hong Kong)',
        'ap-south-2': 'Asia Pacific (Hyderabad)',
        'ap-southeast-3': 'Asia Pacific (Jakarta)',
        'ap-southeast-5': 'Asia Pacific (Malaysia)',
        'ap-southeast-4': 'Asia Pacific (Melbourne)',
        'ap-south-1': 'Asia Pacific (Mumbai)',
        'ap-northeast-3': 'Asia Pacific (Osaka)',
        'ap-northeast-2': 'Asia Pacific (Seoul)',
        'ap-southeast-1': 'Asia Pacific (Singapore)',
        'ap-southeast-2': 'Asia Pacific (Sydney)',
        'ap-southeast-7': 'Asia Pacific (Thailand)',
        'ap-northeast-1': 'Asia Pacific (Tokyo)',
        'ca-central-1': 'Canada (Central)',
        'ca-west-1': 'Canada West (Calgary)',
        'eu-central-1': 'Europe (Frankfurt)',
        'eu-west-1': 'Europe (Ireland)',
        'eu-west-2': 'Europe (London)',
        'eu-south-1': 'Europe (Milan)',
        'eu-west-3': 'Europe (Paris)',
        'eu-south-2': 'Europe (Spain)',
        'eu-north-1': 'Europe (Stockholm)',
        'eu-central-2': 'Europe (Zurich)',
        'il-central-1': 'Israel (Tel Aviv)',
        'mx-central-1': 'Mexico (Central)',
        'me-south-1': 'Middle East (Bahrain)',
        'me-central-1': 'Middle East (UAE)',
        'sa-east-1': 'South America (São Paulo)'
    }
    return region_map.get(region_code, region_code)