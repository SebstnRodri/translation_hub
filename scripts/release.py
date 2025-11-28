import argparse
import os
import re
import subprocess
import sys


def update_version_file(version):
	# Script is in scripts/, so we need to go up one level
	file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "translation_hub", "__init__.py")

	with open(file_path) as f:
		content = f.read()

	# Regex to find __version__ = "..."
	pattern = r'__version__\s*=\s*["\'].*["\']'
	replacement = f'__version__ = "{version}"'

	new_content = re.sub(pattern, replacement, content)

	if new_content != content:
		with open(file_path, "w") as f:
			f.write(new_content)
		print(f"Updated {file_path} to version {version}")
		return True
	else:
		print(f"{file_path} is already at version {version}")
		return False


def run_git_commands(version):
	try:
		# git add
		subprocess.check_call(["git", "add", "translation_hub/__init__.py"])

		# git commit
		commit_message = f"chore: release v{version}"
		subprocess.check_call(["git", "commit", "-m", commit_message])

		# git tag
		tag_name = f"v{version}"
		subprocess.check_call(["git", "tag", tag_name])

		print(f"Successfully created commit and tag {tag_name}")
		return True
	except subprocess.CalledProcessError as e:
		print(f"Error running git commands: {e}")
		return False


def main():
	parser = argparse.ArgumentParser(description="Release a new version of Translation Hub")
	parser.add_argument("version", help="The new version string (e.g., 1.0.0)")
	args = parser.parse_args()

	version = args.version
	# Strip 'v' if provided
	if version.startswith("v"):
		version = version[1:]

	print(f"Preparing release for version {version}...")

	if update_version_file(version):
		if run_git_commands(version):
			print("Release process completed successfully!")
		else:
			print("Failed to run git commands.")
			sys.exit(1)
	else:
		print("Version file was not updated (already up to date?). Skipping git operations.")


if __name__ == "__main__":
	main()
