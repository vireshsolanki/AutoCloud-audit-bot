
## 📌 Overview

The **AutoCloud Audit Bot** is a command-line + GUI hybrid Python tool designed to analyze your AWS account for **unused or idle resources**. It connects to your AWS account (with read-only permissions) and scans for:

✅ **Idle EC2 Instances**
✅ **Unattached EBS Volumes**
✅ **Old AMIs**
✅ **Unassociated Elastic IPs**
✅ **Orphan Snapshots**

Currently, **EC2 analysis is fully implemented**. Other modules are under development and will be expanded in future versions.

---

## ⚠️ Development Status

* ✅ EC2 Module — Fully implemented
* 📇 EBS, AMI, EIP, and Snapshot — In progress
* 🧪 Excel export is implemented using styled formatting
* 🧰 GUI directory picker using **PyQt5** (cross-platform)

---

## ⚙️ Features

* 📆 Generates a report in `.xlsx` format
* 🎨 Excel reports have clean formatting
* 🤝 Supports custom output directory selection (GUI)
* 🔐 Uses secure input for credentials via `pwinput`
* 💻 CLI-driven with OS-native GUI directory picker

---

## 🧰 Prerequisites

Make sure you have:

* Python **3.8+**
* AWS **IAM Read-Only** access credentials
* pip and virtual environment setup (recommended)

---

## 📥 Installation

1. **Clone the Repository**

```bash
git clone https://github.com/your-username/aws-resource-analyzer-bot.git
cd aws-resource-analyzer-bot
```

2. **Create & Activate Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**

```bash
pip install -r requirements.txt
```

---

## 🚀 How to Use

```bash
python audit_bot.py
```

1. Provide your AWS **Access Key**, **Secret Key**, and **Region**
2. Choose the thresholds for:

   * Idle EC2 days (default: 7)
   * AMI age (default: 30)
3. Select the **output folder** using the GUI popup
4. Receive your Excel report: `cloud_audit_report.xlsx`

---

## 📂 Output

A report file like:

```
cloud_audit_report.xlsx
```

with styled, structured data per AWS resource type.

---

## 🛡️ Security Notice

* Your credentials are **not stored**
* The script uses **read-only access**
* Always use IAM users with **minimal permissions**

---

## 📌 Roadmap

* [x] EC2 Audit
* [x] Excel Export
* [x] GUI Output Path Picker
* [ ] S3 Bucket Audit
* [ ] Lambda Cleanup Checks
* [ ] Multi-region Support
* [ ] CLI argument support

---

## 🙌 Contributing

We welcome PRs and issue reports! Just fork and submit your change.

---

## 📜 License

MIT License © 2025

---

## ✉️ Contact

Have feedback or feature requests? Open an issue or ping \[[vireshsolanki1027@gmail.com](mailto:vireshsolanki1027@gmail.com)].
