"""
ui/panel_operations.py  – İşlem seçim paneli + parametre popup (v3)

Yeni tasarım:
  • Ana panel (sağ sütun): TAM kompakt — scroll yok, kaydırmaya gerek kalmadan sığar.
    İçerik: Program No / Profil Boyu · P1-P7 butonları · Takım etiketi · Kod gösterimi
  • ParamPopup: P koduna tıklanınca butona yakın (soluna) açılan kayan pencere.
    İçerik: DXF Tıkla · X/Y/Z · Parametreler · Kodu Üret · Kod · MDB Kaydet
    Kapatma: ✕ butonu ya da Esc tuşu.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QButtonGroup, QSizePolicy, QDoubleSpinBox,
    QFormLayout, QGroupBox, QComboBox, QSpinBox, QApplication,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Signal, Qt, QSize, QPoint
from PySide6.QtGui import QFont, QColor

from code_generator import OPERATION_DESC, TOOLS, get_operation_params, build_code
from p_code_icons import get_p_code_icon

# P3 su tahliye sabit değerleri
P3_INNER = dict(tool='T60', L=25, D=8,  x_offset=150)
P3_OUTER = dict(tool='T10', L=25, D=40, x_offset=70)


# ═══════════════════════════════════════════════════════════════
#  ParamPopup — P koduna tıklanınca açılan parametre penceresi
# ═══════════════════════════════════════════════════════════════

class ParamPopup(QWidget):
    """Butona yakın açılan parametre giriş penceresi."""

    pick_requested = Signal()
    code_ready     = Signal(str)
    tool_change    = Signal(str)
    save_to_mdb    = Signal(int, str)

    def __init__(self):
        # Qt.Tool → ana pencerede gösterilir; FramelessWindowHint → kenarsız
        # WindowStaysOnTopHint → DXF tıklaması sırasında da görünür kalır
        super().__init__(None,
                         Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedWidth(270)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._op             = ''
        self._selected_tool  = ''
        self._last_code      = ''
        self._param_inputs   = {}
        self._prog_no_ref    = None   # ana paneldeki QSpinBox referansı
        self._length_ref     = None   # ana paneldeki QDoubleSpinBox referansı

        self._build_ui()

    # ── UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        # Dış çerçeve (gölge için şeffaf arka plan + iç container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)  # gölge için boşluk

        self._container = QFrame()
        self._container.setObjectName('PopupContainer')
        self._container.setStyleSheet('''
            #PopupContainer {
                background: #22223a;
                border: 1px solid #55608a;
                border-radius: 8px;
            }
        ''')
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 180))
        self._container.setGraphicsEffect(shadow)
        outer.addWidget(self._container)

        lay = QVBoxLayout(self._container)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(5)

        # ── Başlık ────────────────────────────────────────
        hdr = QHBoxLayout(); hdr.setSpacing(4)
        self._lbl_icon = QLabel()
        self._lbl_icon.setFixedSize(42, 28)
        hdr.addWidget(self._lbl_icon)
        self._lbl_title = QLabel()
        self._lbl_title.setStyleSheet(
            'color:#56cfe1;font-weight:bold;font-size:12px;')
        hdr.addWidget(self._lbl_title, 1)
        btn_x = QPushButton('✕')
        btn_x.setFixedSize(20, 20)
        btn_x.setStyleSheet(
            'QPushButton{background:transparent;color:#666;border:none;font-size:13px;}'
            'QPushButton:hover{color:#fff;}')
        btn_x.clicked.connect(self.hide)
        hdr.addWidget(btn_x)
        lay.addLayout(hdr)

        sep0 = QFrame(); sep0.setFrameShape(QFrame.HLine)
        sep0.setStyleSheet('color:#444;')
        lay.addWidget(sep0)

        # ── DXF Tıkla ─────────────────────────────────────
        self._btn_pick = QPushButton('📍  DXF\'e Tıkla  (Y, Z al)')
        self._btn_pick.setFixedHeight(28)
        self._btn_pick.setStyleSheet(
            'QPushButton{background:#1a3a7a;color:#8ac;border-radius:4px;font-size:11px;}'
            'QPushButton:hover{background:#1e4a9a;color:white;}')
        self._btn_pick.clicked.connect(self._on_pick)
        lay.addWidget(self._btn_pick)

        # ── X / Y / Z ─────────────────────────────────────
        coord_lay = QFormLayout()
        coord_lay.setSpacing(3)
        coord_lay.setContentsMargins(0, 0, 0, 0)
        coord_lay.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._ed_x = QDoubleSpinBox()
        self._ed_x.setRange(-999999, 999999); self._ed_x.setDecimals(1)
        self._ed_x.setSuffix(' mm'); self._ed_x.setFixedHeight(24)
        self._ed_x.setStyleSheet(self._sp_style())

        self._ed_y = QDoubleSpinBox()
        self._ed_y.setRange(-9999999, 9999999); self._ed_y.setDecimals(1)
        self._ed_y.setSuffix(' mm'); self._ed_y.setReadOnly(True)
        self._ed_y.setFixedHeight(24)
        self._ed_y.setStyleSheet(self._sp_style(ro=True))

        self._ed_z = QDoubleSpinBox()
        self._ed_z.setRange(-9999999, 9999999); self._ed_z.setDecimals(1)
        self._ed_z.setSuffix(' mm'); self._ed_z.setReadOnly(True)
        self._ed_z.setFixedHeight(24)
        self._ed_z.setStyleSheet(self._sp_style(ro=True))

        coord_lay.addRow(self._form_lbl('X:'), self._ed_x)
        coord_lay.addRow(self._form_lbl('Y:'), self._ed_y)
        coord_lay.addRow(self._form_lbl('Z:'), self._ed_z)
        lay.addLayout(coord_lay)

        # ── P3 özel: iç/dış tahliye ───────────────────────
        self._p3_box = QWidget()
        p3l = QVBoxLayout(self._p3_box)
        p3l.setContentsMargins(0, 0, 0, 0); p3l.setSpacing(3)
        sep_p3 = QFrame(); sep_p3.setFrameShape(QFrame.HLine)
        sep_p3.setStyleSheet('color:#3a3a55;')
        p3l.addWidget(sep_p3)
        self._cb_drain = QComboBox()
        self._cb_drain.addItem('İç Tahliye  (T60 · L=25 · D=8)',  'inner')
        self._cb_drain.addItem('Dış Tahliye  (T10 · L=25 · D=40)', 'outer')
        self._cb_drain.setFixedHeight(24)
        self._cb_drain.setStyleSheet(
            'QComboBox{background:#2e2e42;color:#eee;border:1px solid #555;'
            'border-radius:3px;font-size:11px;padding:2px 4px;}'
            'QComboBox QAbstractItemView{background:#2e2e42;color:#eee;}')
        self._cb_drain.currentIndexChanged.connect(self._on_drain_changed)
        self._lbl_p3 = QLabel()
        self._lbl_p3.setStyleSheet('color:#56cfe1;font-size:10px;')
        self._lbl_p3.setWordWrap(True)
        p3l.addWidget(self._cb_drain)
        p3l.addWidget(self._lbl_p3)
        self._p3_box.setVisible(False)
        lay.addWidget(self._p3_box)

        # ── Parametreler (dinamik) ─────────────────────────
        sep_p = QFrame(); sep_p.setFrameShape(QFrame.HLine)
        sep_p.setStyleSheet('color:#3a3a55;')
        lay.addWidget(sep_p)

        self._param_lay = QFormLayout()
        self._param_lay.setSpacing(3)
        self._param_lay.setContentsMargins(0, 0, 0, 0)
        self._param_lay.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addLayout(self._param_lay)

        # ── Hint ──────────────────────────────────────────
        self._lbl_hint = QLabel('DXF\'e tıklayarak Y, Z alın')
        self._lbl_hint.setAlignment(Qt.AlignCenter)
        self._lbl_hint.setStyleSheet('color:#f8c12f;font-size:10px;')
        lay.addWidget(self._lbl_hint)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet('color:#444;')
        lay.addWidget(sep2)

        # ── Kodu Üret ─────────────────────────────────────
        self._btn_gen = QPushButton('✅  Kodu Üret')
        self._btn_gen.setFixedHeight(32)
        self._btn_gen.setStyleSheet(
            'QPushButton{background:#1a5c1a;color:white;border-radius:5px;'
            'font-size:12px;font-weight:bold;}'
            'QPushButton:hover{background:#227022;}')
        self._btn_gen.clicked.connect(self._on_generate)
        lay.addWidget(self._btn_gen)

        # ── Kod gösterimi ─────────────────────────────────
        self._lbl_code = QLabel()
        self._lbl_code.setWordWrap(True)
        self._lbl_code.setMinimumHeight(34)
        self._lbl_code.setStyleSheet(
            'background:#0d1117;color:#56cfe1;'
            'font-family:"Courier New",monospace;font-size:11px;font-weight:bold;'
            'padding:5px;border-radius:4px;border:1px solid #333;')
        self._lbl_code.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self._lbl_code)

        # ── MDB Kaydet ─────────────────────────────────────
        self._btn_mdb = QPushButton('💾  MDB\'ye Kaydet')
        self._btn_mdb.setEnabled(False)
        self._btn_mdb.setFixedHeight(28)
        self._btn_mdb.setStyleSheet(
            'QPushButton{background:#1a3a6a;color:white;border-radius:4px;font-size:11px;}'
            'QPushButton:hover{background:#25509a;}'
            'QPushButton:disabled{background:#252535;color:#555;}')
        self._btn_mdb.clicked.connect(self._on_save_mdb)
        lay.addWidget(self._btn_mdb)

    # ── Dışarıdan API ────────────────────────────────────────

    def open_for(self, op: str, tool: str, prog_no_sp, length_sp,
                 btn_top_left_global: QPoint):
        """Popup'u hazırla, konumlandır ve göster."""
        self._op            = op
        self._selected_tool = tool
        self._prog_no_ref   = prog_no_sp
        self._length_ref    = length_sp

        # İkon + başlık
        pm = __import__('p_code_icons', fromlist=['get_p_code_pixmap']).get_p_code_pixmap(op)
        self._lbl_icon.setPixmap(pm)
        self._lbl_title.setText(f'{op}  —  {OPERATION_DESC.get(op, op)}')

        # P3 özel
        is_p3 = (op == 'P3')
        self._p3_box.setVisible(is_p3)
        if is_p3:
            self._on_drain_changed()
        else:
            self._rebuild_params(op)

        # Sıfırla
        self._lbl_hint.setText('DXF\'e tıklayarak Y, Z alın')
        self._lbl_hint.setStyleSheet('color:#f8c12f;font-size:10px;')
        self._lbl_code.setText('')
        self._btn_mdb.setEnabled(False)
        self._last_code = ''

        # Boyutu güncelle
        self.adjustSize()

        # Konumlandır: butona göre sola
        px = btn_top_left_global.x() - self.width() - 6
        py = btn_top_left_global.y()
        scr = QApplication.primaryScreen().availableGeometry()
        if px < scr.left():
            px = btn_top_left_global.x() + 10   # sola sığmıyorsa sağa
        if py + self.height() > scr.bottom():
            py = scr.bottom() - self.height() - 6
        if py < scr.top():
            py = scr.top() + 6

        self.move(px, py)
        self.show()
        self.raise_()

    def set_yz(self, y: float, z: float):
        """DXF tıklamasından gelen Y/Z değerlerini yazar."""
        self._ed_y.setValue(y)
        self._ed_z.setValue(z)
        self._lbl_hint.setText(f'✅  Y={y:.1f}   Z={z:.1f}  alındı')
        self._lbl_hint.setStyleSheet('color:#44cc88;font-size:10px;')

    # ── Olaylar ─────────────────────────────────────────────

    def _rebuild_params(self, op: str):
        while self._param_lay.rowCount():
            self._param_lay.removeRow(0)
        self._param_inputs.clear()
        for prm in get_operation_params(op):
            sp = QDoubleSpinBox()
            sp.setRange(0, 999999); sp.setDecimals(0)
            sp.setSuffix(' mm'); sp.setFixedHeight(24)
            sp.setStyleSheet(self._sp_style())
            sp.setToolTip(prm['label'])
            self._param_inputs[prm['key']] = sp
            self._param_lay.addRow(self._form_lbl(prm['label'] + ':'), sp)

    def _on_drain_changed(self, *_):
        drain = self._cb_drain.currentData()
        cfg   = P3_INNER if drain == 'inner' else P3_OUTER
        label = 'İç Tahliye' if drain == 'inner' else 'Dış Tahliye'
        self._selected_tool = cfg['tool']
        self.tool_change.emit(cfg['tool'])
        while self._param_lay.rowCount():
            self._param_lay.removeRow(0)
        self._param_inputs.clear()
        for key, val in [('L', cfg['L']), ('D', cfg['D'])]:
            sp = QDoubleSpinBox()
            sp.setRange(0, 999999); sp.setDecimals(0)
            sp.setValue(val); sp.setSuffix(' mm'); sp.setFixedHeight(24)
            sp.setStyleSheet(self._sp_style())
            self._param_inputs[key] = sp
            self._param_lay.addRow(self._form_lbl(f'{key}:'), sp)
        self._lbl_p3.setText(
            f'{label} · Takım={cfg["tool"]} · L={cfg["L"]} · D={cfg["D"]}\n'
            f'X₁=Boy−{cfg["x_offset"]}  X₂={cfg["x_offset"]}')

    def _on_pick(self):
        self.pick_requested.emit()

    def _on_generate(self):
        if not self._selected_tool:
            self._lbl_code.setText('⚠ Takım seçin (sol panel)')
            return
        prog_no = self._prog_no_ref.value() if self._prog_no_ref else 1
        if self._op == 'P3':
            code = self._gen_p3()
            if not code:
                return
        else:
            params = {k: sp.value() * 10 for k, sp in self._param_inputs.items()}
            code = build_code(
                operation=self._op,
                tool=self._selected_tool,
                x=self._ed_x.value() * 10,
                y=self._ed_y.value() * 10,
                z=self._ed_z.value() * 10,
                params=params,
            )
        self._last_code = code
        self._lbl_code.setText(f'#{prog_no}  →  {code}')
        self._btn_mdb.setEnabled(True)
        self.code_ready.emit(code)

    def _gen_p3(self) -> str:
        from PySide6.QtWidgets import QMessageBox
        drain      = self._cb_drain.currentData()
        cfg        = P3_INNER if drain == 'inner' else P3_OUTER
        length_x10 = int(self._length_ref.value()) if self._length_ref else 0
        if length_x10 == 0:
            QMessageBox.warning(self, 'Uyarı', '"Boy" alanına profil boyunu ×10 girin.')
            return ''
        offset = cfg['x_offset']; tool = cfg['tool']
        yi = int(round(self._ed_y.value() * 10))
        zi = int(round(self._ed_z.value() * 10))
        x1 = max(0, length_x10 - offset); x2 = offset
        L  = int(self._param_inputs['L'].value() * 10) if 'L' in self._param_inputs else cfg['L'] * 10
        D  = int(self._param_inputs['D'].value() * 10) if 'D' in self._param_inputs else cfg['D'] * 10
        return f'P3{tool}X{x1}Y{yi}Z{zi}L{L}D{D}//P3{tool}X{x2}Y{yi}Z{zi}L{L}D{D}//'

    def _on_save_mdb(self):
        if not self._last_code or not self._prog_no_ref:
            return
        self.save_to_mdb.emit(self._prog_no_ref.value(), self._last_code)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    @staticmethod
    def _form_lbl(text: str) -> 'QLabel':
        """Form layout satır etiketi — okunabilir açık renk."""
        lbl = QLabel(text)
        lbl.setStyleSheet('color:#c8cfdd;font-size:11px;')
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return lbl

    @staticmethod
    def _sp_style(ro: bool = False) -> str:
        bg = '#181828' if ro else '#2a2a3e'
        return (
            f'QDoubleSpinBox{{background:{bg};color:#eee;border:1px solid #555;'
            f'border-radius:3px;padding:2px 4px;font-size:11px;}}')


