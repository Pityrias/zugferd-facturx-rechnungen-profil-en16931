import subprocess
import os

pot_path = "../extension/package/i18n/facturx_macro.pot"
source_files = [
    "../extension/package/libreoffice_facturx_macro.py",
    "../extension/package/pythonpath/factur_x_data.py",
]

# Check if pot file already exists and save first 4 lines
file_header = None
if os.path.exists(pot_path):
    with open(pot_path, "r") as f:
        file_header = [f.readline() for _ in range(4)]

# Execute xgettext command
subprocess.run(["xgettext", "-o", pot_path] + source_files)

# Replace first 4 lines with saved lines if they exist
if file_header:
    with open(pot_path, "r") as f:
        all_lines = f.readlines()

    # Replace the first 4 lines with the saved ones
    all_lines[:4] = file_header

    with open(pot_path, "w") as f:
        f.writelines(all_lines)

po_files = [
    "../extension/package/i18n/de/LC_MESSAGES/facturx_macro.po",
    "../extension/package/i18n/en/LC_MESSAGES/facturx_macro.po",
]

for po_file in po_files:
    subprocess.run(["msgmerge", "--update", po_file, pot_path])
