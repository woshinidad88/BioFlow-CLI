"""BioFlow-CLI 核心模块测试"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bioflow.bio_tasks import _format_fasta, _parse_env_int, _parse_fasta, _wrap_sequence
from bioflow.i18n import _get_config_dir, load_config, set_language, t


# === Fixtures ===

@pytest.fixture()
def isolated_config(tmp_path, monkeypatch):
    """将所有配置路径重定向到临时目录，完全隔离文件系统副作用。"""
    import bioflow.i18n as mod
    monkeypatch.setattr(mod, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(mod, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(mod, "_LEGACY_CONFIG_PATH", tmp_path / "legacy_config.json")
    monkeypatch.setattr(mod, "_migration_done", False)
    return tmp_path


# === FASTA 解析 ===

class TestParseFasta:
    def test_normal_multi_seq(self):
        text = ">seq1\nATCG\nGGCC\n>seq2\nTTTT"
        records = _parse_fasta(text)
        assert len(records) == 2
        assert records[0] == (">seq1", "ATCGGGCC")
        assert records[1] == (">seq2", "TTTT")

    def test_empty_input(self):
        assert _parse_fasta("") == []

    def test_no_header(self):
        assert _parse_fasta("ATCG\nGGCC") == []

    def test_single_seq(self):
        records = _parse_fasta(">only\nACGT")
        assert len(records) == 1
        assert records[0] == (">only", "ACGT")


# === 序列换行 ===

class TestWrapSequence:
    def test_normal(self):
        assert _wrap_sequence("AABBCCDD", 4) == "AABB\nCCDD"

    def test_width_one(self):
        assert _wrap_sequence("ABC", 1) == "A\nB\nC"

    def test_empty(self):
        assert _wrap_sequence("", 80) == ""


# === FASTA 格式化 ===

class TestFormatFasta:
    def test_uppercase_conversion(self):
        output = _format_fasta([(">s", "atcg")], width=80)
        assert "ATCG" in output

    def test_wrap_width(self):
        output = _format_fasta([(">s", "AABBCCDD")], width=4)
        lines = output.strip().splitlines()
        assert lines[0] == ">s"
        assert lines[1] == "AABB"
        assert lines[2] == "CCDD"


# === 环境变量安全解析 ===

class TestParseEnvInt:
    def test_valid(self, monkeypatch):
        monkeypatch.setenv("TEST_INT_VAR", "200")
        assert _parse_env_int("TEST_INT_VAR", 500) == 200

    def test_invalid_fallback(self, monkeypatch):
        monkeypatch.setenv("TEST_INT_VAR", "abc")
        assert _parse_env_int("TEST_INT_VAR", 500) == 500

    def test_missing_fallback(self):
        assert _parse_env_int("NONEXISTENT_VAR_XYZ", 42) == 42


# === 国际化 ===

class TestI18n:
    def test_translate_en(self, isolated_config):
        set_language("en")
        assert "Install" in t("menu_env")

    def test_translate_zh(self, isolated_config):
        set_language("zh")
        assert "安装" in t("menu_env")

    def test_missing_key_returns_key(self, isolated_config):
        set_language("en")  # 显式设置，避免依赖全局状态
        assert t("nonexistent_key_xyz") == "nonexistent_key_xyz"

    def test_format_kwargs(self, isolated_config):
        set_language("en")
        result = t("env_installing", tool="BWA")
        assert "BWA" in result

    def test_save_and_load_roundtrip(self, isolated_config):
        set_language("zh")
        import bioflow.i18n as mod
        cfg = mod.load_config()
        assert cfg["language"] == "zh"

    def test_load_config_corrupted(self, isolated_config):
        import bioflow.i18n as mod
        mod.CONFIG_PATH.write_text("{invalid json", encoding="utf-8")
        assert mod.load_config() == {}


# === 旧配置迁移 ===

class TestMigration:
    def test_migration_moves_legacy(self, isolated_config):
        import bioflow.i18n as mod
        # 在旧路径写入配置
        mod._LEGACY_CONFIG_PATH.write_text('{"language":"zh"}', encoding="utf-8")
        cfg = mod.load_config()
        assert cfg["language"] == "zh"
        assert not mod._LEGACY_CONFIG_PATH.exists()  # 旧文件已移走
        assert mod.CONFIG_PATH.exists()  # 新文件已存在

    def test_no_migration_if_new_exists(self, isolated_config):
        import bioflow.i18n as mod
        mod.CONFIG_PATH.write_text('{"language":"en"}', encoding="utf-8")
        mod._LEGACY_CONFIG_PATH.write_text('{"language":"zh"}', encoding="utf-8")
        cfg = mod.load_config()
        assert cfg["language"] == "en"  # 新文件优先
        assert mod._LEGACY_CONFIG_PATH.exists()  # 旧文件未被动


# === 跨平台配置路径 ===

class TestConfigDir:
    @patch("bioflow.i18n.platform.system", return_value="Darwin")
    def test_macos(self, _mock):
        p = _get_config_dir()
        assert "Library" in str(p) and "Application Support" in str(p)

    @patch("bioflow.i18n.platform.system", return_value="Linux")
    @patch.dict("os.environ", {"XDG_CONFIG_HOME": "/custom/xdg"})
    def test_linux_xdg(self, _mock):
        p = _get_config_dir()
        assert str(p) == "/custom/xdg/bioflow"

    @patch("bioflow.i18n.platform.system", return_value="Linux")
    @patch.dict("os.environ", {}, clear=True)
    def test_linux_default(self, _mock):
        p = _get_config_dir()
        assert ".config/bioflow" in str(p)

    @patch("bioflow.i18n.platform.system", return_value="Windows")
    @patch.dict("os.environ", {"APPDATA": "C:\\Users\\test\\AppData\\Roaming"})
    def test_windows(self, _mock):
        p = _get_config_dir()
        assert "AppData" in str(p)


# === Conda 预检 ===

class TestCondaCheck:
    @patch("bioflow.env_manager.shutil.which", return_value=None)
    def test_conda_missing(self, _mock):
        from bioflow.env_manager import _check_conda
        assert _check_conda() is False

    @patch("bioflow.env_manager.shutil.which", return_value="/usr/bin/conda")
    def test_conda_present(self, _mock):
        from bioflow.env_manager import _check_conda
        assert _check_conda() is True