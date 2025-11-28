import frappe


@frappe.whitelist()
def get_monitored_apps_count():
	settings = frappe.get_single("Translator Settings")
	return len(settings.monitored_apps)
