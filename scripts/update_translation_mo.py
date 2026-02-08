import subprocess
import glob
import os

translations_path = "../extension/package/i18n/"

# Find all .po files in the translations folder (lang/LC_MESSAGES/ subdirectories)
po_files = glob.glob(os.path.join(translations_path, "*/LC_MESSAGES/*.po"))

# Convert each .po file to .mo using msgfmt
for po_file in po_files:
    print(f"Processing {po_file}...")
    mo_file = po_file.replace(".po", ".mo")
    subprocess.run(["msgfmt", "-o", mo_file, po_file])

# Delete all po~ backup files
backup_files = glob.glob(os.path.join(translations_path, "*/LC_MESSAGES/*.po~"))
for backup_file in backup_files:
    print(f"Removing backup file {backup_file}...")
    os.remove(backup_file)
