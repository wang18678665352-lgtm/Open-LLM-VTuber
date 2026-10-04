"""conf.yaml 读写与启动器本地设置。

写回 conf.yaml 时优先使用 ruamel.yaml（保留注释与排版），
若运行环境缺少该库则退化为定点正则替换。
"""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import MutableMapping
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


def _plain(value: Any) -> Any:
    """把 ruamel 的 CommentedMap/CommentedSeq 递归转换成普通 dict/list。"""
    if isinstance(value, MutableMapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def load_conf() -> dict[str, Any]:
    """把 conf.yaml 读成普通 dict（解析失败时返回空 dict）。"""
    if not CONF_PATH.exists():
        return {}
    try:
        text = CONF_PATH.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe", pure=True)
        data = yaml.load(text)
    except ImportError:
        return _parse_simple_yaml(text)
    except Exception:  # noqa: BLE001 - YAML 语法问题不应让界面崩掉
        return _parse_simple_yaml(text)
    return data if isinstance(data, dict) else {}


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """没有 ruamel.yaml 时的极简 YAML 读取（仅支持缩进映射与标量）。"""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw
        hash_pos = raw.find(" #")
        if hash_pos != -1:
            line = raw[:hash_pos]
        line = line.rstrip()
        key, sep, value = line.strip().partition(":")
        if not sep or key.startswith("-"):
            continue
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        value = value.strip()
        if value == "":
            child: dict[str, Any] = {}
            parent[key.strip()] = child
            stack.append((indent, child))
        else:
            parent[key.strip()] = _scalar(value)
    return root


def _scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in ("null", "~"):
        return None
    if lowered in ("true", "false"):
        return lowered == "true"
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [_scalar(item.strip()) for item in inner.split(",")] if inner else []
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def conf_get_path(dotted: str, default: Any = None) -> Any:
    """按任意深度的路径读取 conf.yaml，例如 ``character_config.tts_config.tts_model``。"""
    node: Any = load_conf()
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return default
    return _plain(node)


def conf_get_dict(dotted: str) -> dict[str, Any]:
    """读取某个配置节点下的所有键值（用于填充表单）。"""
    value = conf_get_path(dotted, {})
    return value if isinstance(value, dict) else {}


def _backup_conf() -> None:
    if CONF_PATH.exists() and not CONF_BAK_PATH.exists():
        try:
            shutil.copy2(CONF_PATH, CONF_BAK_PATH)
        except OSError:
            pass


def conf_set(updates: dict[str, Any]) -> tuple[bool, str]:
    """把 ``{"system_config.port": 12393}`` 形式的更新写回 conf.yaml，保留注释。

    路径支持任意深度，例如
    ``character_config.tts_config.fish_speech_tts.api_key``。

    写入顺序：① 定点行编辑（只改目标行，文件其余部分逐字节不动）
    ② ruamel.yaml 重写（会重排版式，但语义安全）③ 两级路径的定点正则替换。
    """
    if not CONF_PATH.exists():
        return False, "conf.yaml 不存在"
    try:
        text = CONF_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        return False, str(exc)

    _backup_conf()

    try:
        edited = _conf_set_lines(text, updates)
    except _PathNotFound:
        edited = None
    if edited == text:
        # 目标值与文件里的值完全一致：不写盘，也就不会产生任何格式改动
        return True, "值与 conf.yaml 一致，未修改文件"
    if edited is not None and _verify_update(edited, updates, text):
        return _write_conf(edited, "已保存")
    return _conf_set_ruamel(text, updates)


def _write_conf(text: str, message: str) -> tuple[bool, str]:
    try:
        with open(CONF_PATH, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
    except OSError as exc:
        return False, str(exc)
    return True, message


class _PathNotFound(Exception):
    """定点行编辑无法定位目标路径（需要新增多级结构）。"""


_MAP_LINE_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<key>[A-Za-z0-9_][A-Za-z0-9_.\-]*):(?P<rest>.*)$")

_BLOCK_SCALARS = ("|", "|-", "|+", ">", ">-", ">+")

_UNSAFE_PLAIN = set("-?:,[]{}#&*!|>'\"%@`")


def _split_comment(rest: str) -> tuple[str, str]:
    """把 ``' value # 注释'`` 拆成 (值部分, 注释部分)，引号内的 # 不算注释。"""
    quote = ""
    for index, char in enumerate(rest):
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in "'\"":
            quote = char
            continue
        if char == "#" and (index == 0 or rest[index - 1] in " \t"):
            return rest[:index], rest[index:]
    return rest, ""


def _strip_scalar(raw: str) -> str:
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


def _index_paths(lines: list[str]) -> dict[str, int]:
    """扫描出 ``点分路径 -> 行号`` 的索引（跳过注释与块标量正文）。"""
    index: dict[str, int] = {}
    stack: list[tuple[int, str]] = []
    in_block = -1
    for number, line in enumerate(lines):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" \t"))
        if in_block >= 0:
            if line.lstrip().startswith("#") or indent > in_block:
                continue
            in_block = -1
        if line.lstrip().startswith("#"):
            continue
        match = _MAP_LINE_RE.match(line)
        if not match:
            continue
        key = match.group("key")
        while stack and stack[-1][0] >= indent:
            stack.pop()
        path = ".".join([item[1] for item in stack] + [key])
        index.setdefault(path, number)
        if _strip_scalar(_split_comment(match.group("rest"))[0]) in _BLOCK_SCALARS:
            in_block = indent
            continue
        stack.append((indent, key))
    return index


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _child_indent_step(lines: list[str], index: dict[str, int], parent: str) -> int:
    """推断子键相对父键的缩进量（默认 2）。"""
    parent_line = index.get(parent)
    if parent_line is None:
        return 2
    parent_indent = _indent_of(lines[parent_line])
    for number in range(parent_line + 1, len(lines)):
        line = lines[number]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = _indent_of(line)
        if indent <= parent_indent:
            return 2
        return max(indent - parent_indent, 1)
    return 2


