# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

import os
import frappe
from frappe import _
from frappe import get_app_path

def execute(filters: dict | None = None):
	columns = get_columns()
	data = get_data()
	return columns, data

def get_columns() -> list[dict]:
	return [
		{
			"label": _("App"),
			"fieldname": "app",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Translated"),
			"fieldname": "translated",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("Untranslated"),
			"fieldname": "untranslated",
			"fieldtype": "Int",
			"width": 120
		},
	]

def get_data() -> list[dict]:
	settings = frappe.get_single("Translator Settings")

	if not settings.monitored_apps:
		return []

	# Import polib once at the top for better performance
	try:
		import polib
	except ImportError:
		frappe.msgprint(_("Please install polib library to view translation progress."))
		return []

	data = []

	for monitored_app in settings.monitored_apps:
		try:
			app_path = get_app_path(monitored_app.source_app)
			po_path = os.path.join(app_path, "locale", f"{monitored_app.target_language}.po")
			pot_path = os.path.join(app_path, "locale", "main.pot")

			# Check if POT file exists
			if not os.path.exists(pot_path):
				continue

			# Parse POT file to get total strings
			pot = polib.pofile(pot_path)
			total_strings = len([entry for entry in pot if not entry.obsolete])

			if total_strings == 0:
				continue

			# Check if PO file exists and parse it
			if os.path.exists(po_path):
				po = polib.pofile(po_path)
				translated_strings = len([entry for entry in po if entry.translated() and not entry.obsolete])
			else:
				translated_strings = 0

			untranslated_strings = total_strings - translated_strings

			data.append({
				"app": f"{monitored_app.source_app} ({monitored_app.target_language})",
				"translated": translated_strings,
				"untranslated": untranslated_strings
			})

		except Exception as e:
			frappe.log_error(f"Error calculating progress for {monitored_app.source_app}: {str(e)}", "Monitored Apps Progress Report")
			continue

	return data
