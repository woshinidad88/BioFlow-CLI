#!/usr/bin/env bash
# BioFlow-CLI 安装脚本 / Installation Script
set -euo pipefail

# --- 语言检测 / Language Detection ---
detect_lang() {
    local sys_lang="${LANG:-en_US}"
    if [[ "$sys_lang" == zh_CN* ]] || [[ "$sys_lang" == zh_TW* ]]; then
        echo "zh"
    else
        echo "en"
    fi
}

LANG_CODE="$(detect_lang)"

# --- 双语消息函数 / Bilingual Message Functions ---
msg() {
    if [[ "$LANG_CODE" == "zh" ]]; then
        echo "$2"
    else
        echo "$1"
    fi
}

# --- 主流程 / Main ---
echo ""
msg "=== BioFlow-CLI Installer ===" "=== BioFlow-CLI 安装程序 ==="
echo ""

# 语言选择
msg "Select language / 选择语言:" "Select language / 选择语言:"
msg "  1) English" "  1) English"
msg "  2) 中文" "  2) 中文"
printf "> "
read -r lang_choice
case "$lang_choice" in
    2) LANG_CODE="zh" ;;
    *) LANG_CODE="en" ;;
esac
echo ""

# 检查 Python
msg "Checking Python..." "正在检查 Python..."
if ! command -v python3 &>/dev/null; then
    msg "Error: Python 3 is not installed. Please install Python 3.9+ first." \
        "错误：未找到 Python 3。请先安装 Python 3.9+。"
    exit 1
fi

PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="$(python3 -c 'import sys; print(sys.version_info.major)')"
PY_MINOR="$(python3 -c 'import sys; print(sys.version_info.minor)')"

msg "Found Python $PY_VERSION" "检测到 Python $PY_VERSION"

# Python 版本检查（需要 3.9+）
if [[ "$PY_MAJOR" -lt 3 ]] || { [[ "$PY_MAJOR" -eq 3 ]] && [[ "$PY_MINOR" -lt 9 ]]; }; then
    echo ""
    msg "Error: Python 3.9+ is required (found $PY_VERSION)" \
        "错误：需要 Python 3.9+（当前版本 $PY_VERSION）"
    echo ""

    # 平台特定的安装引导
    case "$(uname -s)" in
        Darwin)
            msg "Install Python on macOS:" "在 macOS 上安装 Python："
            msg "  • Homebrew: brew install python@3.11" \
                "  • Homebrew：brew install python@3.11"
            msg "  • Official: https://www.python.org/downloads/macos/" \
                "  • 官方网站：https://www.python.org/downloads/macos/"
            ;;
        Linux)
            msg "Install Python on Linux:" "在 Linux 上安装 Python："
            msg "  • Ubuntu/Debian: sudo apt install python3.11" \
                "  • Ubuntu/Debian：sudo apt install python3.11"
            msg "  • Fedora/RHEL: sudo dnf install python3.11" \
                "  • Fedora/RHEL：sudo dnf install python3.11"
            msg "  • Arch: sudo pacman -S python" \
                "  • Arch：sudo pacman -S python"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            msg "Install Python on Windows:" "在 Windows 上安装 Python："
            msg "  • Official: https://www.python.org/downloads/windows/" \
                "  • 官方网站：https://www.python.org/downloads/windows/"
            msg "  • Winget: winget install Python.Python.3.11" \
                "  • Winget：winget install Python.Python.3.11"
            ;;
    esac
    echo ""
    exit 1
fi

# 创建虚拟环境
VENV_DIR=".venv"
if [[ -d "$VENV_DIR" ]]; then
    msg "Virtual environment already exists. Skipping creation." \
        "虚拟环境已存在，跳过创建。"
else
    msg "Creating virtual environment..." "正在创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi

# 激活虚拟环境
msg "Activating virtual environment..." "正在激活虚拟环境..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# 安装依赖
msg "Installing dependencies..." "正在安装依赖..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 安装项目（可编辑模式）
msg "Installing BioFlow-CLI..." "正在安装 BioFlow-CLI..."
pip install -e . -q

# 创建符号链接到 ~/.local/bin
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

BIOFLOW_EXEC="$(which bioflow 2>/dev/null || echo "$VENV_DIR/bin/bioflow")"
LINK_PATH="$LOCAL_BIN/bioflow"

if [[ -L "$LINK_PATH" ]] || [[ -f "$LINK_PATH" ]]; then
    msg "Updating existing bioflow link in $LOCAL_BIN..." \
        "正在更新 $LOCAL_BIN 中的 bioflow 链接..."
    rm -f "$LINK_PATH"
fi

ln -s "$BIOFLOW_EXEC" "$LINK_PATH"
msg "Created symlink: $LINK_PATH -> $BIOFLOW_EXEC" \
    "已创建符号链接：$LINK_PATH -> $BIOFLOW_EXEC"

# 检查 PATH 配置
echo ""
if echo "$PATH" | grep -q "$LOCAL_BIN"; then
    msg "✓ $LOCAL_BIN is already in your PATH" \
        "✓ $LOCAL_BIN 已在您的 PATH 中"
else
    msg "⚠ $LOCAL_BIN is NOT in your PATH" \
        "⚠ $LOCAL_BIN 不在您的 PATH 中"
    echo ""
    msg "Add it to your shell profile:" "将其添加到您的 shell 配置文件："

    # 检测 shell 类型
    SHELL_NAME="$(basename "$SHELL")"
    case "$SHELL_NAME" in
        bash)
            PROFILE_FILE="$HOME/.bashrc"
            ;;
        zsh)
            PROFILE_FILE="$HOME/.zshrc"
            ;;
        fish)
            PROFILE_FILE="$HOME/.config/fish/config.fish"
            ;;
        *)
            PROFILE_FILE="$HOME/.profile"
            ;;
    esac

    if [[ "$SHELL_NAME" == "fish" ]]; then
        echo "  fish_add_path $LOCAL_BIN"
        msg "  # Add to $PROFILE_FILE" "  # 添加到 $PROFILE_FILE"
    else
        echo "  export PATH=\"$LOCAL_BIN:\$PATH\""
        msg "  # Add to $PROFILE_FILE" "  # 添加到 $PROFILE_FILE"
    fi
    echo ""
fi

echo ""
msg "Installation complete!" "安装完成！"
msg "Run with:  bioflow  (after adding to PATH)" \
    "运行方式：bioflow（添加到 PATH 后）"
msg "Or:        source $VENV_DIR/bin/activate && bioflow" \
    "或者：    source $VENV_DIR/bin/activate && bioflow"
echo ""
