# Pralay-VulX
Advanced Vulnerability Scanner - Pralay.VulX by Vimal Bijalwan
# 🔥 Pralay.VulX – Advanced Vulnerability Scanner

**Author:** Vimal Bijalwan  
**Version:** 2.0 (Live Progress Indicator)  
**Tagline:** *"No Firewall Can Stop The Apocalypse"*

Pralay.VulX is a powerful, all-in-one vulnerability scanner that combines **network scanning (Nmap)** with **deep web application fuzzing**. It automatically discovers parameters, tests for 7+ vulnerability classes, matches CVEs, and provides real-time progress updates. Built for ethical hackers, penetration testers, and security researchers.

---

## 📋 Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Command Line Options](#command-line-options)
- [Understanding the Output](#understanding-the-output)
- [Firewall Evasion Techniques](#firewall-evasion-techniques)
- [Sample Report](#sample-report)
- [Legal Disclaimer](#legal-disclaimer)
- [Author & Contact](#author--contact)
- [Star the Repo](#star-the-repo)

---

## ✨ Features

| Category | Capabilities |
|----------|--------------|
| **Network Scanning** | Port discovery, service version detection (`-sV`), Nmap vulners script for CVE matching |
| **Vulnerability Detection** | SQLi, XSS, LFI, RCE, SSTI, XXE, SSRF – **7+ payload types** |
| **Intelligent Crawling** | Automatically finds all links, forms, and input parameters |
| **Parameter Fuzzing** | Tests each parameter with hundreds of payloads |
| **Severity Scoring** | CVSS-based: **CRITICAL (9-10)**, **HIGH (7-8.9)**, **MEDIUM (4-6.9)**, **LOW (0-3.9)** |
| **Live Progress** | Real-time percentage, current parameter, and payload type |
| **Firewall Evasion** | Stealth mode (slow scan, decoy IPs, fragmentation) + Tor routing |
| **Report Generation** | Saves detailed findings to `PralayVulX_report_<target>.txt` |
| **Zero-Click Simplicity** | One command to rule them all |

---

## 📥 Installation

### Prerequisites
- Python 3.6 or higher
- Kali Linux / Ubuntu / Debian (recommended) or any Linux distro
- Internet connection for CVE API lookups

### Step 1: Clone the repository
```bash
git clone https://github.com/Hackteachbhai/Pralay-VulX  
cd Pralay-VulX
