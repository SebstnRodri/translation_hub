import frappe
from frappe.tests.utils import FrappeTestCase


class TestInstalledAppDocType(FrappeTestCase):
	def test_get_list(self):
		# Fetch list from Virtual DocType
		installed_apps = frappe.get_list("Installed App")
		app_names = [app["name"] for app in installed_apps]

		# Verify "frappe" and "translation_hub" are present
		self.assertIn("frappe", app_names)
		self.assertIn("translation_hub", app_names)

		# Verify count matches frappe.get_installed_apps()
		self.assertEqual(len(installed_apps), len(frappe.get_installed_apps()))

	def test_get_count(self):
		# Virtual DocTypes don't support frappe.db.count directly as it runs SQL
		# We verify count via get_list instead
		installed_apps = frappe.get_list("Installed App")
		self.assertEqual(len(installed_apps), len(frappe.get_installed_apps()))


if __name__ == "__main__":
	frappe.init(site="dev.localhost", sites_path="/home/ubuntu/Project/frappe/sites")
	frappe.connect()
	try:
		TestInstalledAppDocType().test_get_list()
		print("test_get_list passed")
		TestInstalledAppDocType().test_get_count()
		print("test_get_count passed")
	except Exception as e:
		print(f"Test failed: {e}")
