from unittest.mock import ANY, MagicMock, patch

import pytest

from translation_hub.translation_hub.main import main


@pytest.fixture
def mock_args(tmp_path):
	"""
	Provides default mocked arguments for the CLI.
	"""
	return [
		"translation_hub/main.py",
		str(tmp_path / "main.pot"),
		"-o",
		str(tmp_path / "pt_BR.po"),
		"-b",
		"50",
		"-g",
		str(tmp_path / "guide.md"),
	]


@patch("translation_hub.main.TranslationConfig")
@patch("translation_hub.main.TranslationFile")
@patch("translation_hub.main.GeminiService")
@patch("translation_hub.main.TranslationOrchestrator")
def test_main_cli_handler(
	mock_orchestrator_cls,
	mock_service_cls,
	mock_file_cls,
	mock_config_cls,
	mock_args,
):
	"""
	Tests that the main function (CLI Handler) correctly parses arguments
	and initializes and runs the orchestrator.
	"""
	# Mock instances
	mock_config_instance = MagicMock()
	mock_orchestrator_instance = MagicMock()

	# Setup mock returns
	mock_config_cls.from_json.return_value = mock_config_instance
	mock_orchestrator_cls.return_value = mock_orchestrator_instance

	# Patch sys.argv and run main
	with patch("sys.argv", mock_args):
		main()

	# --- Assertions ---

	# 1. Config loading
	mock_config_cls.from_json.assert_called_with("translation_hub_config.json")

	# 2. Config updates from args
	assert mock_config_instance.batch_size == 50
	mock_config_instance.load_standardization_guide.assert_called_with(mock_args[7])

	# 3. Component instantiation
	mock_file_cls.assert_called_once_with(
		po_path=mock_config_instance.po_file,
		pot_path=mock_config_instance.pot_file,
		logger=ANY,
	)
	mock_service_cls.assert_called_once_with(config=mock_config_instance, logger=ANY)
	mock_orchestrator_cls.assert_called_once_with(
		config=mock_config_instance,
		file_handler=mock_file_cls.return_value,
		service=mock_service_cls.return_value,
		logger=ANY,
	)

	# 4. Orchestrator execution
	mock_orchestrator_instance.run.assert_called_once()


@patch("translation_hub.main.TranslationOrchestrator")
def test_main_keyboard_interrupt(mock_orchestrator_cls, mock_args):
	"""
	Tests that the main function handles KeyboardInterrupt gracefully.
	(The orchestrator is responsible for the actual handling, this test
	just ensures the exception propagates to it).
	"""
	mock_orchestrator_instance = MagicMock()
	mock_orchestrator_instance.run.side_effect = KeyboardInterrupt
	mock_orchestrator_cls.return_value = mock_orchestrator_instance

	with patch("sys.argv", mock_args):
		# The test will pass if KeyboardInterrupt is raised and not caught by main
		with pytest.raises(SystemExit) as e:
			# The orchestrator calls sys.exit(130)
			main()
		assert e.value.code == 130
