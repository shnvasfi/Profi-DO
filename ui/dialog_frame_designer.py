"""
ui/dialog_frame_designer.py  —  Çerçeve Tasarımcısı

Sol : Çerçeve listesi (tip bazlı gruplu)
Orta: Seçili çerçeve detay + parça tablosu
Sağ : Görsel önizleme

Kasa → 4 parça (Üst/Alt=W+kerf, Sol/Sağ=H+kerf, 45°)
Kanat→ 4 parça, ölçüler kasadan otomatik hesaplanır:
  kanat_W = kasa_W - 2×kasa_pw + 27
  kanat_H = kasa_H - 2×kasa_pw + 27
"""

import os, json
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QFrame, QSizePolicy, QMessageBox, QWidget,
    QAbstractItemView, QTreeWidget, QTreeWidgetItem, QSplitter,
    QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QBrush

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches

from models import PROFILE_TYPES, COLOR_CODES

KERF_DEFAULT  = 6.0
SASH_OVERLAP  = 27.0   # Kanat bindirme (kasa_iç + 27mm = kanat_dış)

# Tip → profil rengi
_TYPE_COLORS = {
    'A': '#999999', 'F': '#7a9a7a', 'H': '#9a7a9a', 'I': '#888888',
    'B': '#c8a800', 'C': '#b89a00', 'D': '#a88800',
    'G': '#5a8a5a', 'J': '#8a6a40', 'E': '#707070',
}

def _type_color(typ: str) -> str:
    return _TYPE_COLORS.get(typ, '#aaaaaa')

def _label_color(hex_color: str) -> str:
    """Arka plan rengine göre siyah/beyaz etiket rengi döndür."""
    h = hex_color.lstrip('#')
    if len(h) == 6:
        r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        lum = 0.299*r + 0.587*g + 0.114*b
        return '#111111' if lum > 140 else '#eeeeee'
    return '#111111'

TYPE_GROUP = {
    'A': ('Kasalar',           '#2d2d8a'),
    'F': ('Sürme Kasalar',     '#1f6b1f'),
    'H': ('Pervazlı Kasalar',  '#7a2d5a'),
    'I': ('Denizlikli Kasalar','#555'),
    'B': ('Kanatlar',          '#7a6a10'),
    'C': ('Damlalıklı Kanatlar','#7a6a10'),
    'D': ('Dış Açılım Kanatlar','#7a6a10'),
    'G': ('Sürme Kanatlar',    '#7a6a10'),
    'J': ('Kapı Kanatlar',     '#7a3a20'),
    'E': ('Orta Kayıtlar',     '#555'),
}

SIDE_COLOR = {1:'#7a2d5a', 2:'#2d2d8a', 3:'#7a6a10', 4:'#1f6b1f'}
SIDE_NAME  = {1:'SOL', 2:'ÜST', 3:'SAĞ', 4:'ALT'}


# ─────────────────────────────────────────────────────────────────────
# DXF seçim yardımcısı
# ─────────────────────────────────────────────────────────────────────

def _ask_dxf(parent, title="DXF Dosyası Seç") -> str:
    """Kullanıcıya DXF dosyası seçtirir. Seçilmezse '' döner."""
    path, _ = QFileDialog.getOpenFileName(parent, title, '', 'DXF Dosyaları (*.dxf)')
    return path


def _dxf_dims(dxf_path: str):
    """DXF'ten (height_mm, width_mm) döndürür."""
    if not dxf_path or not os.path.exists(dxf_path):
        return 0.0, 0.0
    try:
        from dxf_loader import load_dxf, calc_profile_dimensions
        segs = load_dxf(dxf_path)
        return calc_profile_dimensions(segs)
    except Exception:
        return 0.0, 0.0


# ─────────────────────────────────────────────────────────────────────
# Çerçeve Ekle dialog'u
# ─────────────────────────────────────────────────────────────────────

