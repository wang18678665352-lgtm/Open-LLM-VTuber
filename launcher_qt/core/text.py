"""控制台文本处理：ANSI 清理与日志级别着色。"""

from __future__ import annotations

import re

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")
LEVEL_RE = re.compile(r"\|\s*(TRACE|DEBUG|INFO|SUCCESS|WARNING|ERROR|CRITICAL)\s*\|")

# 日志级别 -> 调色板键
LEVEL_KEYS = {
    "TRACE": "debug",
    "DEBUG": "debug",
    "INFO": "ok",
    "SUCCESS": "info",
    "WARNING": "warn",
    "ERROR": "err",
    "CRITICAL": "err",
}


def strip_ansi(text: str) -> str:
    """去掉日志中的 ANSI 转义序列。"""
    return ANSI_RE.sub("", text)


def level_of_line(line: str) -> str:
    """返回一行日志对应的调色板键：launcher / debug / ok / info / warn / err / text。"""
    if line.startswith("[启动器]") or line.startswith(">>>"):
        return "launcher"
    match = LEVEL_RE.search(line)
    if match:
        return LEVEL_KEYS.get(match.group(1), "text")
    return "text"
