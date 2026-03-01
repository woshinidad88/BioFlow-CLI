#!/usr/bin/env bash
# 生成 install.sh 的 SHA256 校验文件
# Generate SHA256 checksum for install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -f "install.sh" ]]; then
    echo "Error: install.sh not found in current directory"
    exit 1
fi

echo "Generating SHA256 checksum for install.sh..."

# 生成校验和文件
if command -v sha256sum &>/dev/null; then
    sha256sum install.sh > install.sh.sha256
    echo "✓ Created install.sh.sha256 (using sha256sum)"
elif command -v shasum &>/dev/null; then
    shasum -a 256 install.sh > install.sh.sha256
    echo "✓ Created install.sh.sha256 (using shasum)"
else
    echo "Error: Neither sha256sum nor shasum found"
    exit 1
fi

echo ""
echo "Checksum file contents:"
cat install.sh.sha256
echo ""
echo "Users can verify with:"
echo "  sha256sum -c install.sh.sha256    # Linux"
echo "  shasum -a 256 -c install.sh.sha256  # macOS"
