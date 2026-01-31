# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

"""
AgentOrchestrator: Coordinates the multi-agent translation pipeline.

Pipeline flow:
1. TranslatorAgent: Domain-specific translation
2. RegionalReviewerAgent: Cultural/regional adjustments
3. QualityAgent: Quality evaluation and human review routing

Design decisions:
- Quality over economy: 3 LLM calls per batch (no economy mode)
- No automatic fallback: If pipeline fails, pause for inspection
"""

from typing import Any

import frappe

from translation_hub.core.agents.base import TranslationEntry, TranslationResult
from translation_hub.core.agents.quality_agent import QualityAgent
from translation_hub.core.agents.regional_reviewer_agent import RegionalReviewerAgent
from translation_hub.core.agents.translator_agent import TranslatorAgent


class AgentOrchestrator:
	"""
	Coordinates the translation process through multiple specialized agents.
	Ensures review before any data is saved.
	"""

	def __init__(self, config, app_name: str | None = None, regional_profile: str | None = None, logger=None):
		self.config = config
		self.app_name = app_name
		self.regional_profile = regional_profile
		self.logger = logger

		# Initialize agents
		self.translator_agent = TranslatorAgent(config, app_name, logger)
		self.reviewer_agent = RegionalReviewerAgent(config, regional_profile, logger)
		self.quality_agent = QualityAgent(config, logger)

		self._log("AgentOrchestrator initialized with 3 agents")

	def _log(self, message: str):
		if self.logger:
			self.logger.info(f"[AgentOrchestrator] {message}")

	def _log_error(self, message: str):
		if self.logger:
			self.logger.error(f"[AgentOrchestrator] {message}")

	def translate_with_review(self, entries: list[dict]) -> list[TranslationResult]:
		"""
		Execute the full translation pipeline with mandatory review.

		Pipeline:
		1. TranslatorAgent translates
		2. RegionalReviewerAgent adjusts for culture
		3. QualityAgent evaluates and routes

		Args:
			entries: List of dictionaries from PO entries (msgid, context, etc.)

		Returns:
			List of TranslationResult objects with quality scores and review flags
		"""
		self._log(f"Starting pipeline for {len(entries)} entries")

		# Convert to TranslationEntry objects
		translation_entries = self._convert_entries(entries)

		try:
			# Phase 1: Translation
			self._log("Phase 1: Translation")
			translated = self.translator_agent.translate(translation_entries)

			# Phase 2: Regional Review
			self._log("Phase 2: Regional Review")
			reviewed = self.reviewer_agent.review(translated)

			# Phase 3: Quality Evaluation
			self._log("Phase 3: Quality Evaluation")
			results = self.quality_agent.evaluate(reviewed)

			self._log(f"Pipeline complete: {len(results)} results")
			return results

		except Exception as e:
			# NO AUTOMATIC FALLBACK - pause for inspection
			self._log_error(f"Pipeline failed: {e}")
			self._save_pipeline_state(translation_entries, str(e))
			raise PipelineFailedError(
				f"Agent pipeline failed at an intermediate step. " f"State saved for inspection. Error: {e}"
			)

	def _convert_entries(self, entries: list[dict]) -> list[TranslationEntry]:
		"""Convert PO entry dictionaries to TranslationEntry objects."""
		result = []
		for entry in entries:
			te = TranslationEntry(
				msgid=entry.get("msgid", ""),
				msgstr=entry.get("msgstr", ""),
				context=entry.get("msgctxt", "") or entry.get("context", ""),
				occurrences=entry.get("occurrences", []),
				flags=entry.get("flags", []),
				comment=entry.get("comment", ""),
			)
			result.append(te)
		return result

	def _save_pipeline_state(self, entries: list[TranslationEntry], error: str):
		"""Save current pipeline state for later inspection/resume."""
		try:
			state = {
				"entries_count": len(entries),
				"error": error,
				"entries_snapshot": [
					{
						"msgid": e.msgid,
						"raw_translation": e.raw_translation,
						"reviewed_translation": e.reviewed_translation,
						"msgstr": e.msgstr,
					}
					for e in entries
				],
			}

			# Log to Translation Job if available
			import json

			self._log(f"Pipeline state saved: {json.dumps(state, indent=2, ensure_ascii=False)[:500]}...")

		except Exception as e:
			self._log_error(f"Failed to save pipeline state: {e}")


class PipelineFailedError(Exception):
	"""Raised when the agent pipeline fails and needs inspection."""

	pass


def create_review_from_result(result: TranslationResult, source_app: str, language: str) -> str:
	"""
	Create a Translation Review record for a result that needs human review.

	Returns:
		Name of the created Translation Review, or empty string if skipped
	"""
	# Validate required fields - skip if empty
	if not result.msgid or not result.msgstr:
		import frappe
		frappe.log_error(
			f"Skipped creating Translation Review: empty msgid='{result.msgid}' or msgstr='{result.msgstr}'",
			"Translation Hub - Empty Review"
		)
		return ""
	
	review = frappe.get_doc(
		{
			"doctype": "Translation Review",
			"source_text": result.msgid,
			"suggested_text": result.msgstr,
			"source_app": source_app,
			"language": language,
			"status": "Pending",
			"ai_suggestion_snapshot": result.msgstr,
			"context_snapshot": ", ".join(result.review_reasons),
		}
	)
	review.insert(ignore_permissions=True)
	return review.name
