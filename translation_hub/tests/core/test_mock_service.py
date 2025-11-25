import pytest

from translation_hub.core.config import TranslationConfig
from translation_hub.core.translation_service import MockTranslationService


def test_mock_service_basic_translation():
	"""Test that MockTranslationService adds [ES] prefix."""
	config = TranslationConfig()
	service = MockTranslationService(config=config)

	entries = [
		{"msgid": "Hello", "context": {}},
		{"msgid": "World", "context": {}},
	]

	translations = service.translate(entries)

	assert len(translations) == 2
	assert translations[0]["msgid"] == "Hello"
	assert translations[0]["msgstr"] == "[ES] Hello"
	assert translations[1]["msgid"] == "World"
	assert translations[1]["msgstr"] == "[ES] World"


def test_mock_service_preserves_whitespace():
	"""Test that MockTranslationService preserves leading/trailing whitespace."""
	config = TranslationConfig()
	service = MockTranslationService(config=config)

	entries = [
		{"msgid": "  Hello  ", "context": {}},
	]

	translations = service.translate(entries)

	assert translations[0]["msgstr"] == "  [ES] Hello  "


def test_mock_service_with_delay():
	"""Test that MockTranslationService simulates processing delay."""
	import time

	config = TranslationConfig()
	service = MockTranslationService(config=config)
	service.delay = 0.05  # 50ms per entry

	entries = [
		{"msgid": "Test1", "context": {}},
		{"msgid": "Test2", "context": {}},
	]

	start = time.time()
	service.translate(entries)
	elapsed = time.time() - start

	# Should take at least 100ms for 2 entries
	assert elapsed >= 0.1


def test_mock_service_failure_simulation():
	"""Test that MockTranslationService can simulate failures."""
	config = TranslationConfig()
	service = MockTranslationService(config=config)
	service.fail_rate = 1.0  # 100% failure rate

	entries = [
		{"msgid": "Test", "context": {}},
	]

	translations = service.translate(entries)

	assert translations[0]["msgstr"] == "[TRANSLATION_FAILED] Test"
