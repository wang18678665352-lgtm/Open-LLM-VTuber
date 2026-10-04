"""conf.yaml 读写与启动器本地设置。

写回 conf.yaml 时优先使用 ruamel.yaml（保留注释与排版），
若运行环境缺少该库则退化为定点正则替换。
"""

from __future__ import annotations

import json
import re
import shutil
from typing import Any

from .paths import CONF_BAK_PATH, CONF_PATH, SETTINGS_PATH

SETTINGS_DEFAULTS: dict[str, bool] = {
    "verbose": False,
    "hf_mirror": False,
    "open_browser": True,
    "autoscroll": True,
    "minimize_to_tray": False,
}


def conf_get(key: str, default: str = "") -> str:
    """从 conf.yaml 中按行正则读取键值（去掉引号与行尾注释）。"""
    if not CONF_PATH.exists():
        return default
    try:
        text = CONF_PATH.read_text(encoding="utf-8")
    except OSError:
        return default
    match = re.search(
        rf"(?m)^[ \t]*{re.escape(key)}[ \t]*:[ \t]*['\"]?([^'\"\n#]+)", text
    )
    return match.group(1).strip() if match else default


def _backup_conf() -> None:
    if CONF_PATH.exists() and not CONF_BAK_PATH.exists():
        try:
            shutil.copy2(CONF_PATH, CONF_BAK_PATH)
        except OSError:
            pass


def conf_set(updates: dict[str, Any]) -> tuple[bool, str]:
    """把 ``{"system_config.port": 12393}`` 形式的更新写回 conf.yaml，保留注释。"""
    if not CONF_PATH.exists():
        return False, "conf.yaml 不存在"
    try:
        text = CONF_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        return False, str(exc)

    _backup_conf()

    try:
        from ruamel.yaml import YAML
    except ImportError:
        return _conf_set_regex(text, updates)

    try:
        yaml = YAML()
        yaml.preserve_quotes = True
        data = yaml.load(text)
        if data is None:
            return False, "conf.yaml 内容为空或无法解析"
        for dotted, value in updates.items():
            section, key = dotted.split(".", 1)
            if data.get(section) is None:
                data[section] = {}
            data[section][key] = value
        with open(CONF_PATH, "w", encoding="utf-8", newline="") as handle:
            yaml.dump(data, handle)
        return True, "已保存"
    except Exception as exc:  # noqa: BLE001
        return False, f"写入 conf.yaml 失败: {exc}"


def _conf_set_regex(text: str, updates: dict[str, Any]) -> tuple[bool, str]:
    """没有 ruamel.yaml 时的退化方案：按行定点替换。"""
    new_text = text
    for dotted, value in updates.items():
        _, key = dotted.split(".", 1)
        if isinstance(value, bool):
            pattern = rf"(?m)^([ \t]*{re.escape(key)}[ \t]*:[ \t]*)\S+"
            new_text, count = re.subn(
                pattern, rf"\g<1>{'true' if value else 'false'}", new_text, count=1
            )
        elif isinstance(value, int):
            pattern = rf"(?m)^([ \t]*{re.escape(key)}[ \t]*:[ \t]*)\d+"
            new_text, count = re.subn(pattern, rf"\g<1>{value}", new_text, count=1)
        else:
            pattern = rf"(?m)^([ \t]*{re.escape(key)}[ \t]*:[ \t]*)['\"]?[^'\"\n#]*['\"]?"
            new_text, count = re.subn(
                pattern, lambda m: f"{m.group(1)}'{value}'", new_text, count=1
            )
        if count == 0:
            return False, f"未能在 conf.yaml 中找到配置项: {dotted}"
    try:
        with open(CONF_PATH, "w", encoding="utf-8", newline="") as handle:
            handle.write(new_text)
    except OSError as exc:
        return False, str(exc)
    return True, "已保存（正则模式）"


def server_url() -> str:
    """读取 conf.yaml 的 host/port，拼出可访问地址。"""
    host = conf_get("host", "localhost") or "localhost"
    port = conf_get("port", "12393") or "12393"
    connect_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    return f"http://{connect_host}:{port}"


def load_settings() -> dict[str, bool]:
    settings = dict(SETTINGS_DEFAULTS)
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            settings.update(
                {key: bool(value) for key, value in data.items() if key in settings}
            )
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    payload = {key: bool(value) for key, value in settings.items()}
    try:
        SETTINGS_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass
