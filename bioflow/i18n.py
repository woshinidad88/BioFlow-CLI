"""BioFlow-CLI 国际化核心模块"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
from pathlib import Path
from typing import Any

from bioflow.locales import LOCALES

logger = logging.getLogger("bioflow")


# === 跨平台配置路径 ===

def _get_config_dir() -> Path:
    """根据操作系统返回原生配置目录。"""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "bioflow"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "bioflow"
        return Path.home() / ".bioflow"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            return Path(xdg) / "bioflow"
        return Path.home() / ".config" / "bioflow"


CONFIG_DIR = _get_config_dir()
CONFIG_PATH = CONFIG_DIR / "config.json"

# 旧版配置路径（项目根目录），用于一次性迁移
_LEGACY_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

_current_lang: str = "en"
_migration_done: bool = False


def _migrate_legacy_config() -> None:
    """若旧路径存在 config.json 且新路径不存在，执行一次性迁移。"""
    if _LEGACY_CONFIG_PATH.exists() and not CONFIG_PATH.exists():
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            shutil.move(str(_LEGACY_CONFIG_PATH), str(CONFIG_PATH))
            logger.info("Migrated config from %s to %s", _LEGACY_CONFIG_PATH, CONFIG_PATH)
        except OSError as exc:
            logger.warning("Config migration failed: %s", exc)


def load_config() -> dict[str, Any]:
    """加载配置文件，损坏时降级为空字典。首次调用时触发旧配置迁移。"""
    global _migration_done
    if not _migration_done:
        _migrate_legacy_config()
        _migration_done = True
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("config.json is corrupted (%s), resetting to defaults.", exc)
    except OSError as exc:
        logger.warning("Cannot read config (%s), using defaults.", exc)
    return {}


def save_config(cfg: dict[str, Any]) -> None:
    """保存配置到用户目录。写入失败时记录警告而非崩溃。"""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as exc:
        logger.warning("Cannot save config (%s), preference will not persist.", exc)


def init_language() -> str:
    """初始化语言设置，返回当前语言代码。"""
    global _current_lang
    cfg = load_config()
    _current_lang = cfg.get("language", "en")
    return _current_lang


def set_language(lang: str) -> None:
    """设置并持久化语言偏好。"""
    global _current_lang
    if lang not in LOCALES:
        raise ValueError(f"Unsupported language: {lang}")
    _current_lang = lang
    cfg = load_config()
    cfg["language"] = lang
    save_config(cfg)


def get_language() -> str:
    """获取当前语言代码。"""
    return _current_lang


def t(key: str, **kwargs: Any) -> str:
    """根据当前语言获取翻译文本，支持 format 参数。"""
    strings = LOCALES.get(_current_lang, LOCALES["en"])
    text = strings.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text