def _insert_at(lines: list[str], start: int, indent: int) -> int:
    """返回父映射块内适合插入新子键的位置（跳过块尾的空行与注释）。"""
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if not line.strip():
            end += 1
            continue
        if _indent_of(line) <= indent and not line.lstrip().startswith("#"):
            break
        end += 1
    while end - 1 > start:
        previous = lines[end - 1]
        if previous.strip() and not previous.lstrip().startswith("#"):
            break
        end -= 1
    return end


def _format_value(value: Any, raw_old: str | None) -> str:
    """按原值的写法把新值格式化成 YAML 标量（尽量沿用原有引号与大小写风格）。

    ``raw_old`` 为 None 表示这是新增的键，没有历史写法可参考。
    """
    old = "" if raw_old is None else _strip_scalar(raw_old)
    if value is None:
        if raw_old is not None and old in ("~", "null", "Null", "NULL"):
            return old
        if raw_old is not None and raw_old.strip() == "":
            return ""
        return "null"
    if isinstance(value, bool):
        if old in ("True", "False"):
            return "True" if value else "False"
        if old in ("true", "false"):
            return "true" if value else "false"
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    text = str(value)
    if "\n" in text or "\r" in text:
        return json.dumps(text, ensure_ascii=False)
    trimmed = "" if raw_old is None else raw_old.strip()
    quote = trimmed[0] if len(trimmed) >= 2 and trimmed[0] == trimmed[-1] and trimmed[0] in "'\"" else ""
    if quote == '"':
        return json.dumps(text, ensure_ascii=False)
    if quote == "'" or _needs_quotes(text):
        return "'" + text.replace("'", "''") + "'"
    return text


def _needs_quotes(text: str) -> bool:
    if text == "" or text != text.strip():
        return True
    if text[0] in _UNSAFE_PLAIN:
        return True
    if ": " in text or " #" in text or "\t" in text:
        return True
    if text.lower() in ("null", "~", "true", "false", "yes", "no", "on", "off"):
        return True
    try:
        float(text)
    except ValueError:
        return False
    return True


