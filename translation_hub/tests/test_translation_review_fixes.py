"""
Tests for Translation Review Creation (v1.6.1 Critical Fix)

Ensures that Translation Review can be created even when
current translation is empty, using source_text as fallback
for the mandatory suggested_text field.
"""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestTranslationReviewFixes(FrappeTestCase):
	"""Test Translation Review creation with empty translations"""

	def setUp(self):
		# Ensure Language exists
		if not frappe.db.exists("Language", "pt-BR"):
			lang = frappe.get_doc(
				{"doctype": "Language", "language_code": "pt-BR", "language_name": "Portuguese (Brazil)"}
			)
			lang.insert(ignore_permissions=True)

		# Clean up any pending reviews from previous tests
		frappe.db.delete("Translation Review", {"status": "Pending", "source_app": "frappe"})
		frappe.db.commit()

	def tearDown(self):
		frappe.db.rollback()

	def test_empty_translation_fallback(self):
		"""Test suggested_text fallback when translation is empty"""
		from translation_hub.translation_hub.doctype.translation_review.translation_review import (
			create_translation_review,
		)

		# Create review with empty current translation
		# The function should fall back to source_text
		review_name = create_translation_review(
			source_text="Hello World", language="pt-BR", source_app="frappe"
		)

		review = frappe.get_doc("Translation Review", review_name)

		# suggested_text should be populated (fallback to source_text)
		self.assertIsNotNone(review.suggested_text)
		self.assertNotEqual(review.suggested_text, "")
		self.assertEqual(review.suggested_text, "Hello World")  # Fallback value

	def test_suggested_text_never_empty(self):
		"""Test that suggested_text is always populated"""
		from translation_hub.translation_hub.doctype.translation_review.translation_review import (
			create_translation_review,
		)

		# Test multiple scenarios
		test_cases = [{"source_text": "Login"}, {"source_text": "Welcome to ERPNext"}]

		for case in test_cases:
			review_name = create_translation_review(
				source_text=case["source_text"], language="pt-BR", source_app="frappe"
			)
			review = frappe.get_doc("Translation Review", review_name)

			# Should never be empty
			self.assertTrue(review.suggested_text)
			self.assertGreater(len(review.suggested_text), 0)

	def test_existing_translation_used(self):
		"""Test that existing translation is used when available"""
		from translation_hub.translation_hub.doctype.translation_review.translation_review import (
			create_translation_review,
		)

		# Create a translation in database first
		trans = frappe.get_doc(
			{
				"doctype": "Translation",
				"source_text": "Dashboard",
				"language": "pt-BR",
				"translated_text": "Painel",
			}
		)
		trans.insert(ignore_permissions=True)

		# Create review for same text
		review_name = create_translation_review(
			source_text="Dashboard", language="pt-BR", source_app="frappe"
		)
		review = frappe.get_doc("Translation Review", review_name)

		# Should use existing translation
		self.assertEqual(review.suggested_text, "Painel")

	def test_mandatory_validation(self):
		"""Test that suggested_text is truly mandatory"""
		# Attempt to create review with explicitly empty suggested_text
		# Should fail validation
		review = frappe.get_doc(
			{
				"doctype": "Translation Review",
				"source_text": "Test",
				"language": "pt-BR",
				"source_app": "frappe",
				"suggested_text": "",  # Explicitly empty
			}
		)

		# Should raise error or auto-populate
		try:
			review.insert()
			# If it succeeds, suggested_text must not be empty
			self.assertNotEqual(review.suggested_text, "")
		except frappe.MandatoryError:
			# This is expected if validation catches empty suggested_text
			pass
