#!/usr/bin/env python3

import os
import qrcode
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
import validators
from PIL import Image, ImageDraw, ImageFont
import datetime

console = Console()

class QRPhisher:
    def __init__(self):
        self.output_dir = 'output/qr_codes'
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """Ensure output directory exists."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def generate_qr_code(self, url, template="default"):
        """Generate a QR code with optional template."""
        if not validators.url(url):
            console.print("[red]Invalid URL provided![/red]")
            return None

        # Create QR code with better error correction and size
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # Higher error correction
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Create QR code image with better contrast
        qr_image = qr.make_image(fill_color="black", back_color="white")

        if template == "wifi":
            # Create a template for WiFi connection with improved styling
            final_image = Image.new('RGB', (500, 600), 'white')
            draw = ImageDraw.Draw(final_image)
            
            # Add WiFi symbol and text with better positioning
            try:
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
                font_subtitle = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            except:
                font_title = ImageFont.load_default()
                font_subtitle = ImageFont.load_default()
            
            # Center-align text
            title_text = "Free WiFi"
            subtitle_text = "Scan to Connect"
            title_width = draw.textlength(title_text, font=font_title) if hasattr(draw, 'textlength') else 150
            subtitle_width = draw.textlength(subtitle_text, font=font_subtitle) if hasattr(draw, 'textlength') else 120
            
            draw.text(((500 - title_width) // 2, 30), title_text, fill="black", font=font_title)
            draw.text(((500 - subtitle_width) // 2, 80), subtitle_text, fill="black", font=font_subtitle)
            
            # Center the QR code
            qr_pos = ((500 - qr_image.size[0]) // 2, 150)
            final_image.paste(qr_image, qr_pos)
            
        elif template == "payment":
            # Create a template for payment with improved styling
            final_image = Image.new('RGB', (500, 700), 'white')
            draw = ImageDraw.Draw(final_image)
            
            try:
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
                font_subtitle = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            except:
                font_title = ImageFont.load_default()
                font_subtitle = ImageFont.load_default()
            
            # Center-align text
            title_text = "Quick Pay"
            subtitle_text = "Scan to Pay Securely"
            title_width = draw.textlength(title_text, font=font_title) if hasattr(draw, 'textlength') else 150
            subtitle_width = draw.textlength(subtitle_text, font=font_subtitle) if hasattr(draw, 'textlength') else 120
            
            draw.text(((500 - title_width) // 2, 30), title_text, fill="black", font=font_title)
            draw.text(((500 - subtitle_width) // 2, 80), subtitle_text, fill="black", font=font_subtitle)
            
            # Center the QR code
            qr_pos = ((500 - qr_image.size[0]) // 2, 150)
            final_image.paste(qr_image, qr_pos)
            
        else:
            final_image = qr_image

        # Save the QR code with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.output_dir, f'qr_code_{template}_{timestamp}.png')
        final_image.save(output_path, quality=95)  # Higher quality save
        
        # Display QR in console
        self.display_qr_in_console(url)
        
        console.print(f"[green]QR code generated successfully: {output_path}[/green]")
        return output_path

    def display_qr_in_console(self, url):
        """Display QR code in the console."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=0.5,  # Reduced from 1 to 0.5
            border=0,      # Reduced from 1 to 0
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Create a string representation of the QR code
        console.print("\n[bold white]Scan this QR code:[/bold white]")
        qr.print_ascii(invert=True)  # White QR code on console

    def list_generated_codes(self):
        """List all generated QR codes."""
        if not os.path.exists(self.output_dir):
            console.print("[yellow]No QR codes generated yet.[/yellow]")
            return

        files = os.listdir(self.output_dir)
        if not files:
            console.print("[yellow]No QR codes generated yet.[/yellow]")
            return

        console.print("\n[bold]Generated QR Codes:[/bold]")
        for file in files:
            console.print(f"- {file}")

    def run(self):
        """Main method to run the QR phishing module."""
        console.print(Panel("[bold red]QR Code Phishing Module[/bold red]"))

        while True:
            console.print("\n1. Generate QR Code")
            console.print("2. List Generated QR Codes")
            console.print("3. Back to Main Menu")

            choice = Prompt.ask("Select an option", choices=["1", "2", "3"])

            if choice == "1":
                url = Prompt.ask("Enter the phishing URL")
                
                # Show template options with numbers
                console.print("\nSelect QR code template:")
                console.print("1. Default QR")
                console.print("2. WiFi Connection")
                console.print("3. Payment")
                
                template_choice = Prompt.ask(
                    "Enter your choice",
                    choices=["1", "2", "3"],
                    default="1"
                )
                
                # Convert number choice to template name
                template_map = {
                    "1": "default",
                    "2": "wifi",
                    "3": "payment"
                }
                
                template = template_map[template_choice]
                self.generate_qr_code(url, template)

            elif choice == "2":
                self.list_generated_codes()

            elif choice == "3":
                break 