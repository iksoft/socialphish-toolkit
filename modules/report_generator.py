#!/usr/bin/env python3

import os
import json
import datetime
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown
import matplotlib.pyplot as plt
import seaborn as sns

console = Console()

class ReportGenerator:
    def __init__(self):
        self.output_dir = 'output/reports'
        self.harvested_dir = 'output/harvested'
        self.qr_dir = 'output/qr_codes'
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """Ensure output directory exists."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def collect_data(self):
        """Collect data from all modules for reporting."""
        data = {
            'harvested_credentials': [],
            'qr_codes': [],
            'timestamp': datetime.datetime.now().isoformat()
        }

        # Collect harvested credentials
        if os.path.exists(self.harvested_dir):
            for file in os.listdir(self.harvested_dir):
                if file.endswith('.json'):
                    with open(os.path.join(self.harvested_dir, file)) as f:
                        try:
                            creds = json.load(f)
                            data['harvested_credentials'].extend(creds)
                        except json.JSONDecodeError:
                            console.print(f"[red]Error reading {file}[/red]")

        # Collect QR code information
        if os.path.exists(self.qr_dir):
            data['qr_codes'] = [f for f in os.listdir(self.qr_dir) if f.endswith('.png')]

        return data

    def generate_statistics(self, data):
        """Generate statistics from collected data."""
        stats = {
            'total_credentials': len(data['harvested_credentials']),
            'total_qr_codes': len(data['qr_codes']),
            'unique_ips': len(set(cred['ip_address'] for cred in data['harvested_credentials'])) if data['harvested_credentials'] else 0,
            'timestamp_range': {
                'start': min((cred['timestamp'] for cred in data['harvested_credentials']), default=None),
                'end': max((cred['timestamp'] for cred in data['harvested_credentials']), default=None)
            }
        }
        return stats

    def generate_graphs(self, data, report_dir):
        """Generate graphs for the report."""
        if not data['harvested_credentials']:
            return []

        graphs = []

        # Credentials over time
        plt.figure(figsize=(10, 6))
        timestamps = [datetime.datetime.fromisoformat(cred['timestamp']) for cred in data['harvested_credentials']]
        plt.hist(timestamps, bins=20)
        plt.title('Credentials Harvested Over Time')
        plt.xlabel('Time')
        plt.ylabel('Number of Credentials')
        plt.xticks(rotation=45)
        graph_path = os.path.join(report_dir, 'credentials_timeline.png')
        plt.savefig(graph_path)
        plt.close()
        graphs.append('credentials_timeline.png')

        # User agent distribution
        plt.figure(figsize=(10, 6))
        user_agents = [cred['user_agent'].split()[0] for cred in data['harvested_credentials']]
        sns.countplot(y=user_agents)
        plt.title('User Agent Distribution')
        plt.xlabel('Count')
        plt.ylabel('User Agent')
        graph_path = os.path.join(report_dir, 'user_agents.png')
        plt.savefig(graph_path)
        plt.close()
        graphs.append('user_agents.png')

        return graphs

    def generate_report(self, data, stats, graphs):
        """Generate a markdown report."""
        report = f"""# Social Engineering Campaign Report
        
## Overview
Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Statistics
- Total Credentials Harvested: {stats['total_credentials']}
- Unique IP Addresses: {stats['unique_ips']}
- QR Codes Generated: {stats['total_qr_codes']}

## Campaign Timeline
- Start: {stats['timestamp_range']['start']}
- End: {stats['timestamp_range']['end']}

## Harvested Credentials Summary
"""
        
        if data['harvested_credentials']:
            report += "\n### Recent Credentials\n"
            for cred in data['harvested_credentials'][-5:]:  # Show last 5 entries
                report += f"""
- Timestamp: {cred['timestamp']}
- IP: {cred['ip_address']}
- Data: {json.dumps(cred['credentials'], indent=2)}
"""

        if graphs:
            report += "\n## Visualizations\n"
            for graph in graphs:
                report += f"\n![{graph}]({graph})\n"

        return report

    def create_report(self):
        """Create a complete report."""
        # Create report directory
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = os.path.join(self.output_dir, f'report_{timestamp}')
        os.makedirs(report_dir, exist_ok=True)

        # Collect and process data
        data = self.collect_data()
        stats = self.generate_statistics(data)
        graphs = self.generate_graphs(data, report_dir)

        # Generate report
        report_content = self.generate_report(data, stats, graphs)
        report_file = os.path.join(report_dir, 'report.md')

        with open(report_file, 'w') as f:
            f.write(report_content)

        # Display report
        console.print(Markdown(report_content))
        console.print(f"\n[green]Report generated: {report_file}[/green]")

    def run(self):
        """Main method to run the report generator module."""
        console.print(Panel("[bold red]Report Generator Module[/bold red]"))

        while True:
            console.print("\n1. Generate New Report")
            console.print("2. Back to Main Menu")

            choice = Prompt.ask("Select an option", choices=["1", "2"])

            if choice == "1":
                self.create_report()
            elif choice == "2":
                break 