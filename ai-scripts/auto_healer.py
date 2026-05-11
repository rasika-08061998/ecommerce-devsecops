#!/usr/bin/env python3
"""
Auto Healer — monitors pods and automatically restarts crashed ones.
Uses Claude AI to analyze the failure reason and suggest fixes.
"""

import time
import subprocess
import json
from datetime import datetime
from kubernetes import client, config
from anthropic import Anthropic
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv
import os

load_dotenv()

console = Console()
ai_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

NAMESPACES = ["ecommerce", "monitoring", "argocd"]
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))


def load_kube_config():
    """Load Kubernetes config."""
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()


def get_failed_pods(namespace: str) -> list:
    """Get all failed or crash-looping pods."""
    v1 = client.CoreV1Api()
    failed_pods = []

    pods = v1.list_namespaced_pod(namespace)
    for pod in pods.items:
        status = pod.status.phase
        name = pod.metadata.name

        # Check for CrashLoopBackOff or Error
        if pod.status.container_statuses:
            for cs in pod.status.container_statuses:
                if cs.state.waiting:
                    reason = cs.state.waiting.reason
                    if reason in ["CrashLoopBackOff", "Error", "OOMKilled", "ImagePullBackOff"]:
                        failed_pods.append({
                            "name": name,
                            "namespace": namespace,
                            "reason": reason,
                            "restart_count": cs.restart_count,
                            "container": cs.name
                        })
    return failed_pods


def get_pod_logs(pod_name: str, namespace: str, lines: int = 50) -> str:
    """Get recent logs from a pod."""
    try:
        v1 = client.CoreV1Api()
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=lines,
            previous=True
        )
        return logs
    except Exception as e:
        return f"Could not fetch logs: {str(e)}"


def analyze_with_ai(pod_name: str, namespace: str, reason: str, logs: str) -> str:
    """Use Claude AI to analyze pod failure and suggest fix."""
    prompt = f"""
You are a DevOps expert analyzing a Kubernetes pod failure.

Pod: {pod_name}
Namespace: {namespace}
Failure Reason: {reason}
Recent Logs:
{logs[:2000]}

Please provide:
1. Root cause of the failure (1-2 sentences)
2. Immediate fix (specific command or action)
3. Long term prevention (1-2 sentences)

Be concise and specific.
"""
    response = ai_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def restart_pod(pod_name: str, namespace: str):
    """Restart a pod by deleting it (deployment will recreate)."""
    v1 = client.CoreV1Api()
    try:
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        console.print(f"[green]✅ Restarted pod: {pod_name}[/green]")
        return True
    except Exception as e:
        console.print(f"[red]❌ Failed to restart {pod_name}: {e}[/red]")
        return False


def log_incident(pod_name: str, namespace: str, reason: str, ai_analysis: str):
    """Log incident to file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "pod": pod_name,
        "namespace": namespace,
        "reason": reason,
        "ai_analysis": ai_analysis
    }
    with open("ai-scripts/incidents.log", "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def display_status(all_failed: list):
    """Display current status table."""
    table = Table(title=f"🔍 Auto Healer Status — {datetime.now().strftime('%H:%M:%S')}")
    table.add_column("Pod", style="cyan")
    table.add_column("Namespace", style="blue")
    table.add_column("Reason", style="red")
    table.add_column("Restarts", style="yellow")

    for pod in all_failed:
        table.add_row(
            pod["name"],
            pod["namespace"],
            pod["reason"],
            str(pod["restart_count"])
        )

    console.print(table)


def main():
    """Main auto-healing loop."""
    console.print("[bold green]🤖 Auto Healer Started[/bold green]")
    console.print(f"Monitoring namespaces: {', '.join(NAMESPACES)}")
    console.print(f"Check interval: {CHECK_INTERVAL}s\n")

    load_kube_config()

    while True:
        all_failed = []

        for namespace in NAMESPACES:
            failed = get_failed_pods(namespace)
            all_failed.extend(failed)

        if all_failed:
            display_status(all_failed)

            for pod in all_failed:
                console.print(f"\n[yellow]🔍 Analyzing: {pod['name']}[/yellow]")

                # Get logs
                logs = get_pod_logs(pod["name"], pod["namespace"])

                # AI Analysis
                console.print("[blue]🤖 Getting AI analysis...[/blue]")
                analysis = analyze_with_ai(
                    pod["name"],
                    pod["namespace"],
                    pod["reason"],
                    logs
                )
                console.print(f"[italic]{analysis}[/italic]\n")

                # Log incident
                log_incident(pod["name"], pod["namespace"], pod["reason"], analysis)

                # Auto restart if CrashLoopBackOff
                if pod["reason"] == "CrashLoopBackOff" and pod["restart_count"] > 3:
                    console.print(f"[red]🔄 Auto-restarting {pod['name']}...[/red]")
                    restart_pod(pod["name"], pod["namespace"])
        else:
            console.print(f"[green]✅ All pods healthy — {datetime.now().strftime('%H:%M:%S')}[/green]")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()