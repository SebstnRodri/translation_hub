import argparse
import logging
from pathlib import Path

from translation_hub.core.config import TranslationConfig
from translation_hub.core.orchestrator import TranslationOrchestrator
from translation_hub.core.translation_file import TranslationFile
from translation_hub.core.translation_service import GeminiService
from translation_hub.utils.logger import get_logger


def main():
    """
    Main function to run the translation process from the command line.
    Acts as the CLI Handler layer.
    """
    parser = argparse.ArgumentParser(description="Translate a .pot file to Brazilian Portuguese using Gemini.")
    parser.add_argument("pot_file", type=str, help="Path to the .pot file to translate.")
    parser.add_argument("-o", "--output", type=str, help="Path to save the translated .po file.")
    parser.add_argument("-b", "--batch-size", type=int, help="Batch size for translation.")
    parser.add_argument(
        "-g",
        "--guide",
        type=str,
        help="Path to a text file containing standardization rules or glossary for translation.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="translation_hub_config.json",
        help="Path to a JSON configuration file.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level.",
    )
    args = parser.parse_args()

    # --- Logger Initialization ---
    log_level = getattr(logging, args.log_level.upper())
    logger = get_logger("translation_hub", level=log_level)

    # --- Configuration Loading ---
    logger.info("Loading configuration from %s", args.config)
    config = TranslationConfig.from_json(args.config)

    # Command-line arguments override config file settings
    pot_path = Path(args.pot_file)
    po_path = Path(args.output) if args.output else pot_path.with_suffix(".po")
    config.pot_file = pot_path
    config.po_file = po_path
    if args.batch_size:
        config.batch_size = args.batch_size
    if args.guide:
        config.load_standardization_guide(args.guide)

    # --- Dependency Injection ---
    file_handler = TranslationFile(po_path=config.po_file, pot_path=config.pot_file, logger=logger)
    translation_service = GeminiService(config=config, logger=logger)
    orchestrator = TranslationOrchestrator(
        config=config,
        file_handler=file_handler,
        service=translation_service,
        logger=logger,
    )

    # --- Run the Process ---
    orchestrator.run()


if __name__ == "__main__":
    main()
