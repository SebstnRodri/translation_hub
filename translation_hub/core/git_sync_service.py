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
		self.token = settings.get_password("auth_token")
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
		
		full_args = ["git"] + args
		try:
			result = subprocess.run(
				full_args,
				cwd=cwd,
				check=True,
				capture_output=True,
				text=True
			)
			return result.stdout.strip()
		except subprocess.CalledProcessError as e:
			frappe.log_error(f"Git Error: {e.stderr}", "Git Sync Service")
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
				capture_output=True
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

	def collect_translations(self):
		"""Copies PO files from monitored apps to the repo directory."""
		if not self.settings.monitored_apps:
			return

		for app_row in self.settings.monitored_apps:
			app_name = app_row.source_app
			try:
				app_path = frappe.get_app_path(app_name)
				locale_dir = Path(app_path).parent / "locale"
				
				if not locale_dir.exists():
					continue

				# Create app dir in repo
				repo_app_dir = self.repo_dir / app_name / "locale"
				repo_app_dir.mkdir(parents=True, exist_ok=True)

				# Copy PO files
				for po_file in locale_dir.glob("*.po"):
					shutil.copy2(po_file, repo_app_dir / po_file.name)
					
			except Exception as e:
				frappe.log_error(f"Failed to collect translations for {app_name}: {e}", "Git Sync Service")

	def distribute_translations(self):
		"""Copies PO files from the repo directory back to monitored apps."""
		if not self.repo_dir.exists():
			raise Exception("Repository not initialized. Run backup first or check configuration.")

		for app_dir in self.repo_dir.iterdir():
			if not app_dir.is_dir() or app_dir.name == ".git":
				continue
			
			app_name = app_dir.name
			# Check if app is installed
			if app_name not in frappe.get_installed_apps():
				continue

			try:
				repo_locale_dir = app_dir / "locale"
				if not repo_locale_dir.exists():
					continue

				target_app_path = frappe.get_app_path(app_name)
				target_locale_dir = Path(target_app_path).parent / "locale"
				target_locale_dir.mkdir(parents=True, exist_ok=True)

				for po_file in repo_locale_dir.glob("*.po"):
					shutil.copy2(po_file, target_locale_dir / po_file.name)
					frappe.msgprint(f"Restored {po_file.name} for {app_name}")

			except Exception as e:
				frappe.log_error(f"Failed to distribute translations for {app_name}: {e}", "Git Sync Service")

	def backup(self):
		self.setup_repo()
		self.collect_translations()
		
		# Check for changes
		status = self._run_git(["status", "--porcelain"])
		if not status:
			frappe.msgprint("No changes to backup.")
			return

		self._run_git(["add", "."])
		self._run_git(["commit", "-m", "chore: backup translations [skip ci]"])
		self._run_git(["push", "origin", self.branch])
		frappe.msgprint("Backup completed successfully.")

	def restore(self):
		self.setup_repo()
		self.distribute_translations()
		frappe.msgprint("Restore completed successfully.")
