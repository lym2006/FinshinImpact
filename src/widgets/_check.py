# src/widgets/_check.py
"""对勾勾选框

- 无填充形态，勾选态在描边方框内绘制对勾
- 配色取公共调色板，引导层与主界面共用
"""

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QPainter,
    QPaintEvent,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QCheckBox

from theme import PALETTE

# 对勾三顶点在框内的比例坐标，(起笔, 拐点, 收笔)
_CHECK_POINTS = ((0.22, 0.55), (0.42, 0.74), (0.78, 0.28))

# 方框描边与对勾共用线宽
_CHECK_STROKE = 2


class TickedCheckBox(QCheckBox):
    """描边方框内绘对勾的勾选框

    - 边长与文字间距由构造参数传入，颜色取自调色板
    """

    def __init__(self, size: int, spacing: int) -> None:
        """注入指示器边长与文字间距"""
        super().__init__()
        self._size = size
        self._spacing = spacing

    def sizeHint(self) -> QSize:  # noqa: N802
        """按自绘边长与间距给出最小尺寸"""
        hint = super().sizeHint()
        text_width = QFontMetrics(self.font()).horizontalAdvance(self.text())
        own_width = self._size + self._spacing + text_width
        return QSize(max(hint.width(), own_width), max(hint.height(), self._size))

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """按勾选与禁用状态绘制方框、对勾与标签文字"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        inset = _CHECK_STROKE / 2
        top = (self.height() - self._size) / 2
        box = QRectF(0, top, self._size, self._size).adjusted(
            inset, inset, -inset, -inset
        )

        if not self.isEnabled():
            edge = PALETTE.disabled_color
        elif self.isChecked():
            edge = PALETTE.color
        else:
            edge = PALETTE.border_color
        pen = QPen(QColor(edge), _CHECK_STROKE)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawRoundedRect(box, PALETTE.radius, PALETTE.radius)

        if self.isChecked():
            points = [
                QPointF(box.left() + box.width() * fx, box.top() + box.height() * fy)
                for fx, fy in _CHECK_POINTS
            ]
            painter.drawPolyline(QPolygonF(points))

        if self.text():
            text_color = (
                PALETTE.disabled_color if not self.isEnabled() else PALETTE.color
            )
            painter.setPen(QColor(text_color))
            text_rect = QRectF(
                self._size + self._spacing,
                0,
                self.width() - self._size - self._spacing,
                self.height(),
            )
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self.text(),
            )
        painter.end()