def _same(current: Any, value: Any) -> bool:
    """判断 conf.yaml 中已有的值是否与新值等价（用于「值没变就别动文件」）。"""
    if isinstance(current, bool) or isinstance(value, bool):
        return isinstance(current, bool) and isinstance(value, bool) and current == value
    if current == value:
        return True
    if isinstance(current, (int, float)) and isinstance(value, (int, float)):
        return float(current) == float(value)
    return False


def _emit_block(key: str, value: Any, indent: int, step: int, comment: str = "") -> list[str]:
    """把 dict/list 值展开成缩进块（用于替换原有的同名块）。"""
    prefix = " " * indent
    if isinstance(value, dict):
        if not value:
            return [f"{prefix}{key}: {{}}{comment}"]
        lines = [f"{prefix}{key}:{comment}"]
        for child_key, child_value in value.items():
            lines.extend(_emit_block(str(child_key), child_value, indent + step, step))
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{prefix}{key}: []{comment}"]
        lines = [f"{prefix}{key}:{comment}"]
        for item in value:
            if isinstance(item, (dict, list)):
                sub = _emit_block("-", item, indent + step, step)
                first = sub[0]
                lines.append(first.replace("-:", "-", 1))
                lines.extend(sub[1:])
            else:
                lines.append(" " * (indent + step) + f"- {_format_value(item, None)}")
        return lines
    return [f"{prefix}{key}: {_format_value(value, None)}{comment}"]


def _conf_set_lines(text: str, updates: dict[str, Any]) -> str:
    """定点行编辑：只改写命中的键所在行，其余行原样保留。"""
    newline = "\r\n" if "\r\n" in text else "\n"
    trailing = text.endswith(("\n", "\r\n"))
    lines = text.splitlines()
    index = _index_paths(lines)
    parsed = _parse_any(text)

    for dotted, value in updates.items():
        parts = [part for part in dotted.split(".") if part]
        if not parts:
            raise _PathNotFound(dotted)

        if parts[0] not in index:
            # 全新的顶层段：追加到文件末尾（同样只增不改）
            additions = [f"{parts[0]}:"]
            indent = 2
            for part in parts[1:-1]:
                additions.append(" " * indent + f"{part}:")
                indent += 2
            additions.extend(_emit_block(parts[-1], value, indent, 2))
            if lines and lines[-1].strip():
                lines.append("")
            lines.extend(additions)
            index = _index_paths(lines)
            parsed = _parse_any(newline.join(lines))
            continue

        if dotted in index:
            number = index[dotted]
            match = _MAP_LINE_RE.match(lines[number])
            if match is None:
                raise _PathNotFound(dotted)
            if _same(_dig(parsed, dotted), value):
                continue  # 值没有变化：整行原样保留，避免任何无谓改写
            indent = len(match.group("indent"))
            raw_value, comment = _split_comment(match.group("rest"))
            if isinstance(value, (dict, list)):
                step = _child_indent_step(lines, index, dotted) or 2
                lines[number : _insert_at(lines, number, indent)] = _emit_block(
                    match.group("key"), value, indent, step, comment
                )
            else:
                prefix = raw_value[: len(raw_value) - len(raw_value.lstrip(" \t"))]
                suffix = raw_value[len(raw_value.rstrip(" \t")) :]
                value_text = _format_value(value, raw_value)
                lines[number] = (
                    f"{match.group('indent')}{match.group('key')}:"
                    f"{prefix}{value_text}{suffix}{comment}"
                )
            index = _index_paths(lines)
            parsed = _parse_any(newline.join(lines))
            continue

        # 逐级向下：父级必须存在，缺失的中间层就地补出来
        parent_parts: list[str] = []
        parent_line = -1
        for part in parts[:-1]:
            candidate = ".".join([*parent_parts, part])
            if candidate not in index:
                break
            parent_parts.append(part)
            parent_line = index[candidate]
        if parent_line < 0:
            raise _PathNotFound(dotted)

        parent = ".".join(parent_parts)
        parent_indent = _indent_of(lines[parent_line])
        step = _child_indent_step(lines, index, parent)
        position = _insert_at(lines, parent_line, parent_indent)
        indent = parent_indent + step
        additions: list[str] = []
        for part in parts[len(parent_parts) : -1]:
            additions.append(" " * indent + f"{part}:")
            indent += step
        additions.extend(_emit_block(parts[-1], value, indent, step))
        lines[position:position] = additions
        index = _index_paths(lines)
        parsed = _parse_any(newline.join(lines))

    out = newline.join(lines)
    return out + (newline if trailing else "")


