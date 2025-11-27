# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InstalledApp(Document):
	def db_insert(self, *args, **kwargs):
		pass

	def load_from_db(self):
		pass

	def db_update(self, *args, **kwargs):
		pass

	@staticmethod
	def get_list(args):
		apps = frappe.get_installed_apps()
		start = args.get("start", 0)
		page_len = args.get("page_length", 20)

		# Filter if needed (simple implementation)
		if args.get("filters"):
			# Very basic filtering for 'name' or 'app_name'
			name_filter = args.get("filters", {}).get("app_name") or args.get("filters", {}).get("name")
			if name_filter:
				if isinstance(name_filter, list) and name_filter[0] == "like":
					apps = [app for app in apps if name_filter[1].replace("%", "") in app]
				elif isinstance(name_filter, str):
					apps = [app for app in apps if name_filter in app]

		if args.get("as_list"):
			return [(app, app) for app in apps[start : start + page_len]]

		return [{"name": app, "app_name": app} for app in apps[start : start + page_len]]

	@staticmethod
	def get_count(args):
		return len(frappe.get_installed_apps())

	@staticmethod
	def get_stats(args):
		return {}
