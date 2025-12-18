import frappe
from frappe.model.document import Document


class LocalizationProfile(Document):
	def before_save(self):
		self.last_updated = frappe.utils.today()
