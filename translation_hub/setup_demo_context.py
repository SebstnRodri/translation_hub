import os
import sys

import frappe

# Add app path to sys.path to ensure modules can be found
sys.path.append("/home/ubuntu/Project/frappe/apps/translation_hub")


def setup_demo_context():
	app_name = "translation_hub"

	# Ensure App exists
	if not frappe.db.exists("App", app_name):
		frappe.get_doc({"doctype": "App", "app_name": app_name, "app_title": "Translation Hub"}).insert()

	# Update with Demo Context
	app = frappe.get_doc("App", app_name)
	app.domain = "Logistics"
	app.tone = "Friendly"
	app.description = "A system for managing international shipments."

	# Clear existing glossary
	app.glossary = []

	# Add Glossary items
	app.append(
		"glossary", {"term": "Shipment", "translation": "Remessa", "description": "A package being sent."}
	)
	app.append("glossary", {"term": "Carrier", "translation": "Transportadora"})

	app.save()
	frappe.db.commit()
	print(f"Context setup for {app_name} complete.")


if __name__ == "__main__":
	frappe.init(site="dev.localhost", sites_path="/home/ubuntu/Project/frappe/sites")
	frappe.connect()
	setup_demo_context()
