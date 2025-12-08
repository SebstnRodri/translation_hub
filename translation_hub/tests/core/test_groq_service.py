"""
Unit tests for GroqService translation service.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from translation_hub.core.config import TranslationConfig

# Create a mock openai module before importing GroqService
mock_openai = MagicMock()
mock_openai_client = MagicMock()
mock_openai.OpenAI = MagicMock(return_value=mock_openai_client)
sys.modules["openai"] = mock_openai


@pytest.fixture
def mock_config():
	"""
	Provides a default TranslationConfig for Groq tests.
	"""
	return TranslationConfig(
		api_key="test_groq_api_key",
		model_name="llama-3.3-70b-versatile",
		max_batch_retries=2,
		max_single_retries=2,
		retry_wait_seconds=0.1,
		language_code="pt_BR",
	)


@pytest.fixture
def mock_logger():
	"""Mocks the logger."""
	return MagicMock()


@pytest.fixture(autouse=True)
def reset_openai_mock():
	"""Reset the openai mock before each test."""
	mock_openai.reset_mock()
	mock_openai_client.reset_mock()
	mock_openai.OpenAI.reset_mock()
	mock_openai.OpenAI.return_value = mock_openai_client
	yield


@patch("translation_hub.core.translation_service.GroqService._fetch_context", return_value={})
def test_groq_service_init(mock_fetch_context, mock_config, mock_logger):
	"""
	Tests the initialization of the GroqService.
	"""
	from translation_hub.core.translation_service import GroqService

	service = GroqService(config=mock_config, logger=mock_logger)

	mock_openai.OpenAI.assert_called_once_with(
		api_key="test_groq_api_key", base_url="https://api.groq.com/openai/v1"
	)
	assert service.client is not None


@patch("translation_hub.core.translation_service.GroqService._fetch_context", return_value={})
def test_groq_service_translate_batch_success(mock_fetch_context, mock_config, mock_logger):
	"""
	Tests a successful batch translation with GroqService.
	"""
	from translation_hub.core.translation_service import GroqService

	entries_to_translate = [
		{"msgid": "Hello", "context": {}},
		{"msgid": "World", "context": {}},
	]
	api_response_data = '[{"translated": "Olá"}, {"translated": "Mundo"}]'
	expected_translation = [
		{"msgid": "Hello", "msgstr": "Olá"},
		{"msgid": "World", "msgstr": "Mundo"},
	]

	mock_response = MagicMock()
	mock_response.choices = [MagicMock()]
	mock_response.choices[0].message.content = api_response_data
	mock_openai_client.chat.completions.create.return_value = mock_response

	service = GroqService(config=mock_config, logger=mock_logger)
	translations = service.translate(entries_to_translate)

	assert translations == expected_translation
	mock_openai_client.chat.completions.create.assert_called_once()


@patch("translation_hub.core.translation_service.GroqService._fetch_context", return_value={})
def test_groq_service_preserves_whitespace(mock_fetch_context, mock_config, mock_logger):
	"""
	Tests that leading/trailing whitespace is preserved in the translation.
	"""
	from translation_hub.core.translation_service import GroqService

	service = GroqService(config=mock_config, logger=mock_logger)

	original = "  Hello World  "
	translated = "Olá Mundo"
	preserved = service._preserve_whitespace(original, translated)

	assert preserved == "  Olá Mundo  "


@patch("translation_hub.core.translation_service.GroqService._fetch_context", return_value={})
def test_groq_service_clean_json_response(mock_fetch_context, mock_config, mock_logger):
	"""
	Tests the JSON response cleaning for markdown code blocks.
	"""
	from translation_hub.core.translation_service import GroqService

	service = GroqService(config=mock_config, logger=mock_logger)

	# Test with markdown code block
	response_with_markdown = '```json\n[{"translated": "Olá"}]\n```'
	cleaned = service._clean_json_response(response_with_markdown)
	assert cleaned == '[{"translated": "Olá"}]'

	# Test with plain JSON
	response_plain = '[{"translated": "Olá"}]'
	cleaned_plain = service._clean_json_response(response_plain)
	assert cleaned_plain == '[{"translated": "Olá"}]'


@patch("translation_hub.core.translation_service.GroqService._fetch_context", return_value={})
def test_groq_service_fallback_to_single_entry(mock_fetch_context, mock_config, mock_logger):
	"""
	Tests the fallback to single-entry translation when batch fails.
	"""
	from translation_hub.core.translation_service import GroqService

	entries_to_translate = [
		{"msgid": "Hello", "context": {}},
		{"msgid": "World", "context": {}},
	]

	# First calls will fail (for batch), then succeed for single
	mock_response_fail = MagicMock()
	mock_response_fail.choices = [MagicMock()]
	mock_response_fail.choices[0].message.content = "Invalid JSON"

	mock_response_success = MagicMock()
	mock_response_success.choices = [MagicMock()]
	mock_response_success.choices[0].message.content = '{"translated": "Olá"}'

	# Fail batch attempts, then succeed for single entries
	mock_openai_client.chat.completions.create.side_effect = [
		mock_response_fail,  # Batch attempt 1
		mock_response_fail,  # Batch attempt 2
		mock_response_success,  # Single entry 1
		mock_response_success,  # Single entry 2
	]

	service = GroqService(config=mock_config, logger=mock_logger)
	translations = service.translate(entries_to_translate)

	# Should have fallback results
	assert len(translations) == 2
	# Count total API calls: 2 batch + 2 single = 4
	assert mock_openai_client.chat.completions.create.call_count == 4
