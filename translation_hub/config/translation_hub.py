from frappe import _


def get_data():
	return [
		{
			"label": _("Translation Hub"),
			"items": [
				{
					"type": "doctype",
					"name": "Translation Job",
					"description": _("Translation Jobs."),
				},

				{
					"type": "doctype",
					"name": "Translator Settings",
					"description": _("Translator Settings."),
				},
			],
		}
	]
