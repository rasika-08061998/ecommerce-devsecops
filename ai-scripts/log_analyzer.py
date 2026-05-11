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
    """Use Claude AI to analyze logs for anomalies."""
    prompt = f"""
You are a DevSecOps expert analyzing application logs.

Service: {service}
Logs:
{logs[:3000]}

Analyze these logs and provide a JSON response with:
{{
  "status": "healthy|warning|critical",
  "error_count": <number>,
  "warning_count": <number>,
  "anomalies": ["list of detected anomalies"],
  "security_issues": ["list of security concerns"],
  "performance_issues": ["list of performance problems"],
  "recommendations": ["list of action items"],
  "summary": "one line summary"
}}

Return ONLY the JSON, no other text.
"""
    response = ai_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        return json.loads(response.content[0].text)
    except Exception:
        return {
            "status": "unknown",
            "summary": response.content[0].text,
            "anomalies": [],
            "security_issues": [],
            "recommendations": []
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