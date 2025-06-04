import os
import sys
from PyQt5.QtWidgets import QApplication, QFileDialog
import boto3
import pwinput
from botocore.exceptions import NoCredentialsError, ClientError
from modules.compute_modules.ec2_checker import (
    check_idle_ec2_instances,
    check_available_volumes,
    check_old_amis,
    check_unassociated_elastic_ips,
    check_orphan_snapshots
)
from utils.excel_writer import save_report


def get_aws_credentials():
    print("Enter your AWS credentials (Read-only IAM user):")
    access_key = input("Access Key ID: ").strip()
    secret_key = pwinput.pwinput(prompt="Secret Access Key: ", mask="*").strip()
    region = input("Region [default: us-east-1]: ").strip() or "us-east-1"

    idle_days_input = input("Idle days threshold for EC2/Volumes [default: 7]: ").strip()
    ami_days_input = input("Days threshold for old AMIs [default: 30]: ").strip()

    try:
        idle_days = int(idle_days_input) if idle_days_input else 7
    except ValueError:
        print(" Invalid idle days, using default of 7.")
        idle_days = 7

    try:
        ami_days = int(ami_days_input) if ami_days_input else 30
    except ValueError:
        print(" Invalid AMI days, using default of 30.")
        ami_days = 30

    return access_key, secret_key, region, idle_days, ami_days


def connect_to_aws(access_key, secret_key, region):
    try:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        session.client('ec2').describe_instances()
        print(f"\n Connected to AWS in region: {region}")
        return session
    except NoCredentialsError:
        print(" Invalid credentials.")
        return None
    except ClientError as e:
        print(f" AWS error: {e}")
        return None


def choose_output_directory():
    app = QApplication(sys.argv)
    folder = QFileDialog.getExistingDirectory(None, "Select Output Directory for Report")
    return folder


def main():
    print("Welcome to AutoCloud Audit Bot")
    access_key, secret_key, region, idle_days, ami_days = get_aws_credentials()
    session = connect_to_aws(access_key, secret_key, region)

    if not session:
        print(" Could not connect to AWS. Exiting.")
        return

    print("\n Scanning Compute Resources...")

    ec2_idle = check_idle_ec2_instances(session, region, idle_days)
    print(f" Idle EC2 instances: {len(ec2_idle)}")

    ebs_unused = check_available_volumes(session, region)
    print(f" Unattached EBS volumes: {len(ebs_unused)}")

    old_amis = check_old_amis(session, region, ami_days)
    print(f" Old AMIs: {len(old_amis)}")

    eips = check_unassociated_elastic_ips(session, region)
    print(f" Unassociated Elastic IPs: {len(eips)}")

    snapshots = check_orphan_snapshots(session, region)
    print(f" Orphan Snapshots: {len(snapshots)}")

    resource_data = {
        "EC2 - Idle Instances": ec2_idle,
        "EBS - Unattached Volumes": ebs_unused,
        "AMIs - Old": old_amis,
        "Elastic IPs - Unused": eips,
        "Snapshots - Orphaned": snapshots,
    }

    # GUI Directory Selection
    output_dir = choose_output_directory()
    if not output_dir:
        print("No directory selected. Saving in current directory.")
        output_dir = os.getcwd()

    file_path = os.path.join(output_dir, "cloud_audit_report.xlsx")
    save_report(file_path, resource_data)
    print(f"\n Report saved to: {file_path}")


if __name__ == "__main__":
    main()
