"""
ui/panel_tools.py

Sol panel: Takım seçimi (T10 … T71).
Seçilen takım sarı ile vurgulanır ve tool_selected sinyali yayınlanır.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QButtonGroup, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from code_generator import TOOLS


class ToolsPanel(QWidget):
    """Sol kenar – takım seçim paneli."""
    tool_selected = Signal(str)   # 'T30' gibi

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(155)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._selected: str = ''
        self._buttons: dict = {}
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 6, 4, 6)
        outer.setSpacing(3)

        title = QLabel('🔧 TAKIM')
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Segoe UI', 12, QFont.Bold))
        title.setStyleSheet('color:#f8c12f; letter-spacing:1px;')
        outer.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet('color:#444;')
        outer.addWidget(line)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        for tool_id, info in TOOLS.items():
            dia = info['dia']
            tip = info['tip']
            label = f"{tool_id}  ∅{dia}mm" if dia else f"{tool_id}  –"
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setToolTip(f"{tool_id} — {tip}\nÇap: {dia} mm  Boy: {info['len']} mm")
            btn.setStyleSheet(self._btn_style(False))
            btn.clicked.connect(lambda checked, t=tool_id: self._on_tool(t))
            self._btn_group.addButton(btn)
            self._buttons[tool_id] = btn
            outer.addWidget(btn)

        outer.addStretch()

        # Seçim bilgisi
        self._lbl_info = QLabel('Seçili: –')
        self._lbl_info.setAlignment(Qt.AlignCenter)
        self._lbl_info.setStyleSheet('color:#aaa; font-size:11px;')
        self._lbl_info.setWordWrap(True)
        outer.addWidget(self._lbl_info)

    def _on_tool(self, tool_id: str):
        self._selected = tool_id
        info = TOOLS[tool_id]
        self._lbl_info.setText(f'{tool_id}\n{info["tip"]}')
        for tid, btn in self._buttons.items():
            btn.setStyleSheet(self._btn_style(tid == tool_id))
        self.tool_selected.emit(tool_id)

    @staticmethod
    def _btn_style(active: bool) -> str:
        if active:
            return (
                'QPushButton { background:#f8c12f; color:#111; border-radius:5px;'
                ' font-weight:bold; font-size:12px; }'
                'QPushButton:hover { background:#ffd84d; }'
            )
        return (
            'QPushButton { background:#2e2e42; color:#ccc; border:1px solid #444;'
            ' border-radius:5px; font-size:12px; }'
            'QPushButton:hover { background:#3a3a55; }'
        )

    @property
    def selected_tool(self) -> str:
        return self._selected
