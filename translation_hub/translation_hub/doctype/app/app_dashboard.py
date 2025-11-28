from frappe import _


def get_data():
	return {
		"fieldname": "app",
		"non_standard_fieldnames": {"Translation Job": "source_app"},
		"transactions": [{"label": _("Translation"), "items": ["App Glossary", "Translation Job"]}],
	}
