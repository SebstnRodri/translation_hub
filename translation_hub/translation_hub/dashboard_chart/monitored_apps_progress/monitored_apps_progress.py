# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

import os

import frappe
from frappe import get_app_path


def get_data():
	"""
	Calculate translation progress percentage for each monitored app/language combination.
	Returns data formatted for a bar chart.
	"""
	settings = frappe.get_single("Translator Settings")

	if not settings.monitored_apps:
		return {"labels": [], "datasets": [{"name": "Progress %", "values": []}]}

	labels = []
	values = []

	for monitored_app in settings.monitored_apps:
		try:
			app_path = get_app_path(monitored_app.source_app)
			po_path = os.path.join(app_path, "locale", f"{monitored_app.target_language}.po")
			pot_path = os.path.join(app_path, "locale", "main.pot")

			# Check if files exist
			if not os.path.exists(pot_path):
				continue

			# Import polib to parse files
			import polib

			pot = polib.pofile(pot_path)
			total_strings = len([entry for entry in pot if not entry.obsolete])

			if total_strings == 0:
				continue

			# Check if .po file exists
			if os.path.exists(po_path):
				po = polib.pofile(po_path)
				translated_strings = len([entry for entry in po if entry.translated() and not entry.obsolete])
			else:
				translated_strings = 0

			# Calculate percentage
			percentage = round((translated_strings / total_strings) * 100, 1)

			# Create label
			label = f"{monitored_app.source_app} ({monitored_app.target_language})"
			labels.append(label)
			values.append(percentage)

		except Exception as e:
			frappe.log_error(f"Error calculating progress for {monitored_app.source_app}: {e!s}")
			continue

	return {"labels": labels, "datasets": [{"name": "Progress %", "values": values}]}
