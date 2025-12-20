# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

"""
Tests for the AgentOrchestrator - coordinates the multi-agent translation pipeline.
"""

import unittest
from unittest.mock import MagicMock, patch

from translation_hub.core.agent_orchestrator import AgentOrchestrator, PipelineFailedError
from translation_hub.core.agents.base import TranslationEntry, TranslationResult


class MockConfig:
	"""Mock config for testing."""

	def __init__(self):
		self.api_key = "test-key"
		self.model_name = "test-model"
		self.llm_provider = "Gemini"
		self.max_batch_retries = 1
		self.retry_wait_seconds = 1
		self.quality_threshold = 0.8
		self.language_code = "pt-BR"


class TestAgentOrchestrator(unittest.TestCase):
	"""Test cases for AgentOrchestrator pipeline coordination."""

	def setUp(self):
		self.config = MockConfig()

	@patch("translation_hub.core.agent_orchestrator.TranslatorAgent")
	@patch("translation_hub.core.agent_orchestrator.RegionalReviewerAgent")
	@patch("translation_hub.core.agent_orchestrator.QualityAgent")
	def test_pipeline_initialization(self, MockQuality, MockReviewer, MockTranslator):
		"""Orchestrator should initialize all 3 agents."""
		orchestrator = AgentOrchestrator(
			config=self.config, app_name="erpnext", regional_profile=None, logger=None
		)

		MockTranslator.assert_called_once()
		MockReviewer.assert_called_once()
		MockQuality.assert_called_once()
		self.assertIsNotNone(orchestrator)

	@patch("translation_hub.core.agent_orchestrator.TranslatorAgent")
	@patch("translation_hub.core.agent_orchestrator.RegionalReviewerAgent")
	@patch("translation_hub.core.agent_orchestrator.QualityAgent")
	def test_translate_with_review_calls_all_phases(self, MockQuality, MockReviewer, MockTranslator):
		"""Pipeline should call all 3 agents in order."""
		# Setup mock returns
		mock_translator = MockTranslator.return_value
		mock_reviewer = MockReviewer.return_value
		mock_quality = MockQuality.return_value

		entry = TranslationEntry(msgid="Hello", msgstr="")
		mock_translator.translate.return_value = [entry]
		mock_reviewer.review.return_value = [entry]
		mock_quality.evaluate.return_value = [
			TranslationResult(msgid="Hello", msgstr="Olá", quality_score=0.9)
		]

		orchestrator = AgentOrchestrator(
			config=self.config, app_name="erpnext", regional_profile=None, logger=None
		)

		entries = [{"msgid": "Hello", "msgstr": ""}]
		results = orchestrator.translate_with_review(entries)

		# Verify all phases were called
		mock_translator.translate.assert_called_once()
		mock_reviewer.review.assert_called_once()
		mock_quality.evaluate.assert_called_once()

		# Verify results
		self.assertEqual(len(results), 1)
		self.assertEqual(results[0].msgid, "Hello")
		self.assertEqual(results[0].msgstr, "Olá")

	@patch("translation_hub.core.agent_orchestrator.TranslatorAgent")
	@patch("translation_hub.core.agent_orchestrator.RegionalReviewerAgent")
	@patch("translation_hub.core.agent_orchestrator.QualityAgent")
	def test_high_quality_translation_approved(self, MockQuality, MockReviewer, MockTranslator):
		"""Translations with score >= threshold should not need human review."""
		mock_quality = MockQuality.return_value
		mock_quality.evaluate.return_value = [
			TranslationResult(msgid="Hello", msgstr="Olá", quality_score=0.95, needs_human_review=False)
		]

		MockTranslator.return_value.translate.return_value = [TranslationEntry(msgid="Hello")]
		MockReviewer.return_value.review.return_value = [TranslationEntry(msgid="Hello")]

		orchestrator = AgentOrchestrator(self.config, None, None, None)
		results = orchestrator.translate_with_review([{"msgid": "Hello"}])

		self.assertFalse(results[0].needs_human_review)

	@patch("translation_hub.core.agent_orchestrator.TranslatorAgent")
	@patch("translation_hub.core.agent_orchestrator.RegionalReviewerAgent")
	@patch("translation_hub.core.agent_orchestrator.QualityAgent")
	def test_low_quality_translation_flagged(self, MockQuality, MockReviewer, MockTranslator):
		"""Translations with score < threshold should need human review."""
		mock_quality = MockQuality.return_value
		mock_quality.evaluate.return_value = [
			TranslationResult(
				msgid="Hello",
				msgstr="???",
				quality_score=0.3,
				needs_human_review=True,
				review_reasons=["Missing placeholders"],
			)
		]

		MockTranslator.return_value.translate.return_value = [TranslationEntry(msgid="Hello")]
		MockReviewer.return_value.review.return_value = [TranslationEntry(msgid="Hello")]

		orchestrator = AgentOrchestrator(self.config, None, None, None)
		results = orchestrator.translate_with_review([{"msgid": "Hello"}])

		self.assertTrue(results[0].needs_human_review)
		self.assertIn("Missing placeholders", results[0].review_reasons)

	@patch("translation_hub.core.agent_orchestrator.TranslatorAgent")
	@patch("translation_hub.core.agent_orchestrator.RegionalReviewerAgent")
	@patch("translation_hub.core.agent_orchestrator.QualityAgent")
	def test_pipeline_failure_raises_exception(self, MockQuality, MockReviewer, MockTranslator):
		"""Pipeline failure should raise PipelineFailedError (no automatic fallback)."""
		mock_translator = MockTranslator.return_value
		mock_translator.translate.side_effect = Exception("API Error")

		orchestrator = AgentOrchestrator(self.config, None, None, None)

		with self.assertRaises(PipelineFailedError):
			orchestrator.translate_with_review([{"msgid": "Hello"}])

	def test_convert_entries(self):
		"""Entry conversion should work correctly."""
		orchestrator = AgentOrchestrator(self.config, None, None, None)

		dict_entries = [
			{"msgid": "Hello", "msgstr": "", "msgctxt": "greeting"},
			{"msgid": "World", "occurrences": [("file.py", "10")]},
		]

		entries = orchestrator._convert_entries(dict_entries)

		self.assertEqual(len(entries), 2)
		self.assertEqual(entries[0].msgid, "Hello")
		self.assertEqual(entries[0].context, "greeting")
		self.assertEqual(entries[1].occurrences, [("file.py", "10")])


if __name__ == "__main__":
	unittest.main()
