import os
import subprocess
import sys

APP_VERSION = "0.42"
SETUP_SCRIPT = "setup_nd-hub-V042.iss"

print("="*50)
print(f"ND-Hub V{APP_VERSION} - Windows PyInstaller Build Script")
print("="*50)

# Check if PyInstaller is installed
try:
    import PyInstaller  # noqa: F401  # Präsenz-Check für ImportError-Handling
    print("PyInstaller found.")
except ImportError:
    print("PyInstaller not found. Installing now...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "pyinstaller"])
    print("PyInstaller installed.")

requirements_files = ["requirements.txt", "requirements-dev.txt"]
for requirement_file in requirements_files:
    if os.path.exists(requirement_file):
        print(f"Updating packages from {requirement_file}...")
        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "-r",
            requirement_file,
        ])
    else:
        print(f"WARNING: {requirement_file} not found. Skipping.")

# Build command parts
icon_path = "icon.ico"
main_script = "nd_hub.py"

if not os.path.exists(main_script):
    print(f"ERROR: {main_script} not found in current directory.")
    sys.exit(1)

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--windowed", # No console window (GUI only)
    "--name=ND-Hub",
    "--clean"
]

if os.path.exists(icon_path):
    cmd.append(f"--icon={icon_path}")
else:
    print("WARNING: icon.ico not found. Building without custom icon.")

cmd.append(main_script)

print("\nStarting PyInstaller build...")
print("Command:", " ".join(cmd))
print("-" * 50)

# Run PyInstaller
try:
    subprocess.check_call(cmd)
    print("-" * 50)
    print("Build successful! The executable is located in the 'dist' folder.")
    print(f"Next step: Use Inno Setup to compile '{SETUP_SCRIPT}'")
except subprocess.CalledProcessError as e:
    print("-" * 50)
    print(f"Error during PyInstaller build: {e}")
except FileNotFoundError:
    print("-" * 50)
    print("Error: PyInstaller command not found in PATH.")
    print("Try running 'python -m PyInstaller' instead.")