class AddFrameDialog(QDialog):
    """
    Çerçeve ekleme dialogu.
    ─────────────────────
    Soldaki panel: Profil Kütüphanesi listesi (tipe göre filtreli).
    Tıklayınca sağa tüm bilgiler otomatik dolar:
      • Stok kodu / adı / renk / DXF
      • Profil genişliği / yüksekliği (DXF'ten ölçülür)
      • Kesim payı, bar boyu
    Kullanıcı sadece W (genişlik) ve H (yükseklik) girer.
    """

    def __init__(self, parent=None, profile_type='A',
                 suggested_w=None, suggested_h=None,
                 title_extra=''):
        super().__init__(parent)
        self._type        = profile_type
        self._dxf_path    = ''
        self._library     = {}
        type_label        = PROFILE_TYPES.get(profile_type, profile_type)
        self.setWindowTitle(f'Çerçeve Ekle  —  {type_label}{title_extra}')
        self.setMinimumSize(820, 520)
        self.resize(900, 560)
        self._suggested_w = suggested_w
        self._suggested_h = suggested_h

        # Kütüphaneyi yükle
        try:
            import code_generator as cg
            self._library = cg.load_library()
        except Exception:
            pass

        self._setup_ui(type_label)
        self._fill_profile_list()

        self.setStyleSheet("""
            QDialog{background:#1e1e2e;color:#e0e0e0;}
            QLabel{color:#ddd;font-size:12px;}
            QLineEdit,QDoubleSpinBox,QSpinBox,QComboBox{
                background:#252540;color:#fff;border:1px solid #556;
                border-radius:4px;padding:4px;font-size:13px;}
            QComboBox QAbstractItemView{background:#252540;color:#fff;}
            QPushButton{background:#2e2e42;color:#ddd;border:1px solid #444;
                border-radius:4px;padding:6px 14px;font-size:12px;}
            QPushButton:hover{background:#3a3a55;}
            QGroupBox{color:#f8c12f;font-size:12px;font-weight:bold;
                border:1px solid #3a3a55;border-radius:5px;
                margin-top:8px;padding-top:10px;}
            QGroupBox::title{subcontrol-origin:margin;left:8px;}
            QListWidget{background:#151525;color:#ccc;border:1px solid #3a3a55;
                border-radius:4px;font-size:12px;}
            QListWidget::item:selected{background:#3a2860;color:#fff;}
            QListWidget::item:hover{background:#252545;}
        """)

    # ── UI Kurulum ────────────────────────────────────────────────

    def _setup_ui(self, type_label):
        from PySide6.QtWidgets import QListWidget, QSplitter

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── SOL: Profil Kütüphanesi Listesi ──────────────
        left = QVBoxLayout()

        lbl_lib = QLabel('📚  Profil Kütüphanesi')
        lbl_lib.setStyleSheet('color:#f8c12f;font-size:13px;font-weight:bold;')
        left.addWidget(lbl_lib)

        # Arama kutusu
        self._ed_search = QLineEdit()
        self._ed_search.setPlaceholderText('🔍 Profil ara…')
        self._ed_search.textChanged.connect(self._fill_profile_list)
        left.addWidget(self._ed_search)

        # Liste
        self._lst = QListWidget()
        self._lst.setMinimumWidth(260)
        self._lst.itemClicked.connect(self._on_profile_selected)
        left.addWidget(self._lst, 1)

        lbl_hint = QLabel('⬆ Tıkla → bilgiler otomatik dolar')
        lbl_hint.setStyleSheet('color:#667; font-size:10px;')
        left.addWidget(lbl_hint)

        left_w = QWidget(); left_w.setLayout(left)
        root.addWidget(left_w, 3)

        # ── SAĞ: Form ────────────────────────────────────
        right = QVBoxLayout()

        # Seçili profil etiketi
        lbl_tip = QLabel(f'Tip:  <b>{type_label}</b>')
        lbl_tip.setStyleSheet('color:#f8c12f;font-size:13px;')
        right.addWidget(lbl_tip)

        self._lbl_selected = QLabel('Kütüphaneden profil seçin…')
        self._lbl_selected.setStyleSheet(
            'background:#1a1a2e;color:#888;border:1px solid #3a3a55;'
            'border-radius:4px;padding:6px;font-size:11px;')
        self._lbl_selected.setWordWrap(True)
        right.addWidget(self._lbl_selected)

        # ── Çerçeve ölçüleri ─────────────────────────────
        dim_box = QGroupBox('Çerçeve Ölçüleri (zorunlu)')
        dg = QGridLayout(dim_box); dg.setSpacing(8)

        dg.addWidget(QLabel('Genişlik (W):'), 0, 0)
        self._sp_w = QDoubleSpinBox()
        self._sp_w.setRange(100, 5000)
        self._sp_w.setValue(self._suggested_w or 1000)
        self._sp_w.setDecimals(0); self._sp_w.setSuffix(' mm')
        self._sp_w.setFont(QFont('Arial', 13, QFont.Bold))
        dg.addWidget(self._sp_w, 0, 1)

        dg.addWidget(QLabel('Yükseklik (H):'), 0, 2)
        self._sp_h = QDoubleSpinBox()
        self._sp_h.setRange(100, 5000)
        self._sp_h.setValue(self._suggested_h or 1000)
        self._sp_h.setDecimals(0); self._sp_h.setSuffix(' mm')
        self._sp_h.setFont(QFont('Arial', 13, QFont.Bold))
        dg.addWidget(self._sp_h, 0, 3)
        right.addWidget(dim_box)

        # ── Profil teknik ölçüler (kütüphaneden gelir) ───
        tech_box = QGroupBox('Profil Teknik Ölçüler')
        tg = QGridLayout(tech_box); tg.setSpacing(8)

        tg.addWidget(QLabel('Profil Genişliği:'), 0, 0)
        self._sp_pw = QDoubleSpinBox()
        self._sp_pw.setRange(10, 300); self._sp_pw.setValue(66)
        self._sp_pw.setDecimals(1); self._sp_pw.setSuffix(' mm')
        tg.addWidget(self._sp_pw, 0, 1)

        tg.addWidget(QLabel('Profil Yüksekliği:'), 0, 2)
        self._sp_ph = QDoubleSpinBox()
        self._sp_ph.setRange(10, 300); self._sp_ph.setValue(70)
        self._sp_ph.setDecimals(1); self._sp_ph.setSuffix(' mm')
        tg.addWidget(self._sp_ph, 0, 3)

        tg.addWidget(QLabel('Kesim Payı:'), 1, 0)
        self._sp_kerf = QDoubleSpinBox()
        self._sp_kerf.setRange(0, 20); self._sp_kerf.setValue(KERF_DEFAULT)
        self._sp_kerf.setDecimals(1); self._sp_kerf.setSuffix(' mm')
        tg.addWidget(self._sp_kerf, 1, 1)

        tg.addWidget(QLabel('Bar Boyu:'), 1, 2)
        self._sp_bar = QDoubleSpinBox()
        self._sp_bar.setRange(100, 20000); self._sp_bar.setValue(6000)
        self._sp_bar.setDecimals(0); self._sp_bar.setSuffix(' mm')
        tg.addWidget(self._sp_bar, 1, 3)
        right.addWidget(tech_box)

        # ── Stok bilgileri (kütüphaneden gelir, düzenlenebilir) ──
        stok_box = QGroupBox('Stok & Sipariş')
        sg = QGridLayout(stok_box); sg.setSpacing(8)

        sg.addWidget(QLabel('Stok Kodu:'), 0, 0)
        self._ed_sc = QLineEdit()
        self._ed_sc.setMaxLength(16)
        sg.addWidget(self._ed_sc, 0, 1, 1, 3)

        sg.addWidget(QLabel('Stok Adı:'), 1, 0)
        self._ed_sn = QLineEdit()
        sg.addWidget(self._ed_sn, 1, 1, 1, 3)

        sg.addWidget(QLabel('Sipariş No:'), 2, 0)
        self._ed_order = QLineEdit(); self._ed_order.setMaxLength(6)
        sg.addWidget(self._ed_order, 2, 1)

        sg.addWidget(QLabel('Renk Kodu:'), 2, 2)
        self._cb_color = QComboBox()
        for k, v in COLOR_CODES.items():
            self._cb_color.addItem(v, k)
        sg.addWidget(self._cb_color, 2, 3)
        right.addWidget(stok_box)

        # ── Manuel DXF seçimi (kütüphane yoksa yedek) ───
        dxf_row = QHBoxLayout()
        self._lbl_dxf = QLabel('DXF: —')
        self._lbl_dxf.setStyleSheet('color:#667; font-size:10px;')
        dxf_row.addWidget(self._lbl_dxf, 1)
        btn_dxf = QPushButton('📂 DXF Seç')
        btn_dxf.setFixedWidth(90)
        btn_dxf.clicked.connect(self._pick_dxf)
        dxf_row.addWidget(btn_dxf)
        right.addLayout(dxf_row)

        right.addStretch()

        # Butonlar
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet('color:#3a3a55;')
        right.addWidget(sep)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton('✅  Ekle')
        btn_ok.setMinimumHeight(38)
        btn_ok.setStyleSheet(
            'QPushButton{background:#226622;color:#fff;border-radius:5px;'
            'font-size:13px;font-weight:bold;}QPushButton:hover{background:#338833;}')
        btn_ok.clicked.connect(self._on_accept)
        btn_cancel = QPushButton('İptal')
        btn_cancel.setMinimumHeight(38)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        right.addLayout(btn_row)

        right_w = QWidget(); right_w.setLayout(right)
        root.addWidget(right_w, 5)

    # ── Profil listesini doldur ───────────────────────────────────

    def _fill_profile_list(self, search_text: str = ''):
        """Tipe göre filtrelenmiş profilleri listele. Arama varsa uygula."""
        import code_generator as cg
        self._lst.clear()

        # Tipe göre kütüphaneden profilleri al
        profiles = cg.get_profiles_by_type(self._library, self._type)

        # Tip eşleşmiyorsa tüm profilleri göster
        if not profiles:
            profiles = []
            for code, prof in self._library.get('profiles', {}).items():
                entry = dict(prof); entry['stock_code'] = code
                profiles.append(entry)

        search = (search_text or self._ed_search.text()).lower().strip()

        for prof in profiles:
            name = prof.get('name', '')
            code = prof.get('stock_code', '')
            if search and search not in name.lower() and search not in code.lower():
                continue
            # Renk bilgisi varsa göster
            color_str = prof.get('color', '')
            color_label = f'  🎨{color_str}' if color_str else ''
            # Ölçü bilgisi
            h  = prof.get('height_mm', 0) or prof.get('height', 0) or 0
            w  = prof.get('width_mm',  0) or prof.get('width',  0) or 0
            dim_str = f'  {h:.0f}×{w:.0f}mm' if (h or w) else ''

            display = f'{name}  [{code}]{dim_str}{color_label}'

            from PySide6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, prof)
            self._lst.addItem(item)

        # Last-used seçili yap
        last = cg.get_last_used(self._library, self._type)
        if last:
            for i in range(self._lst.count()):
                it = self._lst.item(i)
                if it.data(Qt.UserRole).get('stock_code') == last:
                    self._lst.setCurrentRow(i)
                    self._apply_profile(it.data(Qt.UserRole))
                    break

    def _on_profile_selected(self, item):
        prof = item.data(Qt.UserRole)
        if prof:
            self._apply_profile(prof)

    def _apply_profile(self, prof: dict):
        """Seçilen profilin tüm bilgilerini forma doldur."""
        import code_generator as cg

        sc   = prof.get('stock_code', '')
        name = prof.get('name', '')
        dxf  = prof.get('dxf_path', '')

        # Stok
        self._ed_sc.setText(sc)
        self._ed_sn.setText(name)

        # Renk
        color = prof.get('color', '') or ''
        idx   = self._cb_color.findData(color)
        if idx >= 0:
            self._cb_color.setCurrentIndex(idx)

        # Bar boyu
        bar = prof.get('bar_length', 0) or prof.get('bar_len', 0) or 0
        if bar > 0:
            self._sp_bar.setValue(bar)

        # DXF → profil ölçüleri
        self._dxf_path = dxf
        if dxf and os.path.isfile(dxf):
            ph, pw = _dxf_dims(dxf)
            if ph > 0: self._sp_ph.setValue(round(ph, 1))
            if pw > 0: self._sp_pw.setValue(round(pw, 1))
            self._lbl_dxf.setText(f'DXF: {os.path.basename(dxf)}')
            self._lbl_dxf.setStyleSheet('color:#44cc88; font-size:10px;')
        else:
            # DXF yoksa kütüphanedeki ölçüleri kullan
            h = prof.get('height_mm', 0) or prof.get('height', 0) or 0
            w = prof.get('width_mm',  0) or prof.get('width',  0) or 0
            if h > 0: self._sp_ph.setValue(round(h, 1))
            if w > 0: self._sp_pw.setValue(round(w, 1))
            self._lbl_dxf.setText('DXF: yok (ölçüler kütüphaneden)')
            self._lbl_dxf.setStyleSheet('color:#667; font-size:10px;')

        # Seçili profil etiketi
        h_val = self._sp_ph.value(); w_val = self._sp_pw.value()
        self._lbl_selected.setText(
            f'✅  {name}  |  Stok: {sc}\n'
            f'G={w_val:.1f}mm  Y={h_val:.1f}mm  '
            f'Renk: {color or "—"}'
        )
        self._lbl_selected.setStyleSheet(
            'background:#1a2a1a;color:#80ff80;border:1px solid #3a5a3a;'
            'border-radius:4px;padding:6px;font-size:11px;')

        # last_used güncelle
        try:
            cg.set_last_used(self._library, self._type, sc)
            cg.save_library(self._library)
        except Exception:
            pass

    # ── Manuel DXF ───────────────────────────────────────────────

    def _pick_dxf(self):
        path = _ask_dxf(self, 'Profil DXF Dosyası Seç')
        if not path:
            return
        self._dxf_path = path
        fname = os.path.basename(path)
        self._lbl_dxf.setText(f'DXF: {fname}')
        self._lbl_dxf.setStyleSheet('color:#44cc88; font-size:10px;')
        ph, pw = _dxf_dims(path)
        if ph > 0: self._sp_ph.setValue(round(ph, 1))
        if pw > 0: self._sp_pw.setValue(round(pw, 1))

    # ── Kabul ────────────────────────────────────────────────────

    def _on_accept(self):
        if not self._ed_sc.text().strip():
            QMessageBox.warning(self, 'Eksik Bilgi',
                'Lütfen soldaki listeden bir profil seçin\n'
                'veya Stok Kodu alanını doldurun.')
            return
        self.accept()

    def get_frame_data(self) -> dict:
        return {
            'type':           self._type,
            'w':              self._sp_w.value(),
            'h':              self._sp_h.value(),
            'profile_width':  self._sp_pw.value(),
            'profile_height': self._sp_ph.value(),
            'kerf':           self._sp_kerf.value(),
            'bar_len':        self._sp_bar.value(),
            'stock_code':     self._ed_sc.text().strip(),
            'stock_name':     self._ed_sn.text().strip(),
            'order_no':       self._ed_order.text().strip(),
            'color_code':     self._cb_color.currentData() or '',
            'dxf_path':       self._dxf_path,
        }


