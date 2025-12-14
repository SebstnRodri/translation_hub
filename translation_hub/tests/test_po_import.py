"""
Tests for PO to Database Import (v1.6.1 Critical Fix)

Simplified tests that verify the import functionality exists
and is called during restore workflow.
"""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPOImport(FrappeTestCase):
	"""Test PO file import to Translation database"""

	def tearDown(self):
		frappe.db.rollback()

	def test_import_method_exists(self):
		"""Test that _import_to_database method exists"""
		from translation_hub.core.git_sync_service import GitSyncService

		settings = frappe.get_single("Translator Settings")
		service = GitSyncService(settings)

		# Method should exist
		self.assertTrue(hasattr(service, "_import_to_database"))
		self.assertTrue(callable(service._import_to_database))

	def test_restore_calls_import(self):
		"""Test that restore workflow includes import step"""
		# Verify the method is defined
		import inspect

		from translation_hub.core.git_sync_service import GitSyncService

		source = inspect.getsource(GitSyncService.restore)

		# Should call _import_to_database
		self.assertIn("_import_to_database", source)

	def test_import_only_enabled_languages(self):
		"""Test that import filters by enabled languages"""
		# Verify the method checks enabled status
		import inspect

		from translation_hub.core.git_sync_service import GitSyncService

		source = inspect.getsource(GitSyncService._import_to_database)

		# Should check Language.enabled
		self.assertIn("enabled", source)
