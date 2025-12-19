import json
import os

import frappe


def after_install():
	setup_localization()


def after_migrate():
	setup_localization()


def setup_localization():
	"""
	Sets up initial Translation Domains and Localization Profiles from JSON.
	Idempotent: Checks if records exist before creating.
	"""
	print("Setting up Localization Data...")
	try:
		data = load_initial_data()

		# 1. Create Domains
		for domain_data in data.get("Translation Domain", []):
			create_domain(domain_data)

		# 2. Create Profiles
		for profile_data in data.get("Localization Profile", []):
			create_profile(profile_data)

		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Error setup_localization: {e}")
		print(f"Error setting up localization: {e}")


def load_initial_data():
	file_path = os.path.join(os.path.dirname(__file__), "setup", "initial_data.json")
	with open(file_path) as f:
		return json.load(f)


def create_domain(data):
	if not frappe.db.exists("Translation Domain", data["domain_name"]):
		doc = frappe.get_doc({"doctype": "Translation Domain"})
		doc.update(data)
		doc.insert(ignore_permissions=True)
		print(f"Created Translation Domain: {data['domain_name']}")


def create_profile(data):
	profile_name = data.get("profile_name")
	if frappe.db.exists("Localization Profile", profile_name):
		return

	# Prepare doc data
	country_code = data.pop("country_code", None)
	language_code = data.pop("language_code", None)

	doc = frappe.get_doc({"doctype": "Localization Profile"})
	doc.update(data)

	# Validate and set Country
	if country_code:
		if frappe.db.exists("Country", country_code):
			doc.country = country_code
		# Fallback for Brasil vs Brazil if needed
		elif country_code == "Brazil" and frappe.db.exists("Country", "Brasil"):
			doc.country = "Brasil"

	# Validate and set Language
	if language_code:
		if frappe.db.exists("Language", {"language_code": language_code}):
			doc.language = language_code
		else:
			print(f"Warning: Language {language_code} not found. Skipping language field for {profile_name}.")

	doc.insert(ignore_permissions=True)
	print(f"Created Localization Profile: {profile_name}")
