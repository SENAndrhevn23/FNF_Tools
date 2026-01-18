# Merged Tool (Future Of FNF Charting)
## if complicated.. use setup.bat
A simple Python tool created by Andre Nicholas Jr.

------------------------------------------------------------

Requirements:
- Python 3.13 (or latest version)
- Windows 10 or higher / Linux / macOS / ChromeOS

------------------------------------------------------------

Setup:

1. Open the Python script.
2. Change the ROOT_FOLDER path to your own folder location:

# Example:
ROOT_FOLDER = r"C:\Users\YourName\Documents\Merged Tool"

------------------------------------------------------------
# Installing Python

## 1. Windows

1. Download Python from https://www.python.org/downloads/windows/
2. Run the installer and check "Add Python to PATH"
3. Verify installation in Command Prompt:

python --version

## 2. Linux

### Option 1: Using Package Managers (Recommended)

# Update package lists
Debian/Ubuntu: sudo apt update
Fedora/CentOS/RHEL: sudo dnf update
Arch Linux: sudo pacman -Syu

# Install Python 3
Debian/Ubuntu: sudo apt install python3
Fedora/CentOS/RHEL: sudo dnf install python3
Arch Linux: sudo pacman -S python

# Verify installation
python3 --version

# Optional: Install pip and development libraries
Debian/Ubuntu: sudo apt install python3-pip python3-dev
Fedora: sudo dnf install python3-pip python3-devel

### Option 2: Installing from Source (Advanced)

1. Download Python source from https://www.python.org/downloads/
2. Extract and navigate:
   tar -xf Python-3.x.x.tar.xz
   cd Python-3.x.x
3. Configure, build, and install:
   ./configure --enable-optimizations --prefix=/usr/local
   make -j $(nproc)
   sudo make altinstall  # prevents overwriting system Python
4. Verify installation:
   python3.x --version

## 3. macOS

1. macOS comes with Python pre-installed (usually 2.x). Install latest Python 3:

# Using Homebrew (recommended)
brew update
brew install python

# Verify installation
python3 --version

2. Alternative: Download installer from https://www.python.org/downloads/macos/

## 4. ChromeOS

ChromeOS can run Linux apps via Crostini (Linux Beta).  

1. Enable Linux Beta in Settings > Developers > Linux Development Environment  
2. Open the Terminal and install Python:

# Debian/Ubuntu-based Crostini
sudo apt update
sudo apt install python3 python3-pip

# Verify installation
python3 --version

------------------------------------------------------------
# Using a Virtual Environment (Recommended)

# Create a virtual environment
python3 -m venv my_project_env

# Activate it
# Linux/macOS/ChromeOS
source my_project_env/bin/activate
# Windows (Command Prompt)
my_project_env\Scripts\activate.bat
# Windows (PowerShell)
my_project_env\Scripts\Activate.ps1

This keeps project dependencies isolated and safe.

------------------------------------------------------------
