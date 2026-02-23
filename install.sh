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
msg "Found Python $PY_VERSION" "检测到 Python $PY_VERSION"

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

echo ""
msg "Installation complete!" "安装完成！"
msg "Run with:  source $VENV_DIR/bin/activate && bioflow" \
    "运行方式：source $VENV_DIR/bin/activate && bioflow"
echo ""
