# Translation Hub 🌍

**AI-Powered Translation Agent for Frappe Apps**

Translation Hub automates the translation of your Frappe and ERPNext applications using advanced AI (Google Gemini). It manages the entire workflow—from extracting strings to generating context-aware translations and saving them securely.

## ✨ Key Features

- **🤖 AI-Powered**: Uses Google Gemini to provide accurate, context-aware translations.
- **💾 Database Storage**: Translations are stored directly in the database (Docker-safe), ensuring they survive updates and restarts.
- **⚡ Real-time Updates**: Translations are applied immediately without requiring server restarts.
- **🛠️ Easy Configuration**: Manage API keys and storage preferences directly from the UI.
- **📊 Progress Monitoring**: Track translation jobs in real-time with detailed logs and status updates.

## 🚀 Quick Start

### 1. Installation

Install the app on your Frappe bench:

```bash
bench get-app https://github.com/yourusername/translation_hub
bench install-app translation_hub
```

### 2. Configuration

1. Open **Translator Settings** in your Frappe Desk.
2. Enter your **Google Gemini API Key**.
3. Ensure **Use Database Storage** is checked (recommended).

### 3. Translate an App

1. Go to **Translation Job** list and click **Add Translation Job**.
2. Select the **Source App** (e.g., `frappe`, `erpnext`) and **Target Language** (e.g., `pt-BR`, `es`).
3. Click **Start Job**.
4. Watch the agent work! The status will update as strings are translated.

## 🧪 Development & Testing

For developers contributing to this project:

- **Mock Service**: Use an API key starting with `test-` to simulate translations without costs.
- **Linting**: Run `pre-commit install` to enable code quality checks.
- **Tests**: Run `bench run-tests --app translation_hub` to execute the test suite.

## License

MIT
