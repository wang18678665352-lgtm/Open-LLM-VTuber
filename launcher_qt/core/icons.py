"""矢量图标：用 QPainter 现场绘制，无需外部图片资源，任意缩放都清晰。

所有图标都在 24x24 的逻辑网格上作画，再按目标尺寸缩放，因此在高 DPI
（125% / 150% 缩放）下依然是锐利的矢量效果，而不是被拉伸的位图。
"""

from __future__ import annotations

import math
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

GRID = 24.0
STROKE = 1.85


# ---------------------------------------------------------------------------
# 绘图工具
# ---------------------------------------------------------------------------
def _dot(painter: QPainter, x: float, y: float, radius: float) -> None:
    painter.save()
    painter.setBrush(painter.pen().color())
    painter.drawEllipse(QPointF(x, y), radius, radius)
    painter.restore()


def _polyline(painter: QPainter, points: list[tuple[float, float]]) -> None:
    painter.drawPolyline([QPointF(x, y) for x, y in points])


def _tray(painter: QPainter) -> None:
    """下载/上传图标共用的底部托盘。"""
    path = QPainterPath()
    path.moveTo(4.6, 15.2)
    path.lineTo(4.6, 18.2)
    path.quadTo(4.6, 20.3, 6.7, 20.3)
    path.lineTo(17.3, 20.3)
    path.quadTo(19.4, 20.3, 19.4, 18.2)
    path.lineTo(19.4, 15.2)
    painter.drawPath(path)


# ---------------------------------------------------------------------------
# 图标定义
# ---------------------------------------------------------------------------
def _play(painter: QPainter) -> None:
    painter.save()
    painter.setBrush(painter.pen().color())
    path = QPainterPath()
    path.moveTo(7.8, 5.4)
    path.lineTo(18.4, 12.0)
    path.lineTo(7.8, 18.6)
    path.closeSubpath()
    painter.drawPath(path)
    painter.restore()


def _stop(painter: QPainter) -> None:
    painter.save()
    painter.setBrush(painter.pen().color())
    painter.drawRoundedRect(QRectF(7.2, 7.2, 9.6, 9.6), 2.6, 2.6)
    painter.restore()


def _sliders(painter: QPainter) -> None:
    for y, knob in ((6.6, 9.6), (12.0, 15.4), (17.4, 8.6)):
        gap = 2.3
        painter.drawLine(QPointF(3.6, y), QPointF(knob - gap, y))
        painter.drawLine(QPointF(knob + gap, y), QPointF(20.4, y))
        painter.drawEllipse(QPointF(knob, y), 2.0, 2.0)


def _branch(painter: QPainter) -> None:
    painter.drawLine(QPointF(6.6, 8.7), QPointF(6.6, 15.4))
    path = QPainterPath()
    path.moveTo(17.4, 10.7)
    path.cubicTo(17.4, 14.9, 13.6, 15.8, 8.8, 15.8)
    painter.drawPath(path)
    _dot(painter, 6.6, 6.1, 2.1)
    _dot(painter, 6.6, 18.0, 2.1)
    _dot(painter, 17.4, 8.6, 2.1)


def _scan(painter: QPainter) -> None:
    painter.drawEllipse(QPointF(10.6, 10.6), 5.8, 5.8)
    painter.drawLine(QPointF(14.9, 14.9), QPointF(19.6, 19.6))
    _polyline(
        painter,
        [(7.7, 10.8), (9.3, 10.8), (10.4, 8.3), (11.7, 12.8), (12.7, 10.8), (13.5, 10.8)],
    )


def _info(painter: QPainter) -> None:
    painter.drawEllipse(QPointF(12.0, 12.0), 8.2, 8.2)
    _dot(painter, 12.0, 8.1, 1.15)
    painter.drawLine(QPointF(12.0, 11.1), QPointF(12.0, 16.3))


def _folder(painter: QPainter) -> None:
    painter.drawRoundedRect(QRectF(3.6, 6.4, 16.8, 13.2), 2.4, 2.4)
    painter.drawLine(QPointF(3.6, 10.5), QPointF(20.4, 10.5))


