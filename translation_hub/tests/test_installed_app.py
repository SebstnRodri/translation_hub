# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from translation_hub.translation_hub.doctype.installed_app.installed_app import InstalledApp


class TestInstalledApp(FrappeTestCase):
	def test_get_list_pagination_handling(self):
		"""Test that get_list handles string/int pagination arguments correctly"""

		# Case 1: Standard integers
		args = {"start": 0, "page_length": 10}
		apps = InstalledApp.get_list(args)
		self.assertIsInstance(apps, list)

		# Case 2: String arguments (simulating API payload issue)
		args = {"start": "0", "page_length": "10"}
		apps = InstalledApp.get_list(args)
		self.assertIsInstance(apps, list)

		# Case 3: Missing arguments defaults
		args = {}
		apps = InstalledApp.get_list(args)
		self.assertIsInstance(apps, list)
		self.assertTrue(len(apps) > 0)

	def test_get_list_structure(self):
		"""Verify returned structure matches expectations"""
		apps = InstalledApp.get_list({})
		if apps:
			self.assertIn("name", apps[0])
			self.assertIn("app_name", apps[0])
			self.assertEqual(apps[0]["name"], apps[0]["app_name"])
