# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

"""
Tests for Regional Expert Profile DocType and integration with translation pipeline.
"""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestRegionalExpertProfile(FrappeTestCase):
	"""Test cases for Regional Expert Profile functionality."""

	def setUp(self):
		super().setUp()
		# Ensure pt-BR language exists
		if not frappe.db.exists("Language", "pt-BR"):
			frappe.get_doc(
				{"doctype": "Language", "language_code": "pt-BR", "language_name": "Portuguese (Brazil)"}
			).insert(ignore_permissions=True)

	def tearDown(self):
		# Clean up test profiles
		frappe.db.delete("Regional Expert Profile", {"profile_name": ["like", "Test%"]})
		frappe.db.commit()

	def test_create_profile_basic(self):
		"""Basic profile creation should work."""
		profile = frappe.get_doc(
			{
				"doctype": "Regional Expert Profile",
				"profile_name": "Test Basic Profile",
				"region": "pt-BR",
				"language": "pt-BR",
				"formality_level": "Formal",
			}
		)
		profile.insert(ignore_permissions=True)

		self.assertEqual(profile.region, "pt-BR")
		self.assertEqual(profile.formality_level, "Formal")

	def test_create_profile_with_cultural_context(self):
		"""Profile with cultural context should be created."""
		profile = frappe.get_doc(
			{
				"doctype": "Regional Expert Profile",
				"profile_name": "Test Cultural Profile",
				"region": "pt-BR",
				"language": "pt-BR",
				"cultural_context": "Use 'você' ao invés de 'tu'. Prefira termos técnicos em português.",
				"formality_level": "Formal",
			}
		)
		profile.insert(ignore_permissions=True)

		self.assertIn("você", profile.cultural_context)

	def test_create_profile_with_forbidden_terms(self):
		"""Profile with forbidden terms should be created."""
		profile = frappe.get_doc(
			{
				"doctype": "Regional Expert Profile",
				"profile_name": "Test Forbidden Terms",
				"region": "pt-BR",
				"language": "pt-BR",
				"forbidden_terms": [
					{"term": "deletar", "reason": "Use excluir"},
					{"term": "setar", "reason": "Use definir"},
				],
			}
		)
		profile.insert(ignore_permissions=True)

		self.assertEqual(len(profile.forbidden_terms), 2)
		self.assertEqual(profile.forbidden_terms[0].term, "deletar")

	def test_create_profile_with_preferred_synonyms(self):
		"""Profile with preferred synonyms should be created."""
		profile = frappe.get_doc(
			{
				"doctype": "Regional Expert Profile",
				"profile_name": "Test Synonyms",
				"region": "pt-BR",
				"language": "pt-BR",
				"preferred_synonyms": [
					{"original_term": "invoice", "preferred_term": "fatura", "context": "Fiscal"},
					{"original_term": "stock", "preferred_term": "estoque", "context": "Inventário"},
				],
			}
		)
		profile.insert(ignore_permissions=True)

		self.assertEqual(len(profile.preferred_synonyms), 2)
		self.assertEqual(profile.preferred_synonyms[0].preferred_term, "fatura")

	def test_get_context_for_prompt(self):
		"""get_context_for_prompt should return formatted context."""
		profile = frappe.get_doc(
			{
				"doctype": "Regional Expert Profile",
				"profile_name": "Test Context Method",
				"region": "pt-BR",
				"language": "pt-BR",
				"formality_level": "Formal",
				"cultural_context": "Brazilian Portuguese context",
				"industry_jargon": '{"Invoice": "Fatura"}',
				"forbidden_terms": [
					{"term": "deletar", "reason": "Use excluir"},
				],
				"preferred_synonyms": [
					{"original_term": "stock", "preferred_term": "estoque", "context": "Inventário"},
				],
			}
		)
		profile.insert(ignore_permissions=True)

		context = profile.get_context_for_prompt()

		self.assertEqual(context["region"], "pt-BR")
		self.assertEqual(context["formality_level"], "Formal")
		self.assertEqual(context["cultural_context"], "Brazilian Portuguese context")
		self.assertIn("Invoice", context["industry_jargon"])
		self.assertEqual(len(context["forbidden_terms"]), 1)
		self.assertIn("stock", context["preferred_synonyms"])

	def test_invalid_industry_jargon_json(self):
		"""Invalid JSON in industry_jargon should raise error."""
		profile = frappe.get_doc(
			{
				"doctype": "Regional Expert Profile",
				"profile_name": "Test Invalid JSON",
				"region": "pt-BR",
				"language": "pt-BR",
				"industry_jargon": "{invalid json}",
			}
		)

		with self.assertRaises(frappe.ValidationError):
			profile.insert(ignore_permissions=True)

	def test_profile_linked_to_job(self):
		"""Profile can be linked to Translation Job."""
		# Create profile
		profile = frappe.get_doc(
			{
				"doctype": "Regional Expert Profile",
				"profile_name": "Test Job Link",
				"region": "pt-BR",
				"language": "pt-BR",
			}
		)
		profile.insert(ignore_permissions=True)

		# Verify the profile exists and can be referenced
		self.assertTrue(frappe.db.exists("Regional Expert Profile", "Test Job Link"))
