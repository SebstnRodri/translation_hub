import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TranslationConfig:
    """
    Data class to hold all configuration for the translation process.
    """

    model_name: str = "gemini-2.5-flash"
    max_batch_retries: int = 3
    max_single_retries: int = 3
    retry_wait_seconds: int = 2
    standardization_guide: str = ""
    batch_size: int = 100
    pot_file: Optional[Path] = None
    po_file: Optional[Path] = None

    @classmethod
    def from_json(cls, config_path: Path | str) -> "TranslationConfig":
        """
        Loads configuration from a JSON file and returns a TranslationConfig instance.
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
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

    def load_standardization_guide(self, guide_path: Optional[Path | str]):
        """
        Loads the content of the standardization guide file.
        """
        if not guide_path:
            self.standardization_guide = ""
            return

        try:
            with open(guide_path, "r", encoding="utf-8") as f:
                self.standardization_guide = f.read()
            print(f"Loaded standardization guide from: {guide_path}")
        except FileNotFoundError:
            print(f"Error: Standardization guide file not found at {guide_path}. Proceeding without guide.")
            self.standardization_guide = ""
        except Exception as e:
            print(f"Error loading standardization guide from {guide_path}: {e}. Proceeding without guide.")
            self.standardization_guide = ""
