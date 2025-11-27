import frappe
from frappe.tests.utils import FrappeTestCase


class TestAppValidation(FrappeTestCase):
	def test_valid_app(self):
		# "frappe" is always installed
		if not frappe.db.exists("App", "frappe"):
			doc = frappe.get_doc({"doctype": "App", "app_name": "frappe", "app_title": "Frappe Framework"})
			doc.insert()
		else:
			doc = frappe.get_doc("App", "frappe")
			doc.save()

		self.assertTrue(frappe.db.exists("App", "frappe"))

	def test_invalid_app(self):
		# "fake_app_123" should not be installed
		with self.assertRaises(frappe.ValidationError):
			doc = frappe.get_doc({"doctype": "App", "app_name": "fake_app_123", "app_title": "Fake App"})
			doc.insert()


if __name__ == "__main__":
	frappe.init(site="dev.localhost", sites_path="/home/ubuntu/Project/frappe/sites")
	frappe.connect()
	# Manually run tests if executed as script (simplified)
	try:
		TestAppValidation().test_valid_app()
		print("test_valid_app passed")
		TestAppValidation().test_invalid_app()
		print("test_invalid_app passed")
	except Exception as e:
		print(f"Test failed: {e}")
