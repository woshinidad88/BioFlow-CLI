"""BioFlow-CLI 批量处理子命令测试"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bioflow.cli import (
    EXIT_ARGUMENT_ERROR,
    EXIT_RUNTIME_ERROR,
    EXIT_SUCCESS,
    cmd_batch,
)
from bioflow.bio_tasks import batch_format_sequences


@pytest.fixture()
def batch_test_dir(tmp_path):
    """创建包含多个测试文件的目录结构。"""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    
    # 根目录文件
    (input_dir / "f1.fasta").write_text(">s1\nATGC\n", encoding="utf-8")
    (input_dir / "f2.fasta").write_text(">s2\nGGCC\n", encoding="utf-8")
    (input_dir / "r1.fastq").write_text("@r1\nATGC\n+\nIIII\n", encoding="utf-8")
    (input_dir / "readme.txt").write_text("This is a text file", encoding="utf-8")
    
    # 子目录文件
    sub_dir = input_dir / "subdir"
    sub_dir.mkdir()
    (sub_dir / "f3.fasta").write_text(">s3\nTTTT\n", encoding="utf-8")
    
    return input_dir


@pytest.fixture()
def mock_args():
    """创建模拟的 argparse.Namespace 对象。"""
    class Args:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    return Args


class TestBatchLogic:
    def test_batch_success_basic(self, batch_test_dir, tmp_path):
        """测试基本的批量格式化成功（非递归）。"""
        output_dir = tmp_path / "output"
        results = batch_format_sequences(
            input_dir=batch_test_dir,
            output_dir=output_dir,
            pattern="*.fasta",
            recursive=False,
            width=80,
            quiet=True
        )
        
        assert len(results["success"]) == 2
        assert len(results["failed"]) == 0
        assert len(results["skipped"]) == 0
        assert (output_dir / "f1.formatted.fasta").exists()
        assert (output_dir / "f2.formatted.fasta").exists()

    def test_batch_recursive(self, batch_test_dir, tmp_path):
        """测试递归扫描。"""
        output_dir = tmp_path / "output"
        results = batch_format_sequences(
            input_dir=batch_test_dir,
            output_dir=output_dir,
            pattern="*.fasta",
            recursive=True,
            width=80,
            quiet=True
        )
        
        # f1.fasta, f2.fasta, subdir/f3.fasta
        assert len(results["success"]) == 3
        assert (output_dir / "f1.formatted.fasta").exists()
        assert (output_dir / "f2.formatted.fasta").exists()
        assert (output_dir / "f3.formatted.fasta").exists()

    def test_batch_unsupported_format_skipped(self, batch_test_dir, tmp_path):
        """测试不支持的格式被跳过。"""
        output_dir = tmp_path / "output"
        # 使用 * 匹配所有文件，包含 .txt
        results = batch_format_sequences(
            input_dir=batch_test_dir,
            output_dir=output_dir,
            pattern="*",
            recursive=False,
            width=80,
            quiet=True
        )
        
        # f1.fasta, f2.fasta, r1.fastq -> success
        # readme.txt, subdir -> skipped (subdir is skipped because it's a dir, or ignored by glob if not matching)
        # Actually glob("*") includes directories. 
        # But _detect_sequence_format will return None for txt and dir.
        
        success_files = [item["file"] for item in results["success"]]
        assert "f1.fasta" in success_files
        assert "f2.fasta" in success_files
        assert "r1.fastq" in success_files
        
        skipped_files = [item["file"] for item in results["skipped"]]
        assert "readme.txt" in skipped_files

    def test_batch_parse_error(self, batch_test_dir, tmp_path):
        """测试解析错误处理（格式识别成功但解析失败）。"""
        # 创建一个看起来像 FASTQ 但行数不足的文件，会导致 _parse_fastq 返回 []
        (batch_test_dir / "bad_fastq.fastq").write_text("@r1\nATCG\n+\n", encoding="utf-8")
        output_dir = tmp_path / "output"
        
        results = batch_format_sequences(
            input_dir=batch_test_dir,
            output_dir=output_dir,
            pattern="bad_fastq.fastq",
            recursive=False,
            quiet=True
        )
        
        # _detect_sequence_format 识别为 fastq
        # _parse_fastq 返回 []
        # batch_format_sequences 将其计入 failed
        assert len(results["failed"]) == 1
        assert results["failed"][0]["error"] == "parse_error"


class TestCmdBatch:
    def test_cmd_batch_success(self, batch_test_dir, tmp_path, mock_args, capsys):
        """测试 CLI batch 命令成功执行。"""
        output_dir = tmp_path / "output"
        args = mock_args(
            input_dir=str(batch_test_dir),
            output_dir=str(output_dir),
            pattern="*.fasta",
            recursive=False,
            width=80,
            continue_on_error=True,
            quiet=True,
            json=False
        )
        
        exit_code = cmd_batch(args)
        assert exit_code == EXIT_SUCCESS
        assert (output_dir / "f1.formatted.fasta").exists()

    def test_cmd_batch_json(self, batch_test_dir, tmp_path, mock_args, capsys):
        """测试 CLI batch 命令 JSON 输出。"""
        output_dir = tmp_path / "output"
        args = mock_args(
            input_dir=str(batch_test_dir),
            output_dir=str(output_dir),
            pattern="*.fasta",
            recursive=False,
            width=80,
            continue_on_error=True,
            quiet=False,
            json=True
        )
        
        exit_code = cmd_batch(args)
        captured = capsys.readouterr()
        
        assert exit_code == EXIT_SUCCESS
        data = json.loads(captured.out)
        assert data["status"] == "success"
        assert data["summary"]["success_count"] == 2

    def test_cmd_batch_dir_not_found(self, mock_args):
        """测试输入目录不存在。"""
        args = mock_args(
            input_dir="nonexistent_dir_123",
            output_dir=None,
            pattern="*.fasta",
            recursive=False,
            width=80,
            continue_on_error=True,
            quiet=True,
            json=False
        )
        exit_code = cmd_batch(args)
        assert exit_code == EXIT_ARGUMENT_ERROR

    def test_cmd_batch_continue_on_error(self, batch_test_dir, tmp_path, mock_args):
        """测试 continue_on_error=False 时遇到错误停止。"""
        # 创建一个会失败的文件
        (batch_test_dir / "00_bad.fasta").write_text(">header\n", encoding="utf-8") # Empty seq after header might fail or be skipped
        # In _parse_fasta: if current_header: records.append((current_header, "".join(current_seq)))
        # So it might actually succeed with empty seq.
        
        # Let's mock a real exception during processing if possible, or use a file that's definitely "failed"
        # In batch_format_sequences, failure is if not records.
        # Let's use a file that starts with > but has nothing else.
        (batch_test_dir / "00_fail.fasta").write_text(">", encoding="utf-8") 
        # _detect_sequence_format returns "fasta"
        # _parse_fasta returns records = [(">", "")]
        # So it's not empty.
        
        # How about a file that causes read_text to fail? Hard with pathlib.
        # Use the "failed" logic in batch_format_sequences: if not records.
        # If I give it just ">\n", _parse_fasta returns [(">", "")] which is truthy.
        # If I give it empty file, _detect_sequence_format returns None -> skipped.
        
        # Let's try to trigger a failure via _parse_fastq with invalid format
        (batch_test_dir / "00_fail.fastq").write_text("@r1\nATCG\n+\nI\n", encoding="utf-8") # Length mismatch
        
        output_dir = tmp_path / "output"
        args = mock_args(
            input_dir=str(batch_test_dir),
            output_dir=str(output_dir),
            pattern="*.fastq",
            recursive=False,
            width=80,
            continue_on_error=False,
            quiet=True,
            json=False
        )
        
        exit_code = cmd_batch(args)
        assert exit_code == EXIT_RUNTIME_ERROR
