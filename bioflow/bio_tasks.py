"""BioFlow-CLI 序列处理模块 — FASTA/FASTQ 格式化工具。"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, track
from rich.table import Table

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

SUPPORTED_FORMATS = ("fasta", "fastq")


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


def _detect_sequence_format(text: str) -> str | None:
    """根据首个非空行识别序列格式。"""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            return "fasta"
        if line.startswith("@"):
            return "fastq"
        return None
    return None


def _parse_fastq(text: str) -> list[tuple[str, str, str, str]]:
    """解析 FASTQ 文本，返回 (header, sequence, plus, quality) 列表。"""
    lines = text.splitlines()
    records: list[tuple[str, str, str, str]] = []
    idx = 0

    while idx < len(lines):
        header = lines[idx].strip()
        if not header:
            idx += 1
            continue
        if not header.startswith("@"):
            return []
        if idx + 3 >= len(lines):
            return []

        seq = re.sub(r"\s+", "", lines[idx + 1].strip())
        plus = lines[idx + 2].strip()
        qual = re.sub(r"\s+", "", lines[idx + 3].strip())
        if not plus.startswith("+"):
            return []
        if not seq or not qual or len(seq) != len(qual):
            return []

        records.append((header, seq, plus, qual))
        idx += 4

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


def _format_fastq(records: list[tuple[str, str, str, str]], width: int = 80) -> str:
    """将解析后的记录格式化为标准 FASTQ 输出。"""
    lines: list[str] = []
    for header, seq, plus, qual in records:
        seq_upper = seq.upper()
        if len(seq_upper) != len(qual):
            raise ValueError("FASTQ sequence and quality length mismatch")
        lines.append(header)
        lines.append(_wrap_sequence(seq_upper, width))
        lines.append(plus)
        lines.append(_wrap_sequence(qual, width))
    return "\n".join(lines) + "\n"


def _fastq_quality_stats(records: list[tuple[str, str, str, str]]) -> dict[str, float]:
    """计算 FASTQ 质量统计（Phred+33）。"""
    total_bases = 0
    total_score = 0
    q20_bases = 0
    q30_bases = 0

    for _header, _seq, _plus, qual in records:
        for ch in qual:
            score = ord(ch) - 33
            total_bases += 1
            total_score += score
            if score >= 20:
                q20_bases += 1
            if score >= 30:
                q30_bases += 1

    if total_bases == 0:
        return {"avg_q": 0.0, "q20_ratio": 0.0, "q30_ratio": 0.0, "bases": 0}

    return {
        "avg_q": total_score / total_bases,
        "q20_ratio": q20_bases / total_bases,
        "q30_ratio": q30_bases / total_bases,
        "bases": float(total_bases),
    }


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

    default_suffix = src.suffix if src.suffix else ".fasta"
    default_output = src.with_name(f"{src.stem}.formatted{default_suffix}")
    try:
        output_path = questionary.path(
            t("seq_output_prompt"), default=str(default_output)
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
    seq_format = _detect_sequence_format(text)

    if seq_format not in SUPPORTED_FORMATS:
        console.print(t("seq_invalid_format"), style="bold red")
        input(t("press_enter"))
        return

    output_lines: list[str] = []
    count = 0
    fastq_stats: dict[str, float] | None = None

    if seq_format == "fasta":
        records = _parse_fasta(text)
        if not records:
            console.print(t("seq_invalid_format"), style="bold red")
            input(t("press_enter"))
            return

        # 进度条绑定真实格式化工作
        for header, seq in track(records, description=t("seq_processing")):
            output_lines.append(header)
            output_lines.append(_wrap_sequence(seq.upper(), width))
        count = len(records)
    else:
        records = _parse_fastq(text)
        if not records:
            console.print(t("seq_invalid_format"), style="bold red")
            input(t("press_enter"))
            return
        for header, seq, plus, qual in track(records, description=t("seq_processing")):
            output_lines.append(header)
            output_lines.append(_wrap_sequence(seq.upper(), width))
            output_lines.append(plus)
            output_lines.append(_wrap_sequence(qual, width))
        fastq_stats = _fastq_quality_stats(records)
        count = len(records)

    output = "\n".join(output_lines) + "\n"

    Path(output_path).write_text(output, encoding="utf-8")
    console.print(t("seq_done", count=count, path=output_path), style="bold green")
    if fastq_stats:
        console.print(
            t(
                "seq_fastq_stats",
                avg_q=f"{fastq_stats['avg_q']:.2f}",
                q20=f"{fastq_stats['q20_ratio']:.1%}",
                q30=f"{fastq_stats['q30_ratio']:.1%}",
                bases=int(fastq_stats["bases"]),
            ),
            style="bold cyan",
        )
    input(t("press_enter"))


def _make_unique_output_path(
    file_path: Path,
    input_dir: Path,
    output_dir: Path,
    recursive: bool,
    seen: set[str],
) -> Path:
    """生成唯一的输出文件路径，递归模式下加入相对路径前缀避免冲突。"""
    if recursive:
        try:
            rel = file_path.relative_to(input_dir)
            if rel.parent != Path("."):
                prefix = str(rel.parent).replace("/", "__").replace("\\", "__")
                name = f"{prefix}__{file_path.stem}.formatted{file_path.suffix}"
            else:
                name = f"{file_path.stem}.formatted{file_path.suffix}"
        except ValueError:
            name = f"{file_path.stem}.formatted{file_path.suffix}"
    else:
        name = f"{file_path.stem}.formatted{file_path.suffix}"

    # 冲突检测：追加序号
    base_name = name
    counter = 1
    while name in seen:
        stem, suffix = base_name.rsplit(".", 1) if "." in base_name else (base_name, "")
        name = f"{stem}_{counter}.{suffix}" if suffix else f"{stem}_{counter}"
        counter += 1
    seen.add(name)
    return output_dir / name


def _process_single_file(
    file_path: Path,
    output_path: Path,
    width: int,
) -> tuple[str, int]:
    """处理单个序列文件，返回 (格式化输出文本, 序列数)。

    Raises:
        ValueError: 格式不支持或解析失败。
    """
    text = file_path.read_text(encoding="utf-8")
    seq_format = _detect_sequence_format(text)

    if seq_format not in SUPPORTED_FORMATS:
        raise ValueError("unsupported_format")

    if seq_format == "fasta":
        records = _parse_fasta(text)
        if not records:
            raise ValueError("parse_error")
        return _format_fasta(records, width), len(records)
    else:
        records = _parse_fastq(text)
        if not records:
            raise ValueError("parse_error")
        return _format_fastq(records, width), len(records)


def batch_format_sequences(
    input_dir: Path,
    output_dir: Path,
    pattern: str = "*.fasta",
    recursive: bool = False,
    width: int = 80,
    continue_on_error: bool = True,
    quiet: bool = False,
) -> dict[str, list[dict]]:
    """批量格式化序列文件。

    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        pattern: 文件匹配模式（如 *.fasta, *.fa, *.fastq）
        recursive: 是否递归扫描子目录
        width: 序列换行宽度
        continue_on_error: 遇到错误是否继续处理
        quiet: 静默模式（不显示进度）

    Returns:
        包含 success/failed/skipped 列表的字典
    """
    # 收集文件
    if recursive:
        files = sorted(input_dir.rglob(pattern))
    else:
        files = sorted(input_dir.glob(pattern))

    results: dict[str, list[dict]] = {
        "success": [],
        "failed": [],
        "skipped": [],
    }

    if not files:
        return results

    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    seen_names: set[str] = set()

    def _handle_file(file_path: Path) -> bool:
        """处理单个文件，返回 False 表示应中断循环。"""
        start_time = time.time()
        try:
            output_text, count = _process_single_file(file_path, output_dir, width)
            out_path = _make_unique_output_path(
                file_path, input_dir, output_dir, recursive, seen_names
            )
            out_path.write_text(output_text, encoding="utf-8")
            results["success"].append({
                "file": file_path.name,
                "sequences": count,
                "output": out_path.name,
                "time": time.time() - start_time,
            })
        except ValueError as ve:
            reason = str(ve)
            if reason == "unsupported_format":
                results["skipped"].append({
                    "file": file_path.name,
                    "reason": "unsupported_format",
                    "time": 0.0,
                })
            else:
                results["failed"].append({
                    "file": file_path.name,
                    "error": reason,
                    "time": time.time() - start_time,
                })
                if not continue_on_error:
                    return False
        except Exception as e:
            results["failed"].append({
                "file": file_path.name,
                "error": str(e),
                "time": time.time() - start_time,
            })
            if not continue_on_error:
                return False
        return True

    # 批量处理
    if not quiet:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(t("batch_processing"), total=len(files))
            for file_path in files:
                should_continue = _handle_file(file_path)
                progress.advance(task)
                if not should_continue:
                    break
    else:
        for file_path in files:
            if not _handle_file(file_path):
                break

    return results


def display_batch_results(results: dict[str, list[dict]]) -> None:
    """显示批量处理结果表格。"""
    total = len(results["success"]) + len(results["failed"]) + len(results["skipped"])

    if total == 0:
        console.print(t("batch_no_files"), style="yellow")
        return

    # 成功表格
    if results["success"]:
        table = Table(title=t("batch_success_title"), show_header=True, header_style="bold green")
        table.add_column(t("batch_col_file"), style="cyan")
        table.add_column(t("batch_col_sequences"), justify="right", style="magenta")
        table.add_column(t("batch_col_output"), style="blue")
        table.add_column(t("batch_col_time"), justify="right", style="yellow")

        for item in results["success"]:
            table.add_row(
                item["file"],
                str(item["sequences"]),
                item["output"],
                f"{item['time']:.2f}s",
            )

        console.print(table)

    # 失败表格
    if results["failed"]:
        table = Table(title=t("batch_failed_title"), show_header=True, header_style="bold red")
        table.add_column(t("batch_col_file"), style="cyan")
        table.add_column(t("batch_col_error"), style="red")
        table.add_column(t("batch_col_time"), justify="right", style="yellow")

        for item in results["failed"]:
            table.add_row(
                item["file"],
                item["error"],
                f"{item['time']:.2f}s",
            )

        console.print(table)

    # 跳过表格
    if results["skipped"]:
        table = Table(title=t("batch_skipped_title"), show_header=True, header_style="bold yellow")
        table.add_column(t("batch_col_file"), style="cyan")
        table.add_column(t("batch_col_reason"), style="yellow")

        for item in results["skipped"]:
            table.add_row(item["file"], item["reason"])

        console.print(table)

    # 统计摘要
    console.print(
        t(
            "batch_summary",
            total=total,
            success=len(results["success"]),
            failed=len(results["failed"]),
            skipped=len(results["skipped"]),
        ),
        style="bold cyan",
    )

