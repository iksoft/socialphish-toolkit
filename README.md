# SocialPhish Toolkit

A comprehensive social engineering toolkit designed for penetration testing and security assessments. This tool provides a powerful set of features for conducting social engineering tests and security awareness training.

## 🚀 Features

### Social Media Phishing Module
- Support for multiple platforms:
  - Facebook, Instagram, Twitter, LinkedIn
  - TikTok, Snapchat, GitHub, Binance
  - Telegram, Pinterest, Reddit, Coinbase
- Real-time credential harvesting
- Optional OTP (2FA) verification simulation
- QR code generation for easy sharing
- Automatic URL generation using Cloudflared/Ngrok

### Output Methods
- File-based logging
- Telegram notifications
- Email notifications
- Real-time console updates

### Advanced Features
- Automatic port detection and management
- Multiple tunneling options (Cloudflared/Ngrok)
- Clean process management
- Comprehensive error handling
- User-friendly CLI interface

## 🛠️ Requirements

### System Requirements
- Python 3.8 or higher
- Linux-based operating system (Kali Linux recommended)
- Root privileges (for certain operations)
- Internet connection

### Python Dependencies
```
requests>=2.31.0
beautifulsoup4>=4.12.0
colorama>=0.4.6
qrcode>=7.4.2
Pillow>=10.0.0
flask>=2.3.3
python-dotenv>=1.0.0
argparse>=1.4.0
pyfiglet>=1.0.2
rich>=13.5.2
scapy>=2.5.0
cryptography>=41.0.0
validators>=0.22.0
matplotlib>=3.8.0
seaborn>=0.13.0
```

## 📦 Installation

### Quick Installation (Kali Linux)
```bash
# Clone the repository
git clone https://github.com/iksoft/socialphish-toolkit.git
cd socialphish-toolkit

# Run the setup script
chmod +x setup.sh
sudo ./setup.sh

# Start the toolkit
./run-socialphish.sh
```

### Manual Installation
```bash
# Clone the repository
git clone https://github.com/iksoft/socialphish-toolkit.git
cd socialphish-toolkit

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set permissions
chmod +x socialphish.py
chmod -R 755 modules/
chmod -R 755 templates/
chmod -R 777 output/

# Start the toolkit
sudo python3 socialphish.py
```

## 🔧 Configuration

### Telegram Notifications
1. Create a Telegram bot using @BotFather
2. Get your bot token and chat ID
3. Configure in the toolkit's settings menu

### Email Notifications
1. Configure SMTP settings in the toolkit
2. Provide email credentials
3. Set notification email address

### Ngrok Configuration
1. Create an account at ngrok.com
2. Get your authtoken
3. Configure in the toolkit's settings menu

## 📝 Usage

1. Start the toolkit:
```bash
./run-socialphish.sh
```

2. Select a module:
   - Social Media Phishing
   - QR Phishing
   - Settings

3. For Social Media Phishing:
   - Choose target platform
   - Select tunneling service (Cloudflared/Ngrok)
   - Enable/disable OTP verification
   - Monitor incoming credentials

4. For Settings:
   - Configure output methods
   - Set up notifications
   - Manage tunneling services

## ⚠️ Disclaimer

This tool is designed for educational purposes and authorized penetration testing ONLY. The developers assume NO responsibility for any misuse or damage caused by this program. Users must:

1. Obtain explicit permission before testing any target
2. Use the tool in accordance with local and international laws
3. Not use the tool for malicious purposes
4. Understand that unauthorized testing is illegal

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 🔍 Support

For support, please open an issue in the GitHub repository or contact the maintainers directly. 