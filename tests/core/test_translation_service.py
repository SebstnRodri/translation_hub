import json
import pytest
from unittest.mock import MagicMock, patch, call

from translation_hub.core.config import TranslationConfig
from translation_hub.core.translation_service import GeminiService


@pytest.fixture
def mock_config():
    """
    Provides a default TranslationConfig for tests.
    """
    return TranslationConfig(max_batch_retries=2, max_single_retries=2, retry_wait_seconds=0.1)


@patch("translation_hub.core.translation_service.genai.configure")
@patch("translation_hub.core.translation_service.genai.GenerativeModel")
@patch("translation_hub.core.translation_service.load_dotenv")
def test_gemini_service_init(mock_load_dotenv, mock_generative_model, mock_configure, mock_config):
    """
    Tests the initialization of the GeminiService.
    """
    service = GeminiService(config=mock_config)
    mock_load_dotenv.assert_called_once()
    mock_configure.assert_called_once()
    mock_generative_model.assert_called_with(mock_config.model_name)
    assert service.model is not None


def test_translate_batch_success(mocker, mock_config):
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

    service = GeminiService(config=mock_config)
    translations = service.translate(entries_to_translate)

    assert translations == expected_translation
    service.model.generate_content.assert_called_once()


def test_translate_batch_retry_and_succeed(mocker, mock_config):
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
    mock_model.generate_content.side_effect = [json.JSONDecodeError("Mocked error", "", 0), mock_success_response]

    mocker.patch("translation_hub.core.translation_service.GeminiService._configure_model", return_value=mock_model)

    service = GeminiService(config=mock_config)
    translations = service.translate(entries_to_translate)

    assert translations == expected_translation
    assert service.model.generate_content.call_count == 2


def test_translate_fallback_to_single_entry(mocker, mock_config):
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

    mocker.patch("translation_hub.core.translation_service.GeminiService._configure_model", return_value=mock_model)

    service = GeminiService(config=mock_config)

    mocker.patch.object(
        service,
        "_translate_single",
        side_effect=lambda entry: {"msgid": entry["msgid"], "msgstr": f"[TRANSLATION_FAILED] {entry['msgid']}"},
    )

    translations = service.translate(entries_to_translate)

    assert translations == expected_translations
    assert service.model.generate_content.call_count == mock_config.max_batch_retries
    assert service._translate_single.call_count == len(entries_to_translate)


def test_build_batch_prompt_with_context(mocker, mock_config):
    mocker.patch("translation_hub.core.translation_service.GeminiService._configure_model")
    service = GeminiService(config=mock_config)
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


def test_preserve_whitespace(mocker, mock_config):
    """
    Tests that leading/trailing whitespace is preserved in the translation.
    """
    mocker.patch("translation_hub.core.translation_service.GeminiService._configure_model")
    service = GeminiService(config=mock_config)

    original = "  Hello World  "
    translated = "Olá Mundo"
    preserved = service._preserve_whitespace(original, translated)

    assert preserved == "  Olá Mundo  "
