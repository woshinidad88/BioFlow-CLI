"""BioFlow-CLI 序列处理模块 — FASTA 格式化工具。"""

from __future__ import annotations

import os
import re
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.progress import track

from bioflow.i18n import t

console = Console()


def _parse_env_int(key: str, default: int) -> int:
    """安全解析整型环境变量，非法值静默回退到默认值。"""
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


LARGE_FILE_WARNING_MB = _parse_env_int("BIOFLOW_LARGE_FILE_MB", 500)


def _parse_fasta(text: str) -> list[tuple[str, str]]:
    """解析 FASTA 文本，返回 (header, sequence) 列表。"""
    records: list[tuple[str, str]] = []
    current_header = ""
    current_seq: list[str] = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current_header:
                records.append((current_header, "".join(current_seq)))
            current_header = line
            current_seq = []
        else:
            current_seq.append(re.sub(r"\s+", "", line))

    if current_header:
        records.append((current_header, "".join(current_seq)))
    return records


def _wrap_sequence(seq: str, width: int = 80) -> str:
    """将序列按指定宽度换行。"""
    return "\n".join(seq[i : i + width] for i in range(0, len(seq), width))


def _format_fasta(records: list[tuple[str, str]], width: int = 80) -> str:
    """将解析后的记录格式化为标准 FASTA 输出。"""
    lines: list[str] = []
    for header, seq in records:
        lines.append(header)
        lines.append(_wrap_sequence(seq.upper(), width))
    return "\n".join(lines) + "\n"


def seq_menu() -> None:
    """序列格式化交互菜单。"""
    console.print(Panel(t("seq_title"), style="bold magenta"))

    try:
        input_path = questionary.path(t("seq_input_prompt")).ask()
    except KeyboardInterrupt:
        return
    if not input_path:
        return

    src = Path(input_path)
    if not src.exists():
        console.print(t("seq_file_not_found", path=str(src)), style="bold red")
        input(t("press_enter"))
        return

    # 大文件警告
    file_size_mb = src.stat().st_size / (1024 * 1024)
    if file_size_mb > LARGE_FILE_WARNING_MB:
        console.print(
            t("seq_large_file_warn", size=f"{file_size_mb:.0f}"), style="bold yellow"
        )

    try:
        output_path = questionary.path(
            t("seq_output_prompt"), default=str(src.with_suffix(".formatted.fasta"))
        ).ask()
    except KeyboardInterrupt:
        return
    if not output_path:
        return

    width_str = questionary.text(t("seq_wrap_prompt"), default="80").ask()
    width = int(width_str) if width_str and width_str.isdigit() else 80
    width = max(1, width)  # 钳位，防止 range step=0 崩溃

    console.print(t("seq_processing"), style="cyan")
    text = src.read_text(encoding="utf-8")
    records = _parse_fasta(text)

    if not records:
        console.print(t("seq_invalid_format"), style="bold red")
        input(t("press_enter"))
        return

    # 进度条绑定真实格式化工作
    output_lines: list[str] = []
    for header, seq in track(records, description=t("seq_processing")):
        output_lines.append(header)
        output_lines.append(_wrap_sequence(seq.upper(), width))
    output = "\n".join(output_lines) + "\n"

    Path(output_path).write_text(output, encoding="utf-8")
    console.print(
        t("seq_done", count=len(records), path=output_path), style="bold green"
    )
    input(t("press_enter"))