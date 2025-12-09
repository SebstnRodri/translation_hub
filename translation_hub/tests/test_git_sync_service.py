import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestGitSyncService(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.settings = frappe.get_single("Translator Settings")

		# Setup a local bare git repo for testing
		self.test_repo_dir = Path(frappe.get_site_path("private", "test_git_repo"))
		self.backup_repo_dir = Path(frappe.get_site_path("private", "translation_backup_repo"))

		# Clean up any existing test repos
		if self.test_repo_dir.exists():
			shutil.rmtree(self.test_repo_dir)
		if self.backup_repo_dir.exists():
			shutil.rmtree(self.backup_repo_dir)

		# Create a bare git repo for testing
		self.test_repo_dir.mkdir(parents=True)
		subprocess.run(["git", "init", "--bare"], cwd=self.test_repo_dir, check=True, capture_output=True)

		# Initialize with a commit to create main branch
		temp_clone = self.test_repo_dir.parent / "temp_clone"
		if temp_clone.exists():
			shutil.rmtree(temp_clone)

		subprocess.run(
			["git", "clone", str(self.test_repo_dir), str(temp_clone)], check=True, capture_output=True
		)
		subprocess.run(
			["git", "config", "user.email", "test@test.com"], cwd=temp_clone, check=True, capture_output=True
		)
		subprocess.run(
			["git", "config", "user.name", "Test User"], cwd=temp_clone, check=True, capture_output=True
		)
		subprocess.run(["git", "checkout", "-b", "main"], cwd=temp_clone, check=True, capture_output=True)
		(temp_clone / "README.md").write_text("# Test Repo")
		subprocess.run(["git", "add", "."], cwd=temp_clone, check=True, capture_output=True)
		subprocess.run(
			["git", "commit", "-m", "Initial commit"], cwd=temp_clone, check=True, capture_output=True
		)
		subprocess.run(["git", "push", "origin", "main"], cwd=temp_clone, check=True, capture_output=True)
		shutil.rmtree(temp_clone)

		# Configure settings
		self.settings.backup_repo_url = str(self.test_repo_dir.absolute())
		self.settings.backup_branch = "main"
		self.settings.monitored_apps = []
		self.settings.append("monitored_apps", {"source_app": "translation_hub"})
		self.settings.save()

	def tearDown(self):
		# Clean up backup repo (but keep test repo for subsequent tests)
		if self.backup_repo_dir.exists():
			shutil.rmtree(self.backup_repo_dir)

		# Reset settings
		self.settings.backup_repo_url = None
		self.settings.monitored_apps = []
		self.settings.save()

		super().tearDown()

	@classmethod
	def tearDownClass(cls):
		# Clean up test repo after all tests
		test_repo_dir = Path(frappe.get_site_path("private", "test_git_repo"))
		if test_repo_dir.exists():
			shutil.rmtree(test_repo_dir)
		super().tearDownClass()

	def test_backup_creates_directory_structure(self):
		"""Test that backup creates app/locale directory structure"""
		from translation_hub.core.git_sync_service import GitSyncService

		# Mock version folder to be deterministic
		with patch.object(GitSyncService, "_get_version_folder", return_value="develop"):
			service = GitSyncService(self.settings)

			# Create a dummy PO file in translation_hub
			app_path = frappe.get_app_path("translation_hub")
			# Fix: locale is now inside the module
			locale_dir = Path(app_path) / "locale"
			locale_dir.mkdir(exist_ok=True)

			test_po_file = locale_dir / "test_backup.po"
			test_po_file.write_text('# Test PO file\nmsgid "test"\nmsgstr "teste"\n')

			try:
				# Run backup
				service.backup()

				# Verify repo was cloned
				self.assertTrue(self.backup_repo_dir.exists())

				# Verify directory structure with version folder
				app_locale_dir = self.backup_repo_dir / "develop" / "translation_hub" / "locale"
				self.assertTrue(app_locale_dir.exists())

				# Verify PO file was copied
				backed_up_file = app_locale_dir / "test_backup.po"
				self.assertTrue(backed_up_file.exists())
				self.assertIn("Test PO file", backed_up_file.read_text())

			finally:
				# Clean up test file
				if test_po_file.exists():
					test_po_file.unlink()

	def test_restore_copies_files_back(self):
		"""Test that restore copies files from repo back to apps"""
		from translation_hub.core.git_sync_service import GitSyncService

		with patch.object(GitSyncService, "_get_version_folder", return_value="develop"):
			service = GitSyncService(self.settings)

			# Create a dummy PO file
			app_path = frappe.get_app_path("translation_hub")
			# Fix: locale is now inside the module
			locale_dir = Path(app_path) / "locale"
			locale_dir.mkdir(exist_ok=True)

			test_po_file = locale_dir / "test_restore.po"
			test_po_file.write_text('# Original content\nmsgid "test"\nmsgstr "teste"\n')

			try:
				# Backup first
				service.backup()

				# Modify the original file
				test_po_file.write_text('# Modified content\nmsgid "test"\nmsgstr "modificado"\n')

				# Restore
				service.restore()

				# Verify file was restored to original content
				content = test_po_file.read_text()
				self.assertIn("Original content", content)
				self.assertNotIn("Modified content", content)

			finally:
				# Clean up test file
				if test_po_file.exists():
					test_po_file.unlink()

	def test_backup_with_no_changes(self):
		"""Test that backup handles no changes gracefully"""
		from translation_hub.core.git_sync_service import GitSyncService

		with patch.object(GitSyncService, "_get_version_folder", return_value="develop"):
			service = GitSyncService(self.settings)

			# Create initial backup
			app_path = frappe.get_app_path("translation_hub")
			# Fix: locale is now inside the module
			locale_dir = Path(app_path) / "locale"
			locale_dir.mkdir(exist_ok=True)

			test_po_file = locale_dir / "test_no_change.po"
			test_po_file.write_text('# Test\nmsgid "test"\nmsgstr "teste"\n')

			try:
				service.backup()

				# Backup again without changes
				with patch("frappe.msgprint") as mock_msgprint:
					service.backup()
					# Should show "No changes to backup" message
					mock_msgprint.assert_any_call("No changes to backup.")

			finally:
				if test_po_file.exists():
					test_po_file.unlink()

	def test_multiple_apps_backup(self):
		"""Test backup with multiple monitored apps"""
		from translation_hub.core.git_sync_service import GitSyncService

		# Add frappe to monitored apps
		self.settings.append("monitored_apps", {"source_app": "frappe"})
		self.settings.save()

		with patch.object(GitSyncService, "_get_version_folder", return_value="develop"):
			service = GitSyncService(self.settings)

			# Create test files for both apps
			test_files = []
			for app_name in ["translation_hub", "frappe"]:
				app_path = frappe.get_app_path(app_name)
				# Fix: locale is now inside the module
				locale_dir = Path(app_path) / "locale"
				locale_dir.mkdir(exist_ok=True)

				test_po = locale_dir / f"test_{app_name}.po"
				test_po.write_text(f'# {app_name}\nmsgid "test"\nmsgstr "teste"\n')
				test_files.append(test_po)

			try:
				service.backup()

				# Verify both apps have directories in repo
				for app_name in ["translation_hub", "frappe"]:
					# Check inside version folder
					app_dir = self.backup_repo_dir / "develop" / app_name / "locale"
					self.assertTrue(app_dir.exists(), f"{app_name} directory should exist at {app_dir}")

					po_file = app_dir / f"test_{app_name}.po"
					self.assertTrue(po_file.exists(), f"{app_name} PO file should exist")

			finally:
				for test_file in test_files:
					if test_file.exists():
						test_file.unlink()
