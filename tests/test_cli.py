"""BioFlow-CLI 命令行接口测试"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bioflow.cli import (
    EXIT_ARGUMENT_ERROR,
    EXIT_DEPENDENCY_MISSING,
    EXIT_RUNTIME_ERROR,
    EXIT_SUCCESS,
    cmd_env_install,
    cmd_env_list,
    cmd_seq,
    main,
)


# === Fixtures ===

@pytest.fixture()
def temp_fasta(tmp_path):
    """创建临时 FASTA 测试文件。"""
    fasta_file = tmp_path / "test.fasta"
    fasta_file.write_text(">seq1\nATCGATCG\n>seq2\nGGCCGGCC\n", encoding="utf-8")
    return fasta_file


@pytest.fixture()
def mock_args():
    """创建模拟的 argparse.Namespace 对象。"""
    class Args:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    return Args


# === seq 子命令测试 ===

class TestCmdSeq:
    def test_success_basic(self, temp_fasta, mock_args, capsys):
        """测试基本的 FASTA 格式化成功。"""
        output_path = temp_fasta.parent / "output.fasta"
        args = mock_args(
            input=str(temp_fasta),
            output=str(output_path),
            width=20,
            quiet=False,
            json=False
        )

        exit_code = cmd_seq(args)

        assert exit_code == EXIT_SUCCESS
        assert output_path.exists()
        content = output_path.read_text()
        assert ">seq1" in content
        assert ">seq2" in content

    def test_file_not_found(self, mock_args, capsys):
        """测试文件不存在时返回正确的退出码。"""
        args = mock_args(
            input="nonexistent.fasta",
            output=None,
            width=80,
            quiet=False,
            json=False
        )

        exit_code = cmd_seq(args)

        assert exit_code == EXIT_ARGUMENT_ERROR

    def test_invalid_width(self, temp_fasta, mock_args):
        """测试无效宽度参数返回错误。"""
        args = mock_args(
            input=str(temp_fasta),
            output=None,
            width=-10,
            quiet=False,
            json=False
        )

        exit_code = cmd_seq(args)

        assert exit_code == EXIT_ARGUMENT_ERROR

    def test_json_output(self, temp_fasta, mock_args, capsys):
        """测试 JSON 输出格式。"""
        output_path = temp_fasta.parent / "output_json.fasta"
        args = mock_args(
            input=str(temp_fasta),
            output=str(output_path),
            width=80,
            quiet=False,
            json=True
        )

        exit_code = cmd_seq(args)
        captured = capsys.readouterr()

        assert exit_code == EXIT_SUCCESS
        result = json.loads(captured.out)
        assert result["status"] == "success"
        assert result["records"] == 2
        assert result["width"] == 80

    def test_quiet_mode(self, temp_fasta, mock_args, capsys):
        """测试 quiet 模式不输出进度信息。"""
        output_path = temp_fasta.parent / "output_quiet.fasta"
        args = mock_args(
            input=str(temp_fasta),
            output=str(output_path),
            width=80,
            quiet=True,
            json=False
        )

        exit_code = cmd_seq(args)
        captured = capsys.readouterr()

        assert exit_code == EXIT_SUCCESS
        # stderr 应该为空（quiet 模式）
        assert captured.err == ""

    def test_invalid_fasta_format(self, tmp_path, mock_args):
        """测试无效的 FASTA 格式返回运行时错误。"""
        invalid_file = tmp_path / "invalid.fasta"
        invalid_file.write_text("This is not a FASTA file\nNo headers here\n", encoding="utf-8")

        args = mock_args(
            input=str(invalid_file),
            output=None,
            width=80,
            quiet=False,
            json=False
        )

        exit_code = cmd_seq(args)

        assert exit_code == EXIT_RUNTIME_ERROR


# === env 子命令测试 ===

class TestCmdEnv:
    @patch("bioflow.cli._check_installed")
    def test_list_no_conda(self, mock_check_installed, mock_args, capsys):
        """测试 env --list 不依赖 Conda，即使 Conda 缺失也能列出状态。"""
        mock_check_installed.return_value = False  # 所有工具都未安装
        args = mock_args(quiet=False, json=False)

        exit_code = cmd_env_list(args)
        captured = capsys.readouterr()

        # 应该成功返回，不再检查 Conda
        assert exit_code == EXIT_SUCCESS
        assert "FastQC" in captured.out

    @patch("bioflow.cli._check_installed")
    def test_list_success(self, mock_check_installed, mock_args, capsys):
        """测试成功列出工具状态。"""
        mock_check_installed.side_effect = [True, False, True, False, False]  # 5 个工具的状态

        args = mock_args(quiet=False, json=False)
        exit_code = cmd_env_list(args)
        captured = capsys.readouterr()

        assert exit_code == EXIT_SUCCESS
        # 检查是否包含符号（可能是 ✓/✗ 或 +/-）
        assert "FastQC" in captured.out

    @patch("bioflow.cli._check_conda")
    def test_install_no_conda(self, mock_check_conda, mock_args):
        """测试安装工具时 conda 缺失。"""
        mock_check_conda.return_value = False
        args = mock_args(install="fastqc", quiet=False, json=False)

        exit_code = cmd_env_install(args)

        assert exit_code == EXIT_DEPENDENCY_MISSING

    @patch("bioflow.cli._check_conda")
    def test_install_unknown_tool(self, mock_check_conda, mock_args):
        """测试安装未知工具返回参数错误。"""
        mock_check_conda.return_value = True
        args = mock_args(install="unknown_tool_xyz", quiet=False, json=False)

        exit_code = cmd_env_install(args)

        assert exit_code == EXIT_ARGUMENT_ERROR

    @patch("bioflow.cli._check_conda")
    @patch("bioflow.cli._check_installed")
    def test_install_already_installed(self, mock_check_installed, mock_check_conda, mock_args, capsys):
        """测试工具已安装时的行为。"""
        mock_check_conda.return_value = True
        mock_check_installed.return_value = True

        args = mock_args(install="fastqc", quiet=False, json=False)
        exit_code = cmd_env_install(args)

        assert exit_code == EXIT_SUCCESS


# === 主入口测试 ===

class TestMain:
    def test_no_command_shows_help(self, capsys):
        """测试无子命令时显示帮助信息。"""
        with patch.object(sys, "argv", ["bioflow"]):
            exit_code = main()

        captured = capsys.readouterr()
        assert exit_code == EXIT_ARGUMENT_ERROR
        assert "usage:" in captured.err or "positional arguments:" in captured.err

    def test_version_flag(self, capsys):
        """测试 --version 标志。"""
        with patch.object(sys, "argv", ["bioflow", "--version"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        # argparse 的 --version 会触发 SystemExit(0)
        assert exc_info.value.code == 0

    @patch("bioflow.cli.cmd_seq")
    def test_seq_command_routing(self, mock_cmd_seq):
        """测试 seq 命令正确路由。"""
        mock_cmd_seq.return_value = EXIT_SUCCESS

        with patch.object(sys, "argv", ["bioflow", "seq", "--input", "test.fasta"]):
            exit_code = main()

        assert exit_code == EXIT_SUCCESS
        mock_cmd_seq.assert_called_once()

    @patch("bioflow.cli.cmd_env_list")
    def test_env_list_routing(self, mock_cmd_env_list):
        """测试 env --list 命令正确路由。"""
        mock_cmd_env_list.return_value = EXIT_SUCCESS

        with patch.object(sys, "argv", ["bioflow", "env", "--list"]):
            exit_code = main()

        assert exit_code == EXIT_SUCCESS
        mock_cmd_env_list.assert_called_once()


# === 退出码标准测试 ===

class TestExitCodes:
    """验证所有退出码符合规范。"""

    def test_exit_code_values(self):
        """确保退出码定义正确。"""
        assert EXIT_SUCCESS == 0
        assert EXIT_RUNTIME_ERROR == 1
        assert EXIT_ARGUMENT_ERROR == 2
        assert EXIT_DEPENDENCY_MISSING == 3
