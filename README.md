🛡️ AutoCloud Audit Bot
📌 Overview
AutoCloud Audit Bot is a hybrid command-line + GUI Python tool designed to analyze your AWS account for unused or idle resources. It connects using read-only IAM credentials and scans for:

✅ Idle EC2 Instances (with improved unused detection)

✅ Unattached EBS Volumes

✅ Old AMIs

✅ Unassociated Elastic IPs

✅ Orphan Snapshots

✅ Unused or Idle Lambda Functions (new compute module)

🔍 Currently implemented: EC2 and Lambda modules
📦 More modules are under development and will be added soon!

⚙️ Features
📆 Generates audit reports in .xlsx format

🎨 Well-formatted Excel output using styled formatting

📁 GUI output folder picker using PyQt5

🔐 Secure credential entry using pwinput

🧠 Improved idle EC2 detection via usage patterns

⚙️ Audits Lambda usage, concurrency, errors, and configuration suggestions

🛠️ Development Status
Module	Status
EC2 Audit	✅ Fully implemented
Lambda Audit	✅ Implemented
EBS Volumes	🚧 In progress
AMIs	🚧 In progress
Elastic IPs	🚧 In progress
Snapshots	🚧 In progress
Excel Export	✅ Styled report output
GUI Folder Picker	✅ Cross-platform GUI

🧰 Prerequisites
Ensure you have the following:

Python 3.8+

AWS IAM Read-Only Access credentials

pip and Python virtual environment setup (recommended)

📥 Installation
Clone the Repository

bash
Copy
Edit
git clone https://github.com/your-username/aws-resource-analyzer-bot.git
cd aws-resource-analyzer-bot
Create & Activate Virtual Environment

bash
Copy
Edit
python3 -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
Install Dependencies

bash
Copy
Edit
pip install -r requirements.txt
🚀 Usage
Run the bot:

bash
Copy
Edit
python audit_bot.py
Follow the steps:

Provide AWS Access Key, Secret Key, and Region

Set thresholds:

Idle EC2 days (default: 7)

AMI age in days (default: 30)

Choose an output folder using the GUI popup

Your report will be saved as:

Copy
Edit
cloud_audit_report.xlsx
📂 Output Example
File: cloud_audit_report.xlsx

Tabs for each audited resource

Includes details for EC2 and Lambda analysis

Clearly marked idle/unused indicators

🔒 Security Notice
Credentials are not stored

Uses read-only access

Always use least-privilege IAM policies

🧭 Roadmap
 EC2 Audit (enhanced detection logic)

 Lambda Audit Module

 Excel Export with formatting

 GUI Output Directory Picker

 S3 Bucket Audit

 Multi-region AWS Support

 CLI Argument Support

🤝 Contributing
We welcome all PRs and suggestions!

Fork this repo

Create a feature branch

Submit a pull request

📜 License
MIT License © 2025

📬 Contact
Questions or feature requests?

📧 vireshsolanki1027@gmail.com