# SocialPhish Toolkit

A powerful and modern social engineering toolkit with cross-platform support for Windows, Linux, macOS, and Termux.

## Features

- 🌐 Cross-platform support (Windows, Linux, macOS, Termux)
- 🎯 Social Media Phishing Templates
- 📱 QR Code Phishing Generator
- 📸 Camera Phishing Templates
  - YouTube Live Stream
  - Google Meet
  - Microsoft Teams
  - Zoom
  - Cisco WebEx
- 🔄 Multiple Tunneling Options (Ngrok, Cloudflared)
- 📧 Multiple Output Methods (File, Telegram, Email)
- 🎨 Modern and Interactive UI
- 🔒 Secure Settings Management
- 🚀 Easy to setup and use

## Prerequisites

- Python 3.8 or higher
- Internet connection
- For Tunneling (optional):
  - Ngrok account and authtoken
  - Cloudflared installed

## Installation

### Windows

1. Install Python 3.8+ from [python.org](https://python.org)
2. Download or clone this repository:
   ```bash
   git clone https://github.com/iksoft/socialphish-toolkit.git
   cd socialphish-toolkit
   ```
3. Run the setup script:
   ```bash
   python setup.py
   ```
4. Launch the toolkit:
   ```bash
   run-socialphish.bat
   ```

### Linux

1. Install required packages:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip git
   ```
2. Clone the repository:
   ```bash
   git clone https://github.com/iksoft/socialphish-toolkit.git
   cd socialphish-toolkit
   ```
3. Fix script permissions and line endings:
   ```bash
   chmod +x setup.py
   chmod +x run-socialphish.sh
   chmod +x socialphish.py
   # Fix line endings if needed
   sed -i 's/\r$//' setup.py
   sed -i 's/\r$//' run-socialphish.sh
   sed -i 's/\r$//' socialphish.py
   ```
4. Run the setup script:
   ```bash
   python3 setup.py

5. Run this command to install all packages at once:
   ```bash
   bash pip install "requests>=2.31.0" "beautifulsoup4>=4.12.0" "colorama>=0.4.6" "qrcode>=7.4.2" "Pillow>=10.0.0" "flask>=2.3.3" "python-dotenv>=1.0.0" "argparse>=1.4.0" "pyfiglet>=1.0.2" "rich>=13.5.2" "scapy>=2.5.0" "cryptography>=41.0.0" "validators>=0.22.0" "matplotlib>=3.8.0" "seaborn>=0.13.0" "psutil>=5.9.0"
```
6. Launch the toolkit:
   ```bash
   ./run-socialphish.sh
   ```

### Termux

1. Install required packages:
   ```bash
   pkg update
   pkg install python git
   ```
2. Clone the repository:
   ```bash
   git clone https://github.com/iksoft/socialphish-toolkit.git
   cd socialphish-toolkit
   ```
3. Fix script permissions and line endings:
   ```bash
   chmod +x setup.py
   chmod +x run-socialphish.sh
   chmod +x socialphish.py
   # Fix line endings if needed
   sed -i 's/\r$//' setup.py
   sed -i 's/\r$//' run-socialphish.sh
   sed -i 's/\r$//' socialphish.py
   ```
4. Run the setup script:
   ```bash
   python setup.py
   ```
5. Launch the toolkit:
   ```bash
   ./run-socialphish.sh
   ```

### macOS

1. Install Python 3.8+ using Homebrew:
   ```bash
   brew install python
   ```
2. Clone the repository:
   ```bash
   git clone https://github.com/iksoft/socialphish-toolkit.git
   cd socialphish-toolkit
   ```
3. Run the setup script:
   ```bash
   python3 setup.py
   ```
4. Launch the toolkit:
   ```bash
   ./run-socialphish.sh
   ```

## Usage

1. Launch the toolkit using the appropriate command for your platform
2. Select from available modules:
   - Social Media Phishing
   - QR Phishing
   - Camera Phishing
   - Settings

### Camera Phishing Module

The Camera Phishing module provides templates for various video conferencing and streaming platforms:

1. Available Templates:
   - YouTube Live Stream
   - Google Meet
   - Microsoft Teams
   - Zoom
   - Cisco WebEx
   - Generic Streaming Platform
   - Conference Platform
   - Video Player

2. Features:
   - Modern and responsive UI
   - Real-time camera capture
   - Platform-specific styling
   - Automatic image saving
   - Multiple tunneling options

### Configuring Settings

The toolkit supports multiple output methods and tunneling options. Configure these in the Settings menu:

1. Output Methods:
   - File (default)
   - Telegram
   - Email

2. Tunneling Options:
   - Ngrok
   - Cloudflared

### Setting Up Notifications

#### Telegram
1. Create a Telegram bot using [@BotFather](https://t.me/botfather)
2. Get your Chat ID using [@RawDataBot](https://t.me/rawdatabot)
3. Configure in Settings → Telegram Settings

#### Email
1. Configure your SMTP server details
2. Set up sender and recipient email addresses
3. Configure in Settings → Email Settings

## Troubleshooting

### Common Issues

1. **Tunnel Connection Issues**
   - Ensure you have the latest version of ngrok/cloudflared
   - Check your internet connection
   - Verify your authentication tokens

2. **Python Virtual Environment**
   - If you encounter venv issues, try:
     ```bash
     python -m pip install --upgrade pip
     python -m pip install virtualenv
     ```

3. **Permission Issues**
   - On Linux/macOS, ensure proper permissions:
     ```bash
     chmod +x setup.py
     chmod +x run-socialphish.sh
     ```

4. **Windows Execution Policy**
   - If scripts won't run, try:
     ```powershell
     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
     ```

5. **Script Execution Issues**
   - If you get "command not found" or execution errors:
     ```bash
     # Make sure you're in the correct directory
     cd /path/to/socialphish-toolkit
     
     # Fix script permissions
     chmod +x setup.py
     chmod +x run-socialphish.sh
     chmod +x socialphish.py
     
     # Fix line endings (if scripts were edited on Windows)
     sed -i 's/\r$//' setup.py
     sed -i 's/\r$//' run-socialphish.sh
     sed -i 's/\r$//' socialphish.py
     
     # Try running with bash explicitly
     bash run-socialphish.sh
     ```
   - If still getting permission issues:
     ```bash
     # Set full permissions for the entire toolkit
     chmod -R 755 .
     chmod -R 777 output/
     ```
   - If the virtual environment isn't activated:
     ```bash
     # Activate it manually
     source venv/bin/activate
     python3 socialphish.py
     ```

## Security

- ⚠️ This tool is for educational purposes only
- 🔒 Never store sensitive information
- 🚫 Do not use for malicious purposes
- ⚡ Use at your own risk

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational purposes only. The developer is not responsible for any misuse or damage caused by this program. 
