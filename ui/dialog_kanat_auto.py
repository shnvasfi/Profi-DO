"""
ui/dialog_kanat_auto.py  –  Kanat Otomatik Kod Üretici

Akış:
  1. Program No → kesim boyu otomatik gelir
  2. Yön seç (ALT/ÜST/SOL/SAĞ)
  3. Her grup için [📍 Tıkla] → dialog gizlenir → DXF'e tıkla → geri döner
     → grup kodu anında üretilir ✅
  4. Bütün gruplardaki kodlar YÖN bazlı gösterilir (alt kısımda)
  5. Bütün yönlerin toplam kodu tek alanda gösterilir
  6. [💾 MDB'ye Kaydet] → hepsini tek seferde yazar
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QGroupBox, QFrame,
    QDoubleSpinBox, QSpinBox, QMessageBox, QWidget,
    QSizePolicy, QTextEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

import os
from kanat_operations import (
    KANAT_GROUPS, SIDES, build_group_code, group_needs_click,
    PROFILE_LABEL, get_groups_for_type, is_type_implemented
)


SIDE_COLOR = {
    'ALT': ('#1f6b1f', '#27c027', '#0d2a0d'),
    'ÜST': ('#1f1f8a', '#3535cc', '#0d0d30'),
    'SOL': ('#7a1f55', '#bb2f88', '#2a0a1e'),
    'SAĞ': ('#7a6a10', '#c0a818', '#2a2405'),
}


class GroupRow(QWidget):
    """Tek bir grup satırı: isim | araç | [📍 Tıkla] | Y/Z | kod"""
    click_requested = Signal(object)   # self referansı

    def __init__(self, group_def: dict, length_x10: int, parent=None):
        super().__init__(parent)
        self._group_def   = group_def
        self._length_x10  = length_x10
        self._done        = False
        self._code        = ''
        self._setup()

    def _setup(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(10)

        # Grup adı
        lbl_name = QLabel(self._group_def['name'])
        lbl_name.setFixedWidth(160)
        lbl_name.setFont(QFont('Arial', 12, QFont.Bold))
        lbl_name.setStyleSheet('color:#f0f0f0;')
        lay.addWidget(lbl_name)

        # Araç bilgisi
        ops = self._group_def['ops']
        tools = list(dict.fromkeys(o['tool'] for o in ops))
        codes = list(dict.fromkeys(o['op']   for o in ops))
        lbl_tool = QLabel(' · '.join(codes) + '  ' + ' '.join(tools))
        lbl_tool.setFixedWidth(110)
        lbl_tool.setStyleSheet('color:#56cfe1; font-size:11px;')
        lay.addWidget(lbl_tool)

        # Tıkla butonu
        nc = group_needs_click(self._group_def)
        if nc['y'] or nc['z']:
            self._btn = QPushButton('📍  Tıkla')
            self._btn.setFixedSize(110, 36)
            self._btn.setStyleSheet(
                'QPushButton{background:#1a4aaa;color:#fff;border-radius:5px;'
                'font-size:12px;font-weight:bold;}'
                'QPushButton:hover{background:#2a5acc;}'
            )
            self._btn.clicked.connect(lambda: self.click_requested.emit(self))
        else:
            self._btn = QPushButton('⚙ Otomatik')
            self._btn.setFixedSize(110, 36)
            self._btn.setStyleSheet(
                'QPushButton{background:#335533;color:#88ee88;border-radius:5px;font-size:11px;}'
            )
            self._btn.setEnabled(False)
        lay.addWidget(self._btn)

        # Y / Z gösterge
        self._lbl_yz = QLabel('—')
        self._lbl_yz.setFixedWidth(160)
        self._lbl_yz.setStyleSheet('color:#888; font-size:11px;')
        lay.addWidget(self._lbl_yz)

        # Kod gösterge
        self._lbl_code = QLabel('(bekliyor)')
        self._lbl_code.setStyleSheet(
            'color:#555; font-family:"Courier New"; font-size:11px;')
        self._lbl_code.setWordWrap(True)
        self._lbl_code.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lay.addWidget(self._lbl_code)

        self.setStyleSheet('background:#1e1e2e; border-bottom:1px solid #2a2a40;')

    # ── Dışarıdan API ────────────────────────────────────

    def set_length(self, v: int):
        self._length_x10 = v

    def generate(self, y_mm: float, z_mm: float):
        self._code = build_group_code(
            self._group_def, self._length_x10, y_mm, z_mm)
        self._done = True
        # Y/Z güncelle
        nc = group_needs_click(self._group_def)
        if nc['y'] and nc['z']:
            self._lbl_yz.setText(f'Y={y_mm:.1f}  Z={z_mm:.1f}')
        elif nc['z']:
            self._lbl_yz.setText(f'Z={z_mm:.1f}')
        else:
            self._lbl_yz.setText('(sabit)')
        self._lbl_yz.setStyleSheet('color:#f8c12f; font-size:11px;')
        # Kodu göster
        preview = self._code[:60] + ('…' if len(self._code) > 60 else '')
        self._lbl_code.setText('✅  ' + preview)
        self._lbl_code.setStyleSheet(
            'color:#44ff88; font-family:"Courier New"; font-size:11px;')
        # Butonu güncelle
        self._btn.setText('✅ Tamam')
        self._btn.setStyleSheet(
            'QPushButton{background:#1a5c1a;color:#88ee88;border-radius:5px;font-size:11px;}'
            'QPushButton:hover{background:#237523;}'
        )

    def generate_auto(self):
        """Tıklama gerektirmeyen gruplar için (SAĞ/Üçlü Kol)."""
        self.generate(0.0, 0.0)

    @property
    def code(self) -> str:
        return self._code

    @property
    def done(self) -> bool:
        return self._done


# ─────────────────────────────────────────────────────────────────

class KanatAutoDialog(QDialog):

    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self._db            = db
        self._pending_row   = None
        self._profile_type  = ''   # MDB'den okunan TYPE ('A', 'B' …)
        self._active_groups = {}   # Aktif profil tipinin işlem grupları

        self._rows:        dict = {s: [] for s in SIDES}
        self._side_codes:  dict = {s: '' for s in SIDES}
        self._all_records: list = []      # DB'deki tüm kayıtlar
        self._filter_order: str = ''      # Seçili ORDER_NO filtresi
        self._selected_prog: int = 0      # Tabloda seçili Program No

        self.setWindowTitle('Profil – Otomatik Kod Üretici')
        self.setMinimumSize(900, 600)
        self._setup_ui()
        self._apply_style()
        self._refresh_records()
        self.showMaximized()   # Her zaman tam ekran açıl

    # ─── UI ───────────────────────────────────────────────

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        # ── Ana splitter: Sol=İşlemler  Sağ=Kayıt Tablosu ─
        from PySide6.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter, 1)

        left_w = QWidget()
        root = QVBoxLayout(left_w)
        root.setContentsMargins(0, 0, 4, 0)
        root.setSpacing(6)
        splitter.addWidget(left_w)

        # ── Başlık ────────────────────────────────────────
        title = QLabel('🔧  Profil – Otomatik Kod Üretici')
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 14, QFont.Bold))
        title.setStyleSheet('color:#f8c12f; background:#252538; border-radius:6px; padding:8px;')
        root.addWidget(title)

        # ── Program No + Profil Boyu ──────────────────────
        top = QHBoxLayout()
        top.setSpacing(16)
        top.addWidget(QLabel('Program No:'))
        self._sp_prog = QSpinBox()
        self._sp_prog.setRange(1, 99999)
        self._sp_prog.setFixedWidth(110)
        self._sp_prog.valueChanged.connect(self._on_prog_changed)
        top.addWidget(self._sp_prog)

        top.addSpacing(20)
        top.addWidget(QLabel('Profil Boyu (×10 mm):'))
        self._sp_length = QDoubleSpinBox()
        self._sp_length.setRange(0, 9999999)
        self._sp_length.setDecimals(0)
        self._sp_length.setFixedWidth(140)
        self._sp_length.valueChanged.connect(self._on_length_changed)
        top.addWidget(self._sp_length)
        self._lbl_mm = QLabel('')
        self._lbl_mm.setStyleSheet('color:#56cfe1; font-size:12px;')
        top.addWidget(self._lbl_mm)

        top.addSpacing(24)
        top.addWidget(QLabel('Profil Tipi:'))

        # Tip gösterge etiketi
        self._lbl_type = QLabel('—')
        self._lbl_type.setFixedWidth(220)
        self._lbl_type.setStyleSheet(
            'color:#f8c12f; font-size:13px; font-weight:bold; padding:2px 6px;'
            ' background:#2a2010; border-radius:4px;')
        top.addWidget(self._lbl_type)

        # Manuel seçim (TYPE boşsa görünür)
        self._cb_type = QComboBox()
        self._cb_type.blockSignals(True)   # Doldurma sırasında sinyal tetiklenmesin
        self._cb_type.addItem('— Seçiniz —', '')
        for k, v in sorted(PROFILE_LABEL.items()):
            self._cb_type.addItem(f'{k} – {v}', k)
        self._cb_type.blockSignals(False)
        self._cb_type.setFixedWidth(220)
        self._cb_type.setVisible(False)
        self._cb_type.currentIndexChanged.connect(self._on_manual_type)
        top.addWidget(self._cb_type)

        # "Değiştir" butonu — her zaman görünür
        self._btn_change_type = QPushButton('✏')
        self._btn_change_type.setFixedSize(30, 30)
        self._btn_change_type.setToolTip('Profil tipini değiştir')
        self._btn_change_type.setStyleSheet(
            'QPushButton{background:#3a3a55;color:#ccc;border-radius:4px;font-size:13px;}'
            'QPushButton:hover{background:#5a3ea0;color:#fff;}'
        )
        self._btn_change_type.clicked.connect(self._show_type_selector)
        top.addWidget(self._btn_change_type)

        top.addStretch()
        top_w = QWidget()
        top_w.setLayout(top)
        top_w.setStyleSheet('background:#252538; border-radius:5px; padding:6px;')
        root.addWidget(top_w)

        # ── Yön butonları ─────────────────────────────────
        side_row = QHBoxLayout()
        side_row.setSpacing(8)
        self._side_btns: dict = {}
        icons = {'ALT': '⬇ ALT', 'ÜST': '⬆ ÜST', 'SOL': '⬅ SOL', 'SAĞ': '➡ SAĞ'}
        for s in SIDES:
            btn = QPushButton(icons[s])
            btn.setCheckable(True)
            btn.setMinimumHeight(42)
            btn.setFont(QFont('Arial', 13, QFont.Bold))
            btn.clicked.connect(lambda _, side=s: self._on_side(side))
            self._side_btns[s] = btn
            side_row.addWidget(btn)
        root.addLayout(side_row)

        # ── Yön durum göstergesi ──────────────────────────
        self._lbl_side_info = QLabel(
            '⬆  Program No girin — yön MDB\'den otomatik gelecek')
        self._lbl_side_info.setAlignment(Qt.AlignCenter)
        self._lbl_side_info.setStyleSheet(
            'color:#888; font-size:12px; background:#1e1e2e;'
            ' padding:5px; border-radius:4px;')
        root.addWidget(self._lbl_side_info)

        # ── İşlem alanı: grup satırları ───────────────────
        self._groups_box = QGroupBox('İşlem Grupları')
        self._groups_box.setStyleSheet(
            'QGroupBox{color:#f8c12f;font-size:12px;font-weight:bold;'
            'border:1px solid #3a3a55;border-radius:6px;margin-top:8px;padding-top:10px;}'
            'QGroupBox::title{subcontrol-origin:margin;left:10px;}')
        self._groups_layout = QVBoxLayout(self._groups_box)
        self._groups_layout.setContentsMargins(0, 6, 0, 6)
        self._groups_layout.setSpacing(0)
        root.addWidget(self._groups_box)

        # ── Yön bazlı kodlar ──────────────────────────────
        side_codes_box = QGroupBox('Yön Bazlı Kodlar')
        side_codes_box.setStyleSheet(
            'QGroupBox{color:#aaa;font-size:12px;font-weight:bold;'
            'border:1px solid #3a3a55;border-radius:6px;margin-top:8px;padding-top:10px;}'
            'QGroupBox::title{subcontrol-origin:margin;left:10px;}')
        sc_lay = QVBoxLayout(side_codes_box)
        sc_lay.setSpacing(4)
        sc_lay.setContentsMargins(8, 6, 8, 6)

        self._side_code_lbls: dict = {}
        for s in SIDES:
            row_w = QHBoxLayout()
            lbl_s = QLabel(f'{s}:')
            lbl_s.setFixedWidth(40)
            bg, fg, _ = SIDE_COLOR[s]
            lbl_s.setStyleSheet(
                f'background:{bg}; color:#fff; font-weight:bold; font-size:12px;'
                f' border-radius:3px; padding:2px 6px;')
            row_w.addWidget(lbl_s)
            lbl_c = QLabel('(boş)')
            lbl_c.setStyleSheet(
                'color:#555; font-family:"Courier New"; font-size:11px;')
            lbl_c.setWordWrap(True)
            lbl_c.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self._side_code_lbls[s] = lbl_c
            row_w.addWidget(lbl_c)
            sc_lay.addLayout(row_w)

        root.addWidget(side_codes_box)

        # (Kayıt tablosu sağ panele taşındı — splitter sağ tarafı)

        # ── Toplam kod ────────────────────────────────────
        total_box = QGroupBox('TOPLAM KOD  (tüm yönler)')
        total_box.setStyleSheet(
            'QGroupBox{color:#f8c12f;font-size:12px;font-weight:bold;'
            'border:2px solid #4a4a22;border-radius:6px;margin-top:8px;padding-top:10px;}'
            'QGroupBox::title{subcontrol-origin:margin;left:10px;}')
        t_lay = QVBoxLayout(total_box)
        t_lay.setContentsMargins(8, 6, 8, 6)
        self._lbl_total = QLabel('(henüz kod yok)')
        self._lbl_total.setWordWrap(True)
        self._lbl_total.setMinimumHeight(50)
        self._lbl_total.setStyleSheet(
            'background:#0b0f1a; color:#5ef0ff; font-family:"Courier New",monospace;'
            'font-size:13px; font-weight:bold; padding:10px; border-radius:5px;')
        self._lbl_total.setTextInteractionFlags(Qt.TextSelectableByMouse)
        t_lay.addWidget(self._lbl_total)
        root.addWidget(total_box)

        # ── Alt butonlar ──────────────────────────────────
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet('color:#3a3a55;'); root.addWidget(sep)

        btn_row = QHBoxLayout()
        self._btn_save = QPushButton('💾  Tüm Kodları MDB\'ye Kaydet')
        self._btn_save.setEnabled(False)
        self._btn_save.setMinimumHeight(46)
        self._btn_save.setFont(QFont('Arial', 13, QFont.Bold))
        self._btn_save.setStyleSheet(
            'QPushButton{background:#1a5c1a;color:#fff;border-radius:6px;font-size:13px;font-weight:bold;}'
            'QPushButton:hover{background:#237523;}'
            'QPushButton:disabled{background:#252535;color:#555;}'
        )
        self._btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self._btn_save)
        btn_row.addStretch()
        btn_close = QPushButton('✖  Kapat')
        btn_close.setMinimumHeight(46); btn_close.setMinimumWidth(100)
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

        # ── SAĞ PANEL: Mevcut Kayıtlar ────────────────────
        right_w = QWidget()
        right_lay = QVBoxLayout(right_w)
        right_lay.setContentsMargins(4, 0, 0, 0)
        right_lay.setSpacing(4)
        splitter.addWidget(right_w)
        splitter.setSizes([900, 380])

        rec_header = QHBoxLayout()
        lbl_rt = QLabel('📋  Mevcut Kayıtlar')
        lbl_rt.setStyleSheet('color:#f8c12f; font-size:13px; font-weight:bold;')
        rec_header.addWidget(lbl_rt, 1)
        self._lbl_rec_count = QLabel('— kayıt')
        self._lbl_rec_count.setStyleSheet('color:#888; font-size:11px;')
        rec_header.addWidget(self._lbl_rec_count)
        btn_ref = QPushButton('↺')
        btn_ref.setFixedSize(28, 28)
        btn_ref.setToolTip('Yenile')
        btn_ref.clicked.connect(self._refresh_records)
        rec_header.addWidget(btn_ref)
        right_lay.addLayout(rec_header)

        # ── Liste Seç butonu ──────────────────────────────
        list_row = QHBoxLayout()
        self._btn_select_list = QPushButton('📂  Liste Seç  (Tümü)')
        self._btn_select_list.setMinimumHeight(32)
        self._btn_select_list.setStyleSheet(
            'QPushButton{background:#1a3a6a;color:#fff;border-radius:5px;font-size:12px;'
            'font-weight:bold;text-align:left;padding-left:8px;}'
            'QPushButton:hover{background:#265098;}')
        self._btn_select_list.clicked.connect(self._on_select_list)
        list_row.addWidget(self._btn_select_list, 1)

        btn_clear_filter = QPushButton('✕')
        btn_clear_filter.setFixedSize(28, 28)
        btn_clear_filter.setToolTip('Filtreyi temizle — tümünü göster')
        btn_clear_filter.setStyleSheet(
            'QPushButton{background:#3a2020;color:#ff8888;border-radius:4px;font-size:12px;}'
            'QPushButton:hover{background:#5a2020;}')
        btn_clear_filter.clicked.connect(self._clear_filter)
        list_row.addWidget(btn_clear_filter)
        right_lay.addLayout(list_row)

        # ── Kodu Düzelt butonu ────────────────────────────
        self._btn_edit_code = QPushButton('✏  Seçili Kaydın Kodunu Düzelt')
        self._btn_edit_code.setMinimumHeight(30)
        self._btn_edit_code.setEnabled(False)
        self._btn_edit_code.setStyleSheet(
            'QPushButton{background:#5a3ea0;color:#fff;border-radius:5px;font-size:12px;}'
            'QPushButton:hover{background:#6e50b8;}'
            'QPushButton:disabled{background:#252535;color:#555;}')
        self._btn_edit_code.clicked.connect(self._on_edit_code)
        right_lay.addWidget(self._btn_edit_code)

        # 5 sütun: Prog#, Yön, Stok, Kod (özet), 👁
        self._rec_table = QTableWidget(0, 5)
        self._rec_table.setHorizontalHeaderLabels(['Prog#', 'Yön', 'Stok', 'Kod (özet)', ''])
        rh = self._rec_table.horizontalHeader()
        rh.setSectionResizeMode(0, QHeaderView.Fixed); self._rec_table.setColumnWidth(0, 46)
        rh.setSectionResizeMode(1, QHeaderView.Fixed); self._rec_table.setColumnWidth(1, 36)
        rh.setSectionResizeMode(2, QHeaderView.Fixed); self._rec_table.setColumnWidth(2, 70)
        rh.setSectionResizeMode(3, QHeaderView.Stretch)
        rh.setSectionResizeMode(4, QHeaderView.Fixed); self._rec_table.setColumnWidth(4, 32)
        self._rec_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._rec_table.setAlternatingRowColors(False)   # Manuel kontrol
        self._rec_table.verticalHeader().setVisible(False)
        self._rec_table.setStyleSheet(
            'QTableWidget{background:#16162a;color:#ffffff;font-size:12px;'
            'gridline-color:#2a2a45;border:1px solid #3a3a55;}'
            'QTableWidget::item{color:#ffffff;padding:3px;background:#16162a;}'
            'QHeaderView::section{background:#252540;color:#f8c12f;font-size:11px;'
            'font-weight:bold;border:none;border-bottom:1px solid #3a3a55;padding:4px;}'
        )
        self._rec_table.cellClicked.connect(self._on_rec_cell_clicked)
        self._rec_table.cellPressed.connect(self._on_rec_row_selected)
        right_lay.addWidget(self._rec_table, 1)

        # Yön düzelt ipucu
        lbl_tip = QLabel('💡 Yön sütununa tıkla → değiştir')
        lbl_tip.setStyleSheet('color:#888; font-size:10px;')
        right_lay.addWidget(lbl_tip)

        # ── Robot Yakalama Güncelleme bölümü ─────────────
        robot_box = QGroupBox('🤖  Robot Yakalama Noktası Güncelle')
        robot_box.setStyleSheet(
            'QGroupBox{color:#f8c12f;font-size:11px;font-weight:bold;'
            'border:1px solid #3a3a55;border-radius:5px;margin-top:8px;padding-top:10px;}'
            'QGroupBox::title{subcontrol-origin:margin;left:8px;}'
        )
        robot_lay = QVBoxLayout(robot_box)
        robot_lay.setSpacing(4)
        robot_lay.setContentsMargins(6, 8, 6, 6)

        # Mevcut değerler göstergesi
        robot_info_row = QHBoxLayout()
        self._lbl_robot_cur = QLabel('Seçili kayıt: —')
        self._lbl_robot_cur.setStyleSheet('color:#888; font-size:11px;')
        self._lbl_robot_cur.setWordWrap(True)
        robot_info_row.addWidget(self._lbl_robot_cur)
        robot_lay.addLayout(robot_info_row)

        # Pick butonu
        self._btn_robot_pick = QPushButton('📍  DXF\'ten Yeni Nokta Al')
        self._btn_robot_pick.setEnabled(False)
        self._btn_robot_pick.setMinimumHeight(34)
        self._btn_robot_pick.setStyleSheet(
            'QPushButton{background:#1a4aaa;color:#fff;border-radius:5px;font-size:12px;font-weight:bold;}'
            'QPushButton:hover{background:#2a5acc;}'
            'QPushButton:disabled{background:#252535;color:#555;}'
        )
        self._btn_robot_pick.clicked.connect(self._pick_robot)
        robot_lay.addWidget(self._btn_robot_pick)

        # Y / Z sonuç göstergesi
        yz_row = QHBoxLayout()
        yz_row.addWidget(QLabel('Y:'))
        self._lbl_robot_y = QLabel('—')
        self._lbl_robot_y.setStyleSheet(
            'background:#252540;color:#f8c12f;font-size:12px;font-weight:bold;'
            'border:1px solid #3a3a55;border-radius:3px;padding:3px 6px;')
        yz_row.addWidget(self._lbl_robot_y, 1)
        yz_row.addWidget(QLabel('Z:'))
        self._lbl_robot_z = QLabel('—')
        self._lbl_robot_z.setStyleSheet(
            'background:#252540;color:#f8c12f;font-size:12px;font-weight:bold;'
            'border:1px solid #3a3a55;border-radius:3px;padding:3px 6px;')
        yz_row.addWidget(self._lbl_robot_z, 1)
        robot_lay.addLayout(yz_row)

        # Yönelim
        vert_row = QHBoxLayout()
        vert_row.addWidget(QLabel('Yönelim:'))
        self._cb_robot_vert = QComboBox()
        self._cb_robot_vert.addItem('Yatay (0)', 0)
        self._cb_robot_vert.addItem('Dikey (1)', 1)
        self._cb_robot_vert.setStyleSheet(
            'QComboBox{background:#252540;color:#eee;border:1px solid #555;'
            'border-radius:3px;padding:3px;font-size:11px;}'
            'QComboBox QAbstractItemView{background:#252540;color:#eee;}')
        vert_row.addWidget(self._cb_robot_vert)
        robot_lay.addLayout(vert_row)

        # Kaydet butonu
        self._btn_robot_save = QPushButton('💾  Robot Konumunu Kaydet')
        self._btn_robot_save.setEnabled(False)
        self._btn_robot_save.setMinimumHeight(34)
        self._btn_robot_save.setStyleSheet(
            'QPushButton{background:#1a5c1a;color:#fff;border-radius:5px;font-size:12px;font-weight:bold;}'
            'QPushButton:hover{background:#237523;}'
            'QPushButton:disabled{background:#252535;color:#555;}'
        )
        self._btn_robot_save.clicked.connect(self._save_robot)
        robot_lay.addWidget(self._btn_robot_save)

        right_lay.addWidget(robot_box)

        # İç değişkenler
        self._robot_y_mm: float = 0.0
        self._robot_z_mm: float = 0.0

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog  { background:#16161f; color:#e0e0e0; }
            QLabel   { color:#dddddd; font-size:12px; }
            QDoubleSpinBox, QSpinBox {
                background:#252535; color:#ffffff; border:1px solid #4a4a6a;
                border-radius:4px; padding:5px 8px; font-size:13px; }
            QPushButton {
                background:#2e2e45; color:#cccccc; border:1px solid #4a4a6a;
                border-radius:5px; padding:6px 14px; font-size:12px; }
            QPushButton:hover { background:#3a3a58; color:#ffffff; }
        """)

    # ─── Yön seçimi ───────────────────────────────────────

    def _on_side(self, side: str):
        # Eğer bu yön için zaten kod üretilmişse onay al
        if self._side_codes.get(side, ''):
            mb = QMessageBox(self)
            mb.setWindowTitle(f'{side} — Kod Zaten Üretildi')
            mb.setIcon(QMessageBox.Question)
            existing = self._side_codes[side]
            preview  = existing[:60] + ('…' if len(existing) > 60 else '')
            mb.setText(
                f'<b>{side}</b> yönü için bu oturumda zaten kod üretildi:\n\n'
                f'<code>{preview}</code>\n\n'
                'Yeniden üretmek istiyor musunuz?\n'
                '(Evet seçerseniz mevcut kod silinir)'
            )
            btn_yes    = mb.addButton('✅  Evet, Yeniden Üret', QMessageBox.AcceptRole)
            btn_cancel = mb.addButton('İptal',                  QMessageBox.RejectRole)
            mb.setDefaultButton(btn_cancel)
            mb.exec()
            if mb.clickedButton() != btn_yes:
                # Seçimi önceki yöne geri döndür
                current = self._current_side()
                if current:
                    self._side_btns[current].setChecked(True)
                return
            # Onaylandı — o yönün kodunu temizle
            self._side_codes[side] = ''
            lbl = self._side_code_lbls.get(side)
            if lbl:
                lbl.setText('(boş)')
                lbl.setStyleSheet('color:#555; font-family:"Courier New"; font-size:11px;')

        # Buton stillerini güncelle
        for s, btn in self._side_btns.items():
            bg, fg, _ = SIDE_COLOR[s]
            if s == side:
                btn.setChecked(True)
                btn.setStyleSheet(
                    f'QPushButton{{background:{bg};color:#ffffff;border-radius:5px;'
                    f'font-size:13px;font-weight:bold;border:2px solid {fg};}}')
            else:
                btn.setChecked(False)
                btn.setStyleSheet(
                    'QPushButton{background:#252538;color:#aaa;border-radius:5px;'
                    'font-size:13px;border:1px solid #3a3a55;}'
                    'QPushButton:hover{background:#30304a;color:#fff;}')

        self._load_groups(side)
        # Eğer manuel seçim yapıldıysa (MDB'den gelmedi) göstergeyi güncelle
        if '✅' not in self._lbl_side_info.text():
            self._lbl_side_info.setText(
                f'✏️  Yön manuel seçildi:  {side}')
            self._lbl_side_info.setStyleSheet(
                'color:#56cfe1; font-size:12px;'
                ' background:#0d1a2a; padding:5px; border-radius:4px;')

    def _load_groups(self, side: str):
        """Seçilen yönün grup satırlarını oluştur (veya mevcut olanı göster)."""
        # Pick bekleniyorsa yeniden yükleme yapma
        if self._pending_row is not None:
            return

        # Önceki satırları güvenli şekilde temizle
        while self._groups_layout.count():
            item = self._groups_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.deleteLater()

        length_x10 = int(self._sp_length.value())

        # Profil tipi tanımsızsa uyarı göster
        if not self._active_groups:
            lbl = QLabel(
                f'⚠  "{self._profile_type or "?"}" profil tipi için işlemler\n'
                f'henüz tanımlanmamış.\nSen veri hazırlarken sisteme eklenecek.'
            )
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                'color:#ffaa33; font-size:13px; padding:20px;'
                ' background:#1e1a00; border-radius:6px;')
            self._groups_layout.addWidget(lbl)
            self._rows[side] = []
            self._groups_box.setTitle(f'İşlem Grupları  —  {side}')
            return

        groups = self._active_groups.get(side, [])
        rows = []

        for g_def in groups:
            row = GroupRow(g_def, length_x10)
            row.click_requested.connect(self._on_group_click)
            self._groups_layout.addWidget(row)

            # Tıklama gerektirmiyorsa otomatik üret
            # AMA profil boyu 0 ise ertelenir — uzunluk gelince yeniden tetiklenir
            nc = group_needs_click(g_def)
            if not nc['y'] and not nc['z']:
                if length_x10 > 0:
                    row.generate_auto()
                    self._after_group_done(side, row)
                else:
                    row._pending_auto = True   # uzunluk gelince üretilecek
            rows.append(row)

        self._rows[side] = rows
        self._groups_box.setTitle(f'İşlem Grupları  —  {side}')

    # ─── Tıklama akışı ────────────────────────────────────

    # ─── Liste seçme ──────────────────────────────────────

    def _on_select_list(self):
        """Benzersiz ORDER_NO listesini gösterir, kullanıcı filtre seçer."""
        if not self._db or not self._db.connected:
            QMessageBox.warning(self, 'Uyarı', 'MDB bağlı değil.')
            return

        # Tüm benzersiz ORDER_NO + STOCK_NAME çiftlerini topla
        orders = {}   # order_no → stok_name (ilk bulunan)
        for rec in self._all_records:
            ono  = str(rec.get('ORDER_NO', '') or '').strip()
            stnm = str(rec.get('STOCK_NAME', '') or '').strip()[:20]
            if ono not in orders:
                orders[ono] = stnm

        if not orders:
            QMessageBox.information(self, 'Bilgi', 'Henüz kayıt yok.')
            return

        # Seçim dialogu
        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        dlg = QDialog(self)
        dlg.setWindowTitle('Liste Seç')
        dlg.setFixedSize(380, 320)
        dlg.setStyleSheet(
            'QDialog{background:#1e1e2e;} QLabel{color:#eee;font-size:13px;}'
            'QListWidget{background:#252540;color:#fff;border:1px solid #555;font-size:13px;}'
            'QListWidget::item:selected{background:#5a3ea0;}'
            'QPushButton{background:#226622;color:#fff;border-radius:4px;padding:6px 14px;font-size:13px;}'
        )
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel('Çalışmak istediğin listeyi seç:'))
        lw = QListWidget()

        # "Tümü" seçeneği
        item_all = QListWidgetItem('🔓  Tümünü Göster')
        item_all.setData(Qt.UserRole, '')
        lw.addItem(item_all)

        for ono, stnm in sorted(orders.items()):
            cnt = sum(1 for r in self._all_records
                      if str(r.get('ORDER_NO', '') or '').strip() == ono)
            label = f'📋  Sipariş: {ono or "(boş)"}   |   {stnm}   ({cnt} kayıt)'
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, ono)
            lw.addItem(it)

        lay.addWidget(lw, 1)
        btn_row = QHBoxLayout()
        btn_ok = QPushButton('✅ Seç')
        btn_cancel = QPushButton('İptal')
        btn_cancel.setStyleSheet(
            'QPushButton{background:#333;color:#ccc;border-radius:4px;padding:6px 14px;font-size:13px;}')
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_ok); btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

        if dlg.exec() != QDialog.Accepted:
            return
        sel = lw.currentItem()
        if not sel:
            return

        self._filter_order = sel.data(Qt.UserRole)
        self._refresh_records()

    def _clear_filter(self):
        self._filter_order = ''
        self._refresh_records()

    def _on_rec_row_selected(self, row: int, col: int):
        """Satıra tıklanınca Program No'yu doldur, robot değerlerini yükle."""
        prog_item = self._rec_table.item(row, 0)
        if not prog_item:
            return
        try:
            prog_no = int(prog_item.text())
        except ValueError:
            return
        self._selected_prog = prog_no
        self._sp_prog.setValue(prog_no)
        self._btn_edit_code.setEnabled(True)
        self._btn_robot_pick.setEnabled(True)

        # Seçili satırı vurgula
        for c in range(self._rec_table.columnCount()):
            it = self._rec_table.item(row, c)
            if it:
                it.setBackground(QColor('#3a2870'))

        # IMAGE alanındaki DXF dosyasını otomatik yükle
        if self._db and self._db.connected:
            try:
                self._db.cursor.execute(
                    f'SELECT "IMAGE" FROM "{self._db.table_name}" WHERE "PROGRAM_NO"=?',
                    (prog_no,))
                img_row = self._db.cursor.fetchone()
                if img_row and img_row[0]:
                    dxf_path = str(img_row[0]).strip()
                    if dxf_path.lower().endswith('.dxf'):
                        # Mevcut DXF'ten farklıysa yükle
                        mw = self.parent()
                        current_dxf = getattr(mw, '_dxf_file', '') if mw else ''
                        if os.path.basename(dxf_path) != current_dxf:
                            self._load_dxf_from_path(dxf_path)
                        else:
                            # Aynı DXF zaten yüklü — yeniden yüklemeye gerek yok
                            pass
            except Exception:
                pass

        # Robot değerlerini DB'den yükle
        if self._db and self._db.connected:
            try:
                self._db.cursor.execute(
                    f'SELECT "ROBOT_Y","ROBOT_Z","ROBOT_VERTICAL" '
                    f'FROM "{self._db.table_name}" WHERE "PROGRAM_NO"=?',
                    (prog_no,))
                r = self._db.cursor.fetchone()
                if r:
                    ry = r[0] or 0; rz = r[1] or 0; rv = r[2] or 0
                    self._lbl_robot_cur.setText(
                        f'#{prog_no} mevcut → Y={ry}  Z={rz}  '
                        f'{"Dikey" if rv else "Yatay"}')
                    self._lbl_robot_cur.setStyleSheet('color:#f8c12f; font-size:11px;')
                    # CB'yi ayarla
                    idx = self._cb_robot_vert.findData(int(rv))
                    if idx >= 0:
                        self._cb_robot_vert.setCurrentIndex(idx)
            except Exception:
                pass

    def _on_edit_code(self):
        """Seçili kaydın CODE alanını düzenlenebilir popup'ta gösterir."""
        if not self._selected_prog or not self._db or not self._db.connected:
            return
        prog_no = self._selected_prog
        try:
            self._db.cursor.execute(
                f'SELECT "CODE" FROM "{self._db.table_name}" WHERE "PROGRAM_NO"=?',
                (prog_no,))
            row = self._db.cursor.fetchone()
            current_code = (row[0] or '') if row else ''
        except Exception as e:
            QMessageBox.critical(self, 'Hata', str(e))
            return

        from PySide6.QtWidgets import QTextEdit
        dlg = QDialog(self)
        dlg.setWindowTitle(f'#{prog_no} — Kodu Düzenle')
        dlg.resize(800, 380)
        dlg.setStyleSheet(
            'QDialog{background:#0d1117;}'
            'QLabel{color:#aaa;font-size:11px;}'
            'QTextEdit{background:#0d1117;color:#5ef0ff;font-family:"Courier New";font-size:13px;'
            'border:1px solid #2a4060;border-radius:5px;padding:8px;}'
            'QPushButton{background:#226622;color:#fff;border-radius:4px;padding:7px 16px;font-size:13px;}'
            'QPushButton:hover{background:#338833;}'
        )
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel(f'Program #{prog_no} — Kodu düzenle ve kaydet. Her işlem // ile bitmeli.'))
        te = QTextEdit()
        te.setPlainText(current_code)
        lay.addWidget(te, 1)

        btn_row = QHBoxLayout()
        btn_save = QPushButton('💾  Kaydet')
        btn_cancel = QPushButton('İptal')
        btn_cancel.setStyleSheet(
            'QPushButton{background:#2e2e42;color:#ccc;border-radius:4px;padding:7px 16px;font-size:13px;}')
        btn_save.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_save); btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

        if dlg.exec() != QDialog.Accepted:
            return

        new_code = te.toPlainText().strip()
        ok, msg = self._db.replace_code_in_record(prog_no, new_code)
        if ok:
            self._refresh_records()
            QMessageBox.information(self, 'Kaydedildi', f'#{prog_no} kodu güncellendi.')
        else:
            QMessageBox.critical(self, 'Hata', msg)

    def _refresh_records(self):
        """Mevcut kayıtları tabloya yükler (5 sütun, son sütun = 👁 popup)."""
        self._rec_table.setRowCount(0)
        if not self._db or not self._db.connected:
            self._lbl_rec_count.setText('MDB bağlı değil')
            return
        try:
            self._all_records = self._db.get_all_records()
        except Exception:
            return

        # Filtre uygula
        records = (
            [r for r in self._all_records
             if str(r.get('ORDER_NO', '') or '').strip() == self._filter_order]
            if self._filter_order
            else self._all_records
        )

        # Buton etiketini güncelle
        if self._filter_order:
            self._btn_select_list.setText(f'📂  Sipariş: {self._filter_order}  ▼')
        else:
            self._btn_select_list.setText(f'📂  Liste Seç  (Tümü, {len(self._all_records)} kayıt)  ▼')
        for rec in records:
            r = self._rec_table.rowCount()
            self._rec_table.insertRow(r)
            pno = rec.get('PROGRAM_NO', '')
            try:    prog = str(int(float(pno)))
            except: prog = str(pno)
            side_val = rec.get('SIDE', '')
            try:    side = str(int(float(side_val))) if side_val not in ('', None) else '–'
            except: side = str(side_val) if side_val else '–'
            stok = str(rec.get('STOCK_NAME', '') or '')[:10]
            code = str(rec.get('CODE', '') or '')
            preview = code[:30] + ('…' if len(code) > 30 else '') if code else '–'

            row_bg = QColor('#1e1e35') if r % 2 == 0 else QColor('#16162a')
            for c, txt in enumerate([prog, side, stok, preview]):
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignCenter if c < 3 else Qt.AlignLeft | Qt.AlignVCenter)
                item.setForeground(QColor('#ffffff'))
                item.setBackground(row_bg)
                if c == 1:   # Yön sütunu — tıklanabilir, sarı
                    item.setForeground(QColor('#f8c12f'))
                    item.setToolTip('Tıklayarak yönü değiştir')
                if c == 3:
                    item.setForeground(QColor('#56cfe1' if code else '#888'))
                    item.setFont(QFont('Courier New', 9))
                    item.setBackground(QColor('#0d0f1a') if r % 2 == 0 else QColor('#0a0c15'))
                self._rec_table.setItem(r, c, item)

            # Col 4: 👁 popup butonu
            btn_eye = QPushButton('👁')
            btn_eye.setFixedSize(28, 24)
            btn_eye.setToolTip('Tam kodu göster')
            btn_eye.setStyleSheet(
                'QPushButton{background:#1a3a6a;color:#fff;border-radius:3px;font-size:11px;}'
                'QPushButton:hover{background:#265098;}')
            btn_eye.clicked.connect(lambda _, c=code, p=prog: self._show_code_popup(p, c))
            self._rec_table.setCellWidget(r, 4, btn_eye)
            self._rec_table.setRowHeight(r, 26)

        self._lbl_rec_count.setText(f'{len(records)} kayıt')

    # ─── Robot Yakalama ───────────────────────────────────

    def _load_dxf_from_path(self, dxf_path: str):
        """IMAGE alanındaki DXF dosyasını ana pencere viewport'una yükler."""
        mw = self.parent()
        if not mw or not hasattr(mw, '_viewport'):
            return
        if not os.path.exists(dxf_path):
            mw.statusBar().showMessage(
                f'⚠  DXF bulunamadı: {os.path.basename(dxf_path)}', 4000)
            return
        try:
            from dxf_loader import load_dxf
            segs = load_dxf(dxf_path)
            if not segs:
                return
            mw._raw_segs   = segs
            mw._cur_segs   = segs
            mw._mirror_y   = False
            mw._mirror_z   = False
            mw._rotate_deg = 0.0
            mw._dxf_file   = os.path.basename(dxf_path)
            mw._sp_extrude.setValue(0)
            mw._viewport.load_segments(segs)
            mw._lbl_dxf.setText(f'DXF: ✅ {mw._dxf_file}  (kayıttan yüklendi)')
            mw.statusBar().showMessage(
                f'📄  DXF otomatik yüklendi: {mw._dxf_file}  — tıklamaya hazır', 4000)
        except Exception as e:
            mw.statusBar().showMessage(f'DXF yükleme hatası: {e}', 3000)

    def _pick_robot(self):
        """DXF üzerinden robot yakalama noktasını seç."""
        from PySide6.QtWidgets import QApplication
        if not self._selected_prog:
            QMessageBox.information(self, 'Uyarı', 'Önce tablodan bir kayıt seçin.')
            return
        mw = self.parent()
        if not mw or not hasattr(mw, '_viewport'):
            return
        if not mw._cur_segs:
            QMessageBox.information(self, 'Uyarı', 'Ana pencereden DXF yükleyin.')
            return

        self.hide()   # macOS'ta lower() çalışmaz, hide() kullan
        mw.raise_(); mw.activateWindow()
        QApplication.setActiveWindow(mw)
        mw._viewport.set_pick_mode(True)
        try:
            mw._viewport.point_selected.disconnect(self._on_robot_picked)
        except Exception:
            pass
        mw._viewport.point_selected.connect(self._on_robot_picked)
        mw.statusBar().showMessage(
            f'📍  #{self._selected_prog} için Robot Yakalama Noktasını seçin…', 0)

    def _on_robot_picked(self, y: float, z: float):
        from PySide6.QtWidgets import QApplication
        mw = self.parent()
        if mw and hasattr(mw, '_viewport'):
            try:
                mw._viewport.point_selected.disconnect(self._on_robot_picked)
            except Exception:
                pass
            mw.statusBar().showMessage('✅  Robot koordinatı alındı.', 3000)

        self._robot_y_mm = y
        self._robot_z_mm = z
        self._lbl_robot_y.setText(f'{y:.2f} mm → {int(round(y*10))}')
        self._lbl_robot_z.setText(f'{z:.2f} mm → {int(round(z*10))}')
        self._btn_robot_save.setEnabled(True)

        self.show()   # Gizleneni tekrar göster
        self.raise_(); self.activateWindow()
        QApplication.setActiveWindow(self)

    def _save_robot(self):
        """Seçili kaydın ROBOT_Y ve ROBOT_Z değerlerini günceller."""
        # Hata ayıklama: ne durumda olduğumuzu göster
        if not self._selected_prog:
            QMessageBox.warning(self, 'Kayıt Seçilmedi',
                'Önce sağ tabloda bir program satırına tıklayın.')
            return
        if self._robot_y_mm == 0.0 and self._robot_z_mm == 0.0:
            QMessageBox.warning(self, 'Koordinat Alınmadı',
                '"📍 DXF\'ten Yeni Nokta Al" butonuna basıp DXF üzerinde tıklayın.')
            return
        if not self._db or not self._db.connected:
            QMessageBox.warning(self, 'MDB Bağlı Değil',
                'Ana pencereden "💾 MDB Bağlan" ile MDB seçin.')
            return

        ry = int(round(self._robot_y_mm * 10))
        rz = int(round(self._robot_z_mm * 10))
        rv = self._cb_robot_vert.currentData()
        if rv is None:
            rv = 0

        # Seçili kaydın stok kodunu bul
        stock_code = ''
        try:
            self._db.cursor.execute(
                f'SELECT "STOCK_CODE" FROM "{self._db.table_name}" WHERE "PROGRAM_NO"=?',
                (self._selected_prog,))
            row = self._db.cursor.fetchone()
            if row:
                stock_code = (row[0] or '').strip()
        except Exception:
            pass

        # Aynı stok kodlu tüm kayıtlara yaz
        if stock_code:
            try:
                ok, msg = self._db.update_robot_all_same_stock(stock_code, ry, rz, int(rv))
            except Exception as e:
                QMessageBox.critical(self, 'Hata', str(e))
                return
        else:
            # Stok kodu bulunamazsa sadece seçili kaydı güncelle
            try:
                ok, msg = self._db.update_robot_position(self._selected_prog, ry, rz, int(rv))
            except Exception as e:
                QMessageBox.critical(self, 'Hata', str(e))
                return

        if ok:
            QMessageBox.information(self, '✅ Kaydedildi',
                f'ROBOT_Y={ry}  ROBOT_Z={rz}  {"Dikey" if rv else "Yatay"}\n{msg}')
            self._lbl_robot_cur.setText(
                f'#{self._selected_prog} ✅ → Y={ry}  Z={rz}  '
                f'{"Dikey" if rv else "Yatay"}')
            self._lbl_robot_cur.setStyleSheet('color:#44ff88; font-size:11px;')
            self._btn_robot_save.setEnabled(False)
            self._refresh_records()
        else:
            QMessageBox.critical(self, 'Kayıt Hatası', msg)

    def _on_rec_cell_clicked(self, row: int, col: int):
        """Yön sütununa (col=1) tıklanınca SIDE değerini değiştirme popup'ı açar."""
        if col != 1:
            return
        prog_item = self._rec_table.item(row, 0)
        if not prog_item:
            return
        try:
            prog_no = int(prog_item.text())
        except ValueError:
            return

        if not self._db or not self._db.connected:
            QMessageBox.warning(self, 'Uyarı', 'MDB bağlı değil.')
            return

        # Mevcut yön
        side_item = self._rec_table.item(row, 1)
        current_side = side_item.text().strip() if side_item else '1'

        # Seçim popup
        from PySide6.QtWidgets import QInputDialog, QComboBox, QDialog, QVBoxLayout, QHBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle(f'#{prog_no} — Yön Değiştir')
        dlg.setFixedSize(300, 130)
        dlg.setStyleSheet('QDialog{background:#1e1e2e;color:#eee;}'
                          'QLabel{color:#eee;font-size:13px;}'
                          'QComboBox{background:#2e2e42;color:#fff;border:1px solid #555;'
                          'border-radius:4px;padding:5px;font-size:13px;}'
                          'QComboBox QAbstractItemView{background:#2e2e42;color:#fff;}'
                          'QPushButton{background:#226622;color:#fff;border-radius:4px;'
                          'padding:6px 14px;font-size:13px;}'
                          'QPushButton:hover{background:#338833;}')
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel(f'Program #{prog_no} için yeni yön:'))
        cb = QComboBox()
        sides = [('1','1 – Sol'), ('2','2 – Üst'), ('3','3 – Sağ'), ('4','4 – Alt')]
        for val, lbl in sides:
            cb.addItem(lbl, val)
            if val == current_side:
                cb.setCurrentIndex(cb.count() - 1)
        lay.addWidget(cb)
        btn_row = QHBoxLayout()
        btn_ok = QPushButton('✅ Kaydet')
        btn_cancel = QPushButton('İptal'); btn_cancel.setStyleSheet(
            'QPushButton{background:#333;color:#ccc;border-radius:4px;padding:6px 14px;font-size:13px;}')
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_ok); btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

        if dlg.exec() != QDialog.Accepted:
            return

        new_side = cb.currentData()
        try:
            self._db.cursor.execute(
                f'UPDATE "{self._db.table_name}" SET "SIDE"=? WHERE "PROGRAM_NO"=?',
                (int(new_side), prog_no))
            self._db.conn.commit()
            self._refresh_records()
            QMessageBox.information(self, 'Güncellendi',
                f'#{prog_no} kaydının yönü → {cb.currentText()} olarak güncellendi.')
        except Exception as e:
            QMessageBox.critical(self, 'Hata', str(e))

    def _show_code_popup(self, prog_no: str, code: str):
        """Seçili satırın tam kodunu popup'ta gösterir."""
        dlg = QDialog(self)
        dlg.setWindowTitle(f'Program #{prog_no} — Tam Kod')
        dlg.resize(700, 300)
        dlg.setStyleSheet('QDialog{background:#0d1117;} QTextEdit{background:#0d1117;'
                          'color:#5ef0ff;font-family:"Courier New";font-size:13px;}'
                          'QPushButton{background:#2e2e42;color:#ccc;border-radius:4px;padding:6px 14px;}')
        lay = QVBoxLayout(dlg)
        from PySide6.QtWidgets import QTextEdit
        te = QTextEdit()
        te.setPlainText(code or '(Kod yok)')
        te.setReadOnly(True)
        lay.addWidget(te, 1)
        btn_close = QPushButton('Kapat')
        btn_close.clicked.connect(dlg.accept)
        lay.addWidget(btn_close)
        dlg.exec()

    def _on_group_click(self, row: GroupRow):
        """Bir grup satırının Tıkla butonuna basıldı."""
        from PySide6.QtWidgets import QApplication
        self._pending_row = row
        mw = self.parent()
        if not mw or not hasattr(mw, '_viewport'):
            return

        # macOS'ta lower() çalışmaz — hide()/show() kullan
        self.hide()

        # Ana pencereyi öne getir ve aktifleştir
        mw.showNormal()
        mw.raise_()
        mw.activateWindow()
        QApplication.setActiveWindow(mw)

        mw._viewport.set_pick_mode(True)
        try:
            mw._viewport.point_selected.disconnect(self._on_point_received)
        except Exception:
            pass
        mw._viewport.point_selected.connect(self._on_point_received)
        mw.statusBar().showMessage(
            f'📍  {row._group_def["name"]} için DXF\'e tıklayın  '
            f'— tıkladıktan sonra bu pencere otomatik açılır',
            0   # süresiz göster
        )

    def _on_point_received(self, y: float, z: float):
        from PySide6.QtWidgets import QApplication
        mw = self.parent()
        if mw and hasattr(mw, '_viewport'):
            try:
                mw._viewport.point_selected.disconnect(self._on_point_received)
            except Exception:
                pass
            mw.statusBar().showMessage('✅  Koordinat alındı.', 3000)

        # Pick bitti — dialog'u geri getir
        self.show()
        self.raise_()
        self.activateWindow()
        QApplication.setActiveWindow(self)

        if self._pending_row:
            # Hangi yöndeyiz?
            side = self._current_side()
            self._pending_row.generate(y, z)
            self._after_group_done(side, self._pending_row)
            self._pending_row = None

    def _after_group_done(self, side: str, row: GroupRow):
        """Bir grup tamamlandığında yön kodunu ve toplam kodu güncelle."""
        # Bu yönün tüm gruplarının kodunu birleştir
        all_done = all(r.done for r in self._rows.get(side, []))
        side_code = ''.join(r.code for r in self._rows.get(side, []))
        self._side_codes[side] = side_code

        # Yön etiketi güncelle
        lbl = self._side_code_lbls.get(side)
        if lbl:
            if side_code:
                lbl.setText(side_code)
                lbl.setStyleSheet('color:#5ef0ff; font-family:"Courier New"; font-size:11px;')
            else:
                lbl.setText('(boş)')

        # Toplam kodu güncelle
        total = ''.join(self._side_codes[s] for s in SIDES)
        if total:
            prog = self._sp_prog.value()
            self._lbl_total.setText(f'#{prog}  →  {total}')
            self._btn_save.setEnabled(True)
        else:
            self._lbl_total.setText('(henüz kod yok)')

    # ─── Yardımcılar ──────────────────────────────────────

    def _current_side(self) -> str:
        for s, btn in self._side_btns.items():
            if btn.isChecked():
                return s
        return ''

    def _on_length_changed(self, val: float):
        mm = val / 10.0
        self._lbl_mm.setText(f'= {mm:.0f} mm')
        length_x10 = int(val)

        for s, rows in self._rows.items():
            for r in rows:
                r.set_length(length_x10)

        # Pick bekleniyorsa grupları yeniden yükleme
        if self._pending_row is not None:
            return

        side = self._current_side()

        # Uzunluk beklediği için üretilemeyen otomatik grupları şimdi üret
        if side and length_x10 > 0:
            for r in self._rows.get(side, []):
                if getattr(r, '_pending_auto', False):
                    r._pending_auto = False
                    r.generate_auto()
                    self._after_group_done(side, r)
            return   # Satırlar zaten var, yeniden yükleme

        if side:
            self._load_groups(side)

    # SIDE (1=SOL, 2=ÜST, 3=SAĞ, 4=ALT) → yön adı
    _SIDE_MAP = {1: 'SOL', 2: 'ÜST', 3: 'SAĞ', 4: 'ALT',
                 '1': 'SOL', '2': 'ÜST', '3': 'SAĞ', '4': 'ALT'}

    def _set_profile_type(self, ptype: str):
        """Profil tipini ayarlar, işlem gruplarını ve etiketleri günceller."""
        self._profile_type  = ptype.upper() if ptype else ''
        self._active_groups = get_groups_for_type(self._profile_type)

        label = PROFILE_LABEL.get(self._profile_type, '?')
        if self._profile_type:
            if is_type_implemented(self._profile_type):
                self._lbl_type.setText(f'✅  {self._profile_type} – {label}')
                self._lbl_type.setStyleSheet(
                    'color:#44ff88; font-size:13px; font-weight:bold;'
                    ' padding:2px 8px; background:#0d2010; border-radius:4px;')
            else:
                self._lbl_type.setText(
                    f'⚠  {self._profile_type} – {label}  (henüz tanımsız)')
                self._lbl_type.setStyleSheet(
                    'color:#ffaa33; font-size:12px; font-weight:bold;'
                    ' padding:2px 8px; background:#2a1a00; border-radius:4px;')
        else:
            self._lbl_type.setText('⚠  Seçilmedi')
            self._lbl_type.setStyleSheet(
                'color:#ff6644; font-size:12px; padding:2px 8px;'
                ' background:#2a0a00; border-radius:4px;')

        # Dropdown: tip seçilmemişse otomatik aç, seçildiyse gizle (✏ butonu ile açılır)
        self._cb_type.setVisible(not bool(self._profile_type))

        side = self._current_side()
        if side and self._pending_row is None:
            self._load_groups(side)

    def _show_type_selector(self):
        """✏ butonuna basılınca dropdown'ı göster."""
        if self._profile_type:
            idx = self._cb_type.findData(self._profile_type)
            if idx >= 0:
                self._cb_type.blockSignals(True)
                self._cb_type.setCurrentIndex(idx)
                self._cb_type.blockSignals(False)
        self._cb_type.setVisible(True)
        self._cb_type.showPopup()

    def _on_manual_type(self, idx: int):
        """Kullanıcı manuel tip seçti."""
        t = self._cb_type.itemData(idx)
        if t and t != '':
            self._cb_type.setVisible(False)
            self._set_profile_type(t)

    def _on_prog_changed(self, no: int):
        if not self._db or not self._db.connected:
            self._lbl_side_info.setText(
                '⚠  MDB bağlı değil — ana pencereden bağlantı kurun')
            self._lbl_side_info.setStyleSheet(
                'color:#ff6644; font-size:12px; background:#1e1e2e; padding:5px; border-radius:4px;')
            return
        try:
            self._db.cursor.execute(
                f'SELECT "LENGTH", "SIDE", "TYPE" FROM "{self._db.table_name}" WHERE "PROGRAM_NO"=?',
                (no,))
            row = self._db.cursor.fetchone()
        except Exception:
            return

        if not row:
            self._lbl_side_info.setText(
                f'⚠  #{no} numaralı kayıt bulunamadı — önce toplu liste girişi yapın')
            self._lbl_side_info.setStyleSheet(
                'color:#ff6644; font-size:12px; background:#2a1010; padding:5px; border-radius:4px;')
            return

        # LENGTH
        if row[0]:
            self._sp_length.setValue(float(row[0]))

        # TYPE → profil tipi otomatik seç
        type_val = str(row[2]).strip() if row[2] else ''
        if type_val and type_val not in ('None', ''):
            self._set_profile_type(type_val)
        else:
            # TYPE boş — dropdown göster
            self._set_profile_type('')
            self._lbl_side_info.setText(
                f'⚠  #{no} için TYPE boş — profil tipini seçin')
            self._lbl_side_info.setStyleSheet(
                'color:#f8c12f; font-size:12px; font-weight:bold;'
                ' background:#2a2000; padding:5px; border-radius:4px;')

        # SIDE → yön otomatik seç (TYPE belirlendikten sonra)
        side_val = row[1]
        if side_val is not None and str(side_val).strip() not in ('', '0', 'None'):
            direction = self._SIDE_MAP.get(int(float(str(side_val))), '')
            if direction:
                self._on_side(direction)
                self._lbl_side_info.setText(
                    f'✅  #{no} → Yön MDB\'den algılandı:  {direction}  '
                    f'(SIDE={int(float(str(side_val)))})  —  gerekirse değiştirebilirsiniz')
                self._lbl_side_info.setStyleSheet(
                    'color:#44ff88; font-size:12px; font-weight:bold;'
                    ' background:#0d2010; padding:5px; border-radius:4px;')
                return

        self._lbl_side_info.setText(
            f'⚠  #{no} için SIDE boş — lütfen aşağıdan yön seçin')
        self._lbl_side_info.setStyleSheet(
            'color:#f8c12f; font-size:12px; font-weight:bold;'
            ' background:#2a2000; padding:5px; border-radius:4px;')

    # ─── MDB kaydet ───────────────────────────────────────

    def _on_save(self):
        total = ''.join(self._side_codes[s] for s in SIDES)
        if not total:
            return
        if not self._db or not self._db.connected:
            QMessageBox.warning(self, 'MDB Bağlı Değil',
                'Ana pencereden "💾 MDB Bağlan" ile MDB dosyasını seçin.')
            return
        prog_no = self._sp_prog.value()

        # Mevcut CODE kontrolü
        existing_code = ''
        try:
            self._db.cursor.execute(
                f'SELECT "CODE" FROM "{self._db.table_name}" WHERE "PROGRAM_NO"=?',
                (prog_no,))
            row = self._db.cursor.fetchone()
            existing_code = (row[0] or '').strip() if row else ''
        except Exception:
            pass

        if existing_code:
            preview = existing_code[:70] + ('…' if len(existing_code) > 70 else '')
            mb = QMessageBox(self)
            mb.setWindowTitle(f'#{prog_no} — Mevcut Kod Var')
            mb.setIcon(QMessageBox.Warning)
            mb.setText(
                f'<b>#{prog_no}</b> numaralı kayıtta zaten işlem kodu var:\n\n'
                f'{preview}\n\nNasıl devam edilsin?'
            )
            btn_replace = mb.addButton('🗑  Sil ve Yenisini Yaz',  QMessageBox.DestructiveRole)
            btn_append  = mb.addButton('➕  Mevcut Koda Ekle',     QMessageBox.AcceptRole)
            btn_cancel  = mb.addButton('İptal',                    QMessageBox.RejectRole)
            mb.setDefaultButton(btn_replace)
            mb.exec()

            if mb.clickedButton() == btn_cancel:
                return
            if mb.clickedButton() == btn_replace:
                ok, msg = self._db.replace_code_in_record(prog_no, total)
            else:
                ok, msg = self._db.append_code_to_record(prog_no, total)
        else:
            ok, msg = self._db.append_code_to_record(prog_no, total)

        if ok:
            QMessageBox.information(self, 'Kaydedildi',
                f'#{prog_no} için tüm yönlerin kodu MDB\'ye yazıldı.')
            self._btn_save.setEnabled(False)
            self._sp_prog.setValue(prog_no + 1)
            for s in SIDES:
                self._side_codes[s] = ''
                lbl = self._side_code_lbls.get(s)
                if lbl:
                    lbl.setText('(boş)')
                    lbl.setStyleSheet('color:#555; font-family:"Courier New"; font-size:11px;')
            self._lbl_total.setText('(henüz kod yok)')
        else:
            QMessageBox.critical(self, 'Hata', msg)
