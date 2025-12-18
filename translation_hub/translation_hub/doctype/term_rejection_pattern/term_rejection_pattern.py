# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TermRejectionPattern(Document):
	def validate(self):
		if self.rejection_count >= 5 and self.status == "Monitoring":
			self.status = "Needs Action"
			self.notify_needs_action()

	def notify_needs_action(self):
		frappe.msgprint(
			f"Warning: Term '{self.source_text}' has been rejected {self.rejection_count} times! "
			"Consider adding it to the Regional Glossary.",
			indicator="orange",
		)
