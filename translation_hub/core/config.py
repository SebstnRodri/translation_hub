import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class TranslationConfig:
	"""
	Data class to hold all configuration for the translation process.
	"""

	model_name: str = "gemini-2.5-flash"
	provider: str = "Gemini"
	max_batch_retries: int = 3
	max_single_retries: int = 3
	retry_wait_seconds: int = 2
	standardization_guide: str = ""
	batch_size: int = 15  # Reduced to avoid rate limits on free tier APIs
	pot_file: Path | None = field(default=None, compare=False)
	po_file: Path | None = field(default=None, compare=False)
	api_key: str | None = field(default=None, compare=False)
	logger: Any = field(default=None, compare=False)
	language_code: str = "en"
	localization_profile: str | None = None

	# Database storage options
	use_database_storage: bool = True  # Use Translation DocType (recommended)
	save_to_po_file: bool = False  # Also save to .po file (optional)
	export_po_on_complete: bool = False  # Export DB to .po when done (optional)

	def __post_init__(self):
		if isinstance(self.pot_file, str):
			self.pot_file = Path(self.pot_file)
		if isinstance(self.po_file, str):
			self.po_file = Path(self.po_file)

	@classmethod
	def from_json(cls, config_path: Path | str) -> "TranslationConfig":
		"""
		Loads configuration from a JSON file and returns a TranslationConfig instance.
		"""
		try:
			with open(config_path, encoding="utf-8") as f:
				config_data = json.load(f)
			return cls(**config_data)
		except FileNotFoundError:
			print(f"[Warning] Configuration file not found at {config_path}. Using default values.")
			return cls()
		except json.JSONDecodeError:
			print(f"[Warning] Invalid JSON in configuration file at {config_path}. Using default values.")
			return cls()
		except TypeError as e:
			print(f"[Warning] Mismatch between config file and class attributes: {e}. Using default values.")
			return cls()

	def load_standardization_guide(self, guide_path: Path | str | None):
		"""
		Loads the content of the standardization guide file.
		"""
		if not guide_path:
			self.standardization_guide = ""
			return

		try:
			with open(guide_path, encoding="utf-8") as f:
				self.standardization_guide = f.read()
			if self.logger:
				self.logger.info(f"Loaded standardization guide from: {guide_path}")
			else:
				print(f"Loaded standardization guide from: {guide_path}")
		except FileNotFoundError:
			error_msg = (
				f"Error: Standardization guide file not found at {guide_path}. Proceeding without guide."
			)
			if self.logger:
				self.logger.warning(error_msg)
			else:
				print(error_msg)
			self.standardization_guide = ""
		except Exception as e:
			error_msg = (
				f"Error loading standardization guide from {guide_path}: {e}. Proceeding without guide."
			)
			if self.logger:
				self.logger.error(error_msg)
			else:
				print(error_msg)
			self.standardization_guide = ""
