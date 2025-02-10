#!/bin/bash

# Print colored output
print_colored() {
    COLOR=$1
    TEXT=$2
    NC='\033[0m'
    echo -e "${COLOR}${TEXT}${NC}"
}

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'

print_colored "$GREEN" "[+] Starting permission and line ending fixes..."

# Fix script permissions
print_colored "$GREEN" "[+] Setting executable permissions for scripts..."
chmod +x setup.py
chmod +x run-socialphish.sh
chmod +x socialphish.py

# Fix directory permissions
print_colored "$GREEN" "[+] Setting directory permissions..."
chmod -R 755 .
chmod -R 777 output/

# Fix line endings
print_colored "$GREEN" "[+] Fixing line endings..."
if command -v dos2unix >/dev/null 2>&1; then
    dos2unix setup.py >/dev/null 2>&1
    dos2unix run-socialphish.sh >/dev/null 2>&1
    dos2unix socialphish.py >/dev/null 2>&1
else
    sed -i 's/\r$//' setup.py
    sed -i 's/\r$//' run-socialphish.sh
    sed -i 's/\r$//' socialphish.py
fi

# Verify virtual environment
print_colored "$GREEN" "[+] Checking virtual environment..."
if [ ! -d "venv" ]; then
    print_colored "$YELLOW" "[!] Virtual environment not found. Running setup..."
    python3 setup.py
else
    print_colored "$GREEN" "[+] Virtual environment exists"
fi

print_colored "$GREEN" "[+] All fixes completed!"
print_colored "$GREEN" "[+] You can now run: ./run-socialphish.sh" 