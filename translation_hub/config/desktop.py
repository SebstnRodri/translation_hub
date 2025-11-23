from frappe import _


def get_data():
	return [
		{
			"module_name": "Translation Hub",
			"color": "#509EEB",
			"icon": "octicon octicon-globe",
			"type": "module",
			"label": _("Translation Hub"),
			"items": [
				{
					"type": "doctype",
					"name": "Translation Job",
					"label": _("Translation Jobs"),
					"description": _("List of all translation jobs."),
				},
				{
					"type": "doctype",
					"name": "Translator Settings",
					"label": _("Translator Settings"),
					"description": _("Global configuration for the translation service."),
				},
			],
		}
	]