def _flatten(data: Any, prefix: str = "") -> dict[str, Any]:
    """把嵌套配置展开成 {点分路径: 值}（映射本身也算一项，列表按整体比较）。"""
    items: dict[str, Any] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            items[path] = value
            if isinstance(value, dict):
                items.update(_flatten(value, path))
    return items


def _touched(path: str, updates: dict[str, Any]) -> bool:
    """该路径是否落在本次改动的影响范围内（自身、祖先或后代）。"""
    for dotted in updates:
        if path == dotted or path.startswith(f"{dotted}.") or dotted.startswith(f"{path}."):
            return True
    return False


def _verify_update(text: str, updates: dict[str, Any], original: str) -> bool:
    """确认定点编辑后的内容能被正确解析、目标键等于期望值、其余部分逐项未变。"""
    before = _parse_any(original)
    after = _parse_any(text)
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    for dotted, expected in updates.items():
        if not _same(_dig(after, dotted), expected):
            return False
    for dotted, value in _flatten(before).items():
        if _touched(dotted, updates):
            continue
        if not _same(_dig(after, dotted), value):
            return False
    return True


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dig(data: Any, dotted: str) -> Any:
    node = data
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def _parse_any(text: str) -> Any:
    try:
        from ruamel.yaml import YAML

        return YAML(typ="safe", pure=True).load(text)
    except ImportError:
        return _parse_simple_yaml(text)
    except Exception:  # noqa: BLE001
        return None


def _conf_set_ruamel(text: str, updates: dict[str, Any]) -> tuple[bool, str]:
    """退化方案一：用 ruamel.yaml 重写整个文件（保留注释，但会重排版式）。"""
    try:
        from ruamel.yaml import YAML
    except ImportError:
        return _conf_set_regex(text, updates)

    try:
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.allow_unicode = True
        yaml.width = 4096
        yaml.indent(mapping=2, sequence=4, offset=2)
        data = yaml.load(text)
        if data is None:
            return False, "conf.yaml 内容为空或无法解析"
        for dotted, value in updates.items():
            parts = [part for part in dotted.split(".") if part]
            if not parts:
                continue
            node = data
            for part in parts[:-1]:
                child = node.get(part) if hasattr(node, "get") else None
                if not isinstance(child, MutableMapping):
                    node[part] = {}
                    child = node[part]
                node = child
            node[parts[-1]] = value
        with open(CONF_PATH, "w", encoding="utf-8", newline="") as handle:
            yaml.dump(data, handle)
        return True, "已保存"
    except Exception as exc:  # noqa: BLE001
        return False, f"写入 conf.yaml 失败: {exc}"


def _conf_set_regex(text: str, updates: dict[str, Any]) -> tuple[bool, str]:
    """没有 ruamel.yaml 时的退化方案：按行定点替换（仅支持两级路径）。"""
    new_text = text
    for dotted, value in updates.items():
        parts = [part for part in dotted.split(".") if part]
        if len(parts) != 2:
            return False, f"当前环境缺少 ruamel.yaml，无法写入多级配置项: {dotted}"
        key = parts[-1]
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
    host = str(conf_get_path("system_config.host", None) or conf_get("host", "localhost") or "localhost")
    port = str(conf_get_path("system_config.port", None) or conf_get("port", "12393") or "12393")
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
