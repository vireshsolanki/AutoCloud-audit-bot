   # 🛡️ AutoCloud Audit Bot

   ## 📌 Overview

   AutoCloud Audit Bot is a hybrid command-line + GUI Python tool designed to analyze your AWS account for unused or idle resources. It connects using read-only IAM credentials and scans for:

   - ✅ **Idle EC2 Instances** (with improved unused detection)
   - ✅ **Unattached EBS Volumes**
   - ✅ **Old AMIs**
   - ✅ **Unassociated Elastic IPs**
   - ✅ **Orphan Snapshots**
   - ✅ **Unused or Idle Lambda Functions** (new compute module)
   - ✅ **S3 Bucket Audit** (requires S3 Access Logs or CloudTrail)*
   - ✅ **Idle or Underutilized** EFS File Systems ✅ (new storage module)



   🔍 **Currently implemented:** EC2, Lambda, EBS, AMI, Elastic IP, Snapshot modules  
   🪣 **S3 Bucket Audit** *(requires S3 Access Logs or CloudTrail to be enabled)*

   ---

   ## ⚙️ Features

   - 📆 **Generates audit reports** in `.xlsx` format
   - 🎨 **Well-formatted Excel output** using styled formatting
   - 📁 **GUI output folder picker** using PyQt5
   - 🔐 **Secure credential entry** using pwinput
   - 🧠 **Improved idle EC2 detection** via usage patterns
   - ⚙️ **Audits Lambda usage**, concurrency, errors, and configuration suggestions
   - 💾 **EBS volume analysis** for unattached and unused volumes
   - 🖼️ **AMI lifecycle management** for old and unused images
   - 🌐 **Elastic IP optimization** for cost savings
   - 📸 **Snapshot cleanup** for orphaned backups
   - 🪣 **S3 Audit** for bucket usage insights *(requires S3 Access Logs or CloudTrail)*
   - 📂 **EFS file system audit** for identifying inactive file systems and lifecycle gaps ✅



   ---

   ## 🛠️ Development Status

   | Module                  | Status                                    |
   |-------------------------|-------------------------------------------|
   | EC2 Audit               | ✅ **Fully implemented**                  |
   | Lambda Audit            | ✅ **Implemented**                        |
   | EBS Volumes             | ✅ **Completed**                          |
   | AMIs                    | ✅ **Completed**                          |
   | Elastic IPs             | ✅ **Completed**                          |
   | Snapshots               | ✅ **Completed**                          |
   | Excel Export            | ✅ **Styled report output**               |
   | GUI Folder Picker       | ✅ **Cross-platform GUI**                 |
   | EFS Audit               | ✅ **Implemented**                        |
   | S3 Bucket Audit         | ✅ **Requires CloudTrail or S3 Access Logs** |


   ---

   ## 🧰 Prerequisites

   Ensure you have the following:

   - **Python 3.8+**
   - **AWS IAM Read-Only Access** credentials
   - **pip** and Python virtual environment setup (recommended)

   ---

   ## 📥 Installation

   ### 1. Clone the Repository
   ```bash
   git clone https://github.com/your-username/aws-resource-analyzer-bot.git
   cd aws-resource-analyzer-bot
   ```

   ### 2. Create & Activate Virtual Environment
   ```bash
   python3 -m venv venv
   source venv/bin/activate        # On Windows: venv\Scripts\activate
   ```

   ### 3. Install Dependencies
   ```bash
   pip install -r requirements.txt
   ```

   ---

   ## 🚀 Usage

   ### Run the bot:
   ```bash
   python audit_bot.py
   ```

   ### Follow the steps:

   1. **Provide AWS credentials:** Access Key, Secret Key, and Region
   2. **Set thresholds:**
      - Idle EC2 days (default: 7)
      - AMI age in days (default: 30)
   3. **Choose an output folder** using the GUI popup
   4. **Your report will be saved as:**
      ```
      cloud_audit_report.xlsx
      ```

   ---

   ## 📂 Output Example

   **File:** `cloud_audit_report.xlsx`

   - **Separate tabs** for each audited resource type
   - **Detailed analysis** for EC2, Lambda, EBS, AMI, Elastic IP, and Snapshots
   - **Clear indicators** for idle/unused resources
   - **Cost optimization recommendations**

   ---

   ## 🔒 Security Notice

   - ✅ **Credentials are not stored**
   - ✅ **Uses read-only access only**
   - ✅ **Always use least-privilege IAM policies**

   ---

   ## 🧭 Roadmap

   - [x] EC2 Audit (enhanced detection logic)
   - [x] Lambda Audit Module
   - [x] EBS Volume Analysis
   - [x] AMI Lifecycle Management
   - [x] Elastic IP Optimization
   - [x] Snapshot Cleanup
   - [x] Excel Export with formatting
   - [x] GUI Output Directory Picker
   - [x] EFS File System Audit
   - [x] S3 Bucket Audit 
   - [ ] Multi-region AWS Support
   - [ ] CLI Argument Support
   - [ ] RDS Instance Analysis
   - [ ] CloudWatch Integration

   ---

   ## 🤝 Contributing

   We welcome all PRs and suggestions!

   1. **Fork this repo**
   2. **Create a feature branch**
   3. **Submit a pull request**

   ---

   ## 📜 License

   **MIT License** © 2025

   ---

   ## 📬 Contact

   Questions or feature requests?

   📧 **vireshsolanki1027@gmail.com**

   ---

   ## 🏆 Key Benefits

   - **💰 Cost Optimization:** Identify unused resources costing you money
   - **🔍 Comprehensive Analysis:** Multi-service AWS resource scanning
   - **📊 Professional Reports:** Excel output with detailed recommendations
   - **🛡️ Security First:** Read-only access with secure credential handling
   - **🎯 Easy to Use:** Simple CLI interface with GUI components