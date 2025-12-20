# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RegionalExpertProfile(Document):
	def validate(self):
		"""Validate the profile configuration."""
		if self.industry_jargon:
			try:
				import json

				json.loads(self.industry_jargon)
			except json.JSONDecodeError:
				frappe.throw("Industry Jargon must be valid JSON")

	def get_context_for_prompt(self) -> dict:
		"""
		Returns a dictionary with all context information
		formatted for injection into LLM prompts.
		"""
		context = {
			"region": self.region,
			"formality_level": self.formality_level,
			"cultural_context": self.cultural_context or "",
		}

		# Parse industry jargon
		if self.industry_jargon:
			try:
				import json

				context["industry_jargon"] = json.loads(self.industry_jargon)
			except json.JSONDecodeError:
				context["industry_jargon"] = {}
		else:
			context["industry_jargon"] = {}

		# Forbidden terms
		context["forbidden_terms"] = []
		for term in self.forbidden_terms:
			context["forbidden_terms"].append({"term": term.term, "reason": term.reason})

		# Preferred synonyms
		context["preferred_synonyms"] = {}
		for syn in self.preferred_synonyms:
			context["preferred_synonyms"][syn.original_term] = {
				"preferred": syn.preferred_term,
				"context": syn.context,
			}

		return context
