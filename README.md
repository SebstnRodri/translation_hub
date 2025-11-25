# Translation Hub 🌍

**AI-Powered Translation Agent for Frappe Apps**

Translation Hub automates the translation of your Frappe and ERPNext applications using advanced AI (Google Gemini). It manages the entire workflow—from extracting strings to generating context-aware translations and saving them securely.

## ✨ Key Features

- **🤖 AI-Powered**: Uses Google Gemini to provide accurate, context-aware translations.
- **💾 Database Storage**: Translations are stored directly in the database (Docker-safe), ensuring they survive updates and restarts.
- **⚡ Real-time Updates**: Translations are applied immediately without requiring server restarts.
- **🛠️ Easy Configuration**: Manage API keys and storage preferences directly from the UI.
- **📊 Progress Monitoring**: Track translation jobs in real-time with detailed logs and status updates.

## 🚀 Getting Started

### 1. Installation (CLI)

Install the app on your Frappe bench via terminal:

```bash
bench get-app https://github.com/SebstnRodri/translation_hub
bench install-app translation_hub
```

**Tip**: Run the setup command to enable common languages (like `pt-BR`, `es-MX`):

```bash
bench setup-languages
```

### 2. Configuration (UI)

1. Open **Translator Settings** in your Frappe Desk.
2. Enter your **Google Gemini API Key**.
3. Ensure **Use Database Storage** is checked (recommended).

### 3. Usage via Desk (UI)

The entire translation process is managed through the Frappe Desk interface:

1. Search for **Translation Job** in the awesome bar.
2. Click **Add Translation Job**.
3. Select the **Source App** (e.g., `frappe`, `erpnext`) and **Target Language** (e.g., `pt-BR`, `es`).
4. Save the document.
5. Click the **Start Job** button in the top right corner.
6. Watch the agent work! The status will update as strings are translated.

## 🧪 Development & Testing

For developers contributing to this project:

- **Mock Service**: Use an API key starting with `test-` to simulate translations without costs.
- **Linting**: Run `pre-commit install` to enable code quality checks.
- **Tests**: Run `bench run-tests --app translation_hub` to execute the test suite.

## License

MIT
