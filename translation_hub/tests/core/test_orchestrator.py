from unittest.mock import MagicMock, call

import pytest

from translation_hub.core.config import TranslationConfig
from translation_hub.core.orchestrator import TranslationOrchestrator


@pytest.fixture
def mock_config():
	"""Provides a default TranslationConfig for orchestrator tests."""
	return TranslationConfig(batch_size=2)


@pytest.fixture
def mock_file_handler():
	"""Mocks the TranslationFile handler."""
	return MagicMock()


@pytest.fixture
def mock_service():
	"""Mocks the TranslationService."""
	return MagicMock()


@pytest.fixture
def mock_logger():
	"""Mocks the logger."""
	return MagicMock()


def test_orchestrator_run_with_untranslated_entries(
	mock_config, mock_file_handler, mock_service, mock_logger
):
	"""
	Tests the main `run` workflow when there are entries to translate.
	"""
	# Setup mocks
	untranslated = [
		{"msgid": "Hello", "context": {}},
		{"msgid": "World", "context": {}},
		{"msgid": "Test", "context": {}},
	]
	mock_file_handler.get_untranslated_entries.return_value = untranslated

	# Mock the translation service to return translated dictionaries
	mock_service.translate.side_effect = [
		[
			{"msgid": "Hello", "msgstr": "Olá"},
			{"msgid": "World", "msgstr": "Mundo"},
		],
		[
			{"msgid": "Test", "msgstr": "Teste"},
		],
	]

	# Run orchestrator
	orchestrator = TranslationOrchestrator(mock_config, mock_file_handler, mock_service, mock_logger)
	orchestrator.run()

	# Assertions
	mock_file_handler.merge.assert_called_once()
	mock_file_handler.get_untranslated_entries.assert_called_once()

	# Check that the service was called for each batch
	assert mock_service.translate.call_count == 2
	mock_service.translate.assert_has_calls(
		[
			call([{"msgid": "Hello", "context": {}}, {"msgid": "World", "context": {}}]),
			call([{"msgid": "Test", "context": {}}]),
		]
	)

	# Check that entries were updated and saved for each batch
	assert mock_file_handler.update_entries.call_count == 2
	mock_file_handler.update_entries.assert_has_calls(
		[
			call(
				[
					{"msgid": "Hello", "msgstr": "Olá"},
					{"msgid": "World", "msgstr": "Mundo"},
				]
			),
			call(
				[
					{"msgid": "Test", "msgstr": "Teste"},
				]
			),
		]
	)
	assert mock_file_handler.save.call_count == 2  # 2 for batches
	mock_file_handler.final_verification.assert_called_once()


def test_orchestrator_run_with_no_untranslated_entries(
	mock_config, mock_file_handler, mock_service, mock_logger
):
	"""
	Tests the `run` workflow when there are no entries to translate.
	"""
	# Setup mocks
	mock_file_handler.get_untranslated_entries.return_value = []

	# Run orchestrator
	orchestrator = TranslationOrchestrator(mock_config, mock_file_handler, mock_service, mock_logger)
	orchestrator.run()

	# Assertions
	mock_file_handler.merge.assert_called_once()
	mock_file_handler.get_untranslated_entries.assert_called_once()

	# Service should not be called
	mock_service.translate.assert_not_called()

	# File should be saved once after merge to update metadata
	mock_file_handler.save.assert_called_once()

	# No updates should happen
	mock_file_handler.update_entries.assert_not_called()
	mock_file_handler.final_verification.assert_not_called()  # Not called if nothing to do


def test_split_into_batches():
	"""
	Tests the static method for splitting entries into batches.
	"""
	entries = [1, 2, 3, 4, 5]
	batches = list(TranslationOrchestrator._split_into_batches(entries, 2))

	assert len(batches) == 3
	assert batches[0] == [1, 2]
	assert batches[1] == [3, 4]
	assert batches[2] == [5]

	# Test with empty list
	batches_empty = list(TranslationOrchestrator._split_into_batches([], 2))
	assert len(batches_empty) == 0
