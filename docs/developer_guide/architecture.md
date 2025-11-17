# Architecture Guide

This document describes the overall architecture and design principles of the `translation_hub` application.

## Design Principles

The system is designed following a **Layered Architecture** pattern. This separates concerns into distinct, independent components, making the codebase more modular, testable, and extensible.

The four main layers are:

1.  **Presentation Layer (CLI)**: Handles user interaction.
2.  **Orchestration Layer**: Coordinates the components to execute the translation workflow.
3.  **Service Layer**: Manages external services, primarily the translation API.
4.  **Data Access Layer**: Handles all interactions with the filesystem.

## Core Components (Classes)

```mermaid
classDiagram
    class CLIHandler {
        +run_application(args)
    }

    class Orchestrator {
        -Config config
        -FileHandler file_handler
        -Service service
        +__init__(config, file_handler, service)
        +run()
        -split_into_batches(entries: List<dict>, batch_size: int)
    }

    class FileHandler {
        -Path po_path
        -Optional<Path> pot_path
        -polib.POFile pofile
        +__init__(po_path, pot_path)
        -load_or_create_pofile()
        +merge()
        +get_untranslated_entries() List<dict>
        +update_entries(translated_entries: List<dict>)
        +save()
        +final_verification()
    }

    class Service {
        <<interface>>
        +translate(entries: List<dict>) List<dict>
    }

    class GeminiService {
        -Config config
        -genai.GenerativeModel model
        +__init__(config)
        -configure_model()
        +translate(entries: List<dict>) List<dict>
        -translate_single(entry: dict) dict
        -build_batch_prompt(entries: List<dict>) str
        -build_single_prompt(entry: dict) str
        -clean_json_response(text: str) str
        -preserve_whitespace(original: str, translated: str) str
    }

    class Config {
        +str model_name
        +int max_batch_retries
        +int max_single_retries
        +int retry_wait_seconds
        +str standardization_guide
        +int batch_size
        +Optional<Path> pot_file
        +Optional<Path> po_file
        +from_json(config_path) Config
        +load_standardization_guide(guide_path)
    }

    CLIHandler --> Orchestrator : instantiates
    CLIHandler --> FileHandler : instantiates
    CLIHandler --> GeminiService : instantiates
    CLIHandler --> Config : uses

    Orchestrator "1" *-- "1" Config : config
    Orchestrator "1" *-- "1" FileHandler : file_handler
    Orchestrator "1" *-- "1" Service : service

    GeminiService --|> Service : implements
    GeminiService "1" *-- "1" Config : config
```

- **`CLIHandler` (`main.py`)**: The application's entry point. Its sole responsibility is to parse command-line arguments, instantiate the necessary components, and trigger the orchestration layer.

- **`Orchestrator`**: The "brain" of the application. It coordinates the entire translation process, including:
  - Requesting untranslated entries from the `FileHandler`.
  - Splitting entries into batches.
  - Sending batches to the `Service`.
  - Updating the `FileHandler` with the results.
  - Saving progress.

- **`Service` (Abstract Base Class)**: Defines a common interface for any translation service. This allows for future extensibility (e.g., adding DeepL or Azure Translator).

- **`GeminiService`**: The concrete implementation of `Service` for the Google Gemini API. It handles:
  - API authentication and model configuration.
  - Building a detailed prompt that includes not just the text to translate but also its **context** (source file occurrences, developer comments, etc.).
  - Executing the API call, including retry and fallback logic.
  - Parsing the JSON response.

- **`FileHandler`**: Encapsulates all logic related to file manipulation using the `polib` library. Its responsibilities include:
  - Loading and creating `.po` files.
  - Merging `.pot` templates.
  - Extracting untranslated/fuzzy entries as dictionaries containing the `msgid` and its `context`.
  - Saving changes to disk.

- **`Config`**: A data class that holds all configuration parameters, such as API keys, batch sizes, and file paths.

## Execution Flow

```mermaid
sequenceDiagram
    participant CLI as CLIHandler
    participant Orch as Orchestrator
    participant File as FileHandler
    participant Service as GeminiService

    CLI->>File: create(pot_path, po_path)
    CLI->>Service: create(config)
    CLI->>Orch: create(File, Service, config)
    CLI->>Orch: run()

    Orch->>File: merge()
    Orch->>File: get_untranslated_entries()
    File-->>Orch: untranslated_entries

    alt All entries are already translated
        Orch->>File: save()
        Note over Orch: No entries to translate.
    else Untranslated entries exist
        loop for each batch in untranslated_entries
            Orch->>Service: translate(batch_entries)
            Service-->>Orch: translated_entries
            Orch->>File: update_entries(translated_entries)
            Orch->>File: save()
        end
        Orch->>File: final_verification()
    end
```
