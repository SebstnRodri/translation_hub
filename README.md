# Translation Hub 🌍

**AI-Powered Translation Agent for Frappe Apps**

Translation Hub is a powerful tool designed to automate the translation of Frappe applications using advanced AI (Google Gemini or Groq). It streamlines the localization process, ensuring your apps are ready for a global audience with minimal manual effort.

> [!NOTE]
> **Compatibility**: This project is compatible with **Frappe Framework v15** and **v16**.

## 🚀 Key Features (v1.2.0)
- **🤖 AI-Powered**: Uses Google Gemini or **Groq** to provide accurate, context-aware translations.
- **⚡ Multiple LLM Providers**: Choose between Gemini and Groq (Llama, Mixtral) for translation.
- **🖥️ Enhanced Workspace**: Improved navigation with dedicated Configuration section for easy access to Settings, Jobs, and Apps.
- **🛡️ Git-Based Backup & Restore**: Automatically backup your translation files to a Git repository and restore them when needed.
- **🔄 Sync Before Translate**: Pull existing translations from remote before starting new jobs – ensures no work is lost.
- **📊 Real-time Monitoring**: Track translation progress and monitored apps directly from the dashboard.
- **💾 Database Storage**: Translations are stored directly in the database (Docker-safe), ensuring they survive updates and restarts.
- **⚡ Real-time Updates**: Translations are applied immediately without requiring server restarts.
- **🛠️ Easy Configuration**: Manage API keys and storage preferences directly from the UI.
-   **🧠 Context-Aware Translation**: Define application-specific context (Domain, Tone, Glossary) to guide the AI for superior translation quality.
-   **📏 Standardization Guides**: Define context-aware guides (Global, App-Specific, Language-Specific) to ensure terminology consistency.
-   **🛡️ Governance & Validation**: Prevents duplicate jobs and ensures all translations strictly follow defined configurations.




## 📚 Documentation

### User Guide
- [Getting Started](docs/user_guide/getting_started.md): Initial setup, configuration, and usage.
- [Workspace & Navigation](docs/user_guide/workspace.md): How to use the Translation Hub workspace.
- [Best Practices](docs/user_guide/best_practices.md): Tips for efficient translation management.

### Developer Guide
- [Architecture](docs/developer_guide/architecture.md): System design and component overview.
- [Contributing](docs/developer_guide/contributing.md): Guidelines for contributing to the project.

## License

MIT
