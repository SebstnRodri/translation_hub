import os
from pathlib import Path


def cleanup_test_files():
	"""
	Scans the translation_hub/locale directory for files ending in '_test.po'
	and deletes them.
	"""
	# Get the directory of the current script
	current_dir = Path(__file__).parent
	# Navigate up to the app root (translation_hub/translation_hub)
	app_root = current_dir.parent
	locale_dir = app_root / "locale"

	if not locale_dir.exists():
		print(f"Locale directory not found at {locale_dir}. Skipping cleanup.")
		return

	print(f"Scanning {locale_dir} for test files...")
	deleted_count = 0

	for file_path in locale_dir.glob("*_test.po"):
		try:
			os.remove(file_path)
			print(f"Deleted: {file_path.name}")
			deleted_count += 1
		except OSError as e:
			print(f"Error deleting {file_path.name}: {e}")

	if deleted_count > 0:
		print(f"Cleanup complete. Deleted {deleted_count} test file(s).")
	else:
		print("No test files found to delete.")


if __name__ == "__main__":
	cleanup_test_files()
