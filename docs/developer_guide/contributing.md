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
    uv pip install -e ".[dev]"
    ```

3.  **Set Up Pre-Commit Hooks**: The project uses pre-commit hooks to enforce code quality.

    ```bash
    pre-commit install
    ```

4.  **Configure API Key**: Create a `.env` file in the root directory and add your API key.

    ```
    GOOGLE_API_KEY="YOUR_API_KEY"
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
