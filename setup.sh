#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}[+] Setting up SocialPhish Toolkit...${NC}"

# Create necessary directories
echo -e "${GREEN}[+] Creating necessary directories...${NC}"
mkdir -p templates/{email,landing,qr_codes}
mkdir -p output/{harvested,qr_codes,reports}

# Install required system packages
echo -e "${GREEN}[+] Installing system requirements...${NC}"
if [ "$EUID" -eq 0 ]; then
    apt-get update
    apt-get install -y python3-venv python3-pip python3-dev build-essential libssl-dev libffi-dev \
        python3-tk python3-matplotlib fonts-dejavu-core
else
    echo -e "${YELLOW}[!] Not running as root - skipping system package installation${NC}"
    echo -e "${YELLOW}[!] If you encounter issues, run: sudo apt-get install python3-venv python3-pip python3-dev build-essential libssl-dev libffi-dev python3-tk python3-matplotlib fonts-dejavu-core${NC}"
fi

# Remove existing venv if it exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}[!] Removing existing virtual environment...${NC}"
    rm -rf venv
fi

# Create virtual environment
echo -e "${GREEN}[+] Creating virtual environment...${NC}"
python3 -m venv venv

# Activate virtual environment and install requirements
echo -e "${GREEN}[+] Installing Python dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install wheel
pip install -r requirements.txt

# Make scripts executable
echo -e "${GREEN}[+] Setting correct permissions...${NC}"
chmod +x socialphish.py
chmod -R 755 modules/
chmod -R 755 templates/
chmod -R 777 output/

# Set current user as owner of the virtual environment
if [ "$EUID" -eq 0 ]; then
    SUDO_USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    chown -R "$SUDO_USER:$SUDO_USER" venv/
    chown -R "$SUDO_USER:$SUDO_USER" output/
fi

# Create a launcher script
echo -e "${GREEN}[+] Creating launcher script...${NC}"
cat > run-socialphish.sh << 'EOL'
#!/bin/bash
source venv/bin/activate
python3 socialphish.py
EOL

chmod +x run-socialphish.sh

echo -e "${GREEN}[+] Setup complete!${NC}"
echo -e "${YELLOW}[*] To run the toolkit, simply use:${NC}"
echo -e "    ${GREEN}./run-socialphish.sh${NC}" 