# ─────────────────────────────────────────────────────────────────────
# Ana dialog
# ─────────────────────────────────────────────────────────────────────

class FrameDesignerDialog(QDialog):
    records_ready = Signal(list)

    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self._db     = db
        self._frames: list = []
        self.setWindowTitle('🏗  Çerçeve Tasarımcısı')
        self.setMinimumSize(1100, 680)
        self.resize(1200, 740)
        self._setup_ui()
        self._apply_style()
        self._update_mdb_label()
        self._load_design()   # Önceki çalışmayı yükle

    # ─── UI ───────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10,10,10,10); root.setSpacing(8)

        title = QLabel('🏗  Çerçeve Tasarımcısı')
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial',14,QFont.Bold))
        title.setStyleSheet('color:#f8c12f; background:#252538; border-radius:6px; padding:8px;')
        root.addWidget(title)

        # Ekle butonları
        add_row = QHBoxLayout()
        add_row.addWidget(QLabel('Ekle:'))
        for typ, (grp_name, grp_color) in TYPE_GROUP.items():
            short = grp_name.rstrip('lar').rstrip('ler').strip()[:10]
            btn = QPushButton(f'＋ {short}')
            btn.setFixedHeight(30)
            btn.setStyleSheet(
                f'QPushButton{{background:{grp_color};color:#fff;border-radius:4px;'
                f'font-size:11px;font-weight:bold;padding:0 6px;}}'
                f'QPushButton:hover{{border:1px solid #fff;}}')
            btn.setToolTip(f'{grp_name}  (Tip {typ})')
            btn.clicked.connect(lambda checked, t=typ: self._add_frame(t))
            add_row.addWidget(btn)
        add_row.addStretch()

        # MDB durum etiketi + bağlan butonu (sağ taraf)
        self._lbl_mdb = QLabel('MDB: bağlı değil')
        self._lbl_mdb.setStyleSheet('color:#ff8888; font-size:11px; padding:0 6px;')
        add_row.addWidget(self._lbl_mdb)

        self._btn_mdb = QPushButton('💾  MDB Bağlan')
        self._btn_mdb.setFixedHeight(30)
        self._btn_mdb.setStyleSheet(
            'QPushButton{background:#1a3a5c;color:#88bbff;border:1px solid #3a5a8a;'
            'border-radius:4px;font-size:11px;font-weight:bold;padding:0 10px;}'
            'QPushButton:hover{background:#2a4a7c;}')
        self._btn_mdb.clicked.connect(self._connect_mdb)
        add_row.addWidget(self._btn_mdb)

        root.addLayout(add_row)

        # ── Kaynak Payı seçeneği ─────────────────────────────
        opt_row = QHBoxLayout()
        opt_row.setContentsMargins(4, 0, 4, 0)

        self._chk_weld = QCheckBox('🔩  Kaynak Payı Ekle')
        self._chk_weld.setChecked(True)
        self._chk_weld.setStyleSheet(
            'QCheckBox{color:#f8c12f;font-size:12px;font-weight:bold;}'
            'QCheckBox::indicator{width:16px;height:16px;}'
            'QCheckBox::indicator:checked{background:#2a6a2a;border:2px solid #4a9a4a;border-radius:3px;}'
            'QCheckBox::indicator:unchecked{background:#3a1a1a;border:2px solid #7a3a3a;border-radius:3px;}')
        self._chk_weld.setToolTip(
            'İşaretli → kesim boyuna kaynak payı eklenir\n'
            'İşaretsiz → sadece çerçeve ölçüsü + kesim payı')
        self._chk_weld.toggled.connect(self._on_weld_toggled)
        opt_row.addWidget(self._chk_weld)

        opt_row.addWidget(QLabel('  Pay:'))
        self._sp_weld = QDoubleSpinBox()
        self._sp_weld.setRange(0, 50)
        self._sp_weld.setValue(1.0)
        self._sp_weld.setDecimals(1)
        self._sp_weld.setSuffix(' mm')
        self._sp_weld.setFixedWidth(90)
        self._sp_weld.setFixedHeight(26)
        self._sp_weld.setToolTip('Her parçaya eklenecek kaynak payı (mm)')
        self._sp_weld.valueChanged.connect(self._on_weld_toggled)
        opt_row.addWidget(self._sp_weld)

        self._lbl_weld_info = QLabel('  (her parçaya +1.0mm)')
        self._lbl_weld_info.setStyleSheet('color:#aaa; font-size:11px;')
        opt_row.addWidget(self._lbl_weld_info)

        opt_row.addStretch()
        root.addLayout(opt_row)

        # Splitter
        from PySide6.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        # Sol: Liste
        left_w = QWidget()
        left_lay = QVBoxLayout(left_w)
        left_lay.setContentsMargins(0,0,4,0)
        splitter.addWidget(left_w)

        lbl_list = QLabel('📋  Çerçeveler  (tipe göre gruplu)')
        lbl_list.setStyleSheet('color:#f8c12f; font-size:12px; font-weight:bold;')
        left_lay.addWidget(lbl_list)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setStyleSheet(
            'QTreeWidget{background:#16162a;color:#fff;border:1px solid #3a3a55;font-size:12px;}'
            'QTreeWidget::item{padding:4px;color:#fff;}'
            'QTreeWidget::item:selected{background:#5a3ea0;}'
            'QTreeWidget::item:hover{background:#2a2a45;}')
        self._tree.currentItemChanged.connect(self._on_tree_selection)
        left_lay.addWidget(self._tree, 1)

        self._lbl_list_info = QLabel('Henüz çerçeve yok')
        self._lbl_list_info.setStyleSheet('color:#888; font-size:11px;')
        left_lay.addWidget(self._lbl_list_info)

        btn_del = QPushButton('🗑  Seçiliyi Sil')
        btn_del.setFixedHeight(28)
        btn_del.clicked.connect(self._del_selected)
        left_lay.addWidget(btn_del)

        # Orta: Detay
        mid_w = QWidget()
        mid_lay = QVBoxLayout(mid_w)
        mid_lay.setContentsMargins(4,0,4,0)
        splitter.addWidget(mid_w)

        lbl_d = QLabel('📐  Detay')
        lbl_d.setStyleSheet('color:#f8c12f; font-size:12px; font-weight:bold;')
        mid_lay.addWidget(lbl_d)

        self._lbl_detail = QLabel('← Soldan bir çerçeve seçin')
        self._lbl_detail.setStyleSheet(
            'background:#252540; color:#aaa; border:1px solid #3a3a55;'
            ' border-radius:4px; padding:8px; font-size:12px;')
        self._lbl_detail.setWordWrap(True)
        mid_lay.addWidget(self._lbl_detail)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ['Yön','SIDE','Kesim Boyu','LENGTH(×10)','Sol°','Sağ°'])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setMaximumHeight(165)
        mid_lay.addWidget(self._table)
        mid_lay.addStretch()

        # Sağ: Görsel
        right_w = QWidget()
        right_lay = QVBoxLayout(right_w)
        right_lay.setContentsMargins(4,0,0,0)
        splitter.addWidget(right_w)

        self._fig    = Figure(facecolor='#f5f5f0')
        self._canvas = FigureCanvas(self._fig)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_lay.addWidget(self._canvas, 1)

        self._lbl_summary = QLabel('')
        self._lbl_summary.setStyleSheet('color:#aaa; font-size:11px;')
        self._lbl_summary.setAlignment(Qt.AlignCenter)
        right_lay.addWidget(self._lbl_summary)

        splitter.setSizes([260, 400, 430])

        # Alt butonlar
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet('color:#3a3a55;'); root.addWidget(sep)

        btn_row = QHBoxLayout()
        self._btn_save_all = QPushButton('✅  Tümünü MDB\'ye Kaydet')
        self._btn_save_all.setEnabled(False)
        self._btn_save_all.setMinimumHeight(44)
        self._btn_save_all.setFont(QFont('Arial',13,QFont.Bold))
        self._btn_save_all.setStyleSheet(
            'QPushButton{background:#1a5c1a;color:#fff;border-radius:6px;}'
            'QPushButton:hover{background:#237523;}'
            'QPushButton:disabled{background:#252535;color:#555;}')
        self._btn_save_all.clicked.connect(self._on_save_all)
        btn_row.addWidget(self._btn_save_all)
        btn_row.addStretch()

        btn_reset = QPushButton('🗑  Tasarımı Sıfırla')
        btn_reset.setMinimumHeight(44)
        btn_reset.setStyleSheet(
            'QPushButton{background:#5a1a1a;color:#ff8888;border-radius:5px;font-size:12px;}'
            'QPushButton:hover{background:#882222;}')
        btn_reset.setToolTip('Tüm çerçeveleri listeden temizle (MDB\'yi etkilemez)')
        btn_reset.clicked.connect(self._reset_design)
        btn_row.addWidget(btn_reset)

        btn_close = QPushButton('✖  Kapat')
        btn_close.setMinimumHeight(44)
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog{background:#16161f; color:#e0e0e0;}
            QLabel{color:#ddd; font-size:12px;}
            QGroupBox{color:#f8c12f; font-size:12px; font-weight:bold;
                border:1px solid #3a3a55; border-radius:5px;
                margin-top:8px; padding-top:10px;}
            QGroupBox::title{subcontrol-origin:margin; left:8px;}
            QPushButton{background:#2e2e42; color:#ddd; border:1px solid #444;
                border-radius:4px; padding:5px 12px; font-size:12px;}
            QPushButton:hover{background:#3a3a55;}
            QTableWidget{background:#16162a; color:#fff; font-size:12px;
                gridline-color:#2a2a45; border:1px solid #3a3a55;}
            QTableWidget::item{color:#fff; padding:4px;}
            QHeaderView::section{background:#252540; color:#f8c12f; font-size:11px;
                font-weight:bold; border:none; border-bottom:1px solid #3a3a55; padding:4px;}
        """)

    # ─── Çerçeve ekle / sil ───────────────────────────────

    def _get_selected_frame(self):
        """Tree'de seçili frame'i döndürür (None ise yok)."""
        item = self._tree.currentItem()
        if not item:
            return None
        fid = item.data(0, Qt.UserRole)
        if fid is None:
            return None
        return next((f for f in self._frames if f['_id'] == fid), None)

    def _add_frame(self, profile_type: str):
        """Seçilen tipe göre frame ekler. Kanat türleri SEÇILI kasadan ölçü önerir."""
        is_sash = profile_type in ('B','C','D','G','J')

        suggested_w = suggested_h = None
        parent_kasa = None
        if is_sash:
            # Önce tree'de seçili kasa var mı?
            sel = self._get_selected_frame()
            if sel and sel['type'] in ('A','F','H','I'):
                parent_kasa = sel   # Seçili kasayı kullan
            else:
                # Seçili kasa yoksa: listede hiç kasa var mı?
                kasa_frames = [f for f in self._frames if f['type'] in ('A','F','H','I')]
                if kasa_frames:
                    # Uyarı: kullanıcıya seçmesini söyle
                    if len(kasa_frames) > 1:
                        QMessageBox.information(self, 'Kasa Seçin',
                            'Birden fazla kasa var.\n'
                            'Soldaki listeden önce hangi kasaya kanat ekleyeceğini seçin.')
                        return
                    parent_kasa = kasa_frames[0]

            if parent_kasa:
                pw = parent_kasa['profile_width']
                suggested_w = (parent_kasa['w'] - 2*pw) + SASH_OVERLAP
                suggested_h = (parent_kasa['h'] - 2*pw) + SASH_OVERLAP

        extra = ''
        if parent_kasa:
            extra = f'  (Kasa: {parent_kasa["w"]:.0f}×{parent_kasa["h"]:.0f})'

        dlg = AddFrameDialog(self, profile_type, suggested_w, suggested_h, extra)

        # DXF yüklüyse profil ölçülerini otomatik doldur
        mw = self.parent()
        if mw and hasattr(mw, '_cur_segs') and mw._cur_segs:
            try:
                from dxf_loader import calc_profile_dimensions
                ph, pw = calc_profile_dimensions(mw._cur_segs)
                if ph > 0: dlg._sp_ph.setValue(round(ph,1))
                if pw > 0: dlg._sp_pw.setValue(round(pw,1))
            except Exception:
                pass

        if dlg.exec() != QDialog.Accepted:
            return

        frame = dlg.get_frame_data()
        frame['_id']       = len(self._frames)
        frame['parent_id'] = parent_kasa['_id'] if parent_kasa else None
        self._frames.append(frame)
        self._rebuild_tree()
        self._save_design()   # Ekle → kaydet
        self._update_mdb_label()

    # ─── JSON kalıcılık ───────────────────────────────────

    def _design_path(self) -> str:
        """Tasarım JSON dosyasının yolu."""
        if self._db and self._db.db_path:
            base = os.path.splitext(self._db.db_path)[0]
            return base + '_frames_design.json'
        # DB yoksa kullanıcı masaüstü
        return os.path.join(os.path.expanduser('~'), 'Desktop',
                            'winsa_frames_design.json')

    def _save_design(self):
        """Çerçeve listesini JSON'a kaydet."""
        try:
            path = self._design_path()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._frames, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'[Çerçeve kayıt hatası] {e}')

    def _reset_design(self):
        reply = QMessageBox.question(self, 'Tasarımı Sıfırla',
            'Tüm çerçeveler listeden silinecek.\nMDB\'deki kayıtlar etkilenmez.\nDevam edilsin mi?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self._frames = []
        self._rebuild_tree()
        self._save_design()
        self._btn_save_all.setEnabled(False)
        self._clear_detail()

    def _load_design(self):
        """Önceki çalışmayı JSON'dan yükle."""
        try:
            path = self._design_path()
            if not os.path.exists(path):
                return
            with open(path, 'r', encoding='utf-8') as f:
                frames = json.load(f)
            if not frames:
                return
            self._frames = frames
            # _id'lerin benzersizliğini koru
            max_id = max((f.get('_id', 0) for f in self._frames), default=0)
            self._next_id = max_id + 1
            self._rebuild_tree()
            self._update_mdb_label()
        except Exception as e:
            print(f'[Çerçeve yükleme hatası] {e}')

    def _del_selected(self):
        item = self._tree.currentItem()
        if not item or item.data(0, Qt.UserRole) is None:
            return
        fid = item.data(0, Qt.UserRole)
        self._frames = [f for f in self._frames if f['_id'] != fid]
        self._rebuild_tree()
        self._save_design()   # Sil → kaydet
        if not self._frames:
            self._btn_save_all.setEnabled(False)
            self._clear_detail()

    def _rebuild_tree(self):
        self._tree.clear()

        # Grupları her zaman TYPE_GROUP sırasında oluştur (sabit sıra)
        for typ, (grp_name, grp_color) in TYPE_GROUP.items():
            type_frames = [f for f in self._frames if f['type'] == typ]
            if not type_frames:
                continue   # Bu tipte çerçeve yoksa grubu gösterme

            root_item = QTreeWidgetItem([f'{grp_name}  ({len(type_frames)})'])
            root_item.setFont(0, QFont('Arial', 11, QFont.Bold))
            root_item.setForeground(0, QBrush(QColor(grp_color)))
            root_item.setFlags(root_item.flags() & ~Qt.ItemIsSelectable)
            self._tree.addTopLevelItem(root_item)
            root_item.setExpanded(True)

            for frame in type_frames:
                w  = frame['w']; h = frame['h']
                sc = frame['stock_name'] or frame['stock_code'][:8]
                dxf_icon = ' 📄' if frame.get('dxf_path') else ''
                label = f'  {w:.0f} × {h:.0f} mm   {sc}{dxf_icon}'
                child = QTreeWidgetItem([label])
                child.setData(0, Qt.UserRole, frame['_id'])
                child.setForeground(0, QBrush(QColor('#ffffff')))
                root_item.addChild(child)

        total = len(self._frames) * 4
        self._lbl_list_info.setText(f'{len(self._frames)} çerçeve  |  {total} parça')

    def _on_tree_selection(self, current, previous):
        if not current:
            return
        fid = current.data(0, Qt.UserRole)
        if fid is None:
            return
        frame = next((f for f in self._frames if f['_id'] == fid), None)
        if frame:
            self._show_detail(frame)

    # ─── Detay + Görsel ───────────────────────────────────

    def _show_detail(self, frame: dict):
        typ      = frame['type']
        w        = frame['w']; h = frame['h']
        pw       = frame['profile_width']
        ph       = frame['profile_height']
        kerf     = frame['kerf']
        dxf_file = os.path.basename(frame.get('dxf_path','')) or '—'

        # İç ölçü (bilgi amaçlı)
        inner_w = w - 2*pw
        inner_h = h - 2*pw

        # Parent kasa bilgisi
        parent_info = ''
        if frame.get('parent_id') is not None:
            pk = next((f for f in self._frames if f['_id'] == frame['parent_id']), None)
            if pk:
                parent_info = f'\nBağlı Kasa: {pk["w"]:.0f}×{pk["h"]:.0f} mm'

        self._lbl_detail.setText(
            f'<b>{PROFILE_TYPES.get(typ,typ)}</b>  —  {w:.0f} × {h:.0f} mm\n'
            f'Profil: G={pw:.1f}mm  Y={ph:.1f}mm   İç açıklık: {inner_w:.0f}×{inner_h:.0f}mm\n'
            f'Stok: {frame["stock_code"]}  {frame["stock_name"]}\n'
            f'Kesim payı: {kerf:.1f}mm   DXF: {dxf_file}{parent_info}'
        )
        self._lbl_detail.setStyleSheet(
            'background:#0d2010; color:#eee; border:1px solid #3a3a55;'
            ' border-radius:4px; padding:8px; font-size:12px;')

        pieces = self._calc_pieces(frame)
        self._table.setRowCount(0)
        for p in pieces:
            r = self._table.rowCount()
            self._table.insertRow(r)
            bg = QColor(SIDE_COLOR[p['side']]); bg.setAlpha(70)
            data = [SIDE_NAME[p['side']], str(p['side']),
                    f'{p["length_mm"]:.1f} mm', str(p['length_x10']), '450','450']
            for c, txt in enumerate(data):
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor('#ffffff'))
                item.setBackground(bg)
                if c == 2:
                    item.setForeground(QColor('#5ef0ff'))
                    item.setFont(QFont('Courier New',11,QFont.Bold))
                self._table.setItem(r, c, item)
            self._table.setRowHeight(r, 28)

        self._draw_preview(frame, pieces)
        weld = self._weld_adj()
        total = 2*(w+weld) + 2*(h+weld)
        weld_str = f' +{weld:.0f}mm kaynak' if weld else ''
        self._lbl_summary.setText(f'Toplam: {total:.0f} mm  |  2×{w+weld:.0f} + 2×{h+weld:.0f} mm{weld_str}')

    def _clear_detail(self):
        self._lbl_detail.setText('← Soldan bir çerçeve seçin')
        self._table.setRowCount(0)
        self._fig.clear(); self._canvas.draw_idle()
        self._lbl_summary.setText('')

    def _calc_pieces(self, frame: dict) -> list:
        w = frame['w']; h = frame['h']
        weld = self._weld_adj()   # 0 ise kaynak payı yok
        pieces = []
        for side, dim in [(2,w),(4,w),(1,h),(3,h)]:
            lmm = dim + weld      # sadece çerçeve ölçüsü + kaynak payı (kerf eklenmez)
            pieces.append({'side':side, 'length_mm':lmm,
                           'length_x10':int(lmm*10),
                           'frame_x':w, 'frame_y':h})
        return pieces

    def _draw_mitered_frame(self, ax, ox, oy, W, H, pw, color, alpha,
                             add_rebate=True, shadow=False, zbase=2):
        """
        45° gönyeli çerçeve çizer.
        - Her kenar profil trapez olarak çizilir (45° köşe)
        - Dış kenar highlight + iç glazing rebate çizgisi eklenir
        - shadow=True: hafif gölge efekti
        """
        from matplotlib.patches import Polygon as MplPolygon, Rectangle

        # ── Hafif dış gölge ──────────────────────────────
        if shadow:
            for sh in (4, 2):
                ax.add_patch(Rectangle(
                    (ox + sh, oy - sh), W, H,
                    facecolor='#999999', alpha=0.06, edgecolor='none', zorder=zbase-1))

        # ── Dış çerçeve doldurma (iç+dış arasındaki alan) ────
        # Dış dikdörtgen dolduruluyor — sonra iç cam alanı üstüne çizilecek
        ax.add_patch(Rectangle(
            (ox, oy), W, H,
            facecolor=color, alpha=alpha,
            edgecolor='none', zorder=zbase))

        # ── 45° köşe gönye çizgileri (trapez kenarları) ──────
        # 4 köşede 45° çizgi — gerçekçi gönye kesiş görünümü
        corner_lines = [
            # alt-sol, alt-sağ, üst-sol, üst-sağ
            [(ox, oy), (ox+pw, oy+pw)],
            [(ox+W, oy), (ox+W-pw, oy+pw)],
            [(ox, oy+H), (ox+pw, oy+H-pw)],
            [(ox+W, oy+H), (ox+W-pw, oy+H-pw)],
        ]
        for (x0, y0), (x1, y1) in corner_lines:
            ax.plot([x0, x1], [y0, y1],
                    color='#555555', lw=0.7, alpha=0.7, zorder=zbase+2)

        # ── Dış kenar (kalın çizgi = metal yüzey) ─────────────
        ax.add_patch(Rectangle(
            (ox, oy), W, H,
            facecolor='none',
            edgecolor='#555555', linewidth=1.5, zorder=zbase+2))

        # ── Profil üst yüzey highlight (metalik parlaklık) ───
        hl_w = pw * 0.18
        # Üst kenar highlight
        ax.add_patch(MplPolygon(
            [(ox, oy+H), (ox+W, oy+H),
             (ox+W-hl_w, oy+H-hl_w), (ox+hl_w, oy+H-hl_w)],
            facecolor='white', alpha=0.22, edgecolor='none', zorder=zbase+1))
        # Sol kenar highlight
        ax.add_patch(MplPolygon(
            [(ox, oy+H), (ox+hl_w, oy+H-hl_w),
             (ox+hl_w, oy+hl_w), (ox, oy)],
            facecolor='white', alpha=0.18, edgecolor='none', zorder=zbase+1))

        # ── Glazing rebate (sır kanalı çizgisi) ──────────────
        if add_rebate:
            rd = pw * 0.60   # iç kenara yakın, gerçek profil gibi
            rc = '#707070'
            rz = zbase + 3
            ax.plot([ox+rd, ox+W-rd], [oy+rd, oy+rd], color=rc, lw=0.6, alpha=0.8, zorder=rz)
            ax.plot([ox+rd, ox+W-rd], [oy+H-rd, oy+H-rd], color=rc, lw=0.6, alpha=0.8, zorder=rz)
            ax.plot([ox+rd, ox+rd], [oy+rd, oy+H-rd], color=rc, lw=0.6, alpha=0.8, zorder=rz)
            ax.plot([ox+W-rd, ox+W-rd], [oy+rd, oy+H-rd], color=rc, lw=0.6, alpha=0.8, zorder=rz)

    def _find_related(self, frame: dict):
        """
        Seçilen çerçeveye ait kasa ve kanat ikilisini döndürür.
        Kasa seçildiyse: (kasa, ilk_child_kanat)
        Kanat seçildiyse: (parent_kasa, kanat)
        Tek çerçeveyse: (frame, None) veya (None, frame)
        """
        is_sash = frame['type'] in ('B','C','D','G','J')
        is_kasa = frame['type'] in ('A','F','H','I')

        if is_kasa:
            # Bu kasaya bağlı kanat var mı?
            fid = frame.get('_id')
            children = [f for f in self._frames
                        if f.get('parent_id') == fid
                        and f['type'] in ('B','C','D','G','J')]
            return frame, (children[0] if children else None)

        if is_sash:
            # Parent kasası var mı?
            pid = frame.get('parent_id')
            if pid is not None:
                kasa = next((f for f in self._frames if f.get('_id') == pid), None)
                return kasa, frame
            # Parent yok ama listede kasa varsa onu kullan
            kasalar = [f for f in self._frames if f['type'] in ('A','F','H','I')]
            return (kasalar[-1] if kasalar else None), frame

        return frame, None

    def _draw_preview(self, frame: dict, pieces: list):
        self._fig.clear()
        ax = self._fig.add_subplot(111)
        ax.set_facecolor('#f5f5f0')
        ax.set_aspect('equal')

        kasa_f, sash_f = self._find_related(frame)

        if kasa_f and sash_f:
            # ── İÇ İÇE: GRİ KASA + SARI KANAT ──
            kW  = kasa_f['w']; kH  = kasa_f['h']; kpw = kasa_f['profile_width']
            W   = sash_f['w']; H   = sash_f['h']; pw  = sash_f['profile_width']

            # Kasa iç alanı arka plan
            ax.add_patch(mpatches.Rectangle(
                (kpw, kpw), kW-2*kpw, kH-2*kpw,
                facecolor='#ddeeff', alpha=0.55, edgecolor='none', zorder=1))

            # Gri kasa (dış çerçeve) — gümüş alüminyum rengi + gölge
            self._draw_mitered_frame(ax, 0, 0, kW, kH, kpw,
                color='#c0c0c0', alpha=0.97, shadow=True, zbase=2)

            kk = kasa_f['kerf']   # kasa kesim payı
            sk = sash_f['kerf']   # kanat kesim payı

            # Kasa iç etiket — sadece küçük tip kısaltması
            for tx, ty, txt in [
                (kW/2, kH-kpw/2, 'K'), (kW/2, kpw/2, 'K'),
                (kpw/2, kH/2, 'K'),    (kW-kpw/2, kH/2, 'K'),
            ]:
                ax.text(tx, ty, txt, ha='center', va='center',
                        color='#444444', fontsize=6.5, zorder=14)

            # Kanat — kasa iç açıklığına bindirerek yerleştirilir
            half = SASH_OVERLAP / 2
            sx = kpw - half   # kanat sol kenarı
            sy = kpw - half   # kanat alt kenarı

            # Kanat çerçevesi (profil rengiyle)
            sash_color = _type_color(sash_f['type'])
            self._draw_mitered_frame(ax, sx, sy, W, H, pw,
                color=sash_color, alpha=0.95, zbase=5)

            # Kanat iç etiket — sadece küçük kısaltma
            lbl_c = _label_color(sash_color)
            for tx, ty, txt in [
                (sx+W/2, sy+H-pw/2, 'Kn'), (sx+W/2, sy+pw/2, 'Kn'),
                (sx+pw/2, sy+H/2, 'Kn'),   (sx+W-pw/2, sy+H/2, 'Kn'),
            ]:
                ax.text(tx, ty, txt, ha='center', va='center',
                        color=lbl_c, fontsize=6, alpha=0.85, zorder=14)

            # ── Cam bölgesi ──────────────────────────────
            gx = sx+pw;  gy = sy+pw
            gw = W-2*pw; gh = H-2*pw
            # Cam ana dolgu — açık mavi, yarı saydam
            ax.add_patch(mpatches.Rectangle(
                (gx, gy), gw, gh,
                facecolor='#cce8f8', alpha=0.65,
                edgecolor='#5599bb', lw=0.8, zorder=9))
            # Cam çapraz çizgileri (X işareti — mimari standart)
            ax.plot([gx, gx+gw], [gy+gh, gy],
                    color='#5577aa', alpha=0.50, lw=0.9, zorder=10)
            ax.plot([gx, gx+gw], [gy, gy+gh],
                    color='#5577aa', alpha=0.50, lw=0.9, zorder=10)
            # Cam yansıma / parlaklık çizgisi (sol-üst köşeden çapraz ince beyaz)
            ax.plot([gx+gw*0.05, gx+gw*0.28], [gy+gh*0.95, gy+gh*0.72],
                    color='white', alpha=0.60, lw=2.5, solid_capstyle='round', zorder=11)
            ax.plot([gx+gw*0.08, gx+gw*0.18], [gy+gh*0.82, gy+gh*0.72],
                    color='white', alpha=0.40, lw=1.2, solid_capstyle='round', zorder=11)
            # İç ölçü etiketi
            ax.text(gx+gw/2, gy+gh/2, f'{gw:.0f} × {gh:.0f}',
                    ha='center', va='center', color='#1a3a55', fontsize=8, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=3', fc='white', alpha=0.88, ec='#99bbcc'),
                    zorder=12)

            # ── Menteşe ve Kol ───────────────────────────
            if sash_f['type'] in ('B','C','D','G','J'):
                h_offset = min(H * 0.20, 180)
                self._draw_hinges(ax, sx + pw*0.5, sy + h_offset, sy + H - h_offset, pw)
                is_door = sash_f['type'] == 'J'
                self._draw_handle(ax, sx + W - pw*0.5, sy + H / 2, is_door, max(kW, kH))

            # ── Dış etiket sistemi ───────────────────────────
            weld  = self._weld_adj()
            gap   = max(kpw, pw) * 0.55
            bk    = dict(boxstyle='round,pad=2', fc='#ffffff', ec='#336699',
                         alpha=0.95, linewidth=0.9)

            def _out_lbl(x, y, txt, ha='center', va='center'):
                ax.text(x, y, txt, ha=ha, va=va, color='#1a1a1a',
                        fontsize=7, fontweight='bold', bbox=bk, zorder=15)

            # ÜST  (kasa dış, kanat iç → iki satır)
            _out_lbl(kW/2, kH + gap*1.6,
                     f'ÜST   K: {kW+weld:.0f} mm  ╱  Kn: {W+weld:.0f} mm',
                     va='bottom')
            # ALT
            _out_lbl(kW/2, -gap*1.6,
                     f'ALT   K: {kW+weld:.0f} mm  ╱  Kn: {W+weld:.0f} mm',
                     va='top')
            # SOL (sol kenar dışı)
            _out_lbl(-gap*1.6, kH/2,
                     f'SOL\nK: {kH+weld:.0f}\nKn: {H+weld:.0f} mm',
                     ha='right')
            # SAĞ (sağ kenar dışı — koldan tamamen uzak)
            _out_lbl(kW + gap*1.6, kH/2,
                     f'SAĞ\nK: {kH+weld:.0f}\nKn: {H+weld:.0f} mm',
                     ha='left')

            # Alt başlık
            sash_type = PROFILE_TYPES.get(sash_f['type'], 'Kanat')
            ax.text(kW/2, -gap*3.2,
                    f'KASA {kW:.0f}×{kH:.0f}   |   {sash_type} {W:.0f}×{H:.0f}',
                    ha='center', color='#444444', fontsize=9, va='top')

            margin = max(kW, kH) * 0.14
            ext    = gap * 2.2
            ax.set_xlim(-ext, kW + ext)
            ax.set_ylim(-gap * 3.8, kH + ext * 0.9)

        else:
            # ── TEK ÇERÇEVE ──
            f = kasa_f or sash_f
            W  = f['w']; H = f['h']; pw = f['profile_width']
            is_kasa_single = f['type'] in ('A','F','H','I')
            color = '#c0c0c0' if is_kasa_single else _type_color(f['type'])

            self._draw_mitered_frame(ax, 0, 0, W, H, pw,
                color=color, alpha=0.95, shadow=True)

            # Cam / iç alan
            ax.add_patch(mpatches.Rectangle((pw, pw), W-2*pw, H-2*pw,
                facecolor='#cce8f8', alpha=0.60, edgecolor='#5599bb', lw=0.7, zorder=9))
            # Cam çapraz
            gx, gy, gw, gh = pw, pw, W-2*pw, H-2*pw
            ax.plot([gx, gx+gw], [gy+gh, gy], color='#5577aa', alpha=0.45, lw=0.9, zorder=10)
            ax.plot([gx, gx+gw], [gy, gy+gh], color='#5577aa', alpha=0.45, lw=0.9, zorder=10)
            ax.plot([gx+gw*0.05, gx+gw*0.28], [gy+gh*0.95, gy+gh*0.72],
                    color='white', alpha=0.55, lw=2.0, solid_capstyle='round', zorder=11)

            tag = 'KASA' if is_kasa_single else 'KANAT'
            ax.text(W/2, H/2, f'{tag}  {W:.0f}×{H:.0f}',
                    ha='center', va='center', color='#1a3355', fontsize=9, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=3', fc='white', alpha=0.88, ec='#99bbcc'),
                    zorder=12)

            margin = max(W, H) * 0.12
            ax.set_xlim(-margin, W+margin*0.5)
            ax.set_ylim(-margin, H+margin*0.5)

        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values(): sp.set_visible(False)
        self._canvas.draw_idle()

    # ─── Menteşe çizimi ──────────────────────────────────

    def _draw_hinges(self, ax, hinge_x, y1, y2, pw):
        """
        Sol profile iki menteşe çiz — referans resme göre:
        • Dışarıdan görünen ince yatay plaka (kasa dışına hafif taşan)
        • İki vida deliği
        """
        from matplotlib.patches import FancyBboxPatch
        pw_s   = max(pw, 50)
        pl_w   = pw_s * 0.55    # plaka toplam genişliği (yatay)
        pl_h   = pw_s * 0.20    # plaka yüksekliği (ince)
        scr_r  = max(pw_s * 0.030, 2.0)

        for cy in (y1, y2):
            # Menteşe plakası — ince yatay dikdörtgen, sol profil dış yüzeyinde
            ax.add_patch(FancyBboxPatch(
                (hinge_x - pl_w * 0.55, cy - pl_h / 2),
                pl_w, pl_h,
                boxstyle='round,pad=1',
                fc='#ececec', ec='#aaaaaa', lw=1.0, zorder=11))
            # Üst kenar parlama
            ax.plot([hinge_x - pl_w*0.52, hinge_x + pl_w*0.42],
                    [cy - pl_h/2 + 1.5, cy - pl_h/2 + 1.5],
                    color='white', alpha=0.55, lw=0.9, zorder=12)
            # Vida delikleri (sol + sağ)
            for dx in (-pl_w*0.30, pl_w*0.28):
                ax.add_patch(mpatches.Circle(
                    (hinge_x + dx, cy), scr_r,
                    fc='#c0c0c0', ec='#888888', lw=0.7, zorder=12))
                # Vida haç
                ax.plot([hinge_x+dx-scr_r*0.65, hinge_x+dx+scr_r*0.65],
                        [cy, cy], color='#666', lw=0.6, zorder=13)
                ax.plot([hinge_x+dx, hinge_x+dx],
                        [cy-scr_r*0.65, cy+scr_r*0.65], color='#666', lw=0.6, zorder=13)

    # ─── Kol çizimi ──────────────────────────────────────

    def _draw_handle(self, ax, handle_x, handle_y, is_door, frame_size):
        """
        Sağ profil üzerine pencere/kapı kolu çiz.
        Referans resme göre: oval / spade şeklinde basit kol.
        """
        from matplotlib.patches import FancyBboxPatch
        import numpy as np
        s  = max(frame_size / 950, 0.5)
        rw = 9  * s   # rozet genişliği
        rh = 26 * s   # rozet yüksekliği

        # Rozet (ince dikey dikdörtgen, profil üstünde)
        ax.add_patch(FancyBboxPatch(
            (handle_x - rw/2, handle_y - rh/2), rw, rh,
            boxstyle='round,pad=1.5',
            fc='#e8e8e8', ec='#bbbbbb', lw=0.8, zorder=11))
        ax.plot([handle_x - rw/2 + 1.5, handle_x + rw/2 - 1.5],
                [handle_y - rh/2 + 2, handle_y - rh/2 + 2],
                color='white', alpha=0.5, lw=0.8, zorder=12)

        if is_door:
            # Kapı kolu: yatay oval kollu kap
            arm  = 44 * s
            kh   = 9  * s
            ax.add_patch(FancyBboxPatch(
                (handle_x + rw/2, handle_y - kh/2), arm, kh,
                boxstyle='round,pad=3.5',
                fc='#e0e0e0', ec='#bbbbbb', lw=0.9, zorder=11))
        else:
            # Pencere kolu: spade/oval — referans resimdeki gibi
            # Pivot noktası: rozetin ortası
            # Kol: ovale benzer şekil, sağa uzanır ve uç kısmında yuvarlak
            kol_w = 36 * s   # kol uzunluğu
            kol_h =  9 * s   # kol gövde yüksekliği
            tip_r =  8 * s   # uç yuvarlak

            # Kol gövdesi (yatay, rozetin sağından uzanır)
            ax.add_patch(FancyBboxPatch(
                (handle_x + rw/2, handle_y - kol_h/2),
                kol_w, kol_h,
                boxstyle='round,pad=2',
                fc='#e2e2e2', ec='#bbbbbb', lw=0.9, zorder=11))
            # Kol ucu (oval top)
            ax.add_patch(mpatches.Ellipse(
                (handle_x + rw/2 + kol_w, handle_y),
                tip_r * 2, tip_r * 1.6,
                fc='#d8d8d8', ec='#bbbbbb', lw=0.9, zorder=11))
            # Parlama
            ax.plot([handle_x + rw/2 + 2,
                     handle_x + rw/2 + kol_w - 2],
                    [handle_y - kol_h/2 + 1.5,
                     handle_y - kol_h/2 + 1.5],
                    color='white', alpha=0.45, lw=0.8, zorder=12)

    # ─── Kaynak Payı ─────────────────────────────────────

    def _on_weld_toggled(self):
        """Checkbox veya spinbox değişince bilgi etiketini güncelle, detayı yenile."""
        active = self._chk_weld.isChecked()
        val    = self._sp_weld.value()
        self._sp_weld.setEnabled(active)
        if active:
            self._lbl_weld_info.setText(f'  (her parçaya +{val:.1f}mm)')
            self._lbl_weld_info.setStyleSheet('color:#88ff88; font-size:11px;')
        else:
            self._lbl_weld_info.setText('  (kaynak payı yok)')
            self._lbl_weld_info.setStyleSheet('color:#ff8888; font-size:11px;')
        # Seçili çerçeve varsa detayı yenile
        frame = self._get_selected_frame()
        if frame:
            self._show_detail(frame)

    def _weld_adj(self) -> float:
        """Aktif kaynak payı miktarını döndür (mm). Kapalıysa 0."""
        if self._chk_weld.isChecked():
            return self._sp_weld.value()
        return 0.0

    # ─── MDB Bağlantı ────────────────────────────────────

    def _connect_mdb(self):
        """Doğrudan bu ekrandan MDB seç ve bağlan."""
        from PySide6.QtWidgets import QFileDialog
        from database import Database

        path, _ = QFileDialog.getOpenFileName(
            self, 'MDB Dosyası Seç', '', 'Access Veritabanı (*.mdb *.accdb)')
        if not path:
            return

        if self._db is None:
            self._db = Database()

        ok, msg = self._db.connect(path)
        self._update_mdb_label()
        if ok:
            # Tasarım yolunu güncelle (DB değişti)
            self._load_design()
            QMessageBox.information(self, '✅ Bağlandı',
                f'{os.path.basename(path)} bağlandı.\n{msg}')
        else:
            QMessageBox.critical(self, '❌ Bağlantı Hatası', msg)

    def _update_mdb_label(self):
        """MDB durum etiketini ve Kaydet butonunu güncelle."""
        if self._db and self._db.connected and getattr(self._db, 'db_path', None):
            name = os.path.basename(self._db.db_path)
            self._lbl_mdb.setText(f'MDB: ✅ {name}')
            self._lbl_mdb.setStyleSheet('color:#88ff88; font-size:11px; padding:0 6px;')
            self._btn_mdb.setText('💾  MDB Değiştir')
            self._btn_save_all.setEnabled(bool(self._frames))
        else:
            self._lbl_mdb.setText('MDB: bağlı değil')
            self._lbl_mdb.setStyleSheet('color:#ff8888; font-size:11px; padding:0 6px;')
            self._btn_mdb.setText('💾  MDB Bağlan')

    # ─── MDB Kaydet ───────────────────────────────────────

    def _on_save_all(self):
        if not self._frames:
            return
        if not self._db or not self._db.connected:
            reply = QMessageBox.question(self, 'MDB Bağlı Değil',
                'Henüz bir MDB dosyası seçilmedi.\nŞimdi bağlanmak ister misiniz?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self._connect_mdb()
            # Bağlantı başarılı olduysa devam et, değilse çık
            if not self._db or not self._db.connected:
                return

        try:
            existing = len(self._db.get_all_records())
        except Exception:
            existing = 0

        total_pieces = len(self._frames) * 4
        mb = QMessageBox(self)
        mb.setWindowTitle("MDB'ye Kaydet")
        mb.setIcon(QMessageBox.Question)
        mb.setText(f'{len(self._frames)} çerçeve → {total_pieces} parça.\nNasıl devam edilsin?')
        btn_append = mb.addButton(f'➕  İlave Et ({existing+1}\'den)',  QMessageBox.AcceptRole)
        btn_clear  = mb.addButton('🗑  Temizle ve Yaz (1\'den)',          QMessageBox.DestructiveRole)
        btn_cancel = mb.addButton('İptal',                                QMessageBox.RejectRole)
        mb.setDefaultButton(btn_append)
        mb.exec()

        if mb.clickedButton() == btn_cancel:
            return
        if mb.clickedButton() == btn_clear:
            self._db.clear_all_records(); start_no = 1
        else:
            try: start_no = self._db.get_next_program_no()
            except Exception: start_no = existing + 1

        # ── Bar atama: GLOBAL bar sayacı ──────────────────
        # Tüm proje boyunca barlar 1,2,3,4,5... diye artar
        # Farklı stok kodları farklı barlar kullanır ama numara global devam eder
        KERF_X10    = 60   # 6mm testere payı × 10
        global_bar  = 0    # Global bar sayacı
        # stock_code → {bar_no, bar_used}
        bar_state: dict = {}

        # ── Çerçeveleri tipe göre sırala ─────────────────────
        # Kasalar → Kanatlar → Kapı Kanatlar → diğerleri
        # Aynı tiptekiler birlikte gruplanır → barlar doğru sıralanır
        TYPE_ORDER = {
            'A': 0, 'F': 1, 'H': 2, 'I': 3,   # Kasalar
            'B': 10, 'C': 11, 'D': 12, 'G': 13, 'J': 14,  # Kanatlar
            'E': 20,                             # Orta Kayıtlar
        }
        sorted_frames = sorted(self._frames,
                               key=lambda f: TYPE_ORDER.get(f.get('type', 'Z'), 99))

        all_records = []
        prog_no = start_no

        for frame in sorted_frames:
            sc      = frame['stock_code']
            bar_x10 = int(frame['bar_len'] * 10)

            if sc not in bar_state:
                # Bu stok kodu için ilk bar — global sayactan al
                global_bar += 1
                bar_state[sc] = {'bar_no': global_bar, 'bar_used': 0}

            pieces = self._calc_pieces(frame)
            pice_counters = {}   # bar_no → pice_no (bu bar içinde kaçıncı parça)

            for p in pieces:
                piece_x10 = p['length_x10']
                state     = bar_state[sc]

                # Bu parça bara sığmıyor → yeni bar (global sayaç artar)
                if state['bar_used'] + piece_x10 + KERF_X10 > bar_x10 and state['bar_used'] > 0:
                    global_bar      += 1
                    state['bar_no']  = global_bar
                    state['bar_used'] = 0

                bar_no  = state['bar_no']
                pice_no = pice_counters.get(bar_no, 0) + 1
                pice_counters[bar_no] = pice_no

                state['bar_used'] += piece_x10 + KERF_X10

                p['bar_no']  = bar_no
                p['pice_no'] = pice_no

            recs = self._build_records_from_pieces(frame, pieces, prog_no, bar_x10)
            all_records.extend(recs)
            prog_no += len(recs)

        count = sum(1 for rec in all_records if self._db.insert_record(rec)[0])
        self._save_design()   # MDB'ye kaydedildi, tasarım da güncellendi
        QMessageBox.information(self, '✅ Kaydedildi',
            f'{count} parça MDB\'ye kaydedildi.\n'
            f'Program No: {start_no} – {start_no + count - 1}\n'
            f'Tasarım otomatik kaydedildi (kapatıp açınca geri yüklenir).')
        self.records_ready.emit(all_records)

    def _build_records_from_pieces(self, frame: dict, pieces: list,
                                    start_no: int, bar_x10: int) -> list:
        """Bar no ve pice no dışarıdan atanmış parçalardan kayıt listesi üretir."""
        pw_x10  = int(frame['profile_width']  * 10)
        ph_x10  = int(frame['profile_height'] * 10)
        dxf_img = frame.get('dxf_path', '')

        records = []
        for i, p in enumerate(pieces):
            sid     = p['side']
            bar_no  = p.get('bar_no',  1)
            pice_no = p.get('pice_no', 1)
            rec = {
                'PROGRAM_NO':       start_no + i,
                'CUSTOMER_CODE':    '',
                'CUSTOMER_NAME':    '',
                'STOCK_CODE':       frame['stock_code'],
                'STOCK_NAME':       frame['stock_name'],
                'ORDER_NO':         frame['order_no'],
                'EXPLANATION1':     SIDE_NAME[sid],
                'EXPLANATION2':     '',
                'LENGTH':           str(p['length_x10']),
                'INCH_MM':          '0',
                'FRAME_X':          str(int(p['frame_x'] * 10)),
                'FRAME_Y':          str(int(p['frame_y'] * 10)),
                'POSE_NO':          0, 'TROLLEY': 0, 'UNIT': 0,
                'LEFT_ANGLE':       450, 'RIGHT_ANGLE': 450,
                'SIDE':             sid, 'CUTTED': 0,
                'HEIGHT':           ph_x10,
                'SELLER':           '',
                'IMAGE':            dxf_img,   # DXF yolu IMAGE alanına
                'PAIR':             0,
                'BAR_NO':           bar_no,
                'TOTAL_SIZE':       str(bar_x10),
                'PICE_NO':          pice_no,
                'GRUP':             '',
                'WIDTH':            pw_x10,
                'TYPE':             frame['type'],
                'COLOR_CODE':       frame['color_code'],
                'STIL_LENGTH':      '',
                'FRAME_NO':         1,
                'REMAINING_LENGTH': '',
                'CODE':             '',
                'ROBOT_Y':          400, 'ROBOT_Z': 400, 'ROBOT_VERTICAL': 0,
            }
            records.append(rec)
        return records
