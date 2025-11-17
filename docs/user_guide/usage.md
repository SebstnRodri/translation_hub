# How to Use the Translator

The Translation Hub is a command-line tool designed to be powerful yet straightforward to use. This guide covers all the available commands and options.

## Basic Command

The main command structure is:

```bash
python translation_hub/main.py [POT_FILE] [OPTIONS]
```

-   `[POT_FILE]`: This is the only **required** argument. It's the path to the `.pot` template file you want to translate.

## Options (Arguments)

You can modify the tool's behavior using the following optional arguments:

-   `-o, --output [FILE_PATH]`
    -   Specifies the path to save the translated `.po` file.
    -   If you omit this, the tool will create a `.po` file with the same name and in the same directory as your `.pot` file.
    -   **Example**: `-o locale/pt_BR.po`

-   `-b, --batch-size [NUMBER]`
    -   Sets the number of strings to send to the translation API in a single batch.
    -   A smaller batch size can be slower but may be more reliable on unstable connections. A larger size is faster.
    -   The default is `100`.
    -   **Example**: `-b 50`

-   `-g, --guide [FILE_PATH]`
    -   Specifies the path to a standardization guide. This is a plain text or Markdown file containing a glossary, specific rules, and terminology for the AI to follow.
    -   Using a guide is **highly recommended** for achieving high-quality, consistent translations.
    -   **Example**: `-g standardization_guide.md`

-   `-c, --config [FILE_PATH]`
    -   Specifies the path to a JSON configuration file.
    -   This allows you to manage settings like `batch_size` and `model_name` in a file instead of typing them every time.
    -   The default is `translation_hub_config.json`.
    -   **Note**: Any arguments you provide on the command line will override the settings in the configuration file.

## Practical Examples

### Simple Translation

Translate `main.pot` and save it as `main.po` in the same directory.

```bash
python translation_hub/main.py main.pot
```

### Translation with a Guide and Custom Output

Translate `frappe.pot`, use a guide for consistency, and save the result in a specific `locale` folder.

```bash
python translation_hub/main.py frappe.pot -o locale/pt_BR.po -g glossary.md
```

### Translation with a Smaller Batch Size

Translate a very large file, using a smaller batch size to improve reliability.

```bash
python translation_hub/main.py erpnext.pot -b 25
```
