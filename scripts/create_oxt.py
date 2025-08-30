import argparse
import zipfile
import os
import tempfile
import shutil

# Set up argument Parser
parser = argparse.ArgumentParser(
    description="Create an oxt file with specified version"
)
parser.add_argument("version", type=str, help="Version number for the extension")

# Parse arguments
args = parser.parse_args()
version = args.version

# Gets the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Creates paths relative to script location
extension_path = os.path.join(script_dir, "../extension")
oxt_file_path = os.path.join(script_dir, "../factur-x_profile_en-16931.oxt")

# Normalizes paths to handle the "../" correctly
extension_path = os.path.normpath(extension_path)
oxt_file_path = os.path.normpath(oxt_file_path)

# Creates an oxt from the current contents of the extension folder

# Create a temporary directory for modified files
temp_dir = tempfile.mkdtemp()
try:
    # Copy extension directory to temp directory
    temp_extension_path = os.path.join(temp_dir, "extension")
    shutil.copytree(extension_path, temp_extension_path)

    # Update version in description.xml
    description_path = os.path.join(temp_extension_path, "description.xml")
    with open(description_path, "r", encoding="utf-8") as file:
        content = file.read()

    # Replace placeholder with actual version
    content = content.replace("{{VERSION}}", version)

    with open(description_path, "w", encoding="utf-8") as file:
        file.write(content)

    # Create zip file (oxt) from temp extension folder contents
    with zipfile.ZipFile(oxt_file_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(temp_extension_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, temp_extension_path)
                zf.write(file_path, rel_path)

    print(f"Created OXT file at: {oxt_file_path}")

finally:
    # Clean up temporary directory
    shutil.rmtree(temp_dir)
