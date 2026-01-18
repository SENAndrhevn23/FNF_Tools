# Merged Tool (Future Of FNF Charting)

A simple Python tool created by Andre Nicholas Jr.

------------------------------------------------------------

Requirements:
- Python 3.13 (Microsoft Store version recommended)
- Windows 10 or higher

------------------------------------------------------------

Setup:

1. Open the Python script.
2. Change the ROOT_FOLDER path to your own folder location:

# Example:
ROOT_FOLDER = r"C:\Users\YourName\Documents\Merged Tool"

------------------------------------------------------------

Installing Python on Linux:

Option 1: Using Package Managers (Recommended)

1. Open your terminal.
2. Update your package lists:

# Debian/Ubuntu
sudo apt update

# Fedora/CentOS/RHEL
sudo dnf update

# Arch Linux
sudo pacman -Syu

3. Install Python 3:

# Debian/Ubuntu
sudo apt install python3

# Fedora/CentOS/RHEL
sudo dnf install python3

# Arch Linux
sudo pacman -S python

4. Verify installation:

python3 --version

5. Optional: Install pip and development libraries:

# Debian/Ubuntu
sudo apt install python3-pip python3-dev

# Fedora
sudo dnf install python3-pip python3-devel

------------------------------------------------------------

Option 2: Installing from Source (Advanced)

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

------------------------------------------------------------

Using a Virtual Environment (Recommended):

# Create a virtual environment
python3 -m venv my_project_env

# Activate it
source my_project_env/bin/activate

This keeps project dependencies isolated and safe.
