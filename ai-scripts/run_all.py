#!/usr/bin/env python3
"""
DevSecOps AI Control Center
Runs all monitoring scripts and provides unified dashboard.
"""

import os
import sys
import time
import schedule
import threading
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from dotenv import load_dotenv

load_dotenv()

console = Console()

# ─── Import all scripts ───────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))


def run_auto_healer():
    """Run auto healer once."""
    console.print("\n[bold green]🤖 Running Auto Healer...[/bold green]")
    try:
        from auto_healer import load_kube_config, get_failed_pods, \
            get_pod_logs, analyze_with_ai, restart_pod, log_incident

        NAMESPACES = ["ecommerce", "monitoring", "argocd"]
        load_kube_config()

        all_failed = []
        for namespace in NAMESPACES:
            failed = get_failed_pods(namespace)
            all_failed.extend(failed)

        if all_failed:
            console.print(f"[red]Found {len(all_failed)} failed pods![/red]")
            for pod in all_failed:
                logs = get_pod_logs(pod["name"], pod["namespace"])
                analysis = analyze_with_ai(
                    pod["name"], pod["namespace"],
                    pod["reason"], logs
                )
                console.print(f"[yellow]{pod['name']}:[/yellow] {analysis[:200]}")
                log_incident(pod["name"], pod["namespace"],
                           pod["reason"], analysis)
                if pod["restart_count"] > 3:
                    restart_pod(pod["name"], pod["namespace"])
        else:
            console.print("[green]✅ All pods healthy[/green]")

    except Exception as e:
        console.print(f"[red]Auto Healer Error: {e}[/red]")


def run_log_analyzer():
    """Run log analyzer once."""
    console.print("\n[bold blue]🔍 Running Log Analyzer...[/bold blue]")
    try:
        from log_analyzer import load_kube_config, get_deployment_logs, \
            analyze_logs_with_ai, display_analysis

        SERVICES = ["api-gateway", "user-service",
                   "product-service", "order-service", "payment-service"]

        load_kube_config()

        for service in SERVICES:
            logs = get_deployment_logs("ecommerce", service, lines=50)
            if logs.strip():
                analysis = analyze_logs_with_ai(service, logs)
                display_analysis(service, analysis)

    except Exception as e:
        console.print(f"[red]Log Analyzer Error: {e}[/red]")


def run_cost_monitor():
    """Run cost monitor once."""
    console.print("\n[bold yellow]💰 Running Cost Monitor...[/bold yellow]")
    try:
        from cost_monitor import get_total_cost, get_eks_costs, \
            analyze_costs_with_ai, display_cost_table, check_budget_alert

        total = get_total_cost(days=30)
        eks_costs = get_eks_costs(days=7)

        display_cost_table(eks_costs)
        check_budget_alert(total)

        console.print(f"\n[yellow]Total cost (30 days): ${total}[/yellow]")

    except Exception as e:
        console.print(f"[red]Cost Monitor Error: {e}[/red]")


def run_security_scanner():
    """Run security scanner once."""
    console.print("\n[bold red]🔒 Running Security Scanner...[/bold red]")
    try:
        from security_scanner import login_to_ecr, run_trivy_scan, \
            parse_vulnerabilities, display_scan_summary

        SERVICES = [
            "ecommerce-dev-api-gateway",
            "ecommerce-dev-user-service"
        ]
        ECR_REGISTRY = "528757804354.dkr.ecr.ap-south-1.amazonaws.com"

        if login_to_ecr():
            for service in SERVICES:
                image_url = f"{ECR_REGISTRY}/{service}:latest"
                result = run_trivy_scan(image_url)
                summary = parse_vulnerabilities(result)
                display_scan_summary(service, summary)

    except Exception as e:
        console.print(f"[red]Security Scanner Error: {e}[/red]")


def display_banner():
    """Display startup banner."""
    console.print(Panel(
        """
[bold green]
██████╗ ███████╗██╗   ██╗███████╗███████╗ ██████╗ ██████╗ ███████╗
██╔══██╗██╔════╝██║   ██║██╔════╝██╔════╝██╔════╝██╔═══██╗██╔════╝
██║  ██║█████╗  ██║   ██║███████╗█████╗  ██║     ██║   ██║███████╗
██║  ██║██╔══╝  ╚██╗ ██╔╝╚════██║██╔══╝  ██║     ██║   ██║╚════██║
██████╔╝███████╗ ╚████╔╝ ███████║███████╗╚██████╗╚██████╔╝███████║
╚═════╝ ╚══════╝  ╚═══╝  ╚══════╝╚══════╝ ╚═════╝ ╚═════╝ ╚══════╝
[/bold green]
[bold blue]        AI-Powered DevSecOps Control Center[/bold blue]
[yellow]        Ecommerce Platform on AWS EKS[/yellow]
        """,
        title="🚀 DevSecOps AI Platform",
        border_style="green"
    ))


def display_menu():
    """Display interactive menu."""
    table = Table(title="Available Commands")
    table.add_column("Option", style="cyan", justify="center")
    table.add_column("Script", style="green")
    table.add_column("Description", style="white")
    table.add_column("Schedule", style="yellow")

    table.add_row("1", "Auto Healer",      "Monitor & fix crashed pods",      "Every 30s")
    table.add_row("2", "Log Analyzer",     "AI log analysis",                 "Every 1h")
    table.add_row("3", "Cost Monitor",     "AWS cost tracking",               "Every 24h")
    table.add_row("4", "Security Scanner", "Trivy vulnerability scan",        "Every 12h")
    table.add_row("5", "Run All Once",     "Run all scripts once",            "Manual")
    table.add_row("6", "Schedule All",     "Run on schedule (daemon mode)",   "Auto")
    table.add_row("q", "Quit",             "Exit the control center",         "-")

    console.print(table)


def run_scheduled():
    """Run scripts on schedule."""
    console.print("[bold green]🕐 Starting Scheduled Mode[/bold green]")
    console.print("Press Ctrl+C to stop\n")

    # Schedule jobs
    schedule.every(30).seconds.do(run_auto_healer)
    schedule.every(1).hours.do(run_log_analyzer)
    schedule.every(24).hours.do(run_cost_monitor)
    schedule.every(12).hours.do(run_security_scanner)

    # Run immediately
    run_auto_healer()
    run_log_analyzer()

    console.print("\n[green]✅ Scheduler started![/green]")
    console.print("[yellow]Auto Healer: every 30s[/yellow]")
    console.print("[yellow]Log Analyzer: every 1h[/yellow]")
    console.print("[yellow]Cost Monitor: every 24h[/yellow]")
    console.print("[yellow]Security Scanner: every 12h[/yellow]\n")

    while True:
        schedule.run_pending()
        time.sleep(1)


def main():
    """Main control center."""
    display_banner()

    while True:
        display_menu()
        choice = console.input("\n[bold cyan]Enter option: [/bold cyan]").strip()

        if choice == "1":
            run_auto_healer()
        elif choice == "2":
            run_log_analyzer()
        elif choice == "3":
            run_cost_monitor()
        elif choice == "4":
            run_security_scanner()
        elif choice == "5":
            console.print("\n[bold]Running all scripts...[/bold]")
            run_auto_healer()
            run_log_analyzer()
            run_cost_monitor()
            run_security_scanner()
        elif choice == "6":
            run_scheduled()
        elif choice.lower() == "q":
            console.print("[yellow]Goodbye! 👋[/yellow]")
            break
        else:
            console.print("[red]Invalid option. Try again.[/red]")


if __name__ == "__main__":
    main()