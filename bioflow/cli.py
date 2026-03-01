#!/usr/bin/env python3
"""BioFlow-CLI 非交互式命令行接口。"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from rich.console import Console

from bioflow import __version__
from bioflow.bio_tasks import LARGE_FILE_WARNING_MB, _format_fasta, _parse_fasta
from bioflow.env_manager import BIO_TOOLS, _check_conda, _check_installed
from bioflow.i18n import init_language, t

# 退出码标准
EXIT_SUCCESS = 0
EXIT_RUNTIME_ERROR = 1
EXIT_ARGUMENT_ERROR = 2
EXIT_DEPENDENCY_MISSING = 3

# stderr 专用 console（进度、警告、错误）
console_err = Console(stderr=True)
# stdout 专用 console（结果输出）
console_out = Console(stderr=False)

# Unicode 符号缓存（模块加载时一次性计算，与 env_manager 保持一致）
try:
    "✓".encode(sys.stdout.encoding or "utf-8")
    _SYM_OK, _SYM_FAIL = "✓", "✗"
except (UnicodeEncodeError, LookupError):
    _SYM_OK, _SYM_FAIL = "+", "-"


def _setup_logging(quiet: bool = False) -> None:
    """配置日志系统。"""
    root = logging.getLogger("bioflow")
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        root.addHandler(handler)
        root.setLevel(logging.ERROR if quiet else logging.WARNING)


def cmd_seq(args: argparse.Namespace) -> int:
    """处理 seq 子命令：FASTA 格式化。"""
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".formatted.fasta")
    width = args.width

    # JSON 模式自动启用 quiet
    quiet = args.quiet or args.json

    # 参数校验
    if not input_path.exists():
        if args.json:
            print(json.dumps({"error": "file_not_found", "path": str(input_path)}, ensure_ascii=False))
        else:
            console_err.print(t("seq_file_not_found", path=str(input_path)), style="bold red")
        return EXIT_ARGUMENT_ERROR

    if width <= 0:
        if args.json:
            print(json.dumps({"error": "invalid_width", "width": width}, ensure_ascii=False))
        else:
            console_err.print(f"Error: width must be positive (got {width})", style="bold red")
        return EXIT_ARGUMENT_ERROR

    # 读取和解析
    try:
        # 大文件警告（与 TUI 保持一致）
        file_size_mb = input_path.stat().st_size / (1024 * 1024)
        if file_size_mb > LARGE_FILE_WARNING_MB and not quiet:
            console_err.print(
                t("seq_large_file_warn", size=f"{file_size_mb:.0f}"),
                style="bold yellow"
            )

        if not quiet:
            console_err.print(t("seq_processing"), style="cyan")

        text = input_path.read_text(encoding="utf-8")
        records = _parse_fasta(text)

        if not records:
            if args.json:
                print(json.dumps({"error": "invalid_format", "path": str(input_path)}, ensure_ascii=False))
            else:
                console_err.print(t("seq_invalid_format"), style="bold red")
            return EXIT_RUNTIME_ERROR

        # 格式化
        output = _format_fasta(records, width)
        output_path.write_text(output, encoding="utf-8")

        # 输出结果
        if args.json:
            result = json.dumps({
                "status": "success",
                "input": str(input_path),
                "output": str(output_path),
                "records": len(records),
                "width": width
            }, ensure_ascii=False)
            # 直接使用 print 避免 rich 的自动换行
            print(result)
        else:
            if not quiet:
                console_err.print(
                    t("seq_done", count=len(records), path=str(output_path)),
                    style="bold green"
                )

        return EXIT_SUCCESS

    except Exception as exc:
        if args.json:
            print(json.dumps({"error": "runtime_error", "message": str(exc)}, ensure_ascii=False))
        else:
            console_err.print(t("error_unexpected", err=str(exc)), style="bold red")
        return EXIT_RUNTIME_ERROR


def cmd_env_list(args: argparse.Namespace) -> int:
    """处理 env --list：列出工具状态。"""
    # 注意：不检查 Conda，允许只读状态查询
    tools_status = []
    for name, exe, _ in BIO_TOOLS:
        installed = _check_installed(exe)
        tools_status.append({"name": name, "executable": exe, "installed": installed})

    if args.json:
        print(json.dumps({"tools": tools_status}, ensure_ascii=False))
    else:
        for tool in tools_status:
            status = _SYM_OK if tool["installed"] else _SYM_FAIL
            console_out.print(f"{status} {tool['name']}")

    return EXIT_SUCCESS


def cmd_env_install(args: argparse.Namespace) -> int:
    """处理 env --install：安装指定工具。"""
    tool_name = args.install

    # JSON 模式自动启用 quiet
    quiet = args.quiet or args.json

    # 检查 conda
    if not _check_conda():
        if args.json:
            print(json.dumps({"error": "conda_missing"}, ensure_ascii=False))
        else:
            console_err.print(t("env_conda_missing"), style="bold red")
            console_err.print("Install conda from: https://docs.conda.io/en/latest/miniconda.html")
        return EXIT_DEPENDENCY_MISSING

    # 查找工具
    tool_info = None
    for name, exe, cmd in BIO_TOOLS:
        if name.lower() == tool_name.lower():
            tool_info = (name, exe, cmd)
            break

    if not tool_info:
        if args.json:
            print(json.dumps({"error": "unknown_tool", "tool": tool_name}, ensure_ascii=False))
        else:
            console_err.print(f"Error: Unknown tool '{tool_name}'", style="bold red")
            console_err.print(f"Available tools: {', '.join(t[0] for t in BIO_TOOLS)}")
        return EXIT_ARGUMENT_ERROR

    name, exe, cmd = tool_info

    # 检查是否已安装
    if _check_installed(exe):
        if args.json:
            print(json.dumps({"status": "already_installed", "tool": name}, ensure_ascii=False))
        else:
            if not quiet:
                console_err.print(t("env_already", tool=name), style="yellow")
        return EXIT_SUCCESS

    # 执行安装
    try:
        if not quiet:
            console_err.print(t("env_installing", tool=name), style="bold cyan")

        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL if quiet else None)

        if args.json:
            print(json.dumps({"status": "success", "tool": name}, ensure_ascii=False))
        else:
            if not quiet:
                console_err.print(t("env_install_ok", tool=name), style="bold green")

        return EXIT_SUCCESS

    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        if args.json:
            print(json.dumps({"error": "install_failed", "tool": name, "message": str(exc)}, ensure_ascii=False))
        else:
            console_err.print(t("env_install_fail", tool=name, err=str(exc)), style="bold red")
        return EXIT_RUNTIME_ERROR


def main() -> int:
    """CLI 主入口。"""
    parser = argparse.ArgumentParser(
        prog="bioflow",
        description="BioFlow-CLI - Bioinformatics workflow tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress messages")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # seq 子命令
    parser_seq = subparsers.add_parser("seq", help="Format FASTA sequences")
    parser_seq.add_argument("--input", "-i", required=True, help="Input FASTA file")
    parser_seq.add_argument("--output", "-o", help="Output file (default: input.formatted.fasta)")
    parser_seq.add_argument("--width", "-w", type=int, default=80, help="Line width (default: 80)")

    # env 子命令
    parser_env = subparsers.add_parser("env", help="Manage bioinformatics tools")
    env_group = parser_env.add_mutually_exclusive_group(required=True)
    env_group.add_argument("--list", "-l", action="store_true", help="List all tools and their status")
    env_group.add_argument("--install", "-i", metavar="TOOL", help="Install a specific tool")

    args = parser.parse_args()

    # 初始化
    _setup_logging(quiet=args.quiet)
    init_language()

    # 路由到子命令
    if args.command == "seq":
        return cmd_seq(args)
    elif args.command == "env":
        if args.list:
            return cmd_env_list(args)
        elif args.install:
            return cmd_env_install(args)
    else:
        parser.print_help(sys.stderr)
        return EXIT_ARGUMENT_ERROR


if __name__ == "__main__":
    sys.exit(main())
