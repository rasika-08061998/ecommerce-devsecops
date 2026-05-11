#!/usr/bin/env python3
"""
Log Analyzer — uses Claude AI to analyze application logs
and detect anomalies, errors and security issues.
"""

import json
import os
from datetime import datetime
from kubernetes import client, config
from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

load_dotenv()

console = Console()
ai_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SERVICES = {
    "ecommerce": [
        "api-gateway",
        "user-service",
        "product-service",
        "order-service",
        "payment-service"
    ]
}


def load_kube_config():
    """Load Kubernetes config."""
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()


def get_deployment_logs(namespace: str, deployment: str, lines: int = 100) -> str:
    """Get logs from all pods in a deployment."""
    v1 = client.CoreV1Api()
    logs = []

    pods = v1.list_namespaced_pod(
        namespace,
        label_selector=f"app={deployment}"
    )

    for pod in pods.items:
        try:
            log = v1.read_namespaced_pod_log(
                name=pod.metadata.name,
                namespace=namespace,
                tail_lines=lines
            )
            logs.append(f"=== Pod: {pod.metadata.name} ===\n{log}")
        except Exception as e:
            logs.append(f"=== Pod: {pod.metadata.name} === ERROR: {e}")

    return "\n".join(logs)


def analyze_logs_with_ai(service: str, logs: str) -> dict:
    """Rule-based log analysis without AI API."""
    logs_lower = logs.lower()

    error_count = logs_lower.count("error")
    warning_count = logs_lower.count("warning") + logs_lower.count("warn")

    anomalies = []
    security_issues = []
    performance_issues = []
    recommendations = []

    # Detect anomalies
    if "connection refused" in logs_lower:
        anomalies.append("Database/service connection refused")
        recommendations.append("Check if dependent services are running")

    if "timeout" in logs_lower:
        anomalies.append("Timeout detected in service calls")
        recommendations.append("Check network policies and service endpoints")

    if "out of memory" in logs_lower or "oom" in logs_lower:
        anomalies.append("Out of memory error detected")
        recommendations.append("Increase memory limits in Helm values.yaml")

    if "unauthorized" in logs_lower or "403" in logs_lower:
        security_issues.append("Unauthorized access attempts detected")
        recommendations.append("Review IAM roles and RBAC policies")

    if "sql" in logs_lower and "error" in logs_lower:
        anomalies.append("SQL errors detected")
        recommendations.append("Check database migrations and schema")

    if "500" in logs_lower:
        performance_issues.append("HTTP 500 errors detected")
        recommendations.append("Review application error handling")

    if not anomalies and not security_issues:
        recommendations.append("No issues detected — service running normally")

    # Determine status
    if any("critical" in a.lower() or "oom" in a.lower() for a in anomalies):
        status = "critical"
    elif error_count > 10 or security_issues:
        status = "warning"
    else:
        status = "healthy"

    return {
        "status": status,
        "error_count": error_count,
        "warning_count": warning_count,
        "anomalies": anomalies or ["None detected"],
        "security_issues": security_issues or ["None detected"],
        "performance_issues": performance_issues or ["None detected"],
        "recommendations": recommendations,
        "summary": f"{error_count} errors, {warning_count} warnings found"
    }

def display_analysis(service: str, analysis: dict):
    """Display analysis results."""
    status = analysis.get("status", "unknown")
    color = {
        "healthy": "green",
        "warning": "yellow",
        "critical": "red",
        "unknown": "blue"
    }.get(status, "blue")

    console.print(Panel(
        f"""
[bold]Status:[/bold] [{color}]{status.upper()}[/{color}]
[bold]Summary:[/bold] {analysis.get('summary', 'N/A')}
[bold]Errors:[/bold] {analysis.get('error_count', 0)}
[bold]Warnings:[/bold] {analysis.get('warning_count', 0)}

[bold yellow]Anomalies:[/bold yellow]
{chr(10).join(['• ' + a for a in analysis.get('anomalies', ['None detected'])])}

[bold red]Security Issues:[/bold red]
{chr(10).join(['• ' + s for s in analysis.get('security_issues', ['None detected'])])}

[bold blue]Recommendations:[/bold blue]
{chr(10).join(['• ' + r for r in analysis.get('recommendations', ['No actions needed'])])}
        """,
        title=f"🔍 {service} Log Analysis",
        border_style=color
    ))


def save_report(results: list):
    """Save analysis report to file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": timestamp,
        "results": results
    }
    filename = f"ai-scripts/log_report_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(report, f, indent=2)
    console.print(f"\n[green]📄 Report saved: {filename}[/green]")


def main():
    """Main log analysis function."""
    console.print("[bold green]🔍 AI Log Analyzer Started[/bold green]\n")

    load_kube_config()

    results = []

    for namespace, services in SERVICES.items():
        console.print(f"[bold blue]Namespace: {namespace}[/bold blue]")

        for service in services:
            console.print(f"\n[yellow]Analyzing {service}...[/yellow]")

            # Get logs
            logs = get_deployment_logs(namespace, service)

            if not logs.strip():
                console.print(f"[muted]No logs found for {service}[/muted]")
                continue

            # AI Analysis
            analysis = analyze_logs_with_ai(service, logs)
            display_analysis(service, analysis)

            results.append({
                "service": service,
                "namespace": namespace,
                "analysis": analysis
            })

    # Save report
    save_report(results)

    # Summary
    critical = [r for r in results if r["analysis"].get("status") == "critical"]
    warnings = [r for r in results if r["analysis"].get("status") == "warning"]

    console.print(f"\n[bold]📊 Summary:[/bold]")
    console.print(f"  Total services analyzed: {len(results)}")
    console.print(f"  [red]Critical: {len(critical)}[/red]")
    console.print(f"  [yellow]Warnings: {len(warnings)}[/yellow]")
    console.print(f"  [green]Healthy: {len(results) - len(critical) - len(warnings)}[/green]")


if __name__ == "__main__":
    main()