# ═══════════════════════════════════════════════════════════════
#  OperationsPanel — kompakt sağ panel (scroll yok)
# ═══════════════════════════════════════════════════════════════

class OperationsPanel(QWidget):
    operation_selected  = Signal(str)
    pick_requested      = Signal()
    code_ready          = Signal(str)
    tool_change         = Signal(str)
    save_to_mdb         = Signal(int, str)
    program_no_changed  = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(285)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self._selected_op   = ''
        self._selected_tool = ''
        self._op_buttons    = {}
        self._last_code     = ''

        self._setup_ui()
        self._setup_popup()

    # ── Popup kurulum ───────────────────────────────────────

    def _setup_popup(self):
        self._popup = ParamPopup()
        self._popup.pick_requested.connect(self.pick_requested)
        self._popup.code_ready.connect(self._on_popup_code)
        self._popup.tool_change.connect(self._on_popup_tool)
        self._popup.save_to_mdb.connect(self.save_to_mdb)

    # ── Dışarıdan API ──────────────────────────────────────

    def set_tool(self, tool: str):
        self._selected_tool = tool
        self._update_tool_lbl()
        if self._popup.isVisible():
            self._popup._selected_tool = tool

    def set_yz_from_click(self, y: float, z: float):
        if self._popup.isVisible():
            self._popup.set_yz(y, z)

    def set_program_no(self, no: int):
        self._sp_prog_no.setValue(no)

    def set_profile_length(self, length_x10: float):
        self._sp_length.setValue(length_x10)

    # ── UI kurulum ─────────────────────────────────────────

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(5, 5, 5, 5)
        lay.setSpacing(4)

        # Başlık
        title = QLabel('⚙  İŞLEMLER')
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 12, QFont.Bold))
        title.setStyleSheet('color:#f8c12f;letter-spacing:1px;padding:2px;')
        lay.addWidget(title)

        sep0 = QFrame(); sep0.setFrameShape(QFrame.HLine)
        sep0.setStyleSheet('color:#444;'); lay.addWidget(sep0)

        # Program No + Profil Boyu (kompakt, etiketsiz satır)
        info_lay = QFormLayout()
        info_lay.setSpacing(3)
        info_lay.setContentsMargins(4, 0, 4, 0)
        info_lay.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._sp_prog_no = QSpinBox()
        self._sp_prog_no.setRange(1, 99999)
        self._sp_prog_no.setValue(1)
        self._sp_prog_no.setFixedHeight(26)
        self._sp_prog_no.setStyleSheet(self._sp_style())
        self._sp_prog_no.setToolTip('Program numarası')
        self._sp_prog_no.valueChanged.connect(lambda v: self.program_no_changed.emit(v))
        info_lay.addRow(self._panel_lbl('Prog No:'), self._sp_prog_no)

        self._sp_length = QDoubleSpinBox()
        self._sp_length.setRange(0, 9999999)
        self._sp_length.setDecimals(0)
        self._sp_length.setSuffix(' ×10mm')
        self._sp_length.setFixedHeight(26)
        self._sp_length.setStyleSheet(self._sp_style())
        self._sp_length.setToolTip('Profil kesim boyu (×10). P3 su tahliye için gerekli.')
        info_lay.addRow(self._panel_lbl('Boy:'), self._sp_length)
        lay.addLayout(info_lay)

        sep1 = QFrame(); sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet('color:#444;'); lay.addWidget(sep1)

        # P kodu butonları
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        for op, desc in OPERATION_DESC.items():
            btn = QPushButton(f'  {op}   {desc}')
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setIconSize(QSize(40, 26))
            btn.setIcon(get_p_code_icon(op))
            btn.setStyleSheet(self._btn_style(False))
            btn.clicked.connect(lambda checked, o=op, b=btn: self._on_operation(o, b))
            self._btn_group.addButton(btn)
            self._op_buttons[op] = btn
            lay.addWidget(btn)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet('color:#333;'); lay.addWidget(sep2)

        # Takım etiketi
        self._lbl_tool = QLabel('Takım:  —')
        self._lbl_tool.setAlignment(Qt.AlignCenter)
        self._lbl_tool.setStyleSheet('color:#888;font-size:11px;padding:1px;')
        lay.addWidget(self._lbl_tool)

        # Son üretilen kod
        self._lbl_code = QLabel()
        self._lbl_code.setWordWrap(True)
        self._lbl_code.setMinimumHeight(36)
        self._lbl_code.setStyleSheet(
            'background:#0d1117;color:#56cfe1;'
            'font-family:"Courier New",monospace;font-size:11px;font-weight:bold;'
            'padding:6px;border-radius:4px;border:1px solid #333;')
        self._lbl_code.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self._lbl_code)

        # MDB kaydet
        self._btn_mdb = QPushButton('💾  MDB\'ye Kaydet')
        self._btn_mdb.setEnabled(False)
        self._btn_mdb.setFixedHeight(30)
        self._btn_mdb.setStyleSheet(
            'QPushButton{background:#1a3a6a;color:white;border-radius:5px;'
            'font-size:12px;font-weight:bold;}'
            'QPushButton:hover{background:#25509a;}'
            'QPushButton:disabled{background:#252535;color:#555;}')
        self._btn_mdb.clicked.connect(self._on_save_mdb)
        lay.addWidget(self._btn_mdb)

        lay.addStretch()

    # ── Olaylar ─────────────────────────────────────────────

    def _on_operation(self, op: str, btn: QPushButton):
        self._selected_op = op
        for o, b in self._op_buttons.items():
            b.setStyleSheet(self._btn_style(o == op))
        self.operation_selected.emit(op)
        # Butona yakın popup aç
        self._popup.open_for(
            op, self._selected_tool,
            self._sp_prog_no, self._sp_length,
            btn.mapToGlobal(QPoint(0, 0))
        )

    def _on_popup_code(self, code: str):
        prog_no = self._sp_prog_no.value()
        self._last_code = code
        self._lbl_code.setText(f'#{prog_no}  →  {code}')
        self._btn_mdb.setEnabled(True)
        self.code_ready.emit(code)

    def _on_popup_tool(self, tool: str):
        self._selected_tool = tool
        self._update_tool_lbl()
        self.tool_change.emit(tool)

    def _on_save_mdb(self):
        from PySide6.QtWidgets import QMessageBox
        if not self._last_code:
            QMessageBox.warning(None, 'Uyarı', 'Önce "Kodu Üret" butonuna basın.')
            return
        self.save_to_mdb.emit(self._sp_prog_no.value(), self._last_code)

    def _update_tool_lbl(self):
        if self._selected_tool:
            info = TOOLS.get(self._selected_tool, {})
            self._lbl_tool.setText(
                f'Takım: {self._selected_tool} — {info.get("tip", "")}')
            self._lbl_tool.setStyleSheet('color:#f8c12f;font-size:11px;padding:1px;')
        else:
            self._lbl_tool.setText('Takım:  —')
            self._lbl_tool.setStyleSheet('color:#888;font-size:11px;padding:1px;')

    # ── Stiller ─────────────────────────────────────────────

    @staticmethod
    def _panel_lbl(text: str) -> 'QLabel':
        """Ana panel form layout etiketi."""
        lbl = QLabel(text)
        lbl.setStyleSheet('color:#c8cfdd;font-size:12px;')
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return lbl

    @staticmethod
    def _btn_style(active: bool) -> str:
        if active:
            return (
                'QPushButton{background:#5a3ea0;color:white;border-radius:5px;'
                'font-weight:bold;font-size:12px;text-align:left;padding-left:8px;}')
        return (
            'QPushButton{background:#2a2a3e;color:#bbb;border:1px solid #444;'
            'border-radius:5px;font-size:12px;text-align:left;padding-left:8px;}'
            'QPushButton:hover{background:#36364e;}')

    @staticmethod
    def _sp_style() -> str:
        return (
            'QDoubleSpinBox{background:#2a2a3e;color:#eee;border:1px solid #555;'
            'border-radius:3px;padding:2px 4px;font-size:12px;}'
            'QSpinBox{background:#2a2a3e;color:#eee;border:1px solid #555;'
            'border-radius:3px;padding:2px 4px;font-size:12px;}')
