# BioFlow-CLI

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-green.svg)](https://python.org)

**[中文文档](README_CN.md)**

A professional bioinformatics TUI (Terminal User Interface) workflow tool with full i18n (English/Chinese) support.

## Features

- **Interactive TUI** — Built with `questionary` + `rich` for a polished terminal experience
- **i18n Support** — Full English and Chinese localization; language selected on first run and persisted to the user config directory
- **Environment Manager** — One-click detection and installation of common bio-tools (FastQC, SAMtools, BWA, BLAST+, Trimmomatic) via Conda
- **Sequence Formatting** — Standardize FASTA files with configurable line-wrap width
- **Modular Design** — Clean separation of concerns across `env_manager`, `bio_tasks`, and `i18n` modules

## Quick Start

```bash
# Clone the repository
git clone https://github.com/woshinidad88/BioFlow-CLI.git
cd BioFlow-CLI

# Option A: Use the install script
chmod +x install.sh && ./install.sh

# Option B: Manual setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m bioflow.main
```

## Project Structure

```
BioFlow-CLI/
├── bioflow/
│   ├── __init__.py        # Package metadata
│   ├── main.py            # TUI entry point & main menu
│   ├── i18n.py            # Internationalization core
│   ├── env_manager.py     # Bio-tool detection & installation
│   ├── bio_tasks.py       # Sequence formatting tasks
│   └── locales/
│       ├── __init__.py    # Locale registry
│       ├── en.py          # English strings
│       └── zh.py          # Chinese strings
├── install.sh             # Bilingual install script
├── pyproject.toml         # Build configuration
├── requirements.txt       # Dependencies
├── LICENSE                # MIT License
├── README.md              # English documentation
└── README_CN.md           # Chinese documentation
```

## Usage

On first launch, BioFlow-CLI will prompt you to select a language. Your choice is persisted and can be changed anytime via the Settings menu.

### Config Location

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/bioflow/config.json` |
| Linux | `~/.config/bioflow/config.json` (or `$XDG_CONFIG_HOME/bioflow/`) |
| Windows | `%APPDATA%\bioflow\config.json` |

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `BIOFLOW_LARGE_FILE_MB` | Large FASTA file warning threshold (MB) | `500` |

### Main Menu

| Action | Description |
|---|---|
| **[Environment] Install Bio-tools** | Detect and install bioinformatics tools via Conda |
| **[Sequence] Formatting** | Standardize FASTA file formatting |
| **[Settings] Change Language** | Switch between English and Chinese |
| **[Exit] Quit** | Exit the application |

## Requirements

- Python 3.9+
- [Conda](https://docs.conda.io/) (for bio-tool installation)

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
