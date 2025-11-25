import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase


class TestWorkspaceIntegration(FrappeTestCase):
	def test_workspace_exists(self):
		"""Verify that the Translation Hub workspace exists."""
		self.assertTrue(frappe.db.exists("Workspace", "Translation Hub"))

	def test_number_cards_exist(self):
		"""Verify that all required Number Cards exist."""
		cards = ["Total Apps Tracked", "Jobs in Progress", "Jobs Completed (30 Days)", "Strings Translated"]
		for card in cards:
			self.assertTrue(frappe.db.exists("Number Card", card), f"Number Card {card} not found")

	def test_number_cards_configuration(self):
		"""Verify Number Cards are linked to Translation Job."""
		cards = ["Total Apps Tracked", "Jobs in Progress", "Jobs Completed (30 Days)", "Strings Translated"]
		for card_name in cards:
			card = frappe.get_doc("Number Card", card_name)
			self.assertEqual(card.document_type, "Translation Job")

	def test_workspace_content(self):
		"""Verify Workspace content JSON references the cards."""
		workspace = frappe.get_doc("Workspace", "Translation Hub")
		content = json.loads(workspace.content)

		card_names = [item["data"]["card_name"] for item in content if item["type"] == "card"]

		expected_cards = [
			"Total Apps Tracked",
			"Jobs in Progress",
			"Jobs Completed (30 Days)",
			"Strings Translated",
		]

		for expected in expected_cards:
			self.assertIn(expected, card_names, f"Card {expected} not found in Workspace content")
