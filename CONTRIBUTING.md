# Contributing to BioFlow-CLI

Thank you for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/woshinidad88/BioFlow-CLI.git
cd BioFlow-CLI
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/ -v
```

## How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests to ensure nothing is broken
5. Commit with a clear message (`git commit -m "Add: your feature description"`)
6. Push to your fork and open a Pull Request

## Code Style

- Follow PEP 8
- Add type hints to all function signatures
- Keep i18n in mind — all user-facing strings go in `bioflow/locales/en.py` and `zh.py`
- Write tests for new functionality

## Reporting Issues

Open an issue on GitHub with:
- A clear title and description
- Steps to reproduce (if applicable)
- Expected vs actual behavior
- Your Python version and OS

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
