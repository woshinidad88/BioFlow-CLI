"""BioFlow-CLI 质控流程模块 — FastQC → Trimmomatic → FastQC 串联 QC Pipeline。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence

import questionary
from rich.console import Console
from rich.panel import Panel

from bioflow.i18n import t
from bioflow.preflight import PreflightError, preflight_check

console = Console()

# QC 流程依赖的工具
QC_REQUIRED_TOOLS = ("fastqc", "trimmomatic")


def _run_cmd(cmd: list[str], *, description: str = "") -> bool:
    """执行外部命令，返回是否成功。"""
    if description:
        console.print(f"  → {description}", style="cyan")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as exc:
        console.print(
            t("qc_step_failed", step=description, err=exc.stderr.strip()),
            style="bold red",
        )
        return False
    except FileNotFoundError as exc:
        console.print(
            t("qc_step_failed", step=description, err=str(exc)),
            style="bold red",
        )
        return False


def _run_fastqc(input_file: Path, output_dir: Path) -> bool:
    """运行 FastQC 质量检测。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    return _run_cmd(
        ["fastqc", str(input_file), "-o", str(output_dir), "--quiet"],
        description=t("qc_running_fastqc", file=input_file.name),
    )


def _run_trimmomatic(
    input_file: Path,
    output_file: Path,
    *,
    adapter: str | None = None,
    minlen: int = 36,
) -> bool:
    """运行 Trimmomatic 质控修剪。"""
    cmd = [
        "trimmomatic",
        "SE",           # Single-End 模式
        "-phred33",
        str(input_file),
        str(output_file),
    ]

    # 添加修剪步骤
    if adapter:
        cmd.append(f"ILLUMINACLIP:{adapter}:2:30:10")
    cmd.append("LEADING:3")
    cmd.append("TRAILING:3")
    cmd.append("SLIDINGWINDOW:4:15")
    cmd.append(f"MINLEN:{minlen}")

    return _run_cmd(
        cmd,
        description=t("qc_running_trimmomatic", file=input_file.name),
    )


def run_qc_pipeline(
    input_file: Path,
    *,
    output_dir: Path | None = None,
    adapter: str | None = None,
    minlen: int = 36,
    cli_mode: bool = False,
) -> bool:
    """执行完整的 QC 串联流程：FastQC → Trimmomatic → FastQC。

    Args:
        input_file: 输入 FASTQ 文件路径。
        output_dir: 输出目录，默认在输入文件同目录下创建 qc_output/。
        adapter: Trimmomatic adapter 文件路径（可选）。
        minlen: Trimmomatic 最短读长阈值，默认 36。
        cli_mode: 是否为 CLI 模式。

    Returns:
        True 表示全部步骤成功。
    """
    # 1. Preflight 检查
    try:
        if not preflight_check(QC_REQUIRED_TOOLS, cli_mode=cli_mode):
            return False
    except PreflightError:
        raise

    # 2. 准备输出目录
    if output_dir is None:
        output_dir = input_file.parent / "qc_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    fastqc_pre_dir = output_dir / "fastqc_pre"
    fastqc_post_dir = output_dir / "fastqc_post"
    trimmed_file = output_dir / f"{input_file.stem}.trimmed{input_file.suffix}"

    console.print(
        Panel(t("qc_pipeline_start", file=str(input_file)), style="bold magenta")
    )

    # 3. 步骤 1：初始 FastQC
    console.print(t("qc_step_label", step="1/3", name="FastQC"), style="bold blue")
    if not _run_fastqc(input_file, fastqc_pre_dir):
        return False

    # 4. 步骤 2：Trimmomatic 修剪
    console.print(
        t("qc_step_label", step="2/3", name="Trimmomatic"), style="bold blue"
    )
    if not _run_trimmomatic(
        input_file, trimmed_file, adapter=adapter, minlen=minlen
    ):
        return False

    # 5. 步骤 3：修剪后 FastQC
    console.print(t("qc_step_label", step="3/3", name="FastQC"), style="bold blue")
    if not _run_fastqc(trimmed_file, fastqc_post_dir):
        return False

    console.print(
        t("qc_pipeline_done", output=str(output_dir)), style="bold green"
    )
    return True


def qc_menu() -> None:
    """质控流程交互菜单（TUI 模式）。"""
    console.print(Panel(t("qc_title"), style="bold magenta"))

    # Preflight 检查
    if not preflight_check(QC_REQUIRED_TOOLS, cli_mode=False):
        input(t("press_enter"))
        return

    # 输入文件
    try:
        input_path = questionary.path(t("qc_input_prompt")).ask()
    except KeyboardInterrupt:
        return
    if not input_path:
        return

    src = Path(input_path)
    if not src.exists():
        console.print(t("seq_file_not_found", path=str(src)), style="bold red")
        input(t("press_enter"))
        return

    # 输出目录
    default_output = src.parent / "qc_output"
    try:
        output_path = questionary.path(
            t("qc_output_prompt"), default=str(default_output)
        ).ask()
    except KeyboardInterrupt:
        return
    if not output_path:
        return

    # Adapter 文件（可选）
    try:
        adapter_path = questionary.text(
            t("qc_adapter_prompt"), default=""
        ).ask()
    except KeyboardInterrupt:
        return

    adapter = adapter_path if adapter_path and Path(adapter_path).exists() else None

    # 最短读长
    minlen_str = questionary.text(t("qc_minlen_prompt"), default="36").ask()
    minlen = int(minlen_str) if minlen_str and minlen_str.isdigit() else 36
    minlen = max(1, minlen)

    # 执行流程
    run_qc_pipeline(
        src,
        output_dir=Path(output_path),
        adapter=adapter,
        minlen=minlen,
        cli_mode=False,
    )
    input(t("press_enter"))