def _file(painter: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(6.7, 3.8)
    path.lineTo(13.5, 3.8)
    path.lineTo(18.3, 8.6)
    path.lineTo(18.3, 20.2)
    path.lineTo(6.7, 20.2)
    path.closeSubpath()
    painter.drawPath(path)
    _polyline(painter, [(13.5, 3.8), (13.5, 8.6), (18.3, 8.6)])
    painter.drawLine(QPointF(9.7, 13.0), QPointF(15.3, 13.0))
    painter.drawLine(QPointF(9.7, 16.4), QPointF(15.3, 16.4))


def _globe(painter: QPainter) -> None:
    painter.drawEllipse(QPointF(12.0, 12.0), 8.2, 8.2)
    painter.drawEllipse(QRectF(8.2, 3.8, 7.6, 16.4))
    painter.drawLine(QPointF(3.8, 12.0), QPointF(20.2, 12.0))


def _external(painter: QPainter) -> None:
    _polyline(painter, [(13.3, 4.7), (19.3, 4.7), (19.3, 10.7)])
    painter.drawLine(QPointF(19.3, 4.7), QPointF(11.7, 12.3))
    path = QPainterPath()
    path.moveTo(17.5, 14.5)
    path.lineTo(17.5, 18.3)
    path.quadTo(17.5, 20.1, 15.7, 20.1)
    path.lineTo(5.9, 20.1)
    path.quadTo(4.1, 20.1, 4.1, 18.3)
    path.lineTo(4.1, 8.5)
    path.quadTo(4.1, 6.7, 5.9, 6.7)
    path.lineTo(9.7, 6.7)
    painter.drawPath(path)


def _terminal(painter: QPainter) -> None:
    painter.drawRoundedRect(QRectF(3.2, 4.9, 17.6, 14.2), 2.6, 2.6)
    _polyline(painter, [(7.3, 9.7), (10.0, 12.2), (7.3, 14.7)])
    painter.drawLine(QPointF(12.6, 15.1), QPointF(16.7, 15.1))


def _trash(painter: QPainter) -> None:
    painter.drawLine(QPointF(4.4, 6.9), QPointF(19.6, 6.9))
    _polyline(painter, [(9.4, 6.9), (9.4, 5.2), (14.6, 5.2), (14.6, 6.9)])
    path = QPainterPath()
    path.moveTo(6.4, 6.9)
    path.lineTo(7.3, 19.0)
    path.quadTo(7.4, 20.4, 8.8, 20.4)
    path.lineTo(15.2, 20.4)
    path.quadTo(16.6, 20.4, 16.7, 19.0)
    path.lineTo(17.6, 6.9)
    painter.drawPath(path)
    painter.drawLine(QPointF(10.4, 10.4), QPointF(10.7, 17.1))
    painter.drawLine(QPointF(13.6, 10.4), QPointF(13.3, 17.1))


def _refresh(painter: QPainter) -> None:
    painter.drawArc(QRectF(4.6, 4.6, 14.8, 14.8), 45 * 16, 270 * 16)
    angle = math.radians(45.0)
    tip = QPointF(12.0 + 7.4 * math.cos(angle), 12.0 - 7.4 * math.sin(angle))
    painter.save()
    painter.setBrush(painter.pen().color())
    path = QPainterPath()
    path.moveTo(tip.x() + 0.4, tip.y() - 1.4)
    path.lineTo(tip.x() - 2.9, tip.y() + 0.2)
    path.lineTo(tip.x() + 0.3, tip.y() + 3.1)
    path.closeSubpath()
    painter.drawPath(path)
    painter.restore()


def _download(painter: QPainter) -> None:
    painter.drawLine(QPointF(12.0, 3.6), QPointF(12.0, 14.2))
    _polyline(painter, [(7.6, 9.8), (12.0, 14.2), (16.4, 9.8)])
    _tray(painter)


def _upload(painter: QPainter) -> None:
    painter.drawLine(QPointF(12.0, 14.2), QPointF(12.0, 3.6))
    _polyline(painter, [(7.6, 8.0), (12.0, 3.6), (16.4, 8.0)])
    _tray(painter)


def _package(painter: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(12.0, 3.6)
    path.lineTo(20.2, 8.1)
    path.lineTo(20.2, 15.9)
    path.lineTo(12.0, 20.4)
    path.lineTo(3.8, 15.9)
    path.lineTo(3.8, 8.1)
    path.closeSubpath()
    painter.drawPath(path)
    painter.drawLine(QPointF(3.8, 8.1), QPointF(12.0, 12.6))
    painter.drawLine(QPointF(20.2, 8.1), QPointF(12.0, 12.6))
    painter.drawLine(QPointF(12.0, 12.6), QPointF(12.0, 20.4))


def _book(painter: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(4.0, 5.7)
    path.quadTo(8.0, 3.7, 12.0, 5.7)
    path.quadTo(16.0, 3.7, 20.0, 5.7)
    path.lineTo(20.0, 17.7)
    path.quadTo(16.0, 15.7, 12.0, 17.7)
    path.quadTo(8.0, 15.7, 4.0, 17.7)
    path.closeSubpath()
    painter.drawPath(path)
    painter.drawLine(QPointF(12.0, 5.7), QPointF(12.0, 17.7))


def _code(painter: QPainter) -> None:
    _polyline(painter, [(8.4, 7.6), (4.2, 12.0), (8.4, 16.4)])
    _polyline(painter, [(15.6, 7.6), (19.8, 12.0), (15.6, 16.4)])
    painter.drawLine(QPointF(13.6, 4.9), QPointF(10.4, 19.1))


def _power(painter: QPainter) -> None:
    painter.drawArc(QRectF(4.6, 5.2, 14.8, 14.8), -60 * 16, 300 * 16)
    painter.drawLine(QPointF(12.0, 3.6), QPointF(12.0, 10.4))


def _heart(painter: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(12.0, 19.6)
    path.cubicTo(3.6, 14.2, 4.4, 6.4, 8.8, 5.4)
    path.cubicTo(10.9, 4.9, 12.0, 6.6, 12.0, 6.6)
    path.cubicTo(12.0, 6.6, 13.1, 4.9, 15.2, 5.4)
    path.cubicTo(19.6, 6.4, 20.4, 14.2, 12.0, 19.6)
    painter.drawPath(path)


_DRAWERS = {
    "play": _play,
    "stop": _stop,
    "settings": _sliders,
    "branch": _branch,
    "scan": _scan,
    "info": _info,
    "folder": _folder,
    "file": _file,
    "globe": _globe,
    "external": _external,
    "terminal": _terminal,
    "trash": _trash,
    "refresh": _refresh,
    "download": _download,
    "upload": _upload,
    "package": _package,
    "book": _book,
    "code": _code,
    "power": _power,
    "heart": _heart,
}


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------
def _color_key(value) -> str:
    """把 QColor / 调色板键值统一成可哈希的颜色字符串（供 lru_cache 使用）。"""
    if isinstance(value, QColor):
        return value.name(QColor.NameFormat.HexArgb)
    return str(value)


@lru_cache(maxsize=512)
def _pixmap_cached(name: str, size: int, color: str) -> QPixmap:
    drawer = _DRAWERS.get(name)
    canvas = QPixmap(size, size)
    canvas.fill(Qt.GlobalColor.transparent)
    if drawer is None:
        return canvas
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.scale(size / GRID, size / GRID)
    pen = QPen(QColor(color))
    pen.setWidthF(STROKE)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    try:
        drawer(painter)
    finally:
        painter.end()
    return canvas


def pixmap(name: str, size: int = 20, color="#e8e8f2") -> QPixmap:
    """返回绘制好的图标位图（结果按名称/尺寸/颜色缓存）。

    color 可以是颜色字符串（#rrggbb / rgba(...)），也可以是 QColor。
    """
    return _pixmap_cached(name, int(size), _color_key(color))


def icon(name: str, *, color="#e8e8f2", size: int = 20) -> QIcon:
    """返回可直接给按钮/菜单使用的 QIcon。"""
    return QIcon(pixmap(name, size, color))


def apply_icon(widget, name: str, *, color="#e8e8f2", size: int = 18) -> None:
    """给按钮等控件设置图标。"""
    widget.setIcon(icon(name, color=color, size=size))
    widget.setIconSize(pixmap(name, size, color).size())


def cached_pixmap_str(name: str, size: int, color="#e8e8f2") -> str:
    """调试/测试用：确认图标被成功绘制（空图标会返回空字符串）。"""
    canvas = pixmap(name, size, color)
    return "" if canvas.isNull() else f"{name}:{canvas.width()}x{canvas.height()}"
