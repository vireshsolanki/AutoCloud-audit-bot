import boto3
import datetime
from botocore.exceptions import ClientError

def get_cloudwatch_metrics(client, db_id, metric_name, stat, period=86400, days=7):
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(days=days)
    try:
        response = client.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName=metric_name,
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=[stat]
        )
        datapoints = response.get('Datapoints', [])
        if datapoints:
            # Return average of datapoints
            return round(sum(dp[stat] for dp in datapoints) / len(datapoints), 2)
        return None
    except ClientError as e:
        print(f"Error fetching CloudWatch metrics for {db_id}: {e}")
        return None

def check_rds_utilization(session, region):
    rds = session.client('rds', region_name=region)
    cloudwatch = session.client('cloudwatch', region_name=region)
    results = []
    try:
        dbs = rds.describe_db_instances()['DBInstances']
        for db in dbs:
            db_id = db['DBInstanceIdentifier']
            engine = db['Engine']
            instance_class = db['DBInstanceClass']
            allocated = db.get('AllocatedStorage', 0)
            multi_az = db.get('MultiAZ', False)
            tags = rds.list_tags_for_resource(ResourceName=db['DBInstanceArn'])['TagList']

            cpu = get_cloudwatch_metrics(cloudwatch, db_id, 'CPUUtilization', 'Average')
            storage_free = get_cloudwatch_metrics(cloudwatch, db_id, 'FreeStorageSpace', 'Average')
            used_percent = None
            if storage_free and allocated:
                total_bytes = allocated * 1024 * 1024 * 1024
                used_percent = round((1 - (storage_free / total_bytes)) * 100, 2)

            results.append({
                'DB Identifier': db_id,
                'Engine': engine,
                'Class': instance_class,
                'Allocated (GB)': allocated,
                'CPU Utilization (%)': cpu,
                'Used Storage (%)': used_percent,
                'Multi-AZ': multi_az,
                'Tags': {tag['Key']: tag['Value'] for tag in tags},
            })
    except ClientError as e:
        print(f"Error retrieving RDS utilization: {e}")
    return results

def list_rds_snapshots(session, region):
    rds = session.client('rds', region_name=region)
    results = []
    try:
        snapshots = rds.describe_db_snapshots(SnapshotType='manual')['DBSnapshots']
        for snap in snapshots:
            age_days = (datetime.datetime.utcnow() - snap['SnapshotCreateTime'].replace(tzinfo=None)).days
            results.append({
                'Snapshot ID': snap['DBSnapshotIdentifier'],
                'DB Instance': snap['DBInstanceIdentifier'],
                'Created On': snap['SnapshotCreateTime'].strftime('%Y-%m-%d'),
                'Age (days)': age_days,
                'Size (GB)': snap.get('AllocatedStorage', 'N/A')
            })
    except ClientError as e:
        print(f"Error retrieving manual RDS snapshots: {e}")
    return results

def analyze_performance_insights(session, region):
    insights = session.client('pi', region_name=region)
    rds = session.client('rds', region_name=region)
    results = []
    try:
        dbs = rds.describe_db_instances()['DBInstances']
        for db in dbs:
            arn = db['DBInstanceArn']
            id = db['DBInstanceIdentifier']
            try:
                dimensions = insights.describe_dimension_keys(
                    ServiceType='RDS',
                    Identifier=arn,
                    StartTime=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
                    EndTime=datetime.datetime.utcnow(),
                    Metric='db.load.avg',
                    GroupBy={"Group": "db.sql.tokenized", "Dimensions": ["db.sql.tokenized"]},
                    MaxResults=1
                )
                top_query = dimensions['Dimensions'][0]['Value'] if dimensions['Dimensions'] else 'N/A'
                results.append({
                    'DB Identifier': id,
                    'Top Query': top_query,
                    'Recommendation': 'Consider indexing or optimizing this query.'
                })
            except ClientError:
                continue  # Insights may not be enabled
    except ClientError as e:
        print(f"Error analyzing Performance Insights: {e}")
    return results

def check_rds_proxies(session, region):
    rds = session.client('rds', region_name=region)
    results = []
    try:
        proxies = rds.describe_db_proxies()['DBProxies']
        for proxy in proxies:
            proxy_name = proxy['DBProxyName']
            status = proxy['Status']
            is_enabled = proxy['RoleArn'] != ''
            attached_targets = proxy.get('AssociatedDBClusters', []) + proxy.get('AssociatedDBInstances', [])
            results.append({
                'Proxy Name': proxy_name,
                'Status': status,
                'Enabled': is_enabled,
                'Attached Resources': attached_targets
            })
    except ClientError as e:
        print(f"Error retrieving RDS proxies: {e}")
    return results
def audit_rds_instances(session, region):
    return {
        "RDS Instances": check_rds_utilization(session, region) or [],
        "RDS Snapshots": list_rds_snapshots(session, region) or [],
        "RDS Performance Insights": analyze_performance_insights(session, region) or [],
        "RDS Proxies": check_rds_proxies(session, region) or []
    }