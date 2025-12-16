# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from translation_hub.api.review_api import process_review

class TestTranslationFeedbackLoop(FrappeTestCase):
	"""
	Tests the AI Feedback Loop mechanism.
	"""
	def setUp(self):
		frappe.db.delete("Translation Review")
		frappe.db.delete("Translation Learning")

	def test_learning_record_creation(self):
		"""
		Test that approving a review with edits creates a Translation Learning record.
		"""
		source = "Hello World"
		ai_suggestion = "Olá Mundo"
		human_correction = "Olá Mundo!" # Added exclamation
		
		# 1. Create Review
		review = frappe.get_doc({
			"doctype": "Translation Review",
			"source_text": source,
			"suggested_text": ai_suggestion,
			"ai_suggestion_snapshot": ai_suggestion,
			"language": "pt-BR",
			"source_app": "frappe",
			"status": "Pending"
		})
		review.insert()
		
		# 2. Process Review (Approve with edit)
		process_review(review.name, "Approve", adjusted_text=human_correction)
		
		# 3. Verify Learning Record
		learning = frappe.get_all("Translation Learning", fields=["source_text", "ai_output", "human_correction"])
		self.assertEqual(len(learning), 1)
		self.assertEqual(learning[0].source_text, source)
		self.assertEqual(learning[0].ai_output, ai_suggestion)
		self.assertEqual(learning[0].human_correction, human_correction)

	def test_no_learning_if_no_edit(self):
		"""
		Test that approving without edits DOES NOT create a Learning record.
		"""
		source = "Good Morning"
		ai_suggestion = "Bom Dia"
		
		review = frappe.get_doc({
			"doctype": "Translation Review",
			"source_text": source,
			"suggested_text": ai_suggestion,
			"ai_suggestion_snapshot": ai_suggestion,
			"language": "pt-BR",
			"source_app": "frappe",
			"status": "Pending"
		})
		review.insert()
		
		process_review(review.name, "Approve", adjusted_text=ai_suggestion) # Same text
		
		learning = frappe.get_all("Translation Learning")
		self.assertEqual(len(learning), 0)
