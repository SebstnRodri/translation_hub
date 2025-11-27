import frappe
from frappe.tests.utils import FrappeTestCase


class TestInstalledAppSearch(FrappeTestCase):
	def test_get_list_as_list(self):
		# Simulate what search_widget likely does: request as_list=True
		# and expect tuples/lists back
		results = frappe.get_list("Installed App", as_list=True)

		if results:
			first_item = results[0]
			# This should NOT raise KeyError if it's a tuple/list
			# If it's a dict, first_item[0] might fail if key 0 doesn't exist
			try:
				_ = first_item[0]
			except KeyError:
				self.fail("frappe.get_list(as_list=True) returned dicts instead of tuples/lists")
			except TypeError:
				self.fail(
					f"frappe.get_list(as_list=True) returned {type(first_item)} which is not subscriptable like a tuple"
				)


if __name__ == "__main__":
	frappe.init(site="dev.localhost", sites_path="/home/ubuntu/Project/frappe/sites")
	frappe.connect()
	try:
		TestInstalledAppSearch().test_get_list_as_list()
		print("test_get_list_as_list passed")
	except Exception as e:
		print(f"Test failed: {e}")
