# Contributing to Translation Hub

First off, thank you for considering contributing! It's people like you that make open source such a great community.

This document provides guidelines for contributing to the project.

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

- **Reporting Bugs**: If you find a bug, please open an issue and provide as much detail as possible.
- **Suggesting Enhancements**: If you have an idea for a new feature or an improvement, open an issue to discuss it.
- **Pull Requests**: If you've fixed a bug or implemented a new feature, we'd love to see your pull request.

## Setting Up Your Development Environment

1.  **Fork & Clone**: Fork the repository on GitHub and clone your fork locally.

    ```bash
    git clone https://github.com/your-username/translation-hub.git
    cd translation-hub
    ```

2.  **Install Dependencies**: This project uses `uv` for package management. Install the project in editable mode with all development dependencies.

    ```bash
    # Ensure your virtual environment is activated (e.g., source ../../env/bin/activate)
    uv pip install -e ".[dev]"
    ```

3.  **Set Up Pre-Commit Hooks**: The project uses pre-commit hooks to enforce code quality.

    ```bash
    pre-commit install
    ```

4.  **Configure API Key**: Create a `.env` file in the root directory and add your API key.

    **Note**: For development, you can use the **Mock Service** to simulate translations without incurring costs.

    - **Production**: Add your real key: `GOOGLE_API_KEY="YOUR_API_KEY"`
    - **Development/Testing**: Use a dummy key starting with `test-`: `GOOGLE_API_KEY="test-key"`

> [!IMPORTANT]
> **Compatibility Note**: This project is developed and tested on **Frappe Framework v16.0.0-dev (version-16-beta)**. Please ensure your environment matches this version.

## Development Guidelines

### Path Handling
Always use `pathlib.Path` for file system operations instead of string manipulation. This ensures cross-platform compatibility and robustness.

```python
from pathlib import Path
# Good
po_path = Path(app_path) / "locale" / "pt_BR.po"
# Bad
po_path = app_path + "/locale/pt_BR.po"
```

### HTML Preservation
When handling translations, **never strip HTML tags**. The `Translation` DocType in Frappe automatically sanitizes HTML, so we must rely on direct file manipulation (`save_to_po_file=True`) to preserve rich text.

### Security
**Never log full API keys**. Always mask sensitive data before logging.
```python
# Good
masked_key = f"{api_key[:4]}..." if api_key else "None"
logger.info(f"Using key: {masked_key}")
```

## Running Tests

To ensure that your changes haven't broken anything, run the full test suite:

```bash
pytest
```

## Code Style & Linting

This project uses `ruff` for linting and `ruff-format` for formatting. The pre-commit hooks will run these automatically, but you can also run them manually:

```bash
# Check for linting errors
ruff check .

# Format the code
ruff format .
```

## Submitting a Pull Request

1.  Create a new branch for your changes.
    ```bash
    git checkout -b feature/your-awesome-feature
    ```
2.  Make your changes and commit them with a clear, descriptive message.
3.  Push your branch to your fork on GitHub.
4.  Open a pull request from your fork to the `main` branch of the original repository.
5.  Ensure all automated checks (like tests) are passing.
6.  A maintainer will review your PR, provide feedback, and merge it if everything looks good.

Thank you for your contribution!
