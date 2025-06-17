import os
import sys
import signal
import subprocess
import boto3
import pwinput
from PyQt5.QtWidgets import QApplication
from botocore.exceptions import NoCredentialsError, ClientError
from yaspin import yaspin
from modules.compute_modules.ec2_checker import (
    check_idle_ec2_instances,
    check_available_volumes,
    check_old_amis,
    check_unassociated_elastic_ips,
    check_orphan_snapshots,
    check_unattached_enis,
    check_reserved_instance_utilization,
    check_instance_store_backed_amis,
    report_running_instance_costs,
)
from modules.compute_modules.lambda_checker import audit_lambda_functions
from modules.storage_modules.s3_checker import analyze_s3_buckets
from modules.storage_modules.rds_checker import audit_rds_instances
from modules.storage_modules.efs_checker import check_efs_usage
from features.excel_writer import save_report

def handle_sigint(signum, frame):
    print("\nInterrupted by user. Exiting.")
    sys.exit(0)


signal.signal(signal.SIGINT, handle_sigint)

def print_welcome_banner(username=None):
    print("""
****************************************************
*                                                  *
*      WELCOME TO AUTOCloud Resource Auditor       *
*                                                  *
****************************************************
""")
    if username:
        print(f"Hello, {username}!\n")

def get_aws_credentials():
    print("Enter your AWS credentials (Read-only IAM user):")
    try:
        access_key = input("Access Key ID: ").strip()
        secret_key = pwinput.pwinput(prompt="Secret Access Key: ", mask="*").strip()
        region = input("Region [default: us-east-1]: ").strip() or "us-east-1"
        ami_days = 30  # Default value
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.")
        sys.exit(0)

    return access_key, secret_key, region, ami_days

def extract_username_from_arn(arn: str) -> str:
    try:
        return arn.split('/')[-1]
    except Exception:
        return arn

def connect_to_aws(access_key, secret_key, region):
    try:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

        ec2 = session.client("ec2", region_name=region)
        available_regions = [r['RegionName'] for r in ec2.describe_regions(AllRegions=True)['Regions']]
        if region not in available_regions:
            print(f"\n❌ '{region}' is not a valid AWS region.")
            print("✔️ Available regions include:")
            print(", ".join(sorted(available_regions)))
            return None, None

        sts_client = session.client('sts')
        identity = sts_client.get_caller_identity()
        username = extract_username_from_arn(identity.get('Arn', 'Unknown'))
        print("\nConnected to AWS successfully!")
        return session, username

    except NoCredentialsError:
        print("❌ Invalid credentials.")
        return None, None
    except ClientError as e:
        print(f"❌ AWS error: {e}")
        return None, None

def scan_resources_with_spinner(session, region, ami_days):
    resource_data = {}

    with yaspin(text="Checking idle EC2 instances...", color="cyan") as spinner:
        resource_data["EC2 - Idle Instances"] = check_idle_ec2_instances(session, region, idle_days=7, cpu_threshold=1.0, network_threshold=100.0)
        spinner.ok("✅")

    with yaspin(text="Checking unattached EBS volumes...", color="cyan") as spinner:
        resource_data["EBS - Unattached Volumes"] = check_available_volumes(session, region)
        spinner.ok("✅")

    with yaspin(text="Checking old AMIs...", color="cyan") as spinner:
        resource_data["AMIs - Old"] = check_old_amis(session, region, ami_days)
        spinner.ok("✅")

    with yaspin(text="Checking unassociated Elastic IPs...", color="cyan") as spinner:
        resource_data["Elastic IPs - Unused"] = check_unassociated_elastic_ips(session, region)
        spinner.ok("✅")

    with yaspin(text="Checking orphan snapshots...", color="cyan") as spinner:
        resource_data["Snapshots - Orphaned"] = check_orphan_snapshots(session, region)
        spinner.ok("✅")

    with yaspin(text="Checking unattached ENIs...", color="cyan") as spinner:
        resource_data["ENIs - Unattached"] = check_unattached_enis(session, region)
        spinner.ok("✅")

    with yaspin(text="Checking reserved instance utilization...", color="cyan") as spinner:
        resource_data["Reserved Instances - Underutilized"] = check_reserved_instance_utilization(session, region)
        spinner.ok("✅")

    with yaspin(text="Checking instance store-backed AMIs...", color="cyan") as spinner:
        resource_data["AMIs - Instance Store Backed"] = check_instance_store_backed_amis(session, region)
        spinner.ok("✅")

    with yaspin(text="Reporting running instance costs...", color="cyan") as spinner:
        resource_data["Running Instance Costs"] = report_running_instance_costs(session, region)
        spinner.ok("✅")

    with yaspin(text="Auditing Lambda functions...", color="cyan") as spinner:
        resource_data["Lambda - Functions"] = audit_lambda_functions(session, region)
        spinner.ok("✅")

    with yaspin(text="Analyzing S3 buckets...", color="cyan") as spinner:
        s3_client = session.client('s3')
        cloudtrail_client = session.client('cloudtrail')
        resource_data["S3 - Bucket Analysis"] = analyze_s3_buckets(s3_client, cloudtrail_client)
        spinner.ok("✅")

    with yaspin(text="Auditing RDS instances...", color="cyan") as spinner:
        resource_data["RDS - Instances"] = audit_rds_instances(session, region)
        spinner.ok("✅")
    
    with yaspin(text="Auditing EFS file systems...", color="cyan") as spinner:
        resource_data["EFS - File Systems"] = check_efs_usage(session, region)
        spinner.ok("✅")

    return resource_data

def choose_output_directory():
    script = """
import sys
from PyQt5.QtWidgets import QApplication, QFileDialog
app = QApplication(sys.argv)
folder = QFileDialog.getExistingDirectory(None, "Select Output Directory for Report")
if folder:
    print(folder)
app.quit()
"""
    try:
        result = subprocess.run(["python3", "-c", script], capture_output=True, text=True)
        return result.stdout.strip()
    except KeyboardInterrupt:
        print("\nInterrupted during folder selection.")
        sys.exit(0)

def main():
    access_key, secret_key, region, ami_days = get_aws_credentials()
    session, username = connect_to_aws(access_key, secret_key, region)

    if not session:
        print("Could not connect to AWS. Exiting.")
        return

    print_welcome_banner(username)
    resource_data = scan_resources_with_spinner(session, region, ami_days)

    print("\nScan complete!\n")
    for resource_name, items in resource_data.items():
        print(f"{resource_name:<35}: {len(items)}")

    attempts = 0
    while attempts < 2:
        output_dir = choose_output_directory()
        if output_dir:
            break
        else:
            attempts += 1
            if attempts < 2:
                print("Output directory selection is required to save the report. Please select a folder.")
            else:
                print("User interruption happened. Kindly run again.")
                return

    file_path = os.path.join(output_dir, "cloud_audit_report.xlsx")
    save_report(file_path, resource_data)
    print(f"\nReport saved to: {file_path}")

if __name__ == "__main__":
    main()