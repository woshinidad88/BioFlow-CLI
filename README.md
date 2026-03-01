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

### Secure Installation (Recommended)

```bash
# Download the install script and its checksum
curl -LO https://github.com/woshinidad88/BioFlow-CLI/releases/latest/download/install.sh
curl -LO https://github.com/woshinidad88/BioFlow-CLI/releases/latest/download/install.sh.sha256

# Verify integrity before running (platform-specific)
# Linux:
sha256sum -c install.sh.sha256

# macOS:
shasum -a 256 -c install.sh.sha256

# Windows (PowerShell):
# (Get-FileHash install.sh -Algorithm SHA256).Hash -eq (Get-Content install.sh.sha256).Split()[0]

# If verification fails, DO NOT proceed — re-download the files

# Run the installer (Linux/macOS)
bash install.sh
```

### Alternative Installation Methods

```bash
# Clone the repository
git clone https://github.com/woshinidad88/BioFlow-CLI.git
cd BioFlow-CLI

# Option A: Use the install script (without verification)
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

BioFlow-CLI supports both **interactive TUI mode** and **non-interactive CLI mode**.

### TUI Mode (Interactive)

Launch without arguments to enter the interactive menu:

```bash
bioflow
```

On first launch, you'll be prompted to select a language. Your choice is persisted and can be changed anytime via the Settings menu.

### CLI Mode (Non-Interactive)

Use command-line arguments for automation and scripting:

```bash
# Format FASTA sequences
bioflow seq --input input.fasta --output output.fasta --width 80

# List bio-tool installation status
bioflow env --list

# Install a specific tool
bioflow env --install fastqc

# Quiet mode (suppress progress messages)
bioflow --quiet seq --input input.fasta

# JSON output (for parsing)
bioflow --json seq --input input.fasta
```

#### Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Runtime error (e.g., invalid FASTA format, installation failed) |
| `2` | Argument error (e.g., file not found, invalid parameters) |
| `3` | Dependency missing (e.g., Conda not installed) |

#### Output Streams

- **stdout**: Results and data (use for piping)
- **stderr**: Progress messages, warnings, and errors

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
