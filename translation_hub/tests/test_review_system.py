import frappe
from frappe.tests.utils import FrappeTestCase

from translation_hub.translation_hub.doctype.translation_review.translation_review import (
	create_translation_review,
)


class TestReviewSystem(FrappeTestCase):
	def setUp(self):
		# Clean up data before each test
		frappe.db.delete("Translation Review")
		frappe.db.delete("Translation Task")
		frappe.db.delete("Term Rejection Pattern")
		frappe.db.delete("Localization Profile")
		frappe.db.commit()

		# Create localized profile for auto-review tests
		self.create_test_profile()

	def create_test_profile(self):
		if not frappe.db.exists("Localization Profile", "Test Profile"):
			doc = frappe.get_doc(
				{
					"doctype": "Localization Profile",
					"profile_name": "Test Profile",
					"country": "Brazil",
					"language": "pt-BR",
					"is_active": 1,
					"regional_glossary": [
						{"english_term": "Invoice", "localized_term": "Nota Fiscal", "domain": "Accounting"}
					],
					"context_rules": [
						{
							"rule_type": "Regex Pattern",
							"source_pattern": "Return Against (?P<doc>.*)",
							"target_translation": "Devolução de {doc}",
							"priority": 100,
						}
					],
				}
			)
			doc.insert(ignore_permissions=True)

	def test_rejection_crates_task_and_pattern(self):
		"""
		Test that rejecting a review creates a Translation Task and increments Rejection Pattern.
		"""
		source_text = "Test Term"

		# 1. Create Review
		review = frappe.get_doc(
			{
				"doctype": "Translation Review",
				"source_text": source_text,
				"language": "pt-BR",
				"source_app": "translation_hub",
				"suggested_text": "Teste",
				"status": "Pending",
			}
		)
		review.insert(ignore_permissions=True)

		# 2. Reject it
		review.status = "Rejected"
		review.rejection_reason = "Bad Logic"
		review.save(ignore_permissions=True)

		# 3. Check Task Creation
		task_exists = frappe.db.exists("Translation Task", {"source_text": source_text})
		self.assertTrue(task_exists, "Translation Task should be created upon rejection")

		# 4. Check Pattern Creation
		pattern_name = frappe.db.exists("Term Rejection Pattern", {"source_text": source_text})
		self.assertTrue(pattern_name, "Term Rejection Pattern should be created")

		pattern = frappe.get_doc("Term Rejection Pattern", pattern_name)
		self.assertEqual(pattern.rejection_count, 1)

		# 5. Reject Again (Same Term)
		review2 = frappe.get_doc(
			{
				"doctype": "Translation Review",
				"source_text": source_text,
				"language": "pt-BR",
				"source_app": "translation_hub",
				"suggested_text": "Teste 2",
				"status": "Pending",
			}
		)
		review2.insert(ignore_permissions=True)
		review2.status = "Rejected"
		review2.rejection_reason = "Still Bad"
		review2.save(ignore_permissions=True)

		pattern.reload()
		self.assertEqual(pattern.rejection_count, 2)

	def test_auto_review_glossary(self):
		"""
		Test that review is auto-approved if it matches Regional Glossary.
		"""
		# "Invoice" -> "Nota Fiscal" is in Test Profile
		review = frappe.get_doc(
			{
				"doctype": "Translation Review",
				"source_text": "Invoice",
				"language": "pt-BR",
				"source_app": "translation_hub",
				"suggested_text": "Nota Fiscal",  # Matches glossary
				"status": "Pending",
			}
		)
		review.insert(ignore_permissions=True)

		# Logic is in before_insert
		self.assertEqual(review.status, "Approved", "Should be auto-approved based on Glossary")

	def test_auto_review_context_rule(self):
		"""
		Test that review is auto-approved if it matches Context Rule regex.
		"""
		# "Return Against {doc}" -> "Devolução de {doc}"
		review = frappe.get_doc(
			{
				"doctype": "Translation Review",
				"source_text": "Return Against Invoice",
				"language": "pt-BR",
				"source_app": "translation_hub",
				"suggested_text": "Devolução de Invoice",  # Matches rule logic
				"status": "Pending",
			}
		)
		review.insert(ignore_permissions=True)

		self.assertEqual(review.status, "Approved", "Should be auto-approved based on Context Rule")

	def test_no_auto_review_on_mismatch(self):
		"""
		Test that review stays Pending if translation does NOT match profile.
		"""
		review = frappe.get_doc(
			{
				"doctype": "Translation Review",
				"source_text": "Invoice",
				"language": "pt-BR",
				"source_app": "translation_hub",
				"suggested_text": "Fatura",  # Mismatch (Profile expects "Nota Fiscal")
				"status": "Pending",
			}
		)
		review.insert(ignore_permissions=True)

		self.assertEqual(review.status, "Pending", "Should remain Pending if translation mismatches Glossary")
