import frappe
from frappe.tests.utils import FrappeTestCase

from translation_hub.translation_hub.report.monitored_apps_progress_report.monitored_apps_progress_report import (
	execute,
)


class TestMonitoredAppsReport(FrappeTestCase):
	def test_report_execution(self):
		if not frappe.db.exists("Language", "pt-BR"):
			frappe.get_doc(
				{
					"doctype": "Language",
					"language_code": "pt-BR",
					"language_name": "Portuguese (Brazil)",
					"enabled": 1,
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("App", "translation_hub"):
			frappe.get_doc(
				{"doctype": "App", "app_name": "translation_hub", "app_title": "Translation Hub"}
			).insert(ignore_permissions=True)

		# Ensure we have a monitored app setting
		settings = frappe.get_single("Translator Settings")
		settings.monitored_apps = []
		settings.append("monitored_apps", {"source_app": "translation_hub", "target_language": "pt-BR"})
		settings.save()

		# Execute report
		columns, data = execute()

		# Verify structure
		self.assertTrue(len(columns) > 0)
		self.assertTrue(isinstance(data, list))

		# Since we might not have actual .po files in test env populated with data,
		# we at least check that it runs without error and returns a list
		# If data is returned, verify its structure
		if data:
			row = data[0]
			self.assertIn("app", row)
			self.assertIn("progress", row)
