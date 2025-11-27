import subprocess
import re
import os

def get_git_tag():
    try:
        # Get the latest tag
        tag = subprocess.check_output(['git', 'describe', '--tags', '--abbrev=0']).decode().strip()
        # Remove 'v' prefix if present
        if tag.startswith('v'):
            tag = tag[1:]
        return tag
    except subprocess.CalledProcessError:
        print("No git tag found.")
        return None

def update_version_file(version):
    # Script is in scripts/, so we need to go up one level
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'translation_hub', '__init__.py')
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Regex to find __version__ = "..."
    pattern = r'__version__\s*=\s*["\'].*["\']'
    replacement = f'__version__ = "{version}"'
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Updated {file_path} to version {version}")
    else:
        print(f"{file_path} is already up to date.")

if __name__ == "__main__":
    version = get_git_tag()
    if version:
        update_version_file(version)
