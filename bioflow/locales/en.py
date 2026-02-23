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
    "seq_input_prompt": "Enter the path to your FASTA file:",
    "seq_output_prompt": "Enter the output file path:",
    "seq_processing": "Processing sequences...",
    "seq_done": "Done! {count} sequences formatted and saved to {path}.",
    "seq_file_not_found": "File not found: {path}",
    "seq_invalid_format": "Invalid FASTA format.",
    "seq_back": "Back to main menu",
    "seq_wrap_prompt": "Line wrap width (default 80):",

    # === General ===
    "confirm_exit": "Are you sure you want to exit?",
    "yes": "Yes",
    "no": "No",
    "goodbye": "Goodbye!",
    "error_unexpected": "An unexpected error occurred: {err}",
    "press_enter": "Press Enter to continue...",
    "env_conda_missing": "Conda is not installed. Please install Conda first (https://docs.conda.io/).",
    "seq_large_file_warn": "Warning: file is {size} MB, may use significant memory.",
}
