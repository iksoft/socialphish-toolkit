#!/usr/bin/env python3

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def print_colored(text, color):
    colors = {
        'green': '\033[0;32m',
        'yellow': '\033[1;33m',
        'red': '\033[0;31m',
        'nc': '\033[0m'
    }
    # Windows CMD doesn't support ANSI colors by default
    if platform.system() == 'Windows' and not os.environ.get('TERM'):
        print(text)
    else:
        print(f"{colors.get(color, '')}{text}{colors['nc']}")

def run_command(command, shell=True):
    try:
        subprocess.run(command, shell=shell, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def create_directories():
    print_colored("[+] Creating necessary directories...", "green")
    dirs = [
        "templates/email",
        "templates/landing",
        "templates/qr_codes",
        "output/harvested",
        "output/qr_codes",
        "output/reports"
    ]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

def setup_virtual_env():
    print_colored("[+] Setting up virtual environment...", "green")
    if os.path.exists("venv"):
        print_colored("[!] Removing existing virtual environment...", "yellow")
        if platform.system() == "Windows":
            run_command("rmdir /s /q venv")
        else:
            shutil.rmtree("venv")

    # Create virtual environment
    run_command(f"{sys.executable} -m venv venv")

    # Determine the pip path
    if platform.system() == "Windows":
        pip_path = "venv\\Scripts\\pip"
        activate_path = "venv\\Scripts\\activate"
    else:
        pip_path = "venv/bin/pip"
        activate_path = "venv/bin/activate"

    # Install requirements
    if platform.system() == "Windows":
        run_command(f"{pip_path} install --upgrade pip")
        run_command(f"{pip_path} install wheel")
        run_command(f"{pip_path} install -r requirements.txt")
    else:
        run_command(f"source {activate_path} && pip install --upgrade pip && pip install wheel && pip install -r requirements.txt")

def set_permissions():
    print_colored("[+] Setting correct permissions...", "green")
    if platform.system() != "Windows":
        os.chmod("socialphish.py", 0o755)
        for root, dirs, files in os.walk("modules"):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                os.chmod(os.path.join(root, f), 0o755)
        for root, dirs, files in os.walk("templates"):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
        for root, dirs, files in os.walk("output"):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o777)

def create_launcher():
    print_colored("[+] Creating launcher script...", "green")
    if platform.system() == "Windows":
        with open("run-socialphish.bat", "w") as f:
            f.write("@echo off\n")
            f.write("call venv\\Scripts\\activate\n")
            f.write("python socialphish.py\n")
            f.write("pause\n")
        os.chmod("run-socialphish.bat", 0o755)
    else:
        with open("run-socialphish.sh", "w") as f:
            f.write("#!/bin/bash\n")
            f.write("source venv/bin/activate\n")
            f.write("python3 socialphish.py\n")
        os.chmod("run-socialphish.sh", 0o755)

def main():
    print_colored("[+] Setting up SocialPhish Toolkit...", "green")
    
    # Create directories
    create_directories()
    
    # Setup virtual environment and install dependencies
    setup_virtual_env()
    
    # Set correct permissions
    set_permissions()
    
    # Create launcher script
    create_launcher()
    
    print_colored("[+] Setup complete!", "green")
    if platform.system() == "Windows":
        print_colored("[*] To run the toolkit, simply use:", "yellow")
        print_colored("    run-socialphish.bat", "green")
    else:
        print_colored("[*] To run the toolkit, simply use:", "yellow")
        print_colored("    ./run-socialphish.sh", "green")

if __name__ == "__main__":
    main() 