"""BioFlow-CLI BLAST 检索模块 — makeblastdb + blastn 基础检索流程。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel

from bioflow.i18n import t
from bioflow.preflight import preflight_check

console = Console()

SEARCH_REQUIRED_TOOLS = ("makeblastdb", "blastn")


def _print_search_failure(description: str, err: str) -> bool:
    """打印统一的检索错误信息。"""
    console.print(
        t("search_step_failed", step=description, err=err),
        style="bold red",
    )
    return False


def _run_cmd(
    cmd: list[str],
    *,
    description: str = "",
) -> bool:
    """执行外部命令并返回是否成功。"""
    if description:
        console.print(f"  → {description}", style="cyan")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as exc:
        stderr_text = exc.stderr or str(exc)
        return _print_search_failure(description, stderr_text.strip())
    except FileNotFoundError as exc:
        return _print_search_failure(description, str(exc))


def _blast_db_index_files(db_fasta: Path) -> list[Path]:
    """返回 BLAST nucleotide 数据库索引文件列表。"""
    return [db_fasta.with_suffix(db_fasta.suffix + ext) for ext in (".nhr", ".nin", ".nsq")]


def _blast_db_ready(db_fasta: Path) -> bool:
    """判断 BLAST 数据库索引是否已存在。"""
    return all(path.exists() for path in _blast_db_index_files(db_fasta))


def _run_makeblastdb(db_fasta: Path) -> bool:
    """构建 BLAST nucleotide 数据库。"""
    return _run_cmd(
        [
            "makeblastdb",
            "-in",
            str(db_fasta),
            "-dbtype",
            "nucl",
        ],
        description=t("search_building_db", file=db_fasta.name),
    )


def _run_blastn(
    db_fasta: Path,
    query_fasta: Path,
    output_path: Path,
    *,
    evalue: float = 10.0,
    max_target_seqs: int = 10,
) -> bool:
    """执行 blastn 检索。"""
    return _run_cmd(
        [
            "blastn",
            "-query",
            str(query_fasta),
            "-db",
            str(db_fasta),
            "-out",
            str(output_path),
            "-outfmt",
            "6",
            "-evalue",
            str(evalue),
            "-max_target_seqs",
            str(max_target_seqs),
        ],
        description=t("search_running_blastn", file=query_fasta.name),
    )


def _count_hits(output_path: Path) -> int:
    """统计检索结果命中条数。"""
    if not output_path.exists():
        return 0
    with output_path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def run_blast_search(
    db_fasta: Path,
    query_fasta: Path,
    *,
    output: Path | None = None,
    evalue: float = 10.0,
    max_target_seqs: int = 10,
    cli_mode: bool = False,
    skip_preflight: bool = False,
) -> dict[str, int | str | float] | None:
    """执行 makeblastdb + blastn 基础检索流程。"""
    if not skip_preflight:
        if not preflight_check(SEARCH_REQUIRED_TOOLS, cli_mode=cli_mode):
            return None

    if output is None:
        output = query_fasta.parent / f"{query_fasta.stem}.blast.tsv"
    output.parent.mkdir(parents=True, exist_ok=True)

    console.print(
        Panel(
            t("search_pipeline_start", file=str(query_fasta)),
            style="bold magenta",
        )
    )

    if _blast_db_ready(db_fasta):
        console.print(t("search_db_cached"), style="bold blue")
    else:
        console.print(t("search_step_makeblastdb"), style="bold blue")
        if not _run_makeblastdb(db_fasta):
            return None

    console.print(t("search_step_blastn"), style="bold blue")
    if not _run_blastn(
        db_fasta,
        query_fasta,
        output,
        evalue=evalue,
        max_target_seqs=max_target_seqs,
    ):
        return None

    hits = _count_hits(output)
    console.print(
        t("search_pipeline_done", output=str(output), hits=hits),
        style="bold green",
    )
    return {
        "db": str(db_fasta),
        "query": str(query_fasta),
        "output": str(output),
        "hits": hits,
        "evalue": evalue,
        "max_target_seqs": max_target_seqs,
    }


def _parse_float(value: str | None, default: float) -> float:
    """解析浮点输入，非法值回退默认值。"""
    if value is None:
        return default
    try:
        return float(value.strip())
    except (TypeError, ValueError):
        return default


def _parse_int(value: str | None, default: int) -> int:
    """解析整数输入，非法值回退默认值。"""
    if value is None:
        return default
    try:
        return max(1, int(value.strip()))
    except (TypeError, ValueError):
        return default


def search_menu() -> None:
    """BLAST 检索交互菜单（TUI 模式）。"""
    console.print(Panel(t("search_title"), style="bold magenta"))

    if not preflight_check(SEARCH_REQUIRED_TOOLS, cli_mode=False):
        input(t("press_enter"))
        return

    try:
        db_path = questionary.path(t("search_db_prompt")).ask()
    except KeyboardInterrupt:
        return
    if not db_path:
        return

    db_fasta = Path(db_path)
    if not db_fasta.exists():
        console.print(t("seq_file_not_found", path=str(db_fasta)), style="bold red")
        input(t("press_enter"))
        return

    try:
        query_path = questionary.path(t("search_query_prompt")).ask()
    except KeyboardInterrupt:
        return
    if not query_path:
        return

    query_fasta = Path(query_path)
    if not query_fasta.exists():
        console.print(t("seq_file_not_found", path=str(query_fasta)), style="bold red")
        input(t("press_enter"))
        return

    default_output = query_fasta.parent / f"{query_fasta.stem}.blast.tsv"
    try:
        output_path = questionary.path(
            t("search_output_prompt"),
            default=str(default_output),
        ).ask()
    except KeyboardInterrupt:
        return
    if not output_path:
        return

    evalue = _parse_float(questionary.text(t("search_evalue_prompt"), default="10.0").ask(), 10.0)
    max_target_seqs = _parse_int(
        questionary.text(t("search_max_targets_prompt"), default="10").ask(),
        10,
    )

    run_blast_search(
        db_fasta,
        query_fasta,
        output=Path(output_path),
        evalue=evalue,
        max_target_seqs=max_target_seqs,
        cli_mode=False,
        skip_preflight=True,
    )
    input(t("press_enter"))
