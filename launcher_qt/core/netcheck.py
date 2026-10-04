"""只读连通性探测：供「测试连接」按钮使用。

只做 TCP 连接与一次轻量 HTTP GET，不发送任何 API Key，
避免把密钥写进日志或产生计费请求。
"""

from __future__ import annotations

import socket
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

TCP_TIMEOUT = 2.5
HTTP_TIMEOUT = 4.0
_DEFAULT_PORTS = {"http": 80, "https": 443, "ws": 80, "wss": 443}


def split_url(url: str) -> tuple[str, str, int, str]:
    """把 URL 拆成 (scheme, host, port, path)。"""
    raw = (url or "").strip()
    if "://" not in raw:
        raw = "http://" + raw
    parts = urlsplit(raw)
    scheme = (parts.scheme or "http").lower()
    host = parts.hostname or ""
    port = parts.port or _DEFAULT_PORTS.get(scheme, 80)
    return scheme, host, int(port), parts.path or "/"


def tcp_check(host: str, port: int, timeout: float = TCP_TIMEOUT) -> tuple[bool, str]:
    """尝试建立 TCP 连接。"""
    if not host:
        return False, "地址为空"
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"TCP {host}:{port} 可连接"
    except socket.gaierror:
        return False, f"无法解析主机名 {host}"
    except socket.timeout:
        return False, f"连接 {host}:{port} 超时"
    except OSError as exc:
        return False, f"连接 {host}:{port} 失败：{exc}"


def http_probe(url: str, timeout: float = HTTP_TIMEOUT) -> tuple[bool, str]:
    """发一次 GET，任何 HTTP 状态码都算「服务在线」。"""
    request = Request(url, headers={"User-Agent": "Open-LLM-VTuber-Launcher"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - 用户自己的地址
            return True, f"HTTP {response.status}"
    except HTTPError as exc:
        return True, f"HTTP {exc.code}（服务在线）"
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        return False, f"HTTP 请求失败：{reason}"
    except Exception as exc:  # noqa: BLE001
        return False, f"HTTP 请求失败：{exc}"


def check_url(url: str) -> tuple[bool, str]:
    """先 TCP 后 HTTP 地探测一个服务地址。"""
    scheme, host, port, path = split_url(url)
    ok, message = tcp_check(host, port)
    if not ok:
        return False, message
    if scheme not in ("http", "https"):
        return True, message
    target = url if "://" in url else f"{scheme}://{host}:{port}{path}"
    http_ok, http_message = http_probe(target)
    if http_ok:
        return True, f"{message} · {http_message}"
    return True, f"{message}（HTTP 探测未通过：{http_message}）"


def check_file(path: str) -> tuple[bool, str]:
    if not path:
        return False, "未填写路径"
    target = Path(path)
    if target.is_dir():
        return True, f"目录存在：{target}"
    if target.exists():
        return True, f"文件存在：{target}"
    return False, f"路径不存在：{target}"


__all__ = ["check_file", "check_url", "http_probe", "split_url", "tcp_check"]
