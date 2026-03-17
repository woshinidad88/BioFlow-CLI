STRINGS = {
    # === Main Menu ===
    "app_title": "BioFlow-CLI  Bioinformatics Workflow Tool",
    "menu_prompt": "Select an action:",
    "menu_env": "[Environment] Install Bio-tools",
    "menu_seq": "[Sequence] Formatting",
    "menu_settings": "[Settings] Change Language",
    "menu_exit": "[Exit] Quit",

    # === Language Selection ===
    "lang_prompt": "Please select your language:",
    "lang_saved": "Language preference saved.",

    # === Environment Manager ===
    "env_title": "Environment Manager",
    "env_select_tool": "Select a tool to install:",
    "env_installing": "Installing {tool}...",
    "env_install_ok": "{tool} installed successfully.",
    "env_install_fail": "Failed to install {tool}: {err}",
    "env_back": "Back to main menu",
    "env_already": "{tool} is already installed.",
    "env_not_found": "{tool} not found. Ready to install.",
    "env_checking": "Checking {tool} status...",

    # === Sequence Tasks ===
    "seq_title": "Sequence Formatting",
    "seq_input_prompt": "Enter the path to your FASTA/FASTQ file:",
    "seq_output_prompt": "Enter the output file path:",
    "seq_processing": "Processing sequences...",
    "seq_done": "Done! {count} sequences formatted and saved to {path}.",
    "seq_file_not_found": "File not found: {path}",
    "seq_invalid_format": "Invalid sequence format. Supported: FASTA/FASTQ.",
    "seq_back": "Back to main menu",
    "seq_wrap_prompt": "Line wrap width (default 80):",
    "seq_fastq_stats": "FASTQ quality summary: Avg Q={avg_q}, Q20={q20}, Q30={q30}, Bases={bases}",

    # === General ===
    "confirm_exit": "Are you sure you want to exit?",
    "yes": "Yes",
    "no": "No",
    "goodbye": "Goodbye!",
    "error_unexpected": "An unexpected error occurred: {err}",
    "press_enter": "Press Enter to continue...",
    "env_conda_missing": "Conda is not installed. Please install Conda first (https://docs.conda.io/).",
    "seq_large_file_warn": "Warning: file is {size} MB, may use significant memory.",

    # === QC Pipeline ===
    "menu_qc": "[QC] Quality Control Pipeline",
    "qc_title": "Quality Control Pipeline",
    "qc_input_prompt": "Enter the path to your FASTQ file:",
    "qc_output_prompt": "Enter the output directory:",
    "qc_adapter_prompt": "Adapter file path (leave empty to skip):",
    "qc_minlen_prompt": "Minimum read length (default 36):",
    "qc_pipeline_start": "Starting QC pipeline for: {file}",
    "qc_pipeline_done": "QC pipeline completed! Results saved to: {output}",
    "qc_step_label": "[Step {step}] {name}",
    "qc_step_failed": "Step failed ({step}): {err}",
    "qc_running_fastqc": "Running FastQC on {file}...",
    "qc_running_trimmomatic": "Running Trimmomatic on {file}...",

    # === Preflight ===
    "preflight_missing_cli": "Error: {tool} not found. Install with: {cmd}",
    "preflight_missing_tui": "{tool} not found. Install with: {cmd}",
    "preflight_unknown_tool": "Error: unknown tool '{tool}'",
    "preflight_hint_env_manager": "Tip: use [Environment] menu to install missing tools, or install manually.",

    # === Batch Processing ===
    "batch_processing": "Batch processing files...",
    "batch_no_files": "No files found matching the pattern.",
    "batch_success_title": "✓ Successfully Processed",
    "batch_failed_title": "✗ Failed",
    "batch_skipped_title": "⊙ Skipped",
    "batch_col_file": "File",
    "batch_col_sequences": "Sequences",
    "batch_col_output": "Output",
    "batch_col_time": "Time",
    "batch_col_error": "Error",
    "batch_col_reason": "Reason",
    "batch_summary": "Total: {total} files | Success: {success} | Failed: {failed} | Skipped: {skipped}",
}
