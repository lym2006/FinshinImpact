# src/ui/_primitives/_marquee.py
"""循环滚动的文字标签

- 文字画在真正的 QLabel 上，配色与字号仍随样式表走
- 子控件天然被父件裁掉，滚出右缘的那段自己消失
- 同一段文字摆两份，第一份滚到尽头时第二份正好接上头
- 放得下的行不动画，静态左对齐
"""

from PySide6.QtCore import QSize, Qt, QVariantAnimation
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QLabel, QWidget

# 一圈里两份文字之间的空档，一句滚完到下一句接上之间留这段呼吸
_LOOP_GAP = 60

# 滚动速度按每秒像素给，字越长一圈越久，快慢观感一致
_ROLL_SPEED = 40


class MarqueeLabel(QWidget):
    """放不下就从右往左循环滚的文字标签"""

    def __init__(self, text: str) -> None:
        """摆两只同文标签准备接力，全文另挂一份在悬浮提示上"""
        super().__init__()
        self._roll = 0
        self._tags = [self._make_tag(text) for _ in range(2)]
        self.setToolTip(text)

        self._anim = QVariantAnimation(self)
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._shift)

    def _make_tag(self, text: str) -> QLabel:
        """文字挂进本体，按内容量出自带宽度，超出部分由父件裁掉"""
        tag = QLabel(text, self)
        tag.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        tag.adjustSize()
        return tag

    def sizeHint(self) -> QSize:  # noqa: N802
        """宽度不向布局要价，列给多宽就滚多宽"""
        return QSize(0, self._tags[0].sizeHint().height())

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        """列宽一变重算要不要滚、一圈走多久"""
        super().resizeEvent(event)
        self._refit()

    def _shift(self, value: int) -> None:
        """两份文字同向挪，间距恒为一圈行程"""
        middle = (self.height() - self._tags[0].height()) // 2
        for offset, tag in enumerate(self._tags):
            tag.move(value + offset * self._roll, middle)

    def _refit(self) -> None:
        """放得下即停，放不下按行程算时长后开滚"""
        for tag in self._tags:
            tag.adjustSize()
        width = self._tags[0].width()
        if not width or width <= self.width():
            self._anim.stop()
            self._roll = 0
            self._shift(0)
            return
        self._roll = width + _LOOP_GAP
        self._anim.setDuration(self._roll * 1000 // _ROLL_SPEED)
        self._anim.setStartValue(0)
        self._anim.setEndValue(-self._roll)
        self._anim.start()
