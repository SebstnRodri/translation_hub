# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class App(Document):
	def validate(self):
		if self.app_name not in frappe.get_installed_apps():
			frappe.throw(f"App '{self.app_name}' is not installed on this site.", frappe.ValidationError)
