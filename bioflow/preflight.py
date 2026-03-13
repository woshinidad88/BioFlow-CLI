"""BioFlow-CLI 工具预检模块 — 统一的外部工具依赖检查策略。"""

from __future__ import annotations

import shutil
import sys
from typing import Sequence

from bioflow.i18n import t


# 工具名称 → (可执行文件名, conda 安装命令)
TOOL_REGISTRY: dict[str, tuple[str, str]] = {
    "fastqc": ("fastqc", "conda install -y -c bioconda fastqc"),
    "trimmomatic": ("trimmomatic", "conda install -y -c bioconda trimmomatic"),
    "samtools": ("samtools", "conda install -y -c bioconda samtools"),
    "bwa": ("bwa", "conda install -y -c bioconda bwa"),
    "blastn": ("blastn", "conda install -y -c bioconda blast"),
}


class PreflightError(Exception):
    """工具预检失败时抛出的异常。"""

    def __init__(self, missing_tools: list[str]) -> None:
        self.missing_tools = missing_tools
        names = ", ".join(missing_tools)
        super().__init__(f"Missing tools: {names}")


def check_tool(name: str) -> bool:
    """检查单个工具是否可用。"""
    entry = TOOL_REGISTRY.get(name)
    if entry is None:
        return False
    executable, _cmd = entry
    return shutil.which(executable) is not None


def preflight_check(
    tools: Sequence[str],
    *,
    cli_mode: bool = False,
) -> bool:
    """检查一组工具是否全部可用。

    Args:
        tools: 需要检查的工具名称列表。
        cli_mode: 是否为 CLI 模式。CLI 模式下输出到 stderr 并抛出异常；
                  TUI 模式下使用 rich 打印友好提示。

    Returns:
        True 表示全部工具可用。

    Raises:
        PreflightError: CLI 模式下有缺失工具时抛出。
    """
    missing: list[str] = []

    for tool_name in tools:
        if not check_tool(tool_name):
            missing.append(tool_name)

    if not missing:
        return True

    if cli_mode:
        # CLI 模式：输出到 stderr + 抛出异常
        for tool_name in missing:
            entry = TOOL_REGISTRY.get(tool_name)
            if entry:
                _exe, install_cmd = entry
                print(
                    t("preflight_missing_cli", tool=tool_name, cmd=install_cmd),
                    file=sys.stderr,
                )
            else:
                print(
                    t("preflight_unknown_tool", tool=tool_name),
                    file=sys.stderr,
                )
        raise PreflightError(missing)
    else:
        # TUI 模式：使用 rich 打印友好提示
        from rich.console import Console

        console = Console()
        for tool_name in missing:
            entry = TOOL_REGISTRY.get(tool_name)
            if entry:
                _exe, install_cmd = entry
                console.print(
                    t("preflight_missing_tui", tool=tool_name, cmd=install_cmd),
                    style="bold yellow",
                )
            else:
                console.print(
                    t("preflight_unknown_tool", tool=tool_name),
                    style="bold red",
                )
        console.print(t("preflight_hint_env_manager"), style="cyan")
        return False
