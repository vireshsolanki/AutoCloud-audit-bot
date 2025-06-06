import boto3
import datetime
from datetime import timezone
from collections import defaultdict

CLOUDWATCH_NAMESPACE = 'AWS/Lambda'


def list_all_lambdas(session, region):
    client = session.client('lambda', region_name=region)
    paginator = client.get_paginator('list_functions')
    lambdas = []
    for page in paginator.paginate():
        lambdas.extend(page['Functions'])
    return lambdas


def get_function_configuration(session, region, function_name):
    client = session.client('lambda', region_name=region)
    return client.get_function_configuration(FunctionName=function_name)


def check_event_triggers(session, region, function_name):
    client = session.client('lambda', region_name=region)
    mappings = client.list_event_source_mappings(FunctionName=function_name)
    policy = {}
    try:
        policy = client.get_policy(FunctionName=function_name)
    except client.exceptions.ResourceNotFoundException:
        pass
    return mappings['EventSourceMappings'], policy.get('Policy')


def fetch_cloudwatch_metrics(session, region, function_name, days=30):
    cloudwatch = session.client('cloudwatch', region_name=region)
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(days=days)

    metrics = ['Invocations', 'Duration', 'Errors']
    stats = {}

    for metric in metrics:
        response = cloudwatch.get_metric_statistics(
            Namespace=CLOUDWATCH_NAMESPACE,
            MetricName=metric,
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start,
            EndTime=end,
            Period=86400,
            Statistics=['Sum', 'Average', 'Maximum']
        )
        stats[metric] = response['Datapoints']

    return stats


def detect_unused_lambda(metrics):
    invocations = metrics.get('Invocations', [])
    total_invocations = sum(d.get('Sum', 0) for d in invocations)
    return total_invocations == 0


def detect_provisioned_concurrency(config):
    return config.get('ProvisionedConcurrentExecutions', 0) > 0


def detect_reserved_concurrency(config):
    return config.get('ReservedConcurrentExecutions', None)


def detect_edge_functions(config):
    return config.get('Runtime', '').startswith('nodejs') and 'cloudfront' in config.get('FunctionArn', '')


def evaluate_lambda_layers(config):
    layers = config.get('Layers', [])
    return [layer['Arn'] for layer in layers], len(layers) > 3


def get_last_modified_days(config):
    last_modified = config.get('LastModified')
    if last_modified:
        dt = datetime.datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
        return (datetime.datetime.now(timezone.utc) - dt).days
    return None


def validate_dlq(config, metrics):
    dlq_config = config.get('DeadLetterConfig')
    has_errors = any(d.get('Sum', 0) > 0 for d in metrics.get('Errors', []))
    return has_errors and not dlq_config


def generate_suggestions(config, metrics, unused, edge, layer_count_too_high):
    suggestions = []
    memory = config['MemorySize']
    timeout = config.get('Timeout', 3)

    duration_data = metrics.get('Duration', [])
    avg_duration = sum(d.get('Average', 0) for d in duration_data) / len(duration_data) if duration_data else 0
    max_duration = max((d.get('Maximum', 0) for d in duration_data), default=0)

    if unused:
        suggestions.append("Unused function. Consider deleting or archiving.")

    if memory > 512 and avg_duration < 200:
        suggestions.append("Over-provisioned memory. Consider downsizing.")

    if timeout > 60 and max_duration < 1000:
        suggestions.append("Timeout is high relative to max execution duration. Consider reducing it.")

    if layer_count_too_high:
        suggestions.append("Too many Lambda layers. Consider consolidating.")

    if detect_provisioned_concurrency(config):
        if unused:
            suggestions.append("Provisioned concurrency enabled but function is unused — major cost risk.")
        else:
            suggestions.append("Provisioned concurrency enabled. Review usage and cost impact.")

    reserved_concurrency = detect_reserved_concurrency(config)
    if reserved_concurrency is not None and unused:
        suggestions.append(f"Reserved concurrency ({reserved_concurrency}) set but function is unused.")

    if validate_dlq(config, metrics):
        suggestions.append("Function has errors but no Dead Letter Queue (DLQ) configured.")

    if edge:
        suggestions.append("Lambda@Edge function. Review for duplication and necessity.")

    last_modified_days = get_last_modified_days(config)
    if last_modified_days and last_modified_days > 180:
        suggestions.append("Function hasn't been modified in over 6 months. Review its relevance.")

    return suggestions


def audit_lambda_functions(session, region, days=30):
    results = []
    all_lambdas = list_all_lambdas(session, region)

    for fn in all_lambdas:
        name = fn['FunctionName']
        config = get_function_configuration(session, region, name)
        triggers, policy = check_event_triggers(session, region, name)
        metrics = fetch_cloudwatch_metrics(session, region, name, days)

        unused = detect_unused_lambda(metrics)
        edge = detect_edge_functions(config)
        layers, too_many_layers = evaluate_lambda_layers(config)
        last_modified_days = get_last_modified_days(config)

        duration_data = metrics.get('Duration', [])
        avg_duration = sum(d.get('Average', 0) for d in duration_data) / len(duration_data) if duration_data else 0
        invocations = sum(d.get('Sum', 0) for d in metrics.get('Invocations', []))

        suggestions = generate_suggestions(config, metrics, unused, edge, too_many_layers)

        results.append({
            'FunctionName': name,
            'Runtime': config.get('Runtime'),
            'MemorySize': config.get('MemorySize'),
            'Timeout': config.get('Timeout'),
            'AvgDuration': round(avg_duration, 2),
            'Invocations': invocations,
            'Unused': unused,
            'IsEdgeFunction': edge,
            'Layers': layers,
            'Triggers': [t['EventSourceArn'] for t in triggers],
            'LastModifiedDaysAgo': last_modified_days,
            'ProvisionedConcurrency': config.get('ProvisionedConcurrentExecutions'),
            'ReservedConcurrency': config.get('ReservedConcurrentExecutions'),
            'Suggestions': suggestions
        })

    return results
