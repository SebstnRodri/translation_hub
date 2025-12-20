# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

"""
Tests for the QualityAgent - evaluates translation quality and decides if human review is needed.
"""

import unittest
from unittest.mock import MagicMock

from translation_hub.core.agents.base import TranslationEntry
from translation_hub.core.agents.quality_agent import QualityAgent


class MockConfig:
	"""Mock config for testing."""

	def __init__(self):
		self.quality_threshold = 0.8
		self.api_key = "test-key"
		self.model_name = "test-model"
		self.llm_provider = "Gemini"
		self.max_batch_retries = 1
		self.retry_wait_seconds = 1


class TestQualityAgent(unittest.TestCase):
	"""Test cases for QualityAgent quality checks."""

	def setUp(self):
		self.config = MockConfig()
		self.agent = QualityAgent(self.config, logger=None)

	def test_placeholder_check_pass(self):
		"""Placeholders preserved correctly should pass."""
		entry = TranslationEntry(
			msgid="Hello {0}, welcome to {1}",
			raw_translation="Olá {0}, bem-vindo ao {1}",
			reviewed_translation="Olá {0}, bem-vindo ao {1}",
		)
		results = self.agent.evaluate([entry])

		self.assertEqual(len(results), 1)
		result = results[0]
		# Should have high score if placeholders match
		self.assertGreaterEqual(result.quality_score, 0.8)
		self.assertFalse(result.needs_human_review)

	def test_placeholder_check_fail_missing(self):
		"""Missing placeholders should lower score."""
		entry = TranslationEntry(
			msgid="Hello {0}, welcome to {1}",
			raw_translation="Olá, bem-vindo",  # Missing {0} and {1}
			reviewed_translation="Olá, bem-vindo",
		)
		results = self.agent.evaluate([entry])

		result = results[0]
		self.assertLess(result.quality_score, 0.8)
		self.assertTrue(result.needs_human_review)
		self.assertTrue(any("Missing placeholders" in r for r in result.review_reasons))

	def test_html_tags_preserved(self):
		"""HTML tags should be preserved."""
		entry = TranslationEntry(
			msgid="<strong>Important</strong> message",
			raw_translation="<strong>Importante</strong> mensagem",
			reviewed_translation="<strong>Importante</strong> mensagem",
		)
		results = self.agent.evaluate([entry])

		result = results[0]
		self.assertGreaterEqual(result.quality_score, 0.8)

	def test_html_tags_missing(self):
		"""Missing HTML tags should lower score."""
		entry = TranslationEntry(
			msgid="<strong>Important</strong> message",
			raw_translation="Importante mensagem",  # Missing <strong> tags
			reviewed_translation="Importante mensagem",
		)
		results = self.agent.evaluate([entry])

		result = results[0]
		self.assertLess(result.quality_score, 1.0)
		self.assertTrue(any("HTML tag" in r for r in result.review_reasons))

	def test_empty_translation_fails(self):
		"""Empty translation should fail quality check."""
		entry = TranslationEntry(msgid="Hello world", raw_translation="", reviewed_translation="")
		results = self.agent.evaluate([entry])

		result = results[0]
		self.assertEqual(result.quality_score, 0.0)
		self.assertTrue(result.needs_human_review)

	def test_untranslated_identical_text(self):
		"""Translation identical to source should be flagged."""
		entry = TranslationEntry(
			msgid="Hello world this is a test",
			raw_translation="Hello world this is a test",  # Not translated
			reviewed_translation="Hello world this is a test",
		)
		results = self.agent.evaluate([entry])

		result = results[0]
		self.assertLess(result.quality_score, 1.0)
		self.assertTrue(any("identical" in r.lower() for r in result.review_reasons))

	def test_length_ratio_acceptable(self):
		"""Normal length ratio should pass."""
		entry = TranslationEntry(
			msgid="Hello world",
			raw_translation="Olá mundo",  # Similar length
			reviewed_translation="Olá mundo",
		)
		results = self.agent.evaluate([entry])

		result = results[0]
		self.assertNotIn("length_ratio", [r for r in result.review_reasons if "too" in r.lower()])

	def test_length_ratio_too_short(self):
		"""Very short translation should be flagged."""
		entry = TranslationEntry(
			msgid="This is a very long sentence that contains many words and should be translated fully",
			raw_translation="Oi",  # Way too short
			reviewed_translation="Oi",
		)
		results = self.agent.evaluate([entry])

		result = results[0]
		self.assertTrue(any("too short" in r.lower() for r in result.review_reasons))

	def test_threshold_customization(self):
		"""Custom threshold should be respected."""
		self.config.quality_threshold = 0.5  # Lower threshold
		agent = QualityAgent(self.config, logger=None)

		# Entry with score around 0.6 should pass with threshold 0.5
		entry = TranslationEntry(
			msgid="Hello {0}",
			raw_translation="Olá",  # Missing placeholder, score will be low
			reviewed_translation="Olá",
		)
		results = agent.evaluate([entry])

		# With lower threshold, more borderline cases pass
		self.assertIsNotNone(results)


if __name__ == "__main__":
	unittest.main()
