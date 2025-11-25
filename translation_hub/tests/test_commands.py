# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from translation_hub.commands import setup_languages
from click.testing import CliRunner

class TestCommands(FrappeTestCase):
	def setUp(self):
		# Clear existing settings
		frappe.db.delete("Singles", {"doctype": "Translator Settings"})
		frappe.db.delete("Translator Language")
		
		# Ensure test language doesn't exist
		if frappe.db.exists("Language", "tl-TEST"):
			frappe.db.delete("Language", "tl-TEST")

	def test_setup_languages_command(self):
		# 1. Configure Translator Settings with a test language
		# This should trigger on_update -> sync_languages automatically
		settings = frappe.get_single("Translator Settings")
		settings.append("default_languages", {
			"language_code": "tl-TEST",
			"language_name": "Test Language",
			"enabled": 1
		})
		settings.save()

		# 2. Verify the Language was created automatically on save
		self.assertTrue(frappe.db.exists("Language", "tl-TEST"))
		lang_doc = frappe.get_doc("Language", "tl-TEST")
		self.assertEqual(lang_doc.language_name, "Test Language")
		self.assertEqual(lang_doc.enabled, 1)
		
		# 3. Verify the Language was created automatically
		self.assertTrue(frappe.db.exists("Language", "tl-TEST"))
		lang_doc = frappe.get_doc("Language", "tl-TEST")
		self.assertEqual(lang_doc.language_name, "Test Language")
		self.assertEqual(lang_doc.enabled, 1)

	def tearDown(self):
		if frappe.db.exists("Language", "tl-TEST"):
			frappe.db.delete("Language", "tl-TEST")
