#!/usr/bin/env python3

import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
import validators

console = Console()

class EmailPhisher:
    def __init__(self):
        self.config = {
            'smtp_server': '',
            'smtp_port': 587,
            'email': '',
            'password': ''
        }
        self.templates_dir = 'templates/email'
        self._ensure_templates_dir()

    def _ensure_templates_dir(self):
        """Ensure templates directory exists and create default templates if needed."""
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir, exist_ok=True)
            self._create_default_templates()

    def _create_default_templates(self):
        """Create default phishing email templates."""
        templates = {
            'password_reset.html': '''
            <html>
            <body>
            <h2>Security Alert: Password Reset Required</h2>
            <p>Dear {target_name},</p>
            <p>We detected unusual activity on your account. Please reset your password immediately by clicking the link below:</p>
            <p><a href="{phishing_url}">Reset Password</a></p>
            <p>If you didn't request this change, please ignore this email.</p>
            </body>
            </html>
            ''',
            'account_verification.html': '''
            <html>
            <body>
            <h2>Account Verification Required</h2>
            <p>Dear {target_name},</p>
            <p>Your account requires verification. Please click the link below to verify your identity:</p>
            <p><a href="{phishing_url}">Verify Account</a></p>
            <p>This link will expire in 24 hours.</p>
            </body>
            </html>
            '''
        }
        
        for template_name, content in templates.items():
            with open(os.path.join(self.templates_dir, template_name), 'w') as f:
                f.write(content)

    def setup_smtp(self):
        """Configure SMTP settings for sending emails."""
        console.print(Panel("[yellow]SMTP Configuration[/yellow]"))
        
        self.config['smtp_server'] = Prompt.ask("Enter SMTP server")
        self.config['smtp_port'] = int(Prompt.ask("Enter SMTP port", default="587"))
        self.config['email'] = Prompt.ask("Enter email address")
        self.config['password'] = Prompt.ask("Enter password", password=True)

    def load_template(self, template_name):
        """Load an email template from the templates directory."""
        template_path = os.path.join(self.templates_dir, template_name)
        try:
            with open(template_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            console.print(f"[red]Template {template_name} not found![/red]")
            return None

    def send_phishing_email(self, target_email, target_name, template_name, phishing_url):
        """Send a phishing email to the target."""
        if not validators.email(target_email):
            console.print("[red]Invalid target email address![/red]")
            return False

        if not validators.url(phishing_url):
            console.print("[red]Invalid phishing URL![/red]")
            return False

        template_content = self.load_template(template_name)
        if not template_content:
            return False

        # Prepare the email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Important Security Notice"
        msg['From'] = self.config['email']
        msg['To'] = target_email

        # Format template with target information
        html_content = template_content.format(
            target_name=target_name,
            phishing_url=phishing_url
        )

        msg.attach(MIMEText(html_content, 'html'))

        try:
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['email'], self.config['password'])
                server.send_message(msg)
            console.print("[green]Phishing email sent successfully![/green]")
            return True
        except Exception as e:
            console.print(f"[red]Failed to send email: {str(e)}[/red]")
            return False

    def run(self):
        """Main method to run the email phishing module."""
        console.print(Panel("[bold red]Email Phishing Module[/bold red]"))
        
        if not all(self.config.values()):
            self.setup_smtp()

        while True:
            console.print("\n1. Send Phishing Email")
            console.print("2. View Templates")
            console.print("3. Back to Main Menu")
            
            choice = Prompt.ask("Select an option", choices=["1", "2", "3"])

            if choice == "1":
                target_email = Prompt.ask("Enter target email")
                target_name = Prompt.ask("Enter target name")
                template_name = Prompt.ask("Enter template name (e.g., password_reset.html)")
                phishing_url = Prompt.ask("Enter phishing URL")
                
                self.send_phishing_email(target_email, target_name, template_name, phishing_url)
            
            elif choice == "2":
                templates = os.listdir(self.templates_dir)
                console.print("\nAvailable Templates:")
                for template in templates:
                    console.print(f"- {template}")
            
            elif choice == "3":
                break 