import os
import shutil
import subprocess
from pathlib import Path

import frappe

from translation_hub.core.config import TranslationConfig


class GitSyncService:
	def __init__(self, settings):
		self.settings = settings
		self.repo_url = settings.backup_repo_url
		self.branch = settings.backup_branch or "main"
		self.token = settings.get_password("auth_token", raise_exception=False)
		self.repo_dir = Path(frappe.get_site_path("private", "translation_backup_repo"))

	def _get_auth_url(self):
		if not self.token:
			return self.repo_url

		# Insert token into URL: https://TOKEN@github.com/...
		if "https://" in self.repo_url:
			return self.repo_url.replace("https://", f"https://{self.token}@")
		return self.repo_url

	def _run_git(self, args, cwd=None):
		if cwd is None:
			cwd = self.repo_dir

		full_args = ["git", *args]
		try:
			result = subprocess.run(full_args, cwd=cwd, check=True, capture_output=True, text=True)
			return result.stdout.strip()
		except subprocess.CalledProcessError as e:
			frappe.log_error(f"Git Error: {e.stderr}", "Git Sync Service")
			
			# Provide helpful error message for common authentication issues
			if "could not read Username" in e.stderr or "Authentication failed" in e.stderr:
				raise Exception(
					"Git authentication failed. Please configure an Auth Token in Translator Settings "
				)
			
			raise Exception(f"Git command failed: {' '.join(full_args)}\nError: {e.stderr}")

	def setup_repo(self):
		"""Clones or pulls the repository."""
		auth_url = self._get_auth_url()

		if not self.repo_dir.exists():
			self.repo_dir.parent.mkdir(parents=True, exist_ok=True)
			frappe.msgprint("Cloning backup repository...")
			# Clone
			subprocess.run(
				["git", "clone", "-b", self.branch, auth_url, str(self.repo_dir)],
				check=True,
				capture_output=True,
			)
			# Configure user
			self._run_git(["config", "user.email", "translation_hub@bot.com"])
			self._run_git(["config", "user.name", "Translation Hub Bot"])
		else:
			frappe.msgprint("Pulling latest changes...")
			# Update remote URL in case token changed
			self._run_git(["remote", "set-url", "origin", auth_url])
			self._run_git(["fetch", "origin"])
			self._run_git(["reset", "--hard", f"origin/{self.branch}"])

	def _get_version_folder(self):
		"""
		Returns the folder name for the current Frappe version.
		Always uses major version (e.g., 'version-16') for consistency across sites.
		"""
		version = frappe.__version__
		if "develop" in version:
			return "develop"
		# Always use major version for consistency
		major_version = version.split('.')[0]
		return f"version-{major_version}"

	def _get_enabled_language_codes(self):
		"""
		Returns a set of enabled language codes in .po file format (e.g., pt_BR).
		"""
		enabled_langs = frappe.get_all(
			"Language", 
			filters={"enabled": 1}, 
			fields=["name"]
		)
		# Convert to .po filename format: pt-BR -> pt_BR
		return {lang.name.replace("-", "_") for lang in enabled_langs}

	def collect_translations(self, apps=None):
		"""Copies PO files from monitored apps to the repo directory (only enabled languages)."""
		if not self.settings.monitored_apps:
			return

		version_folder = self._get_version_folder()
		enabled_codes = self._get_enabled_language_codes()

		for app_row in self.settings.monitored_apps:
			app_name = app_row.source_app
			
			# Filter by selected apps if provided
			if apps and app_name not in apps:
				continue

			try:
				app_path = frappe.get_app_path(app_name)
				# Correct internal path: app key is module name
				locale_dir = Path(app_path) / "locale"

				if not locale_dir.exists():
					continue

				# Create app dir in repo with version subfolder
				# Structure: repo/version/app/locale/
				repo_app_dir = self.repo_dir / version_folder / app_name / "locale"
				repo_app_dir.mkdir(parents=True, exist_ok=True)

				# Copy PO files (only enabled languages)
				copied_count = 0
				for po_file in locale_dir.glob("*.po"):
					if po_file.name.endswith("_test.po"):
						continue
					
					# Extract lang code from filename (e.g., pt_BR.po -> pt_BR)
					lang_code = po_file.stem
					
					# Only copy if language is enabled
					if lang_code in enabled_codes:
						shutil.copy2(po_file, repo_app_dir / po_file.name)
						copied_count += 1
				
				if copied_count > 0:
					frappe.logger().info(f"Backed up {copied_count} enabled language(s) for {app_name}")

			except Exception as e:
				frappe.log_error(f"Failed to collect translations for {app_name}: {e}", "Git Sync Service")

	def distribute_translations(self, apps=None):
		"""Copies PO files from the repo directory back to monitored apps (only enabled languages)."""
		if not self.repo_dir.exists():
			raise Exception("Repository not initialized. Run backup first or check configuration.")

		version_folder = self._get_version_folder()
		version_dir = self.repo_dir / version_folder

		if not version_dir.exists():
			frappe.msgprint(f"No backup found for version: {version_folder}")
			return

		enabled_codes = self._get_enabled_language_codes()

		for app_dir in version_dir.iterdir():
			if not app_dir.is_dir() or app_dir.name == ".git":
				continue

			app_name = app_dir.name
			
			# Filter by selected apps if provided
			if apps and app_name not in apps:
				continue

			# Check if app is installed
			if app_name not in frappe.get_installed_apps():
				continue

			try:
				repo_locale_dir = app_dir / "locale"
				if not repo_locale_dir.exists():
					continue

				target_app_path = frappe.get_app_path(app_name)
				# Correct internal path
				target_locale_dir = Path(target_app_path) / "locale"
				target_locale_dir.mkdir(parents=True, exist_ok=True)

				restored_count = 0
				for po_file in repo_locale_dir.glob("*.po"):
					# Extract lang code from filename
					lang_code = po_file.stem
					
					# Only restore if language is enabled
					if lang_code in enabled_codes:
						shutil.copy2(po_file, target_locale_dir / po_file.name)
						restored_count += 1
				
				if restored_count > 0:
					frappe.msgprint(f"Restored {restored_count} enabled language(s) for {app_name}")

			except Exception as e:
				frappe.log_error(f"Failed to distribute translations for {app_name}: {e}", "Git Sync Service")

	def backup(self, apps=None):
		self.setup_repo()
		self.collect_translations(apps=apps)

		# Check for changes
		status = self._run_git(["status", "--porcelain"])
		if not status:
			frappe.msgprint("No changes to backup.")
			return

		self._run_git(["add", "."])
		msg = "chore: backup translations [skip ci]"
		if apps:
			app_list = ", ".join(apps)
			msg = f"chore: backup translations for {app_list} [skip ci]"
		
		self._run_git(["commit", "-m", msg])
		self._run_git(["push", "origin", self.branch])
		frappe.msgprint("Backup completed successfully.")

	def restore(self, apps=None):
		self.setup_repo()
		self.distribute_translations(apps=apps)
		
		# Import .po files to Translation database
		self._import_to_database(apps=apps)
		
		# Compile .po files to .mo for immediate use
		self._compile_translations(apps=apps)
		
		# Clear cache to ensure new translations are picked up
		frappe.translate.clear_cache()
		frappe.clear_cache()
		frappe.msgprint("Restore completed successfully.")

	def _import_to_database(self, apps=None):
		"""Imports .po files to Translation database for enabled languages."""
		import polib
		from pathlib import Path
		
		apps_to_import = apps if apps else frappe.get_installed_apps()
		
		# Get enabled languages
		enabled_langs = frappe.get_all("Language", filters={"enabled": 1}, fields=["name"])
		enabled_codes = {lang.name.replace("-", "_") for lang in enabled_langs}
		
		frappe.logger().info(f"Importing translations to database for apps: {apps_to_import}")
		
		imported_count = 0
		for app_name in apps_to_import:
			try:
				app_path = frappe.get_app_path(app_name)
				locale_dir = Path(app_path) / "locale"
				
				if not locale_dir.exists():
					continue
				
				for po_file in locale_dir.glob("*.po"):
					lang_code = po_file.stem
					
					# Only import enabled languages
					if lang_code not in enabled_codes:
						continue
					
					try:
						# Parse PO file
						po = polib.pofile(str(po_file))
						
						# Convert to Frappe format (underscore to dash)
						lang_db = lang_code.replace("_", "-")
						
						# Import each translation entry
						for entry in po:
							if entry.msgid and entry.msgstr:
								# Check if translation exists
								existing = frappe.db.exists(
									"Translation",
									{"source_text": entry.msgid, "language": lang_db}
								)
								
								if existing:
									# Update existing
									frappe.db.set_value(
										"Translation",
										existing,
										"translated_text",
										entry.msgstr
									)
								else:
									# Create new
									frappe.get_doc({
										"doctype": "Translation",
										"source_text": entry.msgid,
										"language": lang_db,
										"translated_text": entry.msgstr,
										"contributed": 0
									}).insert(ignore_permissions=True)
								
								imported_count += 1
						
						frappe.logger().info(f"Imported {lang_code} for {app_name}")
					
					except Exception as e:
						frappe.logger().error(f"Failed to import {lang_code} for {app_name}: {e}")
				
			except Exception as e:
				frappe.log_error(f"Failed to import translations for {app_name}: {e}", "Translation Import")
		
		if imported_count > 0:
			frappe.db.commit()
			frappe.logger().info(f"Translation import completed. {imported_count} entries processed.")

	def _compile_translations(self, apps=None):
		"""Compiles .po files to .mo files for the specified apps."""
		from frappe.gettext.translate import compile_translations
		
		apps_to_compile = apps if apps else frappe.get_installed_apps()
		
		frappe.logger().info(f"Compiling translations for apps: {apps_to_compile}")
		
		for app in apps_to_compile:
			# Compile all language files for this app
			compile_translations(app)
		
		frappe.logger().info("Translation compilation completed")

	def sync(self):
		"""Syncs remote translations to local apps before translating.

		Returns:
			bool: True if sync succeeded, False if no repo configured.
		"""
		if not self.repo_url:
			return False

		try:
			self.setup_repo()
			self.distribute_translations()
			return True
		except Exception as e:
			frappe.log_error(f"Failed to sync translations: {e}", "Git Sync Service")
			return False
