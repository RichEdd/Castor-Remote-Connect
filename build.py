import os
import sys
import subprocess
import shutil

def install_requirements():
    """Install required packages for building."""
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def build_executable(script_name, output_name):
    """Build a standalone executable using PyInstaller."""
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name", output_name,
        "--onefile",  # Create a single executable
        "--windowed",  # Don't show console window
        "--clean",  # Clean PyInstaller cache
        "--add-data", "README.md;.",  # Include README
        script_name
    ]
    
    # Run PyInstaller
    subprocess.check_call(cmd)
    
    # Create dist directory if it doesn't exist
    if not os.path.exists("dist"):
        os.makedirs("dist")
    
    # Move the executable to dist directory
    if os.path.exists(f"{output_name}.exe"):
        shutil.move(f"{output_name}.exe", f"dist/{output_name}.exe")
    
    # Clean up build files
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists(f"{output_name}.spec"):
        os.remove(f"{output_name}.spec")

def main():
    """Build both host and client executables."""
    print("Installing requirements...")
    install_requirements()
    
    print("\nBuilding host application...")
    build_executable("host_app.py", "CastorRemoteConnect-Host")
    
    print("\nBuilding client application...")
    build_executable("client_app.py", "CastorRemoteConnect-Client")
    
    print("\nBuild complete! Executables are in the 'dist' directory.")

if __name__ == "__main__":
    main() 