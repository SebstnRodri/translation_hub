import json
from pathlib import Path

from translation_hub.core.config import TranslationConfig


def test_config_defaults():
	"""
	Tests that the TranslationConfig dataclass initializes with default values.
	"""
	config = TranslationConfig()
	assert config.model_name == "gemini-2.5-flash"
	assert config.max_batch_retries == 3
	assert config.batch_size == 100
	assert config.standardization_guide == ""


def test_config_from_json(tmp_path: Path):
	"""
	Tests loading configuration from a valid JSON file.
	"""
	config_file = tmp_path / "config.json"
	config_data = {
		"model_name": "gemini-2.5-pro",
		"batch_size": 50,
		"max_batch_retries": 5,
	}
	with open(config_file, "w") as f:
		json.dump(config_data, f)

	config = TranslationConfig.from_json(config_file)

	assert config.model_name == "gemini-2.5-pro"
	assert config.batch_size == 50
	assert config.max_batch_retries == 5
	assert config.max_single_retries == 3  # Should remain default


def test_config_from_nonexistent_file():
	"""
	Tests that loading from a non-existent file results in default values.
	"""
	config = TranslationConfig.from_json("non_existent_file.json")
	assert config.model_name == "gemini-2.5-flash"
	assert config.batch_size == 100


def test_config_from_invalid_json(tmp_path: Path):
	"""
	Tests that loading from a malformed JSON file results in default values.
	"""
	config_file = tmp_path / "invalid.json"
	config_file.write_text("{'model_name': 'gemini-2.5-pro',}")  # Invalid JSON

	config = TranslationConfig.from_json(config_file)
	assert config.model_name == "gemini-2.5-flash"
	assert config.batch_size == 100


def test_load_standardization_guide(tmp_path: Path):
	"""
	Tests loading content from a standardization guide file.
	"""
	guide_file = tmp_path / "guide.md"
	guide_content = "Test guide content"
	guide_file.write_text(guide_content)

	config = TranslationConfig()
	config.load_standardization_guide(guide_file)

	assert config.standardization_guide == guide_content


def test_load_nonexistent_guide():
	"""
	Tests that loading a non-existent guide results in an empty string.
	"""
	config = TranslationConfig()
	config.load_standardization_guide("non_existent_guide.md")
	assert config.standardization_guide == ""
