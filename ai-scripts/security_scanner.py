#!/usr/bin/env python3
"""
Security Scanner — runs Trivy scans on all ECR images
and uses Claude AI to prioritize and explain vulnerabilities.
"""

import os
import json
import subprocess
from datetime import datetime
from anthropic import Anthropic
import boto3
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from dotenv import load_dotenv

load_dotenv()

console = Console()
ai_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_ACCOUNT_ID = "528757804354"
ECR_REGISTRY = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com"

SERVICES = [
    "ecommerce-dev-user-service",
    "ecommerce-dev-product-service",
    "ecommerce-dev-order-service",
    "ecommerce-dev-payment-service",
    "ecommerce-dev-api-gateway",
    "ecommerce-dev-frontend"
]


def login_to_ecr():
    """Login to ECR."""
    console.print("[yellow]Logging in to ECR...[/yellow]")
    cmd = f"aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {ECR_REGISTRY}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        console.print("[green]✅ ECR login successful[/green]")
        return True
    else:
        console.print(f"[red]❌ ECR login failed: {result.stderr}[/red]")
        return False


def run_trivy_scan(image_url: str) -> dict:
    """Run Trivy scan on a Docker image."""
    cmd = [
        "trivy", "image",
        "--format", "json",
        "--severity", "CRITICAL,HIGH,MEDIUM",
        "--no-progress",
        image_url
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        return json.loads(result.stdout)
    except Exception:
        return {"error": result.stderr, "Results": []}


def parse_vulnerabilities(scan_result: dict) -> dict:
    """Parse Trivy scan results."""
    summary = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "vulnerabilities": []
    }

    for result in scan_result.get("Results", []):
        for vuln in result.get("Vulnerabilities", []):
            severity = vuln.get("Severity", "UNKNOWN")
            summary[severity] = summary.get(severity, 0) + 1
            if severity in ["CRITICAL", "HIGH"]:
                summary["vulnerabilities"].append({
                    "id": vuln.get("VulnerabilityID"),
                    "severity": severity,
                    "package": vuln.get("PkgName"),
                    "version": vuln.get("InstalledVersion"),
                    "fixed_version": vuln.get("FixedVersion", "No fix available"),
                    "title": vuln.get("Title", "")[:100]
                })

    return summary


def analyze_vulnerabilities_with_ai(
    service: str,
    summary: dict
) -> str:
    """Use Claude AI to analyze and prioritize vulnerabilities."""
    prompt = f"""
You are a security expert analyzing container vulnerabilities.

Service: {service}
Vulnerability Summary:
- CRITICAL: {summary['CRITICAL']}
- HIGH: {summary['HIGH']}
- MEDIUM: {summary['MEDIUM']}

Top Critical/High Vulnerabilities:
{json.dumps(summary['vulnerabilities'][:10], indent=2)}

Please provide:
1. Risk assessment (1-2 sentences)
2. Top 3 vulnerabilities to fix immediately with fix commands
3. Overall security score (0-10)
4. Recommended base image upgrade if applicable

Be specific and actionable.
"""

    response = ai_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def display_scan_summary(service: str, summary: dict):
    """Display vulnerability summary table."""
    critical = summary["CRITICAL"]
    high = summary["HIGH"]
    medium = summary["MEDIUM"]

    status_color = "red" if critical > 0 else "yellow" if high > 0 else "green"
    status = "CRITICAL" if critical > 0 else "HIGH" if high > 0 else "OK"

    console.print(f"\n[{status_color}]{'='*50}[/{status_color}]")
    console.print(f"[bold]{service}[/bold] — [{status_color}]{status}[/{status_color}]")
    console.print(f"  🔴 CRITICAL: {critical}")
    console.print(f"  🟠 HIGH:     {high}")
    console.print(f"  🟡 MEDIUM:   {medium}")


def save_security_report(results: list):
    """Save security scan report."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": timestamp,
        "scan_results": results
    }
    filename = f"ai-scripts/security_report_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(report, f, indent=2)
    console.print(f"\n[green]📄 Security report: {filename}[/green]")
    return filename


def main():
    """Main security scanning function."""
    console.print("[bold red]🔒 Security Scanner Started[/bold red]\n")

    # Login to ECR
    if not login_to_ecr():
        console.print("[red]Cannot proceed without ECR access[/red]")
        return

    results = []
    total_critical = 0
    total_high = 0

    for service in SERVICES:
        image_url = f"{ECR_REGISTRY}/{service}:latest"
        console.print(f"\n[yellow]🔍 Scanning: {service}[/yellow]")

        # Run Trivy scan
        scan_result = run_trivy_scan(image_url)

        if "error" in scan_result:
            console.print(f"[red]Scan failed: {scan_result['error'][:100]}[/red]")
            continue

        # Parse results
        summary = parse_vulnerabilities(scan_result)
        total_critical += summary["CRITICAL"]
        total_high += summary["HIGH"]

        # Display summary
        display_scan_summary(service, summary)

        # AI Analysis for critical/high findings
        if summary["CRITICAL"] > 0 or summary["HIGH"] > 0:
            console.print("[blue]🤖 Getting AI security analysis...[/blue]")
            ai_analysis = analyze_vulnerabilities_with_ai(service, summary)
            console.print(Panel(
                ai_analysis,
                title=f"🤖 AI Analysis — {service}",
                border_style="blue"
            ))
        else:
            ai_analysis = "No critical or high vulnerabilities found."

        results.append({
            "service": service,
            "summary": summary,
            "ai_analysis": ai_analysis
        })

    # Overall summary
    console.print("\n" + "="*50)
    console.print("[bold]🔒 Security Scan Complete[/bold]")
    console.print(f"  Services scanned: {len(results)}")
    console.print(f"  [red]Total CRITICAL: {total_critical}[/red]")
    console.print(f"  [yellow]Total HIGH: {total_high}[/yellow]")

    overall_status = "CRITICAL" if total_critical > 10 else \
                     "HIGH" if total_high > 20 else "OK"
    console.print(f"  Overall Status: {overall_status}")

    # Save report
    save_security_report(results)


if __name__ == "__main__":
    main()