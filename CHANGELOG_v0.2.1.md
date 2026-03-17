## Summary
Feature and maintenance release adding a robust batch processing system for high-throughput sequence formatting with enhanced terminal visualizations.

## Highlights
- Added new `batch` subcommand for non-interactive formatting of multiple FASTA/FASTQ files.
- Implemented recursive directory scanning and glob-based file matching.
- Integrated `rich.progress` for real-time tracking of batch tasks.
- Added structured `rich.table` reports with success, failure, and skipped file statistics.
- Fixed a critical `NameError` in `seq_menu` by resolving a missing `track` component import.
- Synchronized Chinese documentation (`README_CN.md`) and added 13 new i18n translation keys.
- Expanded automated testing with a dedicated batch processing test suite (74 total tests passing).

## Compatibility
- Python 3.9+
- [Conda](https://docs.conda.io/) recommended for bio-tool management
- Fully backward compatible with v0.2.0

## Assets
- `install.sh`
- `install.sh.sha256`
- `BioFlow-CLI-0.2.1.tar.gz`
- `BioFlow-CLI-0.2.1.tar.gz.sha256`

## Open Source
BioFlow-CLI is an open-source project released under the [MIT License](LICENSE).
