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

def create_update_script():
    """Create update script for Windows."""
    print_colored("[+] Creating update script...", "green")
    if platform.system() == "Windows":
        with open("update-windows.bat", "w") as f:
            f.write("@echo off\n")
            f.write("echo [*] SocialPhish Toolkit Updater for Windows\n")
            f.write("echo [*] Checking for updates...\n\n")
            f.write("REM Check if git is installed\n")
            f.write("where git >nul 2>nul\n")
            f.write("if %ERRORLEVEL% NEQ 0 (\n")
            f.write("    echo [!] Git is not installed. Please install Git from https://git-scm.com/download/win\n")
            f.write("    pause\n")
            f.write("    exit /b 1\n")
            f.write(")\n\n")
            f.write("REM Check if we're in a git repository\n")
            f.write("if not exist .git (\n")
            f.write("    echo [!] Not in a git repository. Please run this script from the socialphish-toolkit directory.\n")
            f.write("    pause\n")
            f.write("    exit /b 1\n")
            f.write(")\n\n")
            f.write("REM Stash any local changes\n")
            f.write("echo [*] Saving local changes...\n")
            f.write("git stash\n\n")
            f.write("REM Update from remote repository\n")
            f.write("echo [*] Pulling latest updates...\n")
            f.write("git pull origin main\n\n")
            f.write("if %ERRORLEVEL% NEQ 0 (\n")
            f.write("    echo [!] Failed to pull updates. Please check your internet connection.\n")
            f.write("    git stash pop\n")
            f.write("    pause\n")
            f.write("    exit /b 1\n")
            f.write(")\n\n")
            f.write("REM Restore local changes\n")
            f.write("echo [*] Restoring local changes...\n")
            f.write("git stash pop\n\n")
            f.write("REM Update Python packages\n")
            f.write("echo [*] Updating Python packages...\n")
            f.write("if exist venv\\Scripts\\activate.bat (\n")
            f.write("    call venv\\Scripts\\activate.bat\n")
            f.write("    python -m pip install --upgrade pip\n")
            f.write("    pip install -r requirements.txt\n")
            f.write("    deactivate\n")
            f.write(") else (\n")
            f.write("    echo [!] Virtual environment not found. Running setup...\n")
            f.write("    python setup.py\n")
            f.write(")\n\n")
            f.write("REM Fix permissions\n")
            f.write("echo [*] Fixing permissions...\n")
            f.write("icacls * /reset /T >nul 2>nul\n")
            f.write("icacls *.py /grant:r Everyone:F /T >nul 2>nul\n")
            f.write("icacls *.bat /grant:r Everyone:F /T >nul 2>nul\n")
            f.write("icacls templates /grant:r Everyone:F /T >nul 2>nul\n")
            f.write("icacls modules /grant:r Everyone:F /T >nul 2>nul\n")
            f.write("icacls output /grant:r Everyone:F /T >nul 2>nul\n\n")
            f.write("echo [+] Update completed successfully!\n")
            f.write("echo [*] You can now run the toolkit using run-socialphish.bat\n")
            f.write("pause\n")
        os.chmod("update-windows.bat", 0o755)

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
    
    # Create update script
    create_update_script()
    
    print_colored("[+] Setup complete!", "green")
    if platform.system() == "Windows":
        print_colored("[*] To run the toolkit, simply use:", "yellow")
        print_colored("    run-socialphish.bat", "green")
        print_colored("[*] To update the toolkit, use:", "yellow")
        print_colored("    update-windows.bat", "green")
    else:
        print_colored("[*] To run the toolkit, simply use:", "yellow")
        print_colored("    ./run-socialphish.sh", "green")

if __name__ == "__main__":
    main() 