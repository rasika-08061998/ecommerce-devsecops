#!/usr/bin/env python3
"""
Cost Monitor — tracks AWS costs using Cost Explorer
and uses Claude AI to analyze spending patterns and anomalies.
"""

import os
import json
from datetime import datetime, timedelta
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


def get_cost_by_service(days: int = 7) -> dict:
    """Get AWS costs broken down by service."""
    ce = boto3.client("ce", region_name="us-east-1")

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    response = ce.get_cost_and_usage(
        TimePeriod={"Start": start, "End": end},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]
    )

    costs = {}
    for result in response["ResultsByTime"]:
        date = result["TimePeriod"]["Start"]
        for group in result["Groups"]:
            service = group["Keys"][0]
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            if service not in costs:
                costs[service] = {}
            costs[service][date] = round(amount, 4)

    return costs


def get_total_cost(days: int = 30) -> float:
    """Get total AWS cost for period."""
    ce = boto3.client("ce", region_name="us-east-1")

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    response = ce.get_cost_and_usage(
        TimePeriod={"Start": start, "End": end},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"]
    )

    total = sum(
        float(r["Total"]["UnblendedCost"]["Amount"])
        for r in response["ResultsByTime"]
    )
    return round(total, 2)


def get_eks_costs(days: int = 7) -> dict:
    """Get EKS specific costs."""
    ce = boto3.client("ce", region_name="us-east-1")

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    response = ce.get_cost_and_usage(
        TimePeriod={"Start": start, "End": end},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        Filter={
            "Dimensions": {
                "Key": "SERVICE",
                "Values": [
                    "Amazon Elastic Kubernetes Service",
                    "Amazon EC2",
                    "Amazon Elastic Container Registry (Amazon ECR)",
                    "Amazon Virtual Private Cloud"
                ]
            }
        },
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]
    )

    costs = {}
    for result in response["ResultsByTime"]:
        for group in result["Groups"]:
            service = group["Keys"][0]
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            costs[service] = costs.get(service, 0) + amount

    return {k: round(v, 4) for k, v in costs.items()}


def analyze_costs_with_ai(costs: dict, total: float, eks_costs: dict) -> str:
    """Use Claude AI to analyze costs and provide recommendations."""
    prompt = f"""
You are a cloud cost optimization expert analyzing AWS costs.

Total Cost (last 30 days): ${total}

EKS Platform Costs (last 7 days):
{json.dumps(eks_costs, indent=2)}

Top Services by Cost:
{json.dumps(dict(list(costs.items())[:10]), indent=2)}

Please provide:
1. Cost analysis summary
2. Top 3 cost optimization recommendations specific to EKS
3. Estimated monthly savings if recommendations are implemented
4. Any cost anomalies detected

Be specific with dollar amounts and actionable advice.
"""

    response = ai_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def display_cost_table(eks_costs: dict):
    """Display cost breakdown table."""
    table = Table(title="💰 EKS Platform Costs (Last 7 Days)")
    table.add_column("AWS Service", style="cyan")
    table.add_column("Cost (USD)", style="yellow", justify="right")

    sorted_costs = sorted(eks_costs.items(), key=lambda x: x[1], reverse=True)
    for service, cost in sorted_costs:
        color = "red" if cost > 10 else "yellow" if cost > 5 else "green"
        table.add_row(service, f"[{color}]${cost:.4f}[/{color}]")

    console.print(table)


def save_cost_report(total: float, eks_costs: dict, ai_analysis: str):
    """Save cost report."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": timestamp,
        "total_cost_30_days": total,
        "eks_costs_7_days": eks_costs,
        "ai_analysis": ai_analysis
    }
    filename = f"ai-scripts/cost_report_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(report, f, indent=2)
    console.print(f"\n[green]📄 Cost report saved: {filename}[/green]")


def check_budget_alert(total: float, budget: float = 200.0):
    """Alert if costs exceed budget."""
    percentage = (total / budget) * 100
    if percentage > 90:
        console.print(Panel(
            f"[red]⚠️  BUDGET ALERT!\n"
            f"Current spend: ${total:.2f}\n"
            f"Budget: ${budget:.2f}\n"
            f"Usage: {percentage:.1f}%[/red]",
            title="💸 Budget Warning",
            border_style="red"
        ))
    elif percentage > 70:
        console.print(Panel(
            f"[yellow]⚠️  Budget Warning\n"
            f"Current spend: ${total:.2f}\n"
            f"Budget: ${budget:.2f}\n"
            f"Usage: {percentage:.1f}%[/yellow]",
            title="💰 Budget Notice",
            border_style="yellow"
        ))
    else:
        console.print(Panel(
            f"[green]✅ Budget OK\n"
            f"Current spend: ${total:.2f}\n"
            f"Budget: ${budget:.2f}\n"
            f"Usage: {percentage:.1f}%[/green]",
            title="💰 Budget Status",
            border_style="green"
        ))


def main():
    """Main cost monitoring function."""
    console.print("[bold green]💰 AWS Cost Monitor Started[/bold green]\n")

    # Get costs
    console.print("[yellow]Fetching AWS costs...[/yellow]")
    costs = get_cost_by_service(days=7)
    total = get_total_cost(days=30)
    eks_costs = get_eks_costs(days=7)

    # Display table
    display_cost_table(eks_costs)

    # Budget check
    console.print()
    check_budget_alert(total)

    # AI Analysis
    console.print("\n[blue]🤖 Getting AI cost analysis...[/blue]")
    analysis = analyze_costs_with_ai(costs, total, eks_costs)

    console.print(Panel(
        analysis,
        title="🤖 AI Cost Analysis",
        border_style="blue"
    ))

    # Save report
    save_cost_report(total, eks_costs, analysis)


if __name__ == "__main__":
    main()