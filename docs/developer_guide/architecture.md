# Architecture Guide

This document describes the overall architecture and design principles of the `translation_hub` application.

## Design Principles

The system is designed following a **Layered Architecture** pattern. This separates concerns into distinct, independent components, making the codebase more modular, testable, and extensible.

The four main layers are:

1.  **Presentation Layer (Frappe UI)**: Handles user interaction through Frappe DocTypes and a custom Desk Page.
2.  **Application Layer (Frappe Backend)**: Manages the business logic, including DocType controllers, background jobs, and the scheduler.
3.  **Core Logic Layer**: Contains the domain-specific logic for the translation process. This layer is independent of the Frappe framework.
4.  **Service & Data Access Layer**: Manages external services (translation API) and filesystem interactions (`.po` files).

## Core Components

### Frappe Components

- **`Translator Settings` (Singleton DocType)**: Stores global configuration like API keys and automation settings. Replaces the old `config.json` file.
- **`Translation Job` (Standard DocType)**: Represents a single translation task, tracking its status, progress, and logs.
- **`Translation Workspace` (Desk Page)**: A UI dashboard for creating, managing, and monitoring `Translation Jobs`.
- **Background Job (`tasks.py`)**: A function that is enqueued by Frappe's scheduler or manually from the UI. It's responsible for running the core translation logic.

### Core Logic Components (Classes)

```mermaid
classDiagram
    direction LR
    class FrappeUI {
        +TranslationJob
        +TranslatorSettings
    }

    class BackgroundJob {
        +execute_translation_job(job_name)
    }

    class Orchestrator {
        -Config config
        -FileHandler file_handler
        -Service service
        -Logger logger
        +run()
    }

    class Config {
        +str api_key
        +str model_name
        +int batch_size
        +int max_batch_retries
        +int max_single_retries
        +int retry_wait_seconds
        +str standardization_guide
        +Path pot_file
        +Path po_file
        +Logger logger
        +from_json(config_path)
        +load_standardization_guide(guide_path)
    }

    class FileHandler {
        -Path po_path
        -Logger logger
        +get_untranslated_entries()
        +update_entries()
        +save()
    }

    class Service {
        +translate(entries)*
    }

    class GeminiService {
        -Config config
        -Logger logger
        +translate(entries)
    }

    FrappeUI ..> BackgroundJob : enqueues
    BackgroundJob ..> Orchestrator : instantiates and runs
    BackgroundJob ..> Config : instantiates
    BackgroundJob ..> FileHandler : instantiates
    BackgroundJob ..> GeminiService : instantiates

    Orchestrator o-- Config
    Orchestrator o-- FileHandler
    Orchestrator o-- Service

    GeminiService --|> Service
```

- **`Orchestrator`**: The "brain" of the application. It coordinates the entire translation process. It is instantiated and run by the background job.
- **`Service` (Abstract Base Class)**: Defines a common interface for any translation service.
- **`GeminiService`**: The concrete implementation of `Service` for the Google Gemini API.
- **`FileHandler`**: Encapsulates all logic related to file manipulation using the `polib` library.
- **`Config`**: A data class that holds all configuration parameters, populated from the `Translator Settings` DocType.
- **`DocTypeLogger`**: A custom logger that writes output to the `log` field of a `Translation Job` document.

## Execution Flow

The process can be triggered manually by a user or automatically by the Frappe scheduler.

```mermaid
sequenceDiagram
    participant User
    participant Workspace as Translation Workspace
    participant JobDoc as Translation Job DocType
    participant BGJob as Background Job (tasks.py)
    participant Orch as Orchestrator

    alt Manual Trigger
        User->>Workspace: Clicks "Start Job"
        Workspace->>JobDoc: Calls `enqueue_job()`
    else Automated Trigger
        participant Scheduler
        Scheduler->>BGJob: Triggers `run_automated_translations()`
        BGJob->>JobDoc: Creates new Job & calls `enqueue_job()`
    end

    JobDoc->>BGJob: `frappe.enqueue(execute_translation_job)`
    
    BGJob->>JobDoc: Update status to 'In Progress'
    BGJob->>Orch: create(config, file_handler, service, logger)
    BGJob->>Orch: run()

    loop For each batch
        Orch->>BGJob: (via logger) Update progress
        BGJob->>JobDoc: Save progress
    end

    BGJob->>JobDoc: Update status to 'Completed'
```
