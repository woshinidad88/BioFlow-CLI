"""BioFlow-CLI 预检和质控流程模块测试"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bioflow.cli import (
    EXIT_ARGUMENT_ERROR,
    EXIT_DEPENDENCY_MISSING,
    EXIT_RUNTIME_ERROR,
    EXIT_SUCCESS,
    cmd_qc,
)
from bioflow.preflight import (
    PreflightError,
    check_tool,
    preflight_check,
)


# === Fixtures ===

@pytest.fixture()
def mock_args():
    """创建模拟的 argparse.Namespace 对象。"""
    class Args:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    return Args


@pytest.fixture()
def temp_fastq(tmp_path):
    """创建临时 FASTQ 测试文件。"""
    content = "@r1\nATCG\n+\nIIII\n"
    fq = tmp_path / "test.fastq"
    fq.write_text(content)
    return fq


# === Preflight 模块测试 ===

class TestCheckTool:
    """测试单个工具检查。"""

    @patch("bioflow.preflight.shutil.which", return_value="/usr/bin/fastqc")
    def test_tool_found(self, _mock):
        assert check_tool("fastqc") is True

    @patch("bioflow.preflight.shutil.which", return_value=None)
    def test_tool_missing(self, _mock):
        assert check_tool("fastqc") is False

    def test_unknown_tool(self):
        assert check_tool("nonexistent_tool_xyz") is False


class TestPreflightCheck:
    """测试批量预检。"""

    @patch("bioflow.preflight.shutil.which", return_value="/usr/bin/tool")
    def test_all_found(self, _mock):
        assert preflight_check(["fastqc", "trimmomatic"], cli_mode=False) is True

    @patch("bioflow.preflight.shutil.which", return_value=None)
    def test_missing_cli_mode_raises(self, _mock):
        with pytest.raises(PreflightError) as exc_info:
            preflight_check(["fastqc"], cli_mode=True)
        assert "fastqc" in exc_info.value.missing_tools

    @patch("bioflow.preflight.shutil.which", return_value=None)
    def test_missing_tui_mode_returns_false(self, _mock):
        assert preflight_check(["fastqc"], cli_mode=False) is False

    def test_preflight_error_message(self):
        err = PreflightError(["fastqc", "trimmomatic"])
        assert "fastqc" in str(err)
        assert "trimmomatic" in str(err)
        assert err.missing_tools == ["fastqc", "trimmomatic"]


# === CLI QC 子命令测试 ===

class TestCmdQc:
    """测试 CLI qc 子命令。"""

    def test_file_not_found(self, mock_args):
        args = mock_args(
            input="/nonexistent/file.fastq",
            output=None,
            adapter=None,
            minlen=36,
            quiet=False,
            json=False,
        )
        assert cmd_qc(args) == EXIT_ARGUMENT_ERROR

    def test_invalid_minlen(self, temp_fastq, mock_args):
        args = mock_args(
            input=str(temp_fastq),
            output=None,
            adapter=None,
            minlen=0,
            quiet=False,
            json=False,
        )
        assert cmd_qc(args) == EXIT_ARGUMENT_ERROR

    @patch("bioflow.cli.run_qc_pipeline", side_effect=PreflightError(["fastqc"]))
    def test_missing_dependency(self, _mock, temp_fastq, mock_args):
        args = mock_args(
            input=str(temp_fastq),
            output=None,
            adapter=None,
            minlen=36,
            quiet=False,
            json=True,
        )
        assert cmd_qc(args) == EXIT_DEPENDENCY_MISSING

    @patch("bioflow.cli.run_qc_pipeline", return_value=True)
    def test_success(self, _mock, temp_fastq, mock_args, capsys):
        args = mock_args(
            input=str(temp_fastq),
            output=None,
            adapter=None,
            minlen=36,
            quiet=False,
            json=True,
        )
        result = cmd_qc(args)
        assert result == EXIT_SUCCESS
        out = capsys.readouterr().out
        assert "success" in out

    @patch("bioflow.cli.run_qc_pipeline", return_value=False)
    def test_pipeline_failure(self, _mock, temp_fastq, mock_args):
        args = mock_args(
            input=str(temp_fastq),
            output=None,
            adapter=None,
            minlen=36,
            quiet=False,
            json=False,
        )
        assert cmd_qc(args) == EXIT_RUNTIME_ERROR


# === i18n 翻译键完整性测试 ===

class TestI18nLocaleKeys:
    """验证 en.py 和 zh.py 的翻译键一致。"""

    def test_locale_keys_match(self):
        from bioflow.locales.en import STRINGS as en_strings
        from bioflow.locales.zh import STRINGS as zh_strings
        en_keys = set(en_strings.keys())
        zh_keys = set(zh_strings.keys())
        assert en_keys == zh_keys, (
            f"Missing in zh: {en_keys - zh_keys}, Missing in en: {zh_keys - en_keys}"
        )
