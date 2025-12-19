import frappe


def get_localization_profile(language, app=None):
	"""
	Auto-detects the best Localization Profile.
	Priority:
	1. Active Profile for Language + App
	2. Active Profile for Language + No App (Generic)
	3. None
	"""
	if app:
		profile = frappe.db.get_value(
			"Localization Profile", {"language": language, "app": app, "is_active": 1}, "name"
		)
		if profile:
			return profile

	# Fallback to generic

	# We strictly need a profile without an app, OR if no app-specific existed
	# But frappe.db.get_value doesn't support IS NULL easily in dict filters unless we explicitly query
	# So we get all matching language and filter in python or use sql

	# Cleaner: Use SQL for specificity
	return (
		frappe.db.sql(
			"""
		SELECT name FROM `tabLocalization Profile`
		WHERE language = %s AND is_active = 1
		AND (app IS NULL OR app = '')
		LIMIT 1
	""",
			(language,),
			as_dict=True,
		)[0].get("name")
		if frappe.db.sql(
			"""
		SELECT name FROM `tabLocalization Profile`
		WHERE language = %s AND is_active = 1
		AND (app IS NULL OR app = '')
		LIMIT 1
	""",
			(language,),
			as_dict=True,
		)
		else None
	)
