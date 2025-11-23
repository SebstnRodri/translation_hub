import json
from unittest.mock import MagicMock, call, patch

import pytest

from translation_hub.core.config import TranslationConfig
from translation_hub.core.translation_service import GeminiService


@pytest.fixture
def mock_config():
	"""
	Provides a default TranslationConfig for tests.
	"""
	return TranslationConfig(
		api_key="test_api_key", max_batch_retries=2, max_single_retries=2, retry_wait_seconds=0.1
	)


@pytest.fixture
def mock_logger():
	"""Mocks the logger."""
	return MagicMock()


@patch("translation_hub.core.translation_service.genai.configure")
@patch("translation_hub.core.translation_service.genai.GenerativeModel")
def test_gemini_service_init(mock_generative_model, mock_configure, mock_config, mock_logger):
	"""
	Tests the initialization of the GeminiService.
	"""
	service = GeminiService(config=mock_config, logger=mock_logger)
	mock_configure.assert_called_once_with(api_key="test_api_key")
	mock_generative_model.assert_called_with(mock_config.model_name)
	assert service.model is not None


def test_translate_batch_success(mocker, mock_config, mock_logger):
	"""
	Tests a successful batch translation with the new data structure.
	"""
	entries_to_translate = [
		{"msgid": "Hello", "context": {}},
		{"msgid": "World", "context": {}},
	]
	api_response_data = [{"translated": "Olá"}, {"translated": "Mundo"}]
	expected_translation = [
		{"msgid": "Hello", "msgstr": "Olá"},
		{"msgid": "World", "msgstr": "Mundo"},
	]

	mock_response = MagicMock()
	mock_response.text = json.dumps(api_response_data)

	mocker.patch(
		"translation_hub.core.translation_service.GeminiService._configure_model",
		return_value=MagicMock(generate_content=MagicMock(return_value=mock_response)),
	)

	service = GeminiService(config=mock_config, logger=mock_logger)
	translations = service.translate(entries_to_translate)

	assert translations == expected_translation
	service.model.generate_content.assert_called_once()


def test_translate_batch_retry_and_succeed(mocker, mock_config, mock_logger):
	"""
	Tests the retry mechanism with the new data structure.
	"""
	entries_to_translate = [{"msgid": "Hello", "context": {}}]
	api_response_data = [{"translated": "Olá"}]
	expected_translation = [{"msgid": "Hello", "msgstr": "Olá"}]

	mock_failure_response = MagicMock()
	mock_failure_response.text = "Invalid JSON"
	mock_success_response = MagicMock()
	mock_success_response.text = json.dumps(api_response_data)

	mock_model = MagicMock()
	mock_model.generate_content.side_effect = [
		json.JSONDecodeError("Mocked error", "", 0),
		mock_success_response,
	]

	mocker.patch(
		"translation_hub.core.translation_service.GeminiService._configure_model", return_value=mock_model
	)

	service = GeminiService(config=mock_config, logger=mock_logger)
	translations = service.translate(entries_to_translate)

	assert translations == expected_translation
	assert service.model.generate_content.call_count == 2


def test_translate_fallback_to_single_entry(mocker, mock_config, mock_logger):
	"""
	Tests the fallback to single-entry translation with the new data structure.
	"""
	entries_to_translate = [
		{"msgid": "Hello", "context": {}},
		{"msgid": "World", "context": {}},
	]
	expected_translations = [
		{"msgid": "Hello", "msgstr": "[TRANSLATION_FAILED] Hello"},
		{"msgid": "World", "msgstr": "[TRANSLATION_FAILED] World"},
	]

	mock_model = MagicMock()
	mock_model.generate_content.side_effect = json.JSONDecodeError("Mocked error", "", 0)

	mocker.patch(
		"translation_hub.core.translation_service.GeminiService._configure_model", return_value=mock_model
	)

	service = GeminiService(config=mock_config, logger=mock_logger)

	mocker.patch.object(
		service,
		"_translate_single",
		side_effect=lambda entry: {
			"msgid": entry["msgid"],
			"msgstr": f"[TRANSLATION_FAILED] {entry['msgid']}",
		},
	)

	translations = service.translate(entries_to_translate)

	assert translations == expected_translations
	assert service.model.generate_content.call_count == mock_config.max_batch_retries
	assert service._translate_single.call_count == len(entries_to_translate)


def test_build_batch_prompt_with_context(mocker, mock_config, mock_logger):
	mocker.patch("translation_hub.core.translation_service.GeminiService._configure_model")
	service = GeminiService(config=mock_config, logger=mock_logger)
	entries = [
		{
			"msgid": "Series Name",
			"context": {
				"occurrences": [("erpnext/controllers/series.py", 188)],
				"comment": "Displayed on the Series setup screen",
				"tcomment": "",
				"flags": [],
			},
		}
	]

	prompt = service._build_batch_prompt(entries)

	assert "Você é um tradutor especializado em sistemas ERP" in prompt
	assert '"msgid": "Series Name"' in prompt
	assert '"occurrences":' in prompt
	assert "erpnext/controllers/series.py" in prompt
	assert "188" in prompt
	assert '"comment": "Displayed on the Series setup screen"' in prompt


def test_preserve_whitespace(mocker, mock_config, mock_logger):
	"""
	Tests that leading/trailing whitespace is preserved in the translation.
	"""
	mocker.patch("translation_hub.core.translation_service.GeminiService._configure_model")
	service = GeminiService(config=mock_config, logger=mock_logger)

	original = "  Hello World  "
	translated = "Olá Mundo"
	preserved = service._preserve_whitespace(original, translated)

	assert preserved == "  Olá Mundo  "
