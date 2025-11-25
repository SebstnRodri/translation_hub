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

#### DocTypes

- **`Translator Settings` (Singleton DocType)**: Stores global configuration like API keys, automation settings, and monitored apps.
  - Contains child table `Monitored App` for automated translation configuration
  - Fields: `api_key`, `standardization_guide`, `enable_automated_translation`, `frequency`, `monitored_apps`

- **`Translation Job` (Standard DocType)**: Represents a single translation task, tracking its status, progress, timing, and logs.
  - Links to `App` (source application) and `Language` (target language)
  - Tracks progress metrics: `total_strings`, `translated_strings`, `progress_percentage`
  - Records timing: `start_time`, `end_time`
  - Maintains execution log for debugging and monitoring
  - Status values: Pending, Queued, In Progress, Completed, Failed, Cancelled

- **`App` (Standard DocType)**: Represents a Frappe/ERPNext application available for translation.
  - Stores `app_name` (unique identifier) and `app_title` (display name)
  - Referenced by `Translation Job` and `Monitored App`
  - Used to track which applications are being translated

- **`Monitored App` (Child Table)**: Defines app/language combinations to monitor for automated translation.
  - Part of `Translator Settings.monitored_apps`
  - Links to `App` (source application) and `Language` (target language)
  - Used by scheduler to automatically create translation jobs when untranslated strings are detected

#### Workspace & UI Components

- **`Translation Hub` (Workspace)**: A dashboard for creating, managing, and monitoring Translation Jobs.
  - Displays **Dashboard Chart**: "Translations Over Time" - visualizes translation progress over time
  - Displays **Number Cards** for key metrics:
    - **Total Apps Tracked**: Count of apps configured for translation
    - **Jobs in Progress**: Active translation jobs currently running
    - **Jobs Completed (30 Days)**: Successfully completed jobs in the last 30 days
    - **Strings Translated**: Total number of strings translated across all jobs

#### Background Jobs

- **Background Job (`tasks.py`)**: Functions enqueued by Frappe's scheduler or manually from the UI.
  - **`execute_translation_job(job_name)`**: Runs the translation process for a specific job
    - Updates job status (Queued → In Progress → Completed/Failed)
    - Instantiates and runs the `TranslationOrchestrator` with core logic components
    - Logs progress and errors to the job document
  - **`run_automated_translations()`**: Checks monitored apps and creates jobs automatically
    - Triggered by Frappe scheduler based on configured frequency
    - Scans for untranslated strings in monitored app/language combinations
    - Creates and enqueues new Translation Jobs when work is detected

### Core Logic Components (Classes)

```mermaid
classDiagram
    direction LR
    class FrappeUI {
        +TranslationJob
        +TranslatorSettings
        +App
        +MonitoredApp
        +TranslationHub
        +DashboardChart
        +NumberCards
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

### DocType Relationships

The following diagram shows how the Frappe DocTypes relate to each other:

```mermaid
erDiagram
    TRANSLATOR_SETTINGS ||--o{ MONITORED_APP : "contains"
    MONITORED_APP }o--|| APP : "references"
    MONITORED_APP }o--|| LANGUAGE : "references"
    TRANSLATION_JOB }o--|| APP : "source_app"
    TRANSLATION_JOB }o--|| LANGUAGE : "target_language"
    
    TRANSLATOR_SETTINGS {
        string api_key
        text standardization_guide
        bool enable_automated_translation
        string frequency
    }
    
    MONITORED_APP {
        link source_app
        link target_language
    }
    
    APP {
        string app_name
        string app_title
    }
    
    TRANSLATION_JOB {
        string title
        string status
        link source_app
        link target_language
        int total_strings
        int translated_strings
        float progress_percentage
        datetime start_time
        datetime end_time
        text log
    }
```

### Component Descriptions

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
