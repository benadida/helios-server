# Internationalization (i18n) Guide

This directory contains translation files. We use Django's native translation system to support multiple languages.

## Management Commands

### 1. Create or Update Language Files
To extract new strings from the source code or initialize a new language (e.g., Brazilian Portuguese):
```bash
python manage.py makemessages -l pt_BR
```

### 2. Compile Translations
Translations must be compiled into binary .mo files to be recognized by the system:
```bash
python manage.py compilemessages
```

## Translation Requirements

### No Missing Translations
* Ensure every `msgstr` is populated.
* Empty strings will cause the system to fall back to the default language (English).

### Handle `#, fuzzy` and `#` Markers
* **Fuzzy Flags:** Django marks translations as `#, fuzzy` when the source text changes slightly.
* **Warning:** Fuzzy translations are **ignored** by the system and will not appear in the UI.
* **Action:** Review the text, update the translation, and **delete the `#, fuzzy` line** to activate it.

### Variables and Placeholders
* Preserve all placeholders like `%(variable)s`, `{id}`, or `%d` exactly as they appear in the source.
* Ensure HTML tags within strings are maintained to prevent layout breakage.