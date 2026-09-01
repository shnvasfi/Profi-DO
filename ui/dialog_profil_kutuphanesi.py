"""
ui/dialog_profil_kutuphanesi.py  -  Profil Kutuphanesi Yoneticisi  v4
- Gomulu DXF panel kaldirildi (macOS deadlock'a yol aciyordu)
- DXF secimi icin ayri DxfPickDialog penceresi
- Y/Z mavi kenarlı spinbox ile hem DXF'ten hem elle girilebilir
"""
import os, copy
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QWidget, QFormLayout, QLabel, QLineEdit, QComboBox,
    QSpinBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QMessageBox, QFileDialog, QCheckBox, QDoubleSpinBox,
    QInputDialog, QColorDialog, QAbstractItemView, QGroupBox,
    QListWidget, QListWidgetItem, QFrame, QSizePolicy,
)
from PySide6.QtGui import QColor, QFont, QBrush
import code_generator as cg
from dxf_loader import load_dxf, calc_profile_dimensions, get_bounds
from ui.viewport_widget import ViewportWidget
from ui.kiosk import apply_kiosk

# ── Kasa işlemleri (Tip A) ────────────────────────────────────────────────────
_KASA_OPS = [
    {'id':'ic_su_tahliye',     'name':'İç Su Tahliye',      'p_code':'P3','tool':'T40',
     'x_formulas':[],'param_keys':['L','D'],'default_params':{'L':25,'D':10}},
    {'id':'dis_su_tahliye',    'name':'Dış Su Tahliye',      'p_code':'P3','tool':'T70',
     'x_formulas':[],'param_keys':['L','D'],'default_params':{'L':25,'D':10}},
    {'id':'ic_havalandirma',   'name':'İç Havalandırma',     'p_code':'P7','tool':'T40',
     'x_formulas':[],'param_keys':['D'],'default_params':{'D':10}},
    {'id':'dis_havalandirma',  'name':'Dış Havalandırma',    'p_code':'P7','tool':'T70',
     'x_formulas':[],'param_keys':['D'],'default_params':{'D':10}},
    {'id':'mentese_markalama', 'name':'Menteşe Markalama',   'p_code':'P7','tool':'T30',
     'x_formulas':[],'param_keys':['D'],'default_params':{'D':2}},
    {'id':'montaj_deligi',     'name':'Montaj Deliği',        'p_code':'P7','tool':'T50',
     'x_formulas':[],'param_keys':['D'],'default_params':{'D':10}},
    {'id':'karsilik_markalama','name':'Karşılık Markalama',  'p_code':'P7','tool':'T50',
     'x_formulas':[],'param_keys':['D'],'default_params':{'D':2}},
]

# ── Kanat / Kapı işlemleri (Tip B ve J) ──────────────────────────────────────
_KANAT_OPS = [
    {'id':'ic_su_tahliye',     'name':'İç Su Tahliye',       'p_code':'P3','tool':'T60',
     'x_formulas':[],'param_keys':['L','D'],'default_params':{'L':25,'D':10}},
    {'id':'dis_su_tahliye',    'name':'Dış Su Tahliye',       'p_code':'P3','tool':'T10',
     'x_formulas':[],'param_keys':['L','D'],'default_params':{'L':25,'D':10}},
    {'id':'ic_havalandirma',   'name':'İç Havalandırma',      'p_code':'P7','tool':'T60',
     'x_formulas':[],'param_keys':['D'],'default_params':{'D':10}},
    {'id':'dis_havalandirma',  'name':'Dış Havalandırma',     'p_code':'P7','tool':'T10',
     'x_formulas':[],'param_keys':['D'],'default_params':{'D':10}},
    {'id':'mentese_markalama', 'name':'Menteşe Markalama',    'p_code':'P7','tool':'T50',
     'x_formulas':[],'param_keys':['D'],'default_params':{'D':2}},
    {'id':'uclu_kol_yeri',     'name':'Üçlü Kol Yeri',        'p_code':'P7','tool':'T71',
     'x_formulas':[],'param_keys':['D'],'default_params':{'D':35}},
    {'id':'ispanyolet_kanali', 'name':'İspanyolet Kanalı',    'p_code':'P2','tool':'T10',
     'x_formulas':[],'param_keys':['L','W','R','D'],'default_params':{'L':60,'W':12,'R':'W/2','D':30}},
    {'id':'kilit_kanali',      'name':'Kilit Kanalı',         'p_code':'P1','tool':'T10',
     'x_formulas':[],'param_keys':['L','W','D'],'default_params':{'L':230,'W':16,'D':30}},
    {'id':'kol_deligi_ust',    'name':'Kol Deliği Üst',       'p_code':'P6','tool':'T30',
     'x_formulas':[],'param_keys':['C','D'],'default_params':{'C':18,'D':30}},
    {'id':'kol_deligi_alt',    'name':'Kol Deliği Alt',       'p_code':'P6','tool':'T70',
     'x_formulas':[],'param_keys':['C','D'],'default_params':{'C':18,'D':30}},
    {'id':'sol_barel_ust',     'name':'Sol Barel Üst',        'p_code':'P4','tool':'T30',
     'x_formulas':[],'param_keys':['L','W','C','R','D'],'default_params':{'L':33,'W':10,'C':18,'R':'W/2','D':30}},
    {'id':'sol_barel_alt',     'name':'Sol Barel Alt',        'p_code':'P4','tool':'T70',
     'x_formulas':[],'param_keys':['L','W','C','R','D'],'default_params':{'L':33,'W':10,'C':18,'R':'W/2','D':30}},
    {'id':'sag_barel_ust',     'name':'Sağ Barel Üst',        'p_code':'P5','tool':'T30',
     'x_formulas':[],'param_keys':['L','W','C','R','D'],'default_params':{'L':33,'W':10,'C':18,'R':'W/2','D':30}},
    {'id':'sag_barel_alt',     'name':'Sağ Barel Alt',        'p_code':'P5','tool':'T70',
     'x_formulas':[],'param_keys':['L','W','C','R','D'],'default_params':{'L':33,'W':10,'C':18,'R':'W/2','D':30}},
]

# Tip → standart işlemler listesi
STANDARD_OPS_BY_TYPE = {
    'A': _KASA_OPS,
    'B': _KANAT_OPS,
    'J': _KANAT_OPS,
}
# Geriye dönük uyumluluk için (eski kodlar için)
STANDARD_OPS = _KASA_OPS + [op for op in _KANAT_OPS
                              if op['id'] not in {o['id'] for o in _KASA_OPS}]


def _get_std_ops_for_type(ptype: str) -> list:
    """Profil tipine göre standart işlem listesi döndürür."""
    return STANDARD_OPS_BY_TYPE.get(ptype, _KASA_OPS)

SIDES      = ['ALT', 'ÜST', 'SOL', 'SAĞ']
SIDE_TR    = {'ALT':'ALT ↓','ÜST':'ÜST ↑','SOL':'SOL ←','SAĞ':'SAĞ →'}
SIDE_LABEL = {'ALT':'ALT','ÜST':'ÜST','SOL':'SOL','SAĞ':'SAĞ'}
ALL_PARAM_KEYS = ['L','W','C','R','D']
P_CODES    = ['P1','P2','P3','P4','P5','P6','P7']
_TOOLS_LIST = ['T10','T11','T20','T30','T31','T32','T40','T50','T60','T70','T71']

_STYLE = """
QDialog,QWidget{background:#1e1e2e;color:#ccc;font-size:12px;}
QTreeWidget{background:#161625;border:1px solid #333;color:#ddd;}
QTreeWidget::item:selected{background:#2e4a7a;color:white;}
QTabWidget::pane{border:1px solid #333;}
QTabBar::tab{background:#252535;color:#aaa;padding:5px 14px;border:1px solid #333;border-bottom:none;min-width:120px;}
QTabBar::tab:selected{background:#1e1e2e;color:#fff;}
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox{background:#2e2e42;color:#ddd;border:1px solid #555;border-radius:3px;padding:3px 6px;font-size:12px;}
QPushButton{background:#2e2e42;color:#ccc;border:1px solid #444;border-radius:4px;padding:4px 10px;font-size:12px;}
QPushButton:hover{background:#3a3a55;}
QPushButton#btn_add{background:#1a5c3a;color:white;}
QPushButton#btn_del{background:#5c1a1a;color:white;}
QPushButton#btn_save{background:#1a4a7a;color:white;font-weight:bold;}
QPushButton#btn_side_save{background:#2a5c3a;color:white;font-weight:bold;font-size:12px;}
QPushButton#btn_side_save:hover{background:#3a7a4a;}
QPushButton#btn_dxf{background:#1a3a6a;color:#7af;font-size:11px;padding:2px 6px;}
QTableWidget{background:#161625;color:#ddd;border:1px solid #333;gridline-color:#2a2a3a;font-size:12px;}
QTableWidget QHeaderView::section{background:#252535;color:#f8c12f;border:1px solid #333;padding:4px;font-size:11px;font-weight:bold;}
QListWidget{background:#161625;border:1px solid #333;color:#ddd;font-size:12px;}
QListWidget::item:selected{background:#2e4a7a;}
QLabel#lbl_head{color:#56cfe1;font-size:14px;font-weight:bold;}
QLabel#lbl_hint{color:#666;font-size:11px;font-style:italic;}
"""

# ─────────────────────────────────────────────────────────────────
# DXF Seçim Penceresi  (ana diyalogdan bağımsız — freeze yok)
# ─────────────────────────────────────────────────────────────────

class DxfPickDialog(QDialog):
    """Profil DXF kesitini gosterir; kullanici bir noktaya tiklar."""
    point_picked = Signal(float, float)

    def __init__(self, dxf_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle('DXF Profil Kesiti — Nokta Sec')
        self.resize(820, 540)
        self.setStyleSheet(_STYLE)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8); lay.setSpacing(6)

        # Bilgi satiri
        hdr = QHBoxLayout()
        lbl = QLabel('Profil kesitinde bir noktaya tiklayin  —  Y ve Z koordinati alinacak')
        lbl.setStyleSheet('color:#f8c12f; font-weight:bold;')
        hdr.addWidget(lbl); hdr.addStretch()
        self._lbl_coord = QLabel('')
        self._lbl_coord.setStyleSheet('color:#7af; font-size:11px;')
        hdr.addWidget(self._lbl_coord)
        btn_cancel = QPushButton('Iptal')
        btn_cancel.clicked.connect(self.reject)
        hdr.addWidget(btn_cancel)
        lay.addLayout(hdr)

        # ViewportWidget
        from ui.viewport_widget import ViewportWidget
        self._vp = ViewportWidget()
        self._vp.setMinimumHeight(400)
        self._vp.point_selected.connect(self._on_point)
        lay.addWidget(self._vp, 1)

        # DXF yukle
        try:
            segs = load_dxf(dxf_path)
            self._vp.load_segments(segs)
        except Exception as e:
            QMessageBox.critical(self, 'DXF Hatasi', str(e))
            QTimer.singleShot(0, self.reject)
            return

        # Pick modunu biraz gec ac (render tamamlansin)
        QTimer.singleShot(200, lambda: self._vp.set_pick_mode(True))

    def _on_point(self, y: float, z: float):
        self._lbl_coord.setText(f'Y = {y:.2f}   Z = {z:.2f}')
        self.point_picked.emit(y, z)
        QTimer.singleShot(300, self.accept)   # kisa sure goster, sonra kapat


# ─────────────────────────────────────────────────────────────────
# Grup X-Konum Duzenleme Penceresi
# ─────────────────────────────────────────────────────────────────

_FORMULA_HINTS = [
    'L-2000','L-2400','L-1500','L-700','L-600','L-500','L-300','L-200',
    '2000','2400','1500','700','600','500','300','200',
    'L/2','L/2+2000','L/2-2000','L/2+500','L/2-500','L/3','L/4',
    'L-100','L-150','100','150','0',
]

_TBL_HDR_STYLE = ('QTableWidget{background:#161625;color:#ddd;border:1px solid #333;}'
                  'QTableWidget QHeaderView::section{background:#252535;color:#f8c12f;'
                  'border:1px solid #333;padding:4px;}')


class RangeConditionsDialog(QDialog):
    """
    Boy aralığına göre koşullu X konum tanımlaması.
    Her aralık → farklı X formülleri listesi.

    ranges formatı (JSON):
      [{'max_mm': 500,  'x_formulas': ['L/2']},
       {'max_mm': 1000, 'x_formulas': ['L-300', '300']},
       {'max_mm': None, 'x_formulas': ['L-1500', '1500']}]
    max_mm = None  →  sınırsız (son aralık)
    """

    def __init__(self, op_name: str, ranges: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'{op_name} — Koşullu X Konumları')
        self.resize(660, 460)
        self.setStyleSheet(_STYLE)
        self.result_ranges = None   # Tamam basılınca dolar

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        info = QLabel(
            'Her satır bir boy aralığına karşılık gelir.\n'
            'X Formülleri: virgülle ayırın  (ör: L-1500, 1500)\n'
            '"Sınırsız" işaretli satır o aralığın üstündeki tüm boylar için geçerlidir.')
        info.setStyleSheet('color:#aaa; font-size:11px; font-style:italic;')
        lay.addWidget(info)

        self._tbl = QTableWidget(0, 3)
        self._tbl.setHorizontalHeaderLabels(['Maks Boy (mm)', 'Sınırsız?', 'X Formülleri  (virgülle ayırın)'])
        hdr = self._tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        self._tbl.setStyleSheet(_TBL_HDR_STYLE)
        self._tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        lay.addWidget(self._tbl, 1)

        # Mevcut ranges'ı doldur
        for rng in (ranges or []):
            self._add_row(rng.get('max_mm'), ', '.join(rng.get('x_formulas', [])))
        if not ranges:
            self._add_row(500, '')   # ör. başlangıç satırı

        btn_row = QHBoxLayout()
        btn_add = QPushButton('+ Aralık Ekle')
        btn_add.clicked.connect(lambda: self._add_row(None, ''))
        btn_del = QPushButton('- Seçiliyi Sil')
        btn_del.clicked.connect(self._del_row)
        btn_up = QPushButton('↑'); btn_up.setFixedWidth(32)
        btn_up.clicked.connect(self._move_up)
        btn_dn = QPushButton('↓'); btn_dn.setFixedWidth(32)
        btn_dn.clicked.connect(self._move_down)
        for b in (btn_add, btn_del, btn_up, btn_dn):
            btn_row.addWidget(b)
        btn_row.addStretch()
        hint = QLabel('Sıralama: küçük boy → büyük boy → sınırsız')
        hint.setStyleSheet('color:#666; font-size:10px;')
        btn_row.addWidget(hint)
        lay.addLayout(btn_row)

        footer = QHBoxLayout(); footer.addStretch()
        btn_ok = QPushButton('Tamam'); btn_ok.setObjectName('btn_save')
        btn_ok.clicked.connect(self._accept)
        btn_cl = QPushButton('İptal'); btn_cl.clicked.connect(self.reject)
        footer.addWidget(btn_ok); footer.addWidget(btn_cl)
        lay.addLayout(footer)

    # ── satır yönetimi ────────────────────────────────────────

    def _add_row(self, max_mm, formulas_str: str = ''):
        r = self._tbl.rowCount()
        self._tbl.insertRow(r)
        self._tbl.setRowHeight(r, 32)

        sp = QSpinBox()
        sp.setRange(1, 99999); sp.setSuffix(' mm')
        sp.setStyleSheet('background:#2e2e42;color:#ddd;border:1px solid #555;')
        sp.setValue(int(max_mm) if max_mm else 1000)
        self._tbl.setCellWidget(r, 0, sp)

        chk = QCheckBox('Sınırsız')
        chk.setChecked(max_mm is None)
        chk.setStyleSheet('color:#f8c12f; padding-left:6px;')
        chk.toggled.connect(lambda checked, row=r: self._on_unlimited(row, checked))
        self._tbl.setCellWidget(r, 1, chk)
        if max_mm is None:
            sp.setEnabled(False)

        ed = QLineEdit(formulas_str)
        ed.setPlaceholderText('ör: L-1500, 1500, L/2')
        ed.setStyleSheet('background:#2e2e42;color:#ddd;border:1px solid #555;padding:2px 4px;')
        self._tbl.setCellWidget(r, 2, ed)

    def _on_unlimited(self, row: int, checked: bool):
        sp = self._tbl.cellWidget(row, 0)
        if sp: sp.setEnabled(not checked)

    def _del_row(self):
        r = self._tbl.currentRow()
        if r >= 0:
            self._tbl.removeRow(r)

    def _move_up(self):
        r = self._tbl.currentRow()
        if r > 0: self._swap(r, r - 1); self._tbl.setCurrentCell(r - 1, 0)

    def _move_down(self):
        r = self._tbl.currentRow()
        if 0 <= r < self._tbl.rowCount() - 1:
            self._swap(r, r + 1); self._tbl.setCurrentCell(r + 1, 0)

    def _swap(self, a, b):
        sp_a = self._tbl.cellWidget(a, 0); sp_b = self._tbl.cellWidget(b, 0)
        chk_a = self._tbl.cellWidget(a, 1); chk_b = self._tbl.cellWidget(b, 1)
        ed_a  = self._tbl.cellWidget(a, 2); ed_b  = self._tbl.cellWidget(b, 2)
        if sp_a and sp_b:
            va, vb = sp_a.value(), sp_b.value(); sp_a.setValue(vb); sp_b.setValue(va)
        if chk_a and chk_b:
            ca, cb = chk_a.isChecked(), chk_b.isChecked()
            chk_a.setChecked(cb); chk_b.setChecked(ca)
        if ed_a and ed_b:
            ta, tb = ed_a.text(), ed_b.text(); ed_a.setText(tb); ed_b.setText(ta)

    def _accept(self):
        if self._tbl.rowCount() == 0:
            QMessageBox.warning(self, 'Boş', 'En az 1 aralık gereklidir.'); return
        result = []
        for r in range(self._tbl.rowCount()):
            chk = self._tbl.cellWidget(r, 1)
            sp  = self._tbl.cellWidget(r, 0)
            ed  = self._tbl.cellWidget(r, 2)
            unlimited = chk.isChecked() if chk else False
            max_mm    = None if unlimited else (sp.value() if sp else 0)
            raw       = ed.text().strip() if ed else ''
            formulas  = [f.strip() for f in raw.split(',') if f.strip()]
            if not formulas:
                QMessageBox.warning(self, 'Boş Formül',
                    f'{r+1}. aralıkta en az 1 X formülü gerekli.'); return
            result.append({'max_mm': max_mm, 'x_formulas': formulas})
        self.result_ranges = result
        self.accept()


# ─────────────────────────────────────────────────────────────────

class GroupOpsDialog(QDialog):
    """Bir isleme ait X konum formullerini duzenle (maks 20 satir)."""
    MAX_ROWS = 20

    def __init__(self, op_name: str, ops: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'{op_name} — X Konum Listesi')
        self.resize(540, 380)
        self.setStyleSheet(_STYLE)
        self._src_ops = [dict(o) for o in ops]
        self.result_ops = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12); lay.setSpacing(8)

        info = QLabel('Her satir bir islem konumu. Formul serbest yazabilir veya listeden secebilirsiniz.')
        info.setStyleSheet('color:#aaa;font-size:11px;font-style:italic;')
        lay.addWidget(info)

        self._tbl = QTableWidget(0, 2)
        self._tbl.setHorizontalHeaderLabels(['X Formulu', 'Sirano'])
        self._tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self._tbl.setColumnWidth(1, 70)
        self._tbl.setStyleSheet(_TBL_HDR_STYLE)
        self._tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        lay.addWidget(self._tbl, 1)

        for op in self._src_ops:
            self._add_row(op.get('x_formula', ''))

        btn_row = QHBoxLayout()
        btn_add = QPushButton('+ Konum Ekle');  btn_add.clicked.connect(self._add_empty)
        btn_del = QPushButton('- Seciliyi Sil'); btn_del.clicked.connect(self._del_row)
        btn_up  = QPushButton('↑');  btn_up.setFixedWidth(32);  btn_up.clicked.connect(self._move_up)
        btn_dn  = QPushButton('↓');  btn_dn.setFixedWidth(32);  btn_dn.clicked.connect(self._move_down)
        for b in (btn_add, btn_del, btn_up, btn_dn): btn_row.addWidget(b)
        btn_row.addStretch()
        lbl_lim = QLabel(f'(maks {self.MAX_ROWS} konum)')
        lbl_lim.setStyleSheet('color:#666;font-size:10px;')
        btn_row.addWidget(lbl_lim)
        lay.addLayout(btn_row)

        footer = QHBoxLayout(); footer.addStretch()
        btn_ok = QPushButton('Tamam');  btn_ok.setObjectName('btn_save'); btn_ok.clicked.connect(self._accept)
        btn_cl = QPushButton('Iptal'); btn_cl.clicked.connect(self.reject)
        footer.addWidget(btn_ok); footer.addWidget(btn_cl)
        lay.addLayout(footer)

    # ── satir yonetimi ──────────────────────────────────────
    def _add_row(self, formula: str = ''):
        r = self._tbl.rowCount()
        if r >= self.MAX_ROWS:
            return
        self._tbl.insertRow(r)
        self._tbl.setRowHeight(r, 30)
        cb = QComboBox(); cb.setEditable(True)
        cb.addItems(_FORMULA_HINTS)
        cb.setCurrentText(formula)
        self._tbl.setCellWidget(r, 0, cb)
        self._update_labels()

    def _add_empty(self):
        if self._tbl.rowCount() >= self.MAX_ROWS:
            QMessageBox.information(self, 'Limit', f'En fazla {self.MAX_ROWS} konum eklenebilir.')
            return
        self._add_row('')

    def _del_row(self):
        r = self._tbl.currentRow()
        if r >= 0:
            self._tbl.removeRow(r)
            self._update_labels()

    def _move_up(self):
        r = self._tbl.currentRow()
        if r <= 0: return
        self._swap_rows(r, r - 1)
        self._tbl.setCurrentCell(r - 1, 0)

    def _move_down(self):
        r = self._tbl.currentRow()
        if r < 0 or r >= self._tbl.rowCount() - 1: return
        self._swap_rows(r, r + 1)
        self._tbl.setCurrentCell(r + 1, 0)

    def _swap_rows(self, a, b):
        cb_a = self._tbl.cellWidget(a, 0)
        cb_b = self._tbl.cellWidget(b, 0)
        if cb_a and cb_b:
            ta, tb = cb_a.currentText(), cb_b.currentText()
            cb_a.setCurrentText(tb); cb_b.setCurrentText(ta)

    def _update_labels(self):
        for i in range(self._tbl.rowCount()):
            itm = self._tbl.item(i, 1)
            if not itm:
                itm = QTableWidgetItem()
                itm.setFlags(itm.flags() & ~Qt.ItemIsEditable)
                itm.setForeground(QBrush(QColor('#888')))
                self._tbl.setItem(i, 1, itm)
            itm.setText(f'  {i + 1}. konum')

    def _accept(self):
        formulas = []
        for r in range(self._tbl.rowCount()):
            cb = self._tbl.cellWidget(r, 0)
            f = (cb.currentText() or '').strip()
            if f:
                formulas.append(f)
        if not formulas:
            QMessageBox.warning(self, 'Bos', 'En az 1 konum formulu olmali.'); return
        base = self._src_ops[0] if self._src_ops else {'p_code': 'P7', 'tool': 'T30', 'params': {}}
        self.result_ops = []
        for i, f in enumerate(formulas):
            op = dict(self._src_ops[i]) if i < len(self._src_ops) else dict(base)
            op['x_formula'] = f
            op['label'] = str(i + 1)
            self.result_ops.append(op)
        self.accept()


# ─────────────────────────────────────────────────────────────────
# Yeni Ozel Islem Tanimlama Penceresi
# ─────────────────────────────────────────────────────────────────

class NewOpDialog(QDialog):
    """
    Yeni özel işlem tanımla — veya mevcut bir özel işlemi düzenle.

    Her satır bağımsız bir işlem adımıdır:
      P-Kod | Takım | X Formülü | Y | Z | L | W | C | R | D

    edit_op: dict verilirse düzenleme modunda açılır (ID alanı kilitlenir).
    """

    # Tablo kolon indeksleri
    _COL_PCODE = 0; _COL_TOOL = 1; _COL_X = 2
    _COL_Y = 3; _COL_Z = 4
    _COL_L = 5; _COL_W = 6; _COL_C = 7; _COL_R = 8; _COL_D = 9

    def __init__(self, existing_ids: set, parent=None, edit_op: dict = None,
                 dxf_path: str = None):
        super().__init__(parent)
        self._editing  = edit_op is not None
        self._edit_op  = edit_op or {}
        self._dxf_path = (dxf_path or '').strip()
        self._vp       = None   # ViewportWidget — DXF varsa dolar
        title = 'Islemi Duzenle' if self._editing else 'Yeni Islem Tanimla'
        self.setWindowTitle(title)
        self.setStyleSheet(_STYLE)
        self._existing_ids = existing_ids
        self.result_op = None

        has_dxf = bool(self._dxf_path and os.path.exists(self._dxf_path))
        self.resize(960, 760 if has_dxf else 520)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10); lay.setSpacing(8)

        # ── Temel bilgiler ──────────────────────────────────
        form = QFormLayout(); form.setSpacing(6)
        self._ed_name = QLineEdit()
        self._ed_name.setPlaceholderText('orn. Uclu Kol Yeri')
        form.addRow('Islem Adi *:', self._ed_name)

        self._ed_id = QLineEdit()
        self._ed_id.setPlaceholderText('orn. uclu_kol_yeri  (otomatik)')
        if self._editing:
            self._ed_id.setReadOnly(True)
            self._ed_id.setStyleSheet('background:#1a1a2e; color:#888;')
        form.addRow('Islem ID *:', self._ed_id)
        self._ed_name.textChanged.connect(self._auto_id)
        lay.addLayout(form)

        # ── Başlık + canlı koordinat satırı ─────────────────
        hdr_row = QHBoxLayout(); hdr_row.setSpacing(8)
        lbl_steps = QLabel('Islem Adimlari  (her satir ayri P-kod + takim + X + parametreler):')
        lbl_steps.setStyleSheet('color:#56cfe1; font-weight:bold; margin-top:2px;')
        hdr_row.addWidget(lbl_steps, 1)
        self._lbl_yz = QLabel('Y: –   Z: –')
        self._lbl_yz.setStyleSheet(
            'color:#56cfe1;font-family:"Courier New",monospace;'
            'font-size:11px;font-weight:bold;background:#111120;'
            'padding:2px 8px;border-radius:3px;')
        hdr_row.addWidget(self._lbl_yz)
        lay.addLayout(hdr_row)

        # ── Tablo ────────────────────────────────────────────
        self._tbl = QTableWidget(0, 10)
        self._tbl.setHorizontalHeaderLabels(
            ['P-Kod', 'Takım', 'X Formülü', 'Y (mm)', 'Z (mm)', 'L', 'W', 'C', 'R', 'D'])
        hdr = self._tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        for c in range(5, 10):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self._tbl.setStyleSheet(_TBL_HDR_STYLE)
        self._tbl.setSelectionBehavior(QAbstractItemView.SelectRows)

        if has_dxf:
            # Dikey splitter: tablo üst — DXF alt
            from PySide6.QtWidgets import QSplitter as _Spl
            vsplit = _Spl(Qt.Vertical)
            vsplit.setChildrenCollapsible(False)
            self._tbl.setMinimumHeight(140)
            vsplit.addWidget(self._tbl)

            from ui.viewport_widget import ViewportWidget as _VP
            self._vp = _VP()
            self._vp.setMinimumHeight(150)
            try:
                segs = load_dxf(self._dxf_path)
                self._vp.load_segments(segs)
            except Exception:
                pass
            self._vp.mouse_moved.connect(
                lambda y, z: self._lbl_yz.setText(f'Y: {y:.2f} mm   Z: {z:.2f} mm'))
            self._vp.point_selected.connect(self._on_dxf_point)
            QTimer.singleShot(300, lambda: self._vp.set_pick_mode(True))
            vsplit.addWidget(self._vp)
            vsplit.setSizes([270, 230])
            lay.addWidget(vsplit, 1)
        else:
            self._tbl.setMinimumHeight(200)
            lay.addWidget(self._tbl, 1)

        btn_row = QHBoxLayout()
        btn_add = QPushButton('+ Adim Ekle'); btn_add.clicked.connect(self._add_step)
        btn_dup = QPushButton('Kopyala');     btn_dup.clicked.connect(self._dup_step)
        btn_del = QPushButton('- Sil');       btn_del.clicked.connect(self._del_step)
        btn_up  = QPushButton('↑'); btn_up.setFixedWidth(32); btn_up.clicked.connect(self._move_up)
        btn_dn  = QPushButton('↓'); btn_dn.setFixedWidth(32); btn_dn.clicked.connect(self._move_down)
        for b in (btn_add, btn_dup, btn_del, btn_up, btn_dn): btn_row.addWidget(b)
        hint = QLabel('L/W/C/R/D: 0 = kullanilmaz')
        hint.setStyleSheet('color:#666; font-size:10px;')
        btn_row.addStretch(); btn_row.addWidget(hint)
        lay.addLayout(btn_row)

        # ── X formül test / önizleme satırı ─────────────────────────────────
        test_row = QHBoxLayout(); test_row.setSpacing(8)
        _tlbl = QLabel('Test L:')
        _tlbl.setStyleSheet('color:#888; font-size:11px; min-width:46px;')
        test_row.addWidget(_tlbl)
        self._sp_test_l = QSpinBox()
        self._sp_test_l.setRange(100, 99999)
        self._sp_test_l.setValue(2000)          # 2000mm varsayılan → L-1500 = 500 (sıfır değil)
        self._sp_test_l.setSuffix(' mm')
        self._sp_test_l.setFixedWidth(110)
        self._sp_test_l.setToolTip(
            'X formüllerini test etmek için profil uzunluğu girin.\n'
            'Örn: "L-1500" için L=1500 girilirse X=0 çıkar (başlangıç noktası).\n'
            'L=2000 girilirse X=500mm çıkar.')
        self._sp_test_l.setStyleSheet(
            'background:#2e2e42; color:#ddd; border:1px solid #444; font-size:11px;')
        test_row.addWidget(self._sp_test_l)
        _rlbl = QLabel('→')
        _rlbl.setStyleSheet('color:#666; font-size:11px;')
        test_row.addWidget(_rlbl)
        self._lbl_x_prev = QLabel('–')
        self._lbl_x_prev.setStyleSheet(
            'color:#f8c12f; font-family:"Courier New",monospace; font-size:11px;'
            'background:#111120; padding:2px 10px; border-radius:3px;')
        self._lbl_x_prev.setWordWrap(True)
        test_row.addWidget(self._lbl_x_prev, 1)
        lay.addLayout(test_row)
        self._sp_test_l.valueChanged.connect(self._update_x_preview)

        # ── Alt butonlar ─────────────────────────────────────
        footer = QHBoxLayout(); footer.addStretch()
        btn_lbl = 'Guncelle' if self._editing else 'Olustur'
        btn_ok = QPushButton(btn_lbl)
        btn_ok.setObjectName('btn_save'); btn_ok.clicked.connect(self._accept)
        btn_cl = QPushButton('Iptal'); btn_cl.clicked.connect(self.reject)
        footer.addWidget(btn_ok); footer.addWidget(btn_cl)
        lay.addLayout(footer)

        # ── Mevcut veriyle doldur ─────────────────────────────
        if self._editing:
            self._ed_name.setText(self._edit_op.get('name', ''))
            self._ed_id.setText(self._edit_op.get('id', ''))
            self._load_steps_from_op(self._edit_op)
        else:
            self._add_step()   # boş başlangıç satırı

        # İlk X önizlemesini göster
        QTimer.singleShot(150, self._update_x_preview)

    # ── X formül önizleme ────────────────────────────────────

    def _update_x_preview(self):
        """Test uzunluğu için tüm adımların X formül sonuçlarını hesapla ve göster."""
        if not hasattr(self, '_sp_test_l') or not hasattr(self, '_lbl_x_prev'):
            return
        L = float(self._sp_test_l.value())
        parts = []
        for r in range(self._tbl.rowCount()):
            x_cb = self._tbl.cellWidget(r, self._COL_X)
            xf = (x_cb.currentText() or '').strip() if x_cb else '0'
            if not xf:
                xf = '0'
            try:
                f = xf.replace(',', '.').replace('L', str(L))
                result = float(eval(f, {'__builtins__': {}}))
                result = max(0.0, result)   # CNC negatif X kabul etmez
                x_mdb = int(round(result * 10))
                parts.append(f'Adım {r+1}: {xf} → {result:.1f} mm  (X{x_mdb})')
            except Exception:
                parts.append(f'Adım {r+1}: {xf} → ?')
        self._lbl_x_prev.setText('   |   '.join(parts) if parts else '–')

    # ── DXF tıklama → seçili satıra Y/Z yaz ─────────────────

    def _on_dxf_point(self, y: float, z: float):
        """Gömülü DXF viewport'a tıklandı: seçili satırın Y/Z'sini güncelle."""
        r = self._tbl.currentRow()
        if 0 <= r < self._tbl.rowCount():
            sp_y = self._tbl.cellWidget(r, self._COL_Y)
            sp_z = self._tbl.cellWidget(r, self._COL_Z)
            if sp_y: sp_y.setValue(y)
            if sp_z: sp_z.setValue(z)
        # Pick modunu hemen yeniden etkinleştir (sürekli kullanım)
        if self._vp:
            QTimer.singleShot(80, lambda: self._vp.set_pick_mode(True))

    # ── Adım satırı işlemleri ─────────────────────────────────

    def _add_step(self, p_code='P7', tool='T10', x_formula='', y=0.0, z=0.0, params=None):
        """Tabloya yeni bir işlem adımı satırı ekle."""
        r = self._tbl.rowCount()
        self._tbl.insertRow(r)
        self._tbl.setRowHeight(r, 30)

        _sp_style  = 'QDoubleSpinBox{background:#2e2e42;color:#ddd;border:none;}'
        _yz_style  = ('QDoubleSpinBox{background:#172030;color:#7ec8f0;'
                      'border:1px solid #2a5a7a;border-radius:2px;padding:1px 3px;}')

        cb_p = QComboBox()
        for p in P_CODES: cb_p.addItem(p, p)
        idx = cb_p.findData(p_code)
        if idx >= 0: cb_p.setCurrentIndex(idx)
        self._tbl.setCellWidget(r, self._COL_PCODE, cb_p)

        cb_t = QComboBox()
        for t in _TOOLS_LIST: cb_t.addItem(t, t)
        idx = cb_t.findData(tool)
        if idx >= 0: cb_t.setCurrentIndex(idx)
        self._tbl.setCellWidget(r, self._COL_TOOL, cb_t)

        cb_x = QComboBox(); cb_x.setEditable(True)
        cb_x.addItems(_FORMULA_HINTS)
        cb_x.setCurrentText(x_formula)
        cb_x.setToolTip(
            'X formülü: "L" = profil uzunluğu (mm)\n'
            'Örnekler: L-1500  L/2  500  L-300\n'
            'Test uzunluğu alanından canlı sonucu görebilirsiniz.')
        cb_x.currentTextChanged.connect(
            lambda _: QTimer.singleShot(0, self._update_x_preview)
            if hasattr(self, '_lbl_x_prev') else None)
        self._tbl.setCellWidget(r, self._COL_X, cb_x)

        # Y ve Z — mavi kenarlı spinbox
        sp_y = QDoubleSpinBox(); sp_y.setRange(-9999, 9999); sp_y.setDecimals(1)
        sp_y.setValue(float(y)); sp_y.setStyleSheet(_yz_style)
        sp_y.setToolTip('Y (mm) — profil kesit konumu')
        self._tbl.setCellWidget(r, self._COL_Y, sp_y)

        sp_z = QDoubleSpinBox(); sp_z.setRange(-9999, 9999); sp_z.setDecimals(1)
        sp_z.setValue(float(z)); sp_z.setStyleSheet(_yz_style)
        sp_z.setToolTip('Z (mm) — derinlik ekseni')
        self._tbl.setCellWidget(r, self._COL_Z, sp_z)

        p = params or {}
        for ci, key in enumerate(ALL_PARAM_KEYS):
            sp = QDoubleSpinBox(); sp.setRange(0, 9999); sp.setDecimals(0)
            sp.setSpecialValueText('-'); sp.setToolTip(f'{key} (mm)')
            sp.setStyleSheet(_sp_style)
            sp.setValue(float(p.get(key, 0)) if not isinstance(p.get(key, 0), str) else 0)
            self._tbl.setCellWidget(r, self._COL_L + ci, sp)

    def _load_steps_from_op(self, op: dict):
        """Mevcut op verisinden adım satırlarını doldur."""
        if 'steps' in op:
            for s in op['steps']:
                self._add_step(
                    p_code=s.get('p_code', 'P7'),
                    tool=s.get('tool', 'T10'),
                    x_formula=s.get('x_formula', ''),
                    y=s.get('y', 0.0),
                    z=s.get('z', 0.0),
                    params=s.get('params', {}))
        else:
            # Eski format: tek p_code + birden fazla x_formula
            p_code = op.get('p_code', 'P7')
            tool   = op.get('tool', 'T10')
            dfp    = op.get('default_params', {})
            for xf in op.get('x_formulas', []):
                self._add_step(p_code=p_code, tool=tool, x_formula=xf, params=dfp)
        if self._tbl.rowCount() == 0:
            self._add_step()

    def _dup_step(self):
        r = self._tbl.currentRow()
        if r < 0 or r >= self._tbl.rowCount(): return
        p  = self._tbl.cellWidget(r, self._COL_PCODE)
        t  = self._tbl.cellWidget(r, self._COL_TOOL)
        x  = self._tbl.cellWidget(r, self._COL_X)
        sy = self._tbl.cellWidget(r, self._COL_Y)
        sz = self._tbl.cellWidget(r, self._COL_Z)
        params = {}
        for ci, key in enumerate(ALL_PARAM_KEYS):
            sp = self._tbl.cellWidget(r, self._COL_L + ci)
            if sp: params[key] = sp.value()
        self._add_step(
            p_code=p.currentData() if p else 'P7',
            tool=t.currentData() if t else 'T10',
            x_formula=x.currentText() if x else '',
            y=sy.value() if sy else 0.0,
            z=sz.value() if sz else 0.0,
            params=params)

    def _del_step(self):
        r = self._tbl.currentRow()
        if r >= 0 and self._tbl.rowCount() > 1:
            self._tbl.removeRow(r)

    def _move_up(self):
        r = self._tbl.currentRow()
        if r > 0: self._swap(r, r - 1); self._tbl.setCurrentCell(r - 1, 0)

    def _move_down(self):
        r = self._tbl.currentRow()
        if 0 <= r < self._tbl.rowCount() - 1:
            self._swap(r, r + 1); self._tbl.setCurrentCell(r + 1, 0)

    def _swap(self, a, b):
        """İki satırın widget değerlerini yer değiştir."""
        def vals(row):
            p  = self._tbl.cellWidget(row, self._COL_PCODE)
            t  = self._tbl.cellWidget(row, self._COL_TOOL)
            x  = self._tbl.cellWidget(row, self._COL_X)
            sy = self._tbl.cellWidget(row, self._COL_Y)
            sz = self._tbl.cellWidget(row, self._COL_Z)
            ps = [self._tbl.cellWidget(row, self._COL_L + i) for i in range(5)]
            return (p.currentData() if p else 'P7',
                    t.currentData() if t else 'T10',
                    x.currentText() if x else '',
                    sy.value() if sy else 0.0,
                    sz.value() if sz else 0.0,
                    [s.value() if s else 0 for s in ps])
        va = vals(a); vb = vals(b)
        for row, v in ((a, vb), (b, va)):
            p  = self._tbl.cellWidget(row, self._COL_PCODE)
            t  = self._tbl.cellWidget(row, self._COL_TOOL)
            x  = self._tbl.cellWidget(row, self._COL_X)
            sy = self._tbl.cellWidget(row, self._COL_Y)
            sz = self._tbl.cellWidget(row, self._COL_Z)
            if p:  p.setCurrentIndex(p.findData(v[0]))
            if t:  t.setCurrentIndex(t.findData(v[1]))
            if x:  x.setCurrentText(v[2])
            if sy: sy.setValue(v[3])
            if sz: sz.setValue(v[4])
            for i, val in enumerate(v[5]):
                sp = self._tbl.cellWidget(row, self._COL_L + i)
                if sp: sp.setValue(val)

    # ── ID otomatik slug ─────────────────────────────────────

    def _auto_id(self, text: str):
        if self._editing: return
        import re, unicodedata
        nfkd = unicodedata.normalize('NFKD', text.lower())
        asc  = nfkd.encode('ascii', 'ignore').decode('ascii')
        slug = re.sub(r'[^a-z0-9]+', '_', asc).strip('_')
        self._ed_id.setText(slug)

    # ── Kabul ────────────────────────────────────────────────

    def _accept(self):
        name  = self._ed_name.text().strip()
        op_id = self._ed_id.text().strip()
        if not name or not op_id:
            QMessageBox.warning(self, 'Eksik', 'Islem adi ve ID gerekli.'); return
        if not self._editing and op_id in self._existing_ids:
            QMessageBox.warning(self, 'Cakisma',
                f'"{op_id}" ID\'si zaten kullaniliyor.'); return
        if self._tbl.rowCount() == 0:
            QMessageBox.warning(self, 'Eksik', 'En az 1 islem adimi gerekli.'); return

        steps = []
        for r in range(self._tbl.rowCount()):
            p  = self._tbl.cellWidget(r, self._COL_PCODE)
            t  = self._tbl.cellWidget(r, self._COL_TOOL)
            x  = self._tbl.cellWidget(r, self._COL_X)
            sy = self._tbl.cellWidget(r, self._COL_Y)
            sz = self._tbl.cellWidget(r, self._COL_Z)
            xf = (x.currentText() or '').strip() if x else ''
            if not xf:
                QMessageBox.warning(self, 'Eksik',
                    f'{r+1}. adimda X formulu bos.'); return
            params = {}
            for ci, key in enumerate(ALL_PARAM_KEYS):
                sp = self._tbl.cellWidget(r, self._COL_L + ci)
                v = sp.value() if sp else 0
                if v > 0: params[key] = int(v)
            y_val = sy.value() if sy else 0.0
            z_val = sz.value() if sz else 0.0
            step = {
                'p_code':    p.currentData() if p else 'P7',
                'tool':      t.currentData() if t else 'T10',
                'x_formula': xf,
                'params':    params,
            }
            if y_val != 0.0: step['y'] = y_val
            if z_val != 0.0: step['z'] = z_val
            steps.append(step)

        self.result_op = {
            'id':      op_id,
            'name':    name,
            'steps':   steps,
            # Geriye dönük uyumluluk alanları (eski kodlar için)
            'p_code':         steps[0]['p_code'],
            'tool':           steps[0]['tool'],
            'x_formulas':     [s['x_formula'] for s in steps],
            'param_keys':     list({k for s in steps for k in s['params']}),
            'default_params': steps[0]['params'],
            '_custom':        True,
        }
        self.accept()


# ─────────────────────────────────────────────────────────────────
# Ana Dialog
# ─────────────────────────────────────────────────────────────────

class ProfilKutuphanesiDialog(QDialog):
    library_changed  = Signal()
    request_dxf_pick = Signal()   # geriye donuk uyumluluk

    def __init__(self, parent=None, restricted=False):
        super().__init__(parent)
        self.setWindowTitle('Profil Kutuphanesi Yoneticisi')
        self.resize(1200, 720)
        apply_kiosk(self)   # tam ekran, çerçevesiz kiosk modu
        self.setStyleSheet(_STYLE)

        # restricted=True: ana ekrandaki "Profil Kütüphanesi" butonundan açılır —
        # sadece mevcut profillerin üzerinde değişiklik yapılabilir.
        # Yeni profil ekleme / kopyalama / silme / toplu Excel yükleme
        # yalnızca Ayarlar > Profil Tanımlama sekmesinden (restricted=False) yapılabilir.
        self._restricted     = restricted

        self._library        = cg.load_library()
        self._cur_code       = None
        self._prev_side      = SIDES[0]   # son aktif kenar — combo degismeden once kaydedilir
        self._dirty          = False
        self._info_dirty     = False      # genel bilgi alanlari degisti mi
        self._dxf_target_row = -1

        self._build_ui()
        self._populate_tree()

    # ─────────────────────────────────────────────────────────
    # DXF noktasi geldi (eski API — ana pencereden)
    # ─────────────────────────────────────────────────────────
    def _cur_dxf_path(self) -> str:
        """Şu an seçili profilin DXF dosya yolunu döndürür (yoksa boş string)."""
        try:
            p = getattr(self, '_ed_dxf', None)
            path = p.text().strip() if p else ''
            return path if path and os.path.exists(path) else ''
        except Exception:
            return ''

    def receive_dxf_point(self, y: float, z: float):
        self._write_yz(self._dxf_target_row, y, z)
        self._dxf_target_row = -1

    def _write_yz(self, row: int, y: float, z: float):
        if 0 <= row < self._tbl_ops.rowCount():
            sp_y = self._tbl_ops.cellWidget(row, 4)  # col 4 = Y
            sp_z = self._tbl_ops.cellWidget(row, 5)  # col 5 = Z
            if sp_y: sp_y.setValue(y)
            if sp_z: sp_z.setValue(z)
            self._dirty = True

    # ─────────────────────────────────────────────────────────
    # UI kurulum
    # ─────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6); root.setSpacing(4)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Sol: profil agaci
        left = QWidget(); left.setFixedWidth(220)
        llay = QVBoxLayout(left); llay.setContentsMargins(0,0,0,0); llay.setSpacing(4)
        lbl = QLabel('Profil Kutuphanesi'); lbl.setObjectName('lbl_head')
        llay.addWidget(lbl)
        self._tree = QTreeWidget(); self._tree.setHeaderHidden(True); self._tree.setIndentation(14)
        self._tree.currentItemChanged.connect(self._on_tree_selection)
        llay.addWidget(self._tree, 1)
        if not self._restricted:
            btn_row = QHBoxLayout(); btn_row.setSpacing(3)
            for label, obj, slot in [('+ Yeni','btn_add',self._new_profile),
                                      ('Kopyala','btn_dup',self._duplicate_profile),
                                      ('Sil','btn_del',self._delete_profile)]:
                b = QPushButton(label); b.setObjectName(obj); b.clicked.connect(slot)
                btn_row.addWidget(b)
            llay.addLayout(btn_row)
        else:
            lbl_ro = QLabel('Sadece mevcut profiller üzerinde\ndeğişiklik yapılabilir.')
            lbl_ro.setStyleSheet('color:#888; font-size:10px; padding:2px;')
            lbl_ro.setWordWrap(True)
            llay.addWidget(lbl_ro)
        splitter.addWidget(left)

        # Sag: sekmeler
        right = QWidget()
        rlay = QVBoxLayout(right); rlay.setContentsMargins(4,0,0,0); rlay.setSpacing(6)
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_info_tab(), 'Genel Bilgiler')
        self._tabs.addTab(self._build_ops_tab(),  'Islem Makrolari')
        rlay.addWidget(self._tabs, 1)
        bar = QHBoxLayout()
        btn_xls_exp = QPushButton('📊 Excel\'e Aktar')
        btn_xls_exp.setObjectName('btn_dxf'); btn_xls_exp.setFixedHeight(32)
        btn_xls_exp.setToolTip('Kütüphaneyi .xlsx dosyasına aktar (görüntüleme / düzenleme)')
        btn_xls_exp.clicked.connect(self._export_excel)
        bar.addWidget(btn_xls_exp)
        if not self._restricted:
            btn_xls_imp = QPushButton('📥 Excel\'den Yükle')
            btn_xls_imp.setObjectName('btn_dxf'); btn_xls_imp.setFixedHeight(32)
            btn_xls_imp.setToolTip('Düzenlenmiş .xlsx dosyasından kütüphaneyi geri yükle')
            btn_xls_imp.clicked.connect(self._import_excel)
            bar.addWidget(btn_xls_imp)
        bar.addStretch()
        btn_s = QPushButton('Kutuphanesi Kaydet')
        btn_s.setObjectName('btn_save'); btn_s.setFixedHeight(32)
        btn_s.clicked.connect(self._save_library)
        bar.addWidget(btn_s)
        btn_close = QPushButton('Kapat')
        btn_close.setFixedHeight(32)
        btn_close.clicked.connect(self.close)
        bar.addWidget(btn_close)
        rlay.addLayout(bar)
        splitter.addWidget(right)
        splitter.setSizes([220, 980])
        root.addWidget(splitter, 1)

        self._set_detail_enabled(False)

    # ── Genel Bilgiler sekmesi ─────────────────────────────
    def _build_info_tab(self):
        # Dış kap: dikey splitter — üst form, alt DXF viewport
        outer = QWidget()
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)

        vsplit = QSplitter(Qt.Horizontal)
        vsplit.setChildrenCollapsible(False)

        # ── Üst: form alanları ───────────────────────────────
        w = QWidget(); lay = QFormLayout(w)
        lay.setContentsMargins(16,16,16,8); lay.setSpacing(10)
        lay.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._ed_code   = QLineEdit(); self._ed_code.setPlaceholderText('PIM_KASA_70')
        self._ed_name   = QLineEdit(); self._ed_name.setPlaceholderText('Pimapen Kasa 70')
        self._ed_mfr    = QLineEdit(); self._ed_mfr.setPlaceholderText('Pimapen')
        self._ed_series = QLineEdit(); self._ed_series.setPlaceholderText('70')
        self._cb_type   = QComboBox()
        for k, v in cg.PROFILE_LABEL.items():
            self._cb_type.addItem(f'{k} - {v}', k)
        # Üst Üste Binme Payı — üç alan: [dxf otomatik] + [kullanıcı] = [toplam]
        self._sp_overlap_dxf  = QDoubleSpinBox()
        self._sp_overlap_dxf.setRange(0, 300); self._sp_overlap_dxf.setDecimals(1)
        self._sp_overlap_dxf.setSuffix(' mm'); self._sp_overlap_dxf.setFixedWidth(90)
        self._sp_overlap_dxf.setToolTip('DXF üst 20mm bölgesinden otomatik okunan profil genişliği')
        self._sp_overlap_user = QDoubleSpinBox()
        self._sp_overlap_user.setRange(-200, 200); self._sp_overlap_user.setDecimals(1)
        self._sp_overlap_user.setSuffix(' mm'); self._sp_overlap_user.setFixedWidth(90)
        self._sp_overlap_user.setToolTip('Elle girilecek ek pay (negatif olabilir)')
        self._lbl_overlap_total = QLabel('0,0 mm')
        self._lbl_overlap_total.setStyleSheet('color:#56cfe1;font-weight:bold;min-width:80px;')
        self._lbl_overlap_total.setToolTip('Toplam üst üste binme payı = DXF + Kullanıcı')
        ov_row = QHBoxLayout(); ov_row.setSpacing(4)
        ov_row.addWidget(self._sp_overlap_dxf)
        ov_row.addWidget(QLabel('+'))
        ov_row.addWidget(self._sp_overlap_user)
        ov_row.addWidget(QLabel('='))
        ov_row.addWidget(self._lbl_overlap_total)
        ov_row.addStretch()
        ov_row_widget = QWidget(); ov_row_widget.setLayout(ov_row)

        dxf_row = QHBoxLayout()
        self._ed_dxf = QLineEdit(); self._ed_dxf.setReadOnly(True)
        self._ed_dxf.setPlaceholderText('(DXF dosyasi secin)')
        btn_dxf = QPushButton('...'); btn_dxf.setFixedWidth(32); btn_dxf.clicked.connect(self._pick_dxf)
        dxf_row.addWidget(self._ed_dxf); dxf_row.addWidget(btn_dxf)
        color_row = QHBoxLayout()
        self._ed_color = QLineEdit(); self._ed_color.setFixedWidth(100)
        self._btn_color = QPushButton('  '); self._btn_color.setFixedSize(40,24)
        self._btn_color.clicked.connect(self._pick_color)
        self._ed_color.textChanged.connect(self._update_color_btn)
        color_row.addWidget(self._ed_color); color_row.addWidget(self._btn_color); color_row.addStretch()

        # Genel bilgi degisince _dirty flag'i set et
        # NOT: burada 'w' degisken adi kullanilmamali — _build_info_tab'in w=QWidget() degiskenini ezer!
        for fld in (self._ed_code, self._ed_name, self._ed_mfr, self._ed_series, self._ed_color):
            fld.textChanged.connect(lambda _: self._set_info_dirty())
        self._sp_overlap_dxf.valueChanged.connect(lambda _: (self._set_info_dirty(), self._update_overlap_total()))
        self._sp_overlap_user.valueChanged.connect(lambda _: (self._set_info_dirty(), self._update_overlap_total()))
        self._cb_type.currentIndexChanged.connect(lambda _: self._set_info_dirty())

        # Profil genişlik / yükseklik (DXF'ten otomatik veya elle)
        wh_row = QHBoxLayout()
        self._sp_width_mm  = QSpinBox(); self._sp_width_mm.setRange(0, 999)
        self._sp_width_mm.setSuffix(' mm'); self._sp_width_mm.setFixedWidth(90)
        self._sp_width_mm.setToolTip('Profil kesit genişliği (mm) — DXF seçince otomatik okunur')
        self._sp_height_mm = QSpinBox(); self._sp_height_mm.setRange(0, 999)
        self._sp_height_mm.setSuffix(' mm'); self._sp_height_mm.setFixedWidth(90)
        self._sp_height_mm.setToolTip('Profil kesit yüksekliği (mm) — DXF seçince otomatik okunur')
        wh_row.addWidget(QLabel('G:')); wh_row.addWidget(self._sp_width_mm)
        wh_row.addSpacing(10); wh_row.addWidget(QLabel('Y:')); wh_row.addWidget(self._sp_height_mm)
        wh_row.addStretch()
        self._sp_width_mm.valueChanged.connect(lambda _: self._set_info_dirty())
        self._sp_height_mm.valueChanged.connect(lambda _: self._set_info_dirty())

        # Robot yakalama noktası (×10 değerler — MDB'ye direkt yazılır)
        robot_row = QHBoxLayout()
        self._sp_robot_y = QSpinBox()
        self._sp_robot_y.setRange(-99999, 99999); self._sp_robot_y.setValue(400)
        self._sp_robot_y.setSuffix(' ×10'); self._sp_robot_y.setFixedWidth(90)
        self._sp_robot_y.setToolTip('Robot Y konumu (×10, ör. 40 mm → 400)')
        self._sp_robot_z = QSpinBox()
        self._sp_robot_z.setRange(-99999, 99999); self._sp_robot_z.setValue(400)
        self._sp_robot_z.setSuffix(' ×10'); self._sp_robot_z.setFixedWidth(90)
        self._sp_robot_z.setToolTip('Robot Z konumu (×10, ör. 40 mm → 400)')
        self._cb_robot_vert = QComboBox()
        self._cb_robot_vert.addItem('Yatay (0)', 0)
        self._cb_robot_vert.addItem('Dikey  (1)', 1)
        self._cb_robot_vert.setFixedWidth(105)
        self._btn_robot_pick = QPushButton('📍 DXF\'ten Seç')
        self._btn_robot_pick.setFixedWidth(120)
        self._btn_robot_pick.setToolTip('DXF kesit görünümünde tıklayarak robot noktasını seç')
        self._btn_robot_pick.clicked.connect(self._start_robot_pick)
        robot_row.addWidget(QLabel('Y:')); robot_row.addWidget(self._sp_robot_y)
        robot_row.addSpacing(8)
        robot_row.addWidget(QLabel('Z:')); robot_row.addWidget(self._sp_robot_z)
        robot_row.addSpacing(8)
        robot_row.addWidget(self._cb_robot_vert)
        robot_row.addSpacing(8)
        robot_row.addWidget(self._btn_robot_pick)
        robot_row.addStretch()
        self._sp_robot_y.valueChanged.connect(lambda _: self._set_info_dirty())
        self._sp_robot_z.valueChanged.connect(lambda _: self._set_info_dirty())
        self._cb_robot_vert.currentIndexChanged.connect(lambda _: self._set_info_dirty())

        lay.addRow('Stok Kodu:', self._ed_code)
        lay.addRow('Profil Adi:', self._ed_name)
        lay.addRow('Uretici:', self._ed_mfr)
        lay.addRow('Seri:', self._ed_series)
        lay.addRow('Tip:', self._cb_type)
        lay.addRow('Üst Üste Binme:', ov_row_widget)
        lay.addRow('DXF Dosyasi:', dxf_row)
        lay.addRow('Renk:', color_row)
        lay.addRow('Kesit G / Y:', wh_row)
        lay.addRow('Robot Y / Z:', robot_row)
        btn_a = QPushButton('Profil Bilgilerini Uygula'); btn_a.setObjectName('btn_save')
        btn_a.setFixedHeight(34); btn_a.clicked.connect(self._apply_info)
        lay.addRow('', btn_a)

        # ── Alt: DXF viewport (Y/Z koordinatları gömülü) ────
        self._lib_viewport = ViewportWidget()
        self._lib_viewport.setMinimumWidth(300)
        self._lib_viewport.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        vsplit.addWidget(w)
        vsplit.addWidget(self._lib_viewport)
        vsplit.setSizes([480, 560])

        outer_lay.addWidget(vsplit, 1)
        return outer

    # ── Islem Makrolari sekmesi ────────────────────────────
    def _build_ops_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(6,6,6,6); lay.setSpacing(6)

        top = QHBoxLayout(); top.setSpacing(10)
        top.addWidget(QLabel('Kenar:'))
        self._cb_side = QComboBox()
        for s in SIDES:
            self._cb_side.addItem(SIDE_TR[s], s)
        self._cb_side.setFixedWidth(110)
        self._cb_side.currentIndexChanged.connect(self._on_side_changed)
        top.addWidget(self._cb_side)

        self._btn_side_save = QPushButton('ALT icin kaydet')
        self._btn_side_save.setObjectName('btn_side_save')
        self._btn_side_save.setFixedHeight(28)
        self._btn_side_save.clicked.connect(self._save_current_side)
        top.addWidget(self._btn_side_save)
        top.addStretch()
        lbl_tip = QLabel('Listedeki islemleri isaretleyerek bu kenara ekle')
        lbl_tip.setObjectName('lbl_hint'); top.addWidget(lbl_tip)
        lay.addLayout(top)

        hsplit = QSplitter(Qt.Horizontal); hsplit.setChildrenCollapsible(False)

        left = QWidget(); left.setFixedWidth(210)
        llay = QVBoxLayout(left); llay.setContentsMargins(0,0,4,0); llay.setSpacing(4)

        # Baslik "TOPLU LİSTE" + "+ Yeni Islem" butonu yan yana
        lbl_hdr = QHBoxLayout()
        lbl_l = QLabel('TOPLU LİSTE')
        lbl_l.setStyleSheet('color:#ff6b6b;font-weight:bold;font-size:13px;letter-spacing:1px;')
        lbl_hdr.addWidget(lbl_l); lbl_hdr.addStretch()
        btn_new_op = QPushButton('+ Yeni')
        btn_new_op.setObjectName('btn_dxf')
        btn_new_op.setFixedWidth(52)
        btn_new_op.setToolTip('Ozel islem tanimla (tum profillerde kullanilabilir)')
        btn_new_op.clicked.connect(self._on_add_new_op)
        lbl_hdr.addWidget(btn_new_op)
        llay.addLayout(lbl_hdr)

        self._lst_ops = QListWidget(); self._lst_ops.setSpacing(2)
        # Tıklama → o işlemi bu kenara ekle (checkbox yok)
        self._lst_ops.itemClicked.connect(self._on_catalog_item_clicked)
        llay.addWidget(self._lst_ops, 1)

        # Sol panele kontekst menu: ozel islemi sil / gizle
        self._lst_ops.setContextMenuPolicy(Qt.CustomContextMenu)
        self._lst_ops.customContextMenuRequested.connect(self._on_ops_ctx_menu)

        self._reload_ops_list()   # Profil tipine göre standart + özel işlemler
        hsplit.addWidget(left)

        # ── ORTA panel: aktif profilin işlem özeti ─────────────────
        mid = QWidget(); mid.setFixedWidth(220)
        mlay = QVBoxLayout(mid); mlay.setContentsMargins(4,0,4,0); mlay.setSpacing(4)

        # Profil adı başlığı (seçili profile göre güncellenir)
        self._lbl_profile_ops_header = QLabel('—')
        self._lbl_profile_ops_header.setStyleSheet(
            'color:#56cfe1;font-weight:bold;font-size:13px;letter-spacing:1px;')
        self._lbl_profile_ops_header.setWordWrap(True)
        mlay.addWidget(self._lbl_profile_ops_header)

        lbl_mid_hint = QLabel('✓ olanı tıkla → düzenle  |  sağ tık → kaldır')
        lbl_mid_hint.setStyleSheet('color:#777;font-size:10px;')
        mlay.addWidget(lbl_mid_hint)

        self._lst_profile_ops = QListWidget()
        self._lst_profile_ops.setSpacing(1)
        self._lst_profile_ops.setSelectionMode(QAbstractItemView.SingleSelection)
        self._lst_profile_ops.setStyleSheet(
            'QListWidget { border:1px solid #333; background:#12121e; }'
            'QListWidget::item { padding:3px 4px; }'
            'QListWidget::item:selected { background:#1e3a2e; }')
        # Tıklama → sağ tabloda ilgili satıra kaydır
        self._lst_profile_ops.itemClicked.connect(self._on_profile_op_item_clicked)
        # Sağ-tık → bu kenardan kaldır
        self._lst_profile_ops.setContextMenuPolicy(Qt.CustomContextMenu)
        self._lst_profile_ops.customContextMenuRequested.connect(self._on_profile_ops_ctx_menu)
        mlay.addWidget(self._lst_profile_ops, 1)
        hsplit.addWidget(mid)

        # ── SAĞ panel: parametre tablosu ────────────────────────────
        right = QWidget()
        rlay = QVBoxLayout(right); rlay.setContentsMargins(4,0,0,0); rlay.setSpacing(4)

        hdr_row = QHBoxLayout()
        lbl_r = QLabel('Seçili İşlemlerin Parametreleri')
        lbl_r.setStyleSheet('color:#aaa;font-size:11px;')
        hdr_row.addWidget(lbl_r); hdr_row.addStretch()

        # Y/Z DXF pick butonu — hâlâ kullanılabilir
        self._btn_dxf_pick = QPushButton('📐 DXF\'e Tıkla')
        self._btn_dxf_pick.setObjectName('btn_dxf')
        self._btn_dxf_pick.setToolTip('Tabloda bir satır seç, sonra DXF penceresinde Y/Z noktası seç')
        self._btn_dxf_pick.clicked.connect(self._on_dxf_pick_request)
        hdr_row.addWidget(self._btn_dxf_pick)

        # Tüm işlemleri temizle
        btn_clear = QPushButton('🗑 Tüm İşlemleri Temizle')
        btn_clear.setObjectName('btn_del')
        btn_clear.setFixedHeight(24)
        btn_clear.setToolTip('Bu kenar için tüm işlemleri tablodan kaldır')
        btn_clear.clicked.connect(self._clear_current_side_ops)
        hdr_row.addWidget(btn_clear)

        # Seçili satırı tablodan kaldır
        btn_del_row = QPushButton('✕ Kaldır')
        btn_del_row.setObjectName('btn_del')
        btn_del_row.setFixedHeight(24)
        btn_del_row.setToolTip('Seçili işlemi bu kenardan kaldır')
        btn_del_row.clicked.connect(self._remove_selected_table_row)
        hdr_row.addWidget(btn_del_row)

        rlay.addLayout(hdr_row)

        self._tbl_ops = QTableWidget()
        self._tbl_ops.setColumnCount(11)
        self._tbl_ops.setHorizontalHeaderLabels(
            ['İşlem', 'KOD', 'TAKIM', 'X  (virgülle ayırın)', 'Y mm', 'Z mm', 'L', 'W', 'C', 'R', 'D'])
        hdr = self._tbl_ops.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Interactive)   # İşlem adı
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.Interactive)   # X — kullanıcı genişletebilir
        hdr.setSectionResizeMode(4, QHeaderView.Fixed)         # Y mm — sabit dar
        hdr.setSectionResizeMode(5, QHeaderView.Fixed)         # Z mm — sabit dar
        for c in range(6, 11):
            hdr.setSectionResizeMode(c, QHeaderView.Fixed)     # L W C R D — sabit dar
        self._tbl_ops.setColumnWidth(0, 120)
        self._tbl_ops.setColumnWidth(3, 200)   # X sütunu geniş
        self._tbl_ops.setColumnWidth(4, 68)    # Y mm (~%25 daralma)
        self._tbl_ops.setColumnWidth(5, 68)    # Z mm (~%25 daralma)
        for c in range(6, 11):
            self._tbl_ops.setColumnWidth(c, 42)  # L W C R D (~%50 daralma)
        self._tbl_ops.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tbl_ops.setAlternatingRowColors(True)
        self._tbl_ops.setStyleSheet('alternate-background-color:#1a1a2a;')
        self._tbl_ops.setMinimumHeight(200)
        # Sağ tık: satırı kaldır, X konumları, koşullu
        self._tbl_ops.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tbl_ops.customContextMenuRequested.connect(self._on_tbl_ops_ctx_menu)
        rlay.addWidget(self._tbl_ops, 1)
        hsplit.addWidget(right)
        hsplit.setSizes([210, 220, 560])
        lay.addWidget(hsplit, 1)
        return w

    # ─────────────────────────────────────────────────────────
    # Agac
    # ─────────────────────────────────────────────────────────
    def _populate_tree(self):
        self._tree.blockSignals(True); self._tree.clear()
        groups = {}
        for code, prof in self._library.get('profiles', {}).items():
            t = prof.get('type','?')
            if t not in groups:
                label = cg.PROFILE_LABEL.get(t, t)
                grp = QTreeWidgetItem(self._tree, [f'{t}  -  {label}'])
                grp.setData(0, Qt.UserRole, None)
                font = QFont(); font.setBold(True); grp.setFont(0, font)
                grp.setForeground(0, QBrush(QColor('#56cfe1')))
                groups[t] = grp
            child = QTreeWidgetItem(groups[t], [f'{prof.get("name","?")}  [{code}]'])
            child.setData(0, Qt.UserRole, code)
        self._tree.expandAll()
        self._tree.blockSignals(False)

    def _on_tree_selection(self, item, _prev):
        if item is None: self._set_detail_enabled(False); return
        code = item.data(0, Qt.UserRole)
        if code is None: self._set_detail_enabled(False); return
        # Farkli bir profile gec: once TUMU kaydet (genel bilgi + operasyonlar)
        if self._cur_code and code != self._cur_code:
            self._save_general_info_to_profile()   # genel bilgi alanlarini yaz
            self._save_ops_to_profile(side=self._prev_side)
            cg.save_library(self._library)
            self._dirty = False
        self._cur_code = code
        self._prev_side = self._cb_side.currentData() or SIDES[0]
        self._info_dirty = False   # yeni profil yuklenince temiz
        self._load_profile_to_ui(code)
        self._set_detail_enabled(True)

    def _start_robot_pick(self):
        """DXF viewport'ta tıklama modunu başlatır."""
        if not hasattr(self, '_lib_viewport'):
            return
        # Önceki bağlantıyı temizle
        try:
            self._lib_viewport.point_selected.disconnect(self._on_robot_point_selected)
        except Exception:
            pass
        self._lib_viewport.point_selected.connect(self._on_robot_point_selected)
        self._lib_viewport.set_pick_mode(True)

    def _on_robot_point_selected(self, y_mm: float, z_mm: float):
        """Viewport tıklama koordinatlarını robot spinbox'larına yaz (×10)."""
        self._sp_robot_y.setValue(int(round(y_mm * 10)))
        self._sp_robot_z.setValue(int(round(z_mm * 10)))
        try:
            self._lib_viewport.point_selected.disconnect(self._on_robot_point_selected)
        except Exception:
            pass

    def _update_overlap_total(self):
        """Üst üste binme toplam etiketini güncelle."""
        total = self._sp_overlap_dxf.value() + self._sp_overlap_user.value()
        self._lbl_overlap_total.setText(f'{total:.1f} mm'.replace('.', ','))

    def _set_info_dirty(self):
        """Genel bilgi alanlari degisince cagrılır."""
        if self._cur_code:   # profil secili degilse ignore
            self._info_dirty = True
            self._dirty = True

    def _save_general_info_to_profile(self):
        """Genel bilgi sekmesindeki alanlari mevcut profile yazar (disk kaydı yapmaz)."""
        if not self._cur_code: return
        prof = cg.get_profile(self._library, self._cur_code)
        if not prof: return
        new_code = self._ed_code.text().strip().upper()
        # Stok kodu degistiyse rename yap
        if new_code and new_code != self._cur_code:
            if new_code not in self._library.get('profiles', {}):
                self._library['profiles'][new_code] = prof
                del self._library['profiles'][self._cur_code]
                self._cur_code = new_code
        prof['name']         = self._ed_name.text().strip()
        prof['manufacturer'] = self._ed_mfr.text().strip()
        prof['series']       = self._ed_series.text().strip()
        prof['type']         = self._cb_type.currentData()
        prof['overlap_dxf']  = self._sp_overlap_dxf.value()
        prof['overlap_user'] = self._sp_overlap_user.value()
        # geriye dönük uyumluluk: kerf = overlap_dxf (eski kodlar için)
        prof['kerf']         = int(round(self._sp_overlap_dxf.value()))
        prof['dxf_file']       = self._ed_dxf.text().strip()
        prof['color']          = self._ed_color.text().strip()
        prof['width_mm']       = self._sp_width_mm.value()
        prof['robot_y']        = self._sp_robot_y.value()
        prof['robot_z']        = self._sp_robot_z.value()
        prof['robot_vertical'] = self._cb_robot_vert.currentData()
        prof['height_mm']    = self._sp_height_mm.value()

    # ─────────────────────────────────────────────────────────
    # Profil -> UI
    # ─────────────────────────────────────────────────────────
    def _load_profile_to_ui(self, stock_code):
        prof = cg.get_profile(self._library, stock_code)
        if not prof: return
        # Sinyalleri blokla — UI doldururken sahte _dirty tetiklenmesin
        info_widgets = [self._ed_code, self._ed_name, self._ed_mfr,
                        self._ed_series, self._ed_color, self._cb_type,
                        self._sp_overlap_dxf, self._sp_overlap_user,
                        self._sp_width_mm, self._sp_height_mm,
                        self._sp_robot_y, self._sp_robot_z, self._cb_robot_vert]
        for w in info_widgets: w.blockSignals(True)
        self._ed_code.setText(stock_code)
        self._ed_name.setText(prof.get('name',''))
        self._ed_mfr.setText(prof.get('manufacturer',''))
        self._ed_series.setText(prof.get('series',''))
        idx = self._cb_type.findData(prof.get('type','A'))
        if idx >= 0: self._cb_type.setCurrentIndex(idx)
        # overlap_dxf — eski profillerden kerf değerini taşı
        old_kerf = float(prof.get('kerf', 45))
        ov_dxf  = float(prof.get('overlap_dxf',  old_kerf))
        ov_user = float(prof.get('overlap_user', 0.0))
        self._sp_overlap_dxf.setValue(ov_dxf)
        self._sp_overlap_user.setValue(ov_user)
        self._ed_dxf.setText(prof.get('dxf_file',''))
        self._ed_color.setText(prof.get('color','#808080'))
        w_val = int(prof.get('width_mm', 0))
        h_val = int(prof.get('height_mm', 0))
        # DXF tanımlı ise her zaman oku (boyutlar + üst-20mm overlap)
        dxf_path = prof.get('dxf_file', '').strip()
        _loaded_segs = []
        if dxf_path:
            try:
                segs = load_dxf(dxf_path)
                if segs:
                    _loaded_segs = segs
                    # Yükseklik: standart (max_z - min_z)
                    # Genişlik: alt 30mm bölgede en geniş nokta
                    h_mm, w_mm = calc_profile_dimensions(segs)
                    h_val = int(round(h_mm))
                    w_val = int(round(w_mm))
                    # Üst 20mm genişliğini hesapla → overlap_dxf
                    top_w = self._calc_top_width_from_dxf_segs(segs)
                    if top_w > 0:
                        self._sp_overlap_dxf.setValue(round(top_w, 1))
                    # Profil kütüphanesine kalıcı kaydet
                    prof['width_mm']    = w_val
                    prof['height_mm']   = h_val
                    prof['overlap_dxf'] = self._sp_overlap_dxf.value()
                    prof['kerf']        = int(round(self._sp_overlap_dxf.value()))
                    try:
                        cg.save_library(self._library)
                    except Exception:
                        pass
            except Exception:
                pass
        # Viewport'u güncelle (DXF varsa göster, yoksa temizle)
        if hasattr(self, '_lib_viewport'):
            self._lib_viewport.load_segments(_loaded_segs)
        self._sp_width_mm.setValue(w_val)
        self._sp_height_mm.setValue(h_val)
        # Robot yakalama noktası
        self._sp_robot_y.setValue(int(prof.get('robot_y', 400)))
        self._sp_robot_z.setValue(int(prof.get('robot_z', 400)))
        _rv = self._cb_robot_vert.findData(int(prof.get('robot_vertical', 0)))
        if _rv >= 0: self._cb_robot_vert.setCurrentIndex(_rv)
        for w in info_widgets: w.blockSignals(False)
        self._update_overlap_total()
        self._info_dirty = False
        self._update_color_btn()
        # Orta panel başlığını profil adıyla güncelle
        prof_display = prof.get('name', stock_code) or stock_code
        self._lbl_profile_ops_header.setText(prof_display)
        self._reload_ops_list()          # sol listeyi yenile
        self._refresh_ops_for_side()
        self._reload_profile_ops_list()  # orta paneli yenile

    # ─────────────────────────────────────────────────────────
    # Kenar yonetimi
    # ─────────────────────────────────────────────────────────
    def _on_side_changed(self):
        # Combo degismis; self._prev_side = ESKi kenar, currentData() = YENI kenar
        if self._cur_code:
            self._save_ops_to_profile(side=self._prev_side)   # eski kenara kaydet
        new_side = self._cb_side.currentData()
        self._prev_side = new_side                            # takibi guncelle
        self._refresh_ops_for_side()
        self._reload_profile_ops_list()   # orta paneli güncelle
        self._btn_side_save.setText(f'{SIDE_LABEL.get(new_side, new_side)} icin kaydet')

    def _save_current_side(self):
        if not self._cur_code:
            QMessageBox.warning(self,'Uyari','Once bir profil secin.'); return
        try:
            self._save_ops_to_profile()
            cg.save_library(self._library)
            self._dirty = False
            side = self._cb_side.currentData()
            QMessageBox.information(self, 'Kaydedildi',
                f'{SIDE_LABEL.get(side,side)} kenari kaydedildi.')
        except Exception as e:
            import traceback
            QMessageBox.critical(self,'Hata',f'{e}\n\n{traceback.format_exc()}')

    def _refresh_ops_for_side(self):
        if not self._cur_code: return
        side = self._cb_side.currentData()
        prof = cg.get_profile(self._library, self._cur_code)
        if not prof: return
        macros = prof.get('operations', {}).get(side, [])
        active_ids = {m['id']: m for m in macros}
        self._lst_ops.blockSignals(True)
        for i in range(self._lst_ops.count()):
            item = self._lst_ops.item(i)
            op_id = item.data(Qt.UserRole)
            item.setCheckState(Qt.Checked if op_id in active_ids else Qt.Unchecked)
        self._lst_ops.blockSignals(False)
        self._rebuild_table_from_macros(macros)
        side = self._cb_side.currentData()
        self._btn_side_save.setText(f'{SIDE_LABEL.get(side,side)} icin kaydet')

    def _rebuild_table_from_macros(self, macros):
        self._tbl_ops.blockSignals(True)
        self._tbl_ops.setRowCount(0)
        for macro in macros:
            self._add_table_row(macro)
        self._tbl_ops.blockSignals(False)

    def _on_op_checked(self, item):
        # Artık kullanılmıyor — sol listede checkbox yok.
        # Ekleme: _on_catalog_item_clicked → _add_op_to_current_side
        # Kaldırma: _on_profile_ops_ctx_menu (orta panel sağ-tık)
        pass

    def _find_table_row_by_id(self, op_id):
        for r in range(self._tbl_ops.rowCount()):
            itm = self._tbl_ops.item(r, 0)
            if itm and itm.data(Qt.UserRole) == op_id:
                return r
        return -1

    # ─── Islem sablon sorgu yardimcilari ──────────────────────────
    def _cur_profile_type(self) -> str:
        """Seçili profilin tipini döndürür (varsayılan 'A')."""
        if not self._cur_code: return 'A'
        prof = cg.get_profile(self._library, self._cur_code)
        return prof.get('type', 'A') if prof else 'A'

    def _get_std_op(self, op_id):
        """Global katalogdan ID'ye göre işlem şablonu bul (geriye dönük uyumluluk)."""
        return cg.get_catalog_op(self._library, op_id)

    def _get_all_op(self, op_id):
        """Global katalogdan ID'ye göre işlem şablonu bul."""
        return cg.get_catalog_op(self._library, op_id)

    def _get_all_ops_list(self):
        """
        Global işlem kataloğu — TÜM profil türleri için, tip filtresi olmadan.
        Gizlenmiş işlemler hariç tutulur.
        """
        hidden = set(self._library.get('hidden_standard_ops', []))
        return [op for op in cg.get_catalog_ops(self._library)
                if op['id'] not in hidden]

    def _reload_ops_list(self):
        """
        Sol TOPLU LİSTE — düz isim listesi, checkbox yok.
        Bu kenarda zaten var olan işlemler aksan renkle gösterilir.
        Tıklamak → o işlemi bu kenara ekler (_on_catalog_item_clicked).
        """
        self._lst_ops.blockSignals(True)
        self._lst_ops.clear()

        # Seçili kenardaki mevcut işlem ID'leri
        cur_side_ids: set = set()
        if self._cur_code:
            side = self._cb_side.currentData() or SIDES[0]
            prof = cg.get_profile(self._library, self._cur_code)
            if prof:
                for macro in prof.get('operations', {}).get(side, []):
                    cur_side_ids.add(macro.get('id', ''))

        hidden = set(self._library.get('hidden_standard_ops', []))

        # ── Standart 19 işlem (düz, başlıksız) ──────────────────────
        for op in cg.BUILTIN_OPS:
            if op['id'] in hidden:
                continue
            already = op['id'] in cur_side_ids
            item = QListWidgetItem(op['name'])
            item.setData(Qt.UserRole, op['id'])
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if already:
                # Zaten bu kenarda — yeşilimsi, italik
                item.setForeground(QBrush(QColor('#56cfe1')))
                font = item.font(); font.setItalic(True); item.setFont(font)
                item.setToolTip('Bu kenarda zaten var — tekrar tıklamak etki etmez')
            else:
                item.setForeground(QBrush(QColor('#d0d0d0')))
                item.setToolTip('Tıkla → bu kenara ekle')
            self._lst_ops.addItem(item)

        # ── Özel işlemler (varsa başlıkla) ─────────────────────────
        customs = [op for op in cg.get_custom_ops(self._library) if op['id'] not in hidden]
        if customs:
            sep = QListWidgetItem('  ─── Özel İşlemler ───')
            sep.setFlags(Qt.ItemIsEnabled)
            sep.setForeground(QBrush(QColor('#a0e0ff')))
            font = sep.font(); font.setBold(True); font.setPointSize(9)
            sep.setFont(font); sep.setBackground(QBrush(QColor('#252535')))
            sep.setData(Qt.UserRole, None)
            self._lst_ops.addItem(sep)
            for op in customs:
                already = op['id'] in cur_side_ids
                item = QListWidgetItem(op['name'])
                item.setData(Qt.UserRole, op['id'])
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                if already:
                    item.setForeground(QBrush(QColor('#56cfe1')))
                    font = item.font(); font.setItalic(True); item.setFont(font)
                    item.setToolTip('Bu kenarda zaten var')
                else:
                    item.setForeground(QBrush(QColor('#a0e0ff')))
                    item.setToolTip('Tıkla → bu kenara ekle')
                self._lst_ops.addItem(item)

        self._lst_ops.blockSignals(False)

    # ─── Sol katalog tıklama: kenara ekle ─────────────────────────
    def _on_catalog_item_clicked(self, item):
        """Sol TOPLU LİSTE'de bir isme tıklandı → bu kenara ekle."""
        op_id = item.data(Qt.UserRole)
        if not op_id or not self._cur_code:
            return
        self._add_op_to_current_side(op_id)

    def _add_op_to_current_side(self, op_id: str):
        """Kataloğdaki işlemi seçili kenara ekler (zaten varsa atlar)."""
        if self._find_table_row_by_id(op_id) >= 0:
            return   # zaten var
        tmpl = self._get_all_op(op_id)
        if not tmpl:
            return
        steps = tmpl.get('steps', [])
        p_codes     = list(dict.fromkeys(s.get('p_code', 'P7') for s in steps))
        tools       = list(dict.fromkeys(s.get('tool', 'T10') for s in steps))
        has_step_yz = any('y' in s or 'z' in s for s in steps)
        is_grp      = len(p_codes) > 1 or len(tools) > 1 or has_step_yz or len(steps) > 1
        if is_grp:
            existing = {o['id'] for o in self._get_all_ops_list()} - {op_id}
            dlg = NewOpDialog(existing, self, edit_op=dict(tmpl), dxf_path=self._cur_dxf_path())
            if dlg.exec() == QDialog.Accepted and dlg.result_op:
                self._add_table_row(self._tmpl_to_macro(dlg.result_op))
            else:
                return
        else:
            self._add_table_row(self._tmpl_to_macro(tmpl))
        self._dirty = True
        self._save_ops_to_profile()
        self._reload_profile_ops_list()
        self._reload_ops_list()   # renk göstergesini güncelle

    # ─── Orta panel: tıklama ve sağ-tık ──────────────────────────
    def _macro_to_edit_op(self, macro: dict) -> dict:
        """
        Profil'de saklı makroyu NewOpDialog'un beklediği edit_op formatına çevirir.
        Katalog şablonundan değil, profilin kaydettiği gerçek değerlerden oluşur.
        """
        y_def = float(macro.get('y_value', 0.0))
        z_def = float(macro.get('z_value', 0.0))
        steps = []
        for s in macro.get('ops', []):
            steps.append({
                'p_code':    s.get('p_code', 'P7'),
                'tool':      s.get('tool',   'T10'),
                'x_formula': s.get('x_formula', '0'),
                'y':         float(s.get('y', y_def)),
                'z':         float(s.get('z', z_def)),
                'params':    dict(s.get('params', {})),
            })
        if not steps:
            steps = [{'p_code': 'P7', 'tool': 'T10', 'x_formula': '0',
                      'y': y_def, 'z': z_def, 'params': {}}]
        return {'id': macro.get('id', ''), 'name': macro.get('name', ''), 'steps': steps}

    def _on_profile_op_item_clicked(self, item):
        """
        Orta panelde bir işleme tıklandı.
        ✓ işaretli (seçili kenarda) → profil bazlı düzenleme dialogu aç.
        İşaretsiz (başka kenarda) → yoksay.
        """
        op_id = item.data(Qt.UserRole)
        if not op_id or not self._cur_code:
            return
        cur_side = self._cb_side.currentData() or SIDES[0]
        prof = cg.get_profile(self._library, self._cur_code)
        if not prof:
            return
        macros = prof.setdefault('operations', {}).setdefault(cur_side, [])
        macro_idx = next((i for i, m in enumerate(macros) if m.get('id') == op_id), -1)
        if macro_idx < 0:
            return   # Bu kenarda yok — tıklamayı yoksay

        cur_macro = macros[macro_idx]
        edit_op   = self._macro_to_edit_op(cur_macro)
        existing  = {o['id'] for o in self._get_all_ops_list()} - {op_id}

        dlg = NewOpDialog(existing, self, edit_op=edit_op, dxf_path=self._cur_dxf_path())
        dlg.setWindowTitle(
            f'Düzenle  ·  {cur_macro.get("name", op_id)}'
            f'  [{prof.get("name", self._cur_code)}]')

        if dlg.exec() != QDialog.Accepted or not dlg.result_op:
            return

        # ── Katalog'a dokunmadan sadece profil datasını güncelle ──
        new_macro = self._tmpl_to_macro(dlg.result_op)
        new_macro['id']   = op_id
        new_macro['name'] = cur_macro.get('name', op_id)
        if 'ranges' in cur_macro:
            new_macro['ranges'] = cur_macro['ranges']   # koşullu X aralıklarını koru

        macros[macro_idx] = new_macro   # yerinde güncelle (sıra korunur)
        self._dirty = True
        cg.save_library(self._library)

        # Tabloyu profilden yeniden oluştur (sıra değişmez)
        self._rebuild_table_from_macros(macros)
        self._reload_ops_list()
        self._reload_profile_ops_list()
        # Düzenlenen satırı seç
        row = self._find_table_row_by_id(op_id)
        if row >= 0:
            self._tbl_ops.setCurrentCell(row, 0)

    def _on_profile_ops_ctx_menu(self, pos):
        """Orta panelde sağ-tık → bu kenardan kaldır (sadece ✓ işaretli olanlar)."""
        item = self._lst_profile_ops.itemAt(pos)
        if not item:
            return
        op_id = item.data(Qt.UserRole)
        if not op_id or not self._cur_code:
            return
        # Sadece seçili kenarda olan işlem kaldırılabilir
        cur_side = self._cb_side.currentData() or SIDES[0]
        prof = cg.get_profile(self._library, self._cur_code)
        if not prof:
            return
        cur_ids = {m.get('id') for m in prof.get('operations', {}).get(cur_side, [])}
        if op_id not in cur_ids:
            return
        op_name = item.text().replace('✓', '').strip()
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        act_del = menu.addAction(f'✕  Bu kenardan kaldır  —  "{op_name}"')
        act_del.setObjectName('btn_del')
        act = menu.exec(self._lst_profile_ops.mapToGlobal(pos))
        if act == act_del:
            row = self._find_table_row_by_id(op_id)
            if row >= 0:
                self._tbl_ops.removeRow(row)
                self._dirty = True
                self._save_ops_to_profile()
                self._reload_profile_ops_list()
                self._reload_ops_list()

    # ─── Orta panel: profil işlem özeti ───────────────────────────
    def _reload_profile_ops_list(self):
        """
        Orta panel: aktif profilin TÜM kenarlarındaki işlemlerin birleşimini göster.
        Seçili yöne ait olanlar başında ✓ ile işaretlenir.
        """
        self._lst_profile_ops.clear()
        if not self._cur_code:
            return
        prof = cg.get_profile(self._library, self._cur_code)
        if not prof:
            return

        cur_side = self._cb_side.currentData() or SIDES[0]
        # Seçili yöndeki işlem ID'leri
        cur_side_ids = {m.get('id', '')
                        for m in prof.get('operations', {}).get(cur_side, [])}

        # Tüm kenarlardan benzersiz işlem listesi (ekleme sırasına göre)
        seen: dict = {}   # id → name
        for side in SIDES:
            for macro in prof.get('operations', {}).get(side, []):
                oid = macro.get('id', '')
                if oid and oid not in seen:
                    seen[oid] = macro.get('name', oid)

        if not seen:
            placeholder = QListWidgetItem('  (henüz işlem tanımlanmadı)')
            placeholder.setForeground(QBrush(QColor('#555')))
            placeholder.setFlags(Qt.ItemIsEnabled)
            self._lst_profile_ops.addItem(placeholder)
            return

        for op_id, op_name in seen.items():
            in_cur = op_id in cur_side_ids
            txt  = ('✓  ' if in_cur else '     ') + op_name
            item = QListWidgetItem(txt)
            item.setData(Qt.UserRole, op_id)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if in_cur:
                item.setForeground(QBrush(QColor('#a8e6a3')))   # yeşil
                font = item.font(); font.setBold(True); item.setFont(font)
            else:
                item.setForeground(QBrush(QColor('#666')))
            self._lst_profile_ops.addItem(item)

    # ─── Yeni ozel islem ekleme ────────────────────────────────────
    def _on_add_new_op(self):
        existing = {op['id'] for op in self._get_all_ops_list()}
        dlg = NewOpDialog(existing, self, dxf_path=self._cur_dxf_path())
        if dlg.exec() == QDialog.Accepted and dlg.result_op:
            ok = cg.add_custom_op(self._library, dlg.result_op)
            if not ok:
                QMessageBox.warning(self, 'Hata', 'Bu ID zaten mevcut.')
                return
            cg.save_library(self._library)
            self._reload_ops_list()
            QMessageBox.information(self, 'Eklendi',
                f'"{dlg.result_op["name"]}" islemi kutüphaneye eklendi.')

    def _on_ops_ctx_menu(self, pos):
        """Sag tiklama — sol liste. Kenardan ekle/kaldir + katalog yönetimi."""
        item = self._lst_ops.itemAt(pos)
        if not item or item.data(Qt.UserRole) is None: return   # başlık satırı
        op_id      = item.data(Qt.UserRole)
        is_custom  = any(o['id'] == op_id for o in cg.get_custom_ops(self._library))
        is_builtin = op_id in cg._BUILTIN_IDS
        is_checked = item.checkState() == Qt.Checked
        op_name    = item.text().strip()

        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)

        # Kenardan ekle / kaldır
        act_toggle = menu.addAction(
            f'Bu kenardan kaldır  —  "{op_name}"' if is_checked
            else f'Bu kenara ekle  —  "{op_name}"')

        menu.addSeparator()
        act_edit = act_del = act_hide = None

        if is_custom:
            act_edit = menu.addAction(f'✏️  Düzenle  —  "{op_name}"')
            act_del  = menu.addAction(f'🗑  Katalogdan Sil  —  "{op_name}"')
        elif is_builtin:
            # Yerleşik işlem: düzenlenirse özel kopya olarak kaydedilir
            act_edit = menu.addAction(f'✏️  Düzenle (özel kopya oluştur)  —  "{op_name}"')
            act_hide = menu.addAction(f'🙈  Gizle (listeden kaldır)  —  "{op_name}"')

        act = menu.exec(self._lst_ops.mapToGlobal(pos))

        if act == act_toggle:
            item.setCheckState(Qt.Unchecked if is_checked else Qt.Checked)
        elif act_edit and act == act_edit:
            if is_builtin:
                self._edit_standard_op_as_custom(op_id)
            else:
                self._edit_custom_op(op_id)
        elif act_del and act == act_del:
            if QMessageBox.question(self, 'Islemi Sil',
                    f'"{op_name}" katalogdan kaldirilacak.\nEmin misiniz?',
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                cg.delete_custom_op(self._library, op_id)
                cg.save_library(self._library)
                self._reload_ops_list()
        elif act_hide and act == act_hide:
            self._hide_standard_op(op_id, op_name)

    def _remove_selected_table_row(self):
        """Parametre tablosundan secili satiri kaldir ve sol listede isaretini kaldir."""
        row = self._tbl_ops.currentRow()
        if row < 0:
            QMessageBox.information(self, 'Secim Yok', 'Once tabloda bir satir secin.')
            return
        itm = self._tbl_ops.item(row, 0)
        op_id = itm.data(Qt.UserRole) if itm else None
        self._tbl_ops.removeRow(row)
        self._dirty = True
        # Sol listede de işareti kaldır
        if op_id:
            self._lst_ops.blockSignals(True)
            for i in range(self._lst_ops.count()):
                lst_itm = self._lst_ops.item(i)
                if lst_itm and lst_itm.data(Qt.UserRole) == op_id:
                    lst_itm.setCheckState(Qt.Unchecked)
                    break
            self._lst_ops.blockSignals(False)

    def _clear_current_side_ops(self):
        """Mevcut kenar için tüm işlemleri tablodan temizle."""
        if self._tbl_ops.rowCount() == 0: return
        if QMessageBox.question(self, 'Tüm İşlemleri Temizle',
                'Bu kenardaki tüm işlemler kaldırılacak.\nEmin misiniz?',
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self._tbl_ops.setRowCount(0)
        # Sol listede tüm işaretleri kaldır
        self._lst_ops.blockSignals(True)
        for i in range(self._lst_ops.count()):
            it = self._lst_ops.item(i)
            if it: it.setCheckState(Qt.Unchecked)
        self._lst_ops.blockSignals(False)
        self._dirty = True

    def _on_tbl_ops_ctx_menu(self, pos):
        """Parametre tablosuna sağ tıklama: kaldır, X konumları, koşullu, düzenle."""
        row = self._tbl_ops.rowAt(pos.y())
        if row < 0: return
        self._tbl_ops.selectRow(row)
        itm = self._tbl_ops.item(row, 0)
        if not itm: return
        op_id   = itm.data(Qt.UserRole)
        op_name = itm.text()
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        act_rem      = menu.addAction(f'Bu kenardan kaldır  —  "{op_name}"')
        act_konumlar = menu.addAction('X Konumlarını Düzenle…')
        act_ranges   = menu.addAction('Koşullu X Aralıkları…')
        is_custom = any(o['id'] == op_id for o in cg.get_custom_ops(self._library))
        act_edit = None
        if is_custom:
            menu.addSeparator()
            act_edit = menu.addAction('İşlemi Düzenle (Tanım)…')
        act = menu.exec(self._tbl_ops.mapToGlobal(pos))
        if act == act_rem:
            self._remove_selected_table_row()
        elif act == act_konumlar:
            self._on_konumlar_click(row)
        elif act == act_ranges:
            self._on_ranges_click(row)
        elif act_edit and act == act_edit:
            self._edit_custom_op(op_id)

    def _edit_custom_op(self, op_id: str):
        """Mevcut ozel islemi NewOpDialog ile duzenle ve kutuphaneni guncelle."""
        op = None
        for o in cg.get_custom_ops(self._library):
            if o['id'] == op_id:
                op = o; break
        if not op:
            QMessageBox.warning(self, 'Hata', f'"{op_id}" islemi bulunamadi.')
            return
        # Kendi ID'si disindaki tum ID'leri ver (cakisma kontrolu icin)
        existing = {o['id'] for o in self._get_all_ops_list()} - {op_id}
        dlg = NewOpDialog(existing, self, edit_op=op, dxf_path=self._cur_dxf_path())
        if dlg.exec() == QDialog.Accepted and dlg.result_op:
            # Kutuphanedeki custom_ops listesini guncelle
            custom_ops = list(cg.get_custom_ops(self._library))
            for i, o in enumerate(custom_ops):
                if o['id'] == op_id:
                    custom_ops[i] = dlg.result_op; break
            self._library['custom_ops'] = custom_ops
            cg.save_library(self._library)
            self._reload_ops_list()
            # Eger bu islem tabloda aktif olarak varsa satiri da yenile
            row = self._find_table_row_by_id(op_id)
            if row >= 0:
                self._tbl_ops.removeRow(row)
                self._add_table_row(self._tmpl_to_macro(dlg.result_op))
            QMessageBox.information(self, 'Guncellendi',
                f'"{dlg.result_op["name"]}" islemi guncellendi.')

    def _edit_standard_op_as_custom(self, op_id: str):
        """
        Standart islemi duzenlenebilir custom kopyaya donustur.
        Ayni ID'li custom op olusturulur; standart tanimı override eder.
        """
        # Standart op'u bul ve ozel kopya olarak acik
        std_op = self._get_std_op(op_id)
        if not std_op: return
        # Custom kopya olarak hazirla (steps formatina donustur)
        edit_op = dict(std_op)
        edit_op['_custom'] = True
        # steps yoksa x_formulas'tan olustur
        if 'steps' not in edit_op:
            edit_op['steps'] = [
                {'p_code': edit_op['p_code'], 'tool': edit_op['tool'],
                 'x_formula': xf, 'params': dict(edit_op.get('default_params', {}))}
                for xf in edit_op.get('x_formulas', [])
            ]
        # Bu ID'yi existing'den cikart (ayni ID'li override yapacagiz)
        existing = {o['id'] for o in self._get_all_ops_list()} - {op_id}
        dlg = NewOpDialog(existing, self, edit_op=edit_op, dxf_path=self._cur_dxf_path())
        if dlg.exec() == QDialog.Accepted and dlg.result_op:
            # Mevcut custom_ops'a ekle veya guncelle
            custom_ops = list(cg.get_custom_ops(self._library))
            replaced = False
            for i, o in enumerate(custom_ops):
                if o['id'] == op_id:
                    custom_ops[i] = dlg.result_op; replaced = True; break
            if not replaced:
                custom_ops.append(dlg.result_op)
            self._library['custom_ops'] = custom_ops
            cg.save_library(self._library)
            self._reload_ops_list()
            # Tabloda varsa yenile
            row = self._find_table_row_by_id(op_id)
            if row >= 0:
                self._tbl_ops.removeRow(row)
                self._add_table_row(self._tmpl_to_macro(dlg.result_op))
            QMessageBox.information(self, 'Olusturuldu',
                f'"{dlg.result_op["name"]}" artık özel kopyası ile kullanılacak.\n'
                f'(Mavi renk = düzenlenmiş standart)')

    def _hide_standard_op(self, op_id: str, op_name: str):
        """Standart islemi listeden gizle (hidden_standard_ops listesine ekle)."""
        hidden = self._library.setdefault('hidden_standard_ops', [])
        if op_id not in hidden:
            hidden.append(op_id)
        cg.save_library(self._library)
        self._reload_ops_list()
        QMessageBox.information(self, 'Gizlendi',
            f'"{op_name}" listeden gizlendi.\n'
            f'Geri getirmek için: Araçlar → Gizli İşlemleri Göster '
            f'(veya profile_library.json dosyasından "hidden_standard_ops" listesini düzenleyin).')

    def _tmpl_to_macro(self, tmpl):
        if 'steps' in tmpl:
            # Yeni çok-adımlı format: her adım bağımsız p_code/tool/x_formula/params
            ops = [{'label': str(i + 1), **copy.deepcopy(s)}
                   for i, s in enumerate(tmpl['steps'])]
        else:
            # Eski format: tek p_code/tool + birden fazla x_formula
            ops = [{'label': str(i+1), 'p_code': tmpl['p_code'], 'tool': tmpl['tool'],
                    'x_formula': xf, 'params': copy.deepcopy(tmpl.get('default_params', {}))}
                   for i, xf in enumerate(tmpl['x_formulas'])]
        return {'id': tmpl['id'], 'name': tmpl['name'], 'active': True,
                'y_value': 0.0, 'z_value': 0.0, 'ops': ops}

    def _add_table_row(self, macro):
        r = self._tbl_ops.rowCount()
        self._tbl_ops.insertRow(r)
        self._tbl_ops.setRowHeight(r, 30)

        # Col 0: işlem adı + id (UserRole) + ops listesi (UserRole+1) + ranges (UserRole+2)
        itm = QTableWidgetItem(macro.get('name', ''))
        itm.setFlags(itm.flags() & ~Qt.ItemIsEditable)
        itm.setData(Qt.UserRole,     macro.get('id', ''))
        ops_list = copy.deepcopy(macro.get('ops', []))
        itm.setData(Qt.UserRole + 1, ops_list)
        ranges_data = copy.deepcopy(macro.get('ranges')) or None
        itm.setData(Qt.UserRole + 2, ranges_data)
        self._tbl_ops.setItem(r, 0, itm)

        first_op = ops_list[0] if ops_list else {}

        # ── Grup tespiti: farklı p_code/tool veya adım seviyeli y/z var mı?
        p_codes_in_ops = list(dict.fromkeys(s.get('p_code', 'P7') for s in ops_list))
        tools_in_ops   = list(dict.fromkeys(s.get('tool',   'T10') for s in ops_list))
        has_step_yz    = any('y' in s or 'z' in s for s in ops_list)
        is_group       = len(p_codes_in_ops) > 1 or len(tools_in_ops) > 1 or has_step_yz
        if is_group:
            itm.setText('🔗 ' + macro.get('name', ''))
        _grp_style = ('QComboBox{background:#2a1e3a;color:#c8a0ff;'
                      'border:1px solid #6a4a8a;border-radius:3px;}')

        # Col 1: KOD (P-Kod)
        cb_p = QComboBox()
        if is_group:
            cb_p.addItem('⋮ ' + '/'.join(p_codes_in_ops), '_GROUP_')
            cb_p.setEnabled(False)
            cb_p.setStyleSheet(_grp_style)
        else:
            for p in P_CODES: cb_p.addItem(p, p)
            idx = cb_p.findData(first_op.get('p_code', 'P7'))
            if idx >= 0: cb_p.setCurrentIndex(idx)
            cb_p.currentIndexChanged.connect(lambda _, row=r: self._on_param_changed(row))
        self._tbl_ops.setCellWidget(r, 1, cb_p)

        # Col 2: TAKIM
        cb_t = QComboBox()
        if is_group:
            cb_t.addItem('⋮ ' + '/'.join(tools_in_ops), '_GROUP_')
            cb_t.setEnabled(False)
            cb_t.setStyleSheet(_grp_style)
        else:
            for t in _TOOLS_LIST: cb_t.addItem(t, t)
            idx = cb_t.findData(first_op.get('tool', 'T10'))
            if idx >= 0: cb_t.setCurrentIndex(idx)
            cb_t.currentIndexChanged.connect(lambda _, row=r: self._on_param_changed(row))
        self._tbl_ops.setCellWidget(r, 2, cb_t)

        # Col 3: X — virgülle ayrılmış formüller (ör. "L-1500, 1500")
        x_formulas = [op.get('x_formula', '') for op in ops_list if op.get('x_formula', '')]
        x_text     = ', '.join(x_formulas)
        ed_x = QLineEdit(x_text)
        ed_x.setPlaceholderText('ör: L-1500, 1500, L/2')
        ed_x.setStyleSheet('background:#2e2e42;color:#f8c12f;border:1px solid #555;'
                           'padding:1px 4px;font-size:11px;')
        ed_x.setToolTip('X konumları: virgülle ayırın  (ör: L-1500, 1500)\n'
                        'Sağ tıkla → X Konumlarını Düzenle…')
        ed_x.textChanged.connect(lambda _, row=r: self._on_param_changed(row))
        self._tbl_ops.setCellWidget(r, 3, ed_x)

        # Col 4: Y mm — mavi kenarlı, DXF veya elle
        _yz = ('QDoubleSpinBox{background:#172030;color:#7ec8f0;'
               'border:1px solid #2a5a7a;border-radius:3px;padding:1px 4px;}'
               'QDoubleSpinBox:focus{border:1px solid #56cfe1;}')
        sp_y = QDoubleSpinBox(); sp_y.setRange(-9999, 9999); sp_y.setDecimals(1)
        sp_y.setValue(float(macro.get('y_value', 0)))
        sp_y.setStyleSheet(_yz); sp_y.setToolTip('Y (mm) — DXF tıklayarak veya elle')
        sp_y.valueChanged.connect(lambda _, row=r: self._on_param_changed(row))
        self._tbl_ops.setCellWidget(r, 4, sp_y)

        # Col 5: Z mm — mavi kenarlı
        sp_z = QDoubleSpinBox(); sp_z.setRange(-9999, 9999); sp_z.setDecimals(1)
        sp_z.setValue(float(macro.get('z_value', 0)))
        sp_z.setStyleSheet(_yz); sp_z.setToolTip('Z (mm) — DXF tıklayarak veya elle')
        sp_z.valueChanged.connect(lambda _, row=r: self._on_param_changed(row))
        self._tbl_ops.setCellWidget(r, 5, sp_z)

        # Col 6-10: L, W, C, R, D — QLineEdit (boş = kullanılmaz; R = "W/2" olabilir)
        params = first_op.get('params', {})
        _param_cols = [('L', 6), ('W', 7), ('C', 8), ('R', 9), ('D', 10)]
        _ed_style = 'background:#2e2e42;color:#ddd;border:1px solid #444;padding:1px 3px;font-size:11px;'
        _ed_style_r = 'background:#1e2e3e;color:#a8d8ff;border:1px solid #3a5a7a;padding:1px 3px;font-size:11px;'
        for key, col in _param_cols:
            raw = params.get(key, '')
            # Sayısal 0 → boş göster; string veya pozitif sayı → göster
            if isinstance(raw, str):
                txt = raw.strip()
            else:
                txt = str(int(raw)) if raw and float(raw) > 0 else ''
            ed = QLineEdit(txt)
            ed.setPlaceholderText('—')
            ed.setAlignment(Qt.AlignCenter)
            if key == 'R':
                ed.setStyleSheet(_ed_style_r)
                ed.setToolTip('R (mm) — formül de yazılabilir  (ör: W/2)')
            else:
                ed.setStyleSheet(_ed_style)
                ed.setToolTip(f'{key} (mm)')
            ed.textChanged.connect(lambda _, row=r: self._on_param_changed(row))
            self._tbl_ops.setCellWidget(r, col, ed)

    def _on_konumlar_click(self, row: int):
        """X konumlarını GroupOpsDialog ile düzenle (sağ tık menüsünden erişilir)."""
        itm = self._tbl_ops.item(row, 0)
        if not itm: return
        op_name = itm.text()
        cb_p = self._tbl_ops.cellWidget(row, 1)
        cb_t = self._tbl_ops.cellWidget(row, 2)
        p_code = cb_p.currentData() if cb_p else 'P7'
        tool   = cb_t.currentData() if cb_t else 'T30'

        # X metnini oku → ops listesi oluştur
        ed_x = self._tbl_ops.cellWidget(row, 3)
        x_text = ed_x.text() if ed_x else ''
        x_formulas = [f.strip() for f in x_text.split(',') if f.strip()]
        ops_list = [{'label': str(i+1), 'p_code': p_code, 'tool': tool,
                     'x_formula': xf, 'params': {}}
                    for i, xf in enumerate(x_formulas)]
        if not ops_list:
            ops_list = [{'label': '1', 'p_code': p_code, 'tool': tool,
                         'x_formula': '', 'params': {}}]

        dlg = GroupOpsDialog(op_name, ops_list, self)
        if dlg.exec() == QDialog.Accepted and dlg.result_ops:
            new_formulas = [o.get('x_formula', '') for o in dlg.result_ops
                            if o.get('x_formula', '')]
            if ed_x: ed_x.setText(', '.join(new_formulas))
            itm.setData(Qt.UserRole + 1, dlg.result_ops)
            self._dirty = True

    def _on_ranges_click(self, row: int):
        """Koşullu X aralıklarını düzenle (sağ tık menüsünden erişilir)."""
        itm = self._tbl_ops.item(row, 0)
        if not itm: return
        op_name = itm.text()
        ranges  = itm.data(Qt.UserRole + 2) or []
        dlg = RangeConditionsDialog(op_name, ranges, self)
        if dlg.exec() == QDialog.Accepted and dlg.result_ranges is not None:
            itm.setData(Qt.UserRole + 2, dlg.result_ranges)
            n = len(dlg.result_ranges)
            # İşlem adının yanına kaç aralık olduğunu göster
            op_label = itm.text().split(' [')[0]
            itm.setText(f'{op_label} [📊{n}]')
            self._dirty = True

    def _on_param_changed(self, row):
        self._dirty = True

    # ─────────────────────────────────────────────────────────
    # DXF pick — ayri pencere (freeze yok)
    # ─────────────────────────────────────────────────────────
    def _on_dxf_pick_request(self):
        row = self._tbl_ops.currentRow()
        if row < 0:
            QMessageBox.information(self,'Satir Sec',
                'Once tabloda bir satir secin, sonra DXF butonuna basin.')
            return
        dxf_path = self._ed_dxf.text().strip()
        if not dxf_path or not os.path.exists(dxf_path):
            QMessageBox.warning(self,'DXF Bulunamadi',
                'Bu profil icin DXF dosyasi secilmemis.\n'
                '"Genel Bilgiler" sekmesinden DXF dosyasini secin.')
            return
        self._dxf_target_row = row
        try:
            dlg = DxfPickDialog(dxf_path, self)
            dlg.point_picked.connect(self._on_dxf_point_from_window)
            dlg.exec()
        except Exception as e:
            import traceback
            QMessageBox.critical(self,'DXF Hatasi',f'{e}\n\n{traceback.format_exc()}')

    def _on_dxf_point_from_window(self, y: float, z: float):
        self._write_yz(self._dxf_target_row, y, z)
        self._dxf_target_row = -1

    # ─────────────────────────────────────────────────────────
    # Tablodan JSON kaydet
    # ─────────────────────────────────────────────────────────
    def _save_ops_to_profile(self, side: str = None):
        if not self._cur_code: return
        if side is None:
            side = self._cb_side.currentData()
        prof = cg.get_profile(self._library, self._cur_code)
        if not prof: return
        macros = []
        for r in range(self._tbl_ops.rowCount()):
            itm = self._tbl_ops.item(r, 0)
            if not itm: continue
            op_id   = itm.data(Qt.UserRole)
            # 🔗 görsel grup işareti kaydedilmesin — kümülatif birikmeyi önler
            # replace() kullan: "🔗 🔗 🔗 Ad" gibi aralıklı durumları da temizler
            op_name = itm.text().replace('\U0001f517', '').strip()
            # Sütunları oku
            cb_p   = self._tbl_ops.cellWidget(r, 1)
            cb_t   = self._tbl_ops.cellWidget(r, 2)
            ed_x   = self._tbl_ops.cellWidget(r, 3)
            sp_y   = self._tbl_ops.cellWidget(r, 4)
            sp_z   = self._tbl_ops.cellWidget(r, 5)
            p_code = cb_p.currentData() if cb_p else 'P7'
            tool   = cb_t.currentData() if cb_t else 'T10'
            y_val  = sp_y.value() if sp_y else 0.0
            z_val  = sp_z.value() if sp_z else 0.0

            # X formülleri: virgülle ayrılmış metin → liste
            x_text     = ed_x.text().strip() if ed_x else ''
            x_formulas = [f.strip() for f in x_text.split(',') if f.strip()]

            # L, W, C, R, D — col 6-10
            params = {}
            for key, col in [('L',6),('W',7),('C',8),('R',9),('D',10)]:
                ed = self._tbl_ops.cellWidget(r, col)
                txt = ed.text().strip() if ed else ''
                if txt:
                    # R formül (ör. "W/2") string olarak sakla; diğerleri sayı
                    try:
                        v = float(txt)
                        if v > 0: params[key] = v
                    except ValueError:
                        params[key] = txt   # string formül

            # Grup tespiti: kayıtlı ops_list'te farklı p_code/tool veya adım y/z var mı?
            saved_ops   = itm.data(Qt.UserRole + 1) or []
            p_codes_set = {s.get('p_code') for s in saved_ops}
            tools_set   = {s.get('tool')   for s in saved_ops}
            has_step_yz = any('y' in s or 'z' in s for s in saved_ops)
            is_group    = (len(p_codes_set) > 1 or len(tools_set) > 1 or has_step_yz)

            if not x_formulas:
                x_formulas = ['0']

            if is_group and saved_ops:
                # Grup op: adım seviyesindeki P-kod/takım/Y/Z korunur.
                # X formülleri adım sayısıyla eşleşiyorsa tablodaki metni kullan.
                if len(x_formulas) == len(saved_ops):
                    final_ops = []
                    for i, (xf, s) in enumerate(zip(x_formulas, saved_ops)):
                        step = copy.deepcopy(s)
                        step['x_formula'] = xf
                        step['label'] = str(i + 1)
                        final_ops.append(step)
                else:
                    # Sayı tutmuyorsa orijinal ops_list'i aynen koru
                    final_ops = copy.deepcopy(saved_ops)
            else:
                # Basit op: tablodan yeniden oluştur
                final_ops = []
                for i, xf in enumerate(x_formulas):
                    final_ops.append({
                        'label':     str(i + 1),
                        'p_code':    p_code,
                        'tool':      tool,
                        'x_formula': xf,
                        'params':    copy.deepcopy(params),
                    })

            # Koşullu ranges (UserRole+2)
            ranges_data = itm.data(Qt.UserRole + 2)
            macro_entry = {'id': op_id, 'name': op_name, 'active': True,
                           'y_value': y_val, 'z_value': z_val, 'ops': final_ops}
            if ranges_data:
                macro_entry['ranges'] = copy.deepcopy(ranges_data)
            macros.append(macro_entry)
        prof.setdefault('operations', {})[side] = macros

    # ─────────────────────────────────────────────────────────
    # Genel bilgi uygula
    # ─────────────────────────────────────────────────────────
    def _apply_info(self):
        if not self._cur_code:
            QMessageBox.warning(self,'Uyari','Once sol listeden bir profil secin.')
            return
        try:
            new_code = self._ed_code.text().strip().upper()
            if not new_code:
                QMessageBox.warning(self,'Uyari','Stok kodu bos olamaz.')
                return
            prof = cg.get_profile(self._library, self._cur_code)
            if not prof:
                QMessageBox.warning(self,'Uyari','Profil bulunamadi.')
                return
            self._save_ops_to_profile()
            prof['name']         = self._ed_name.text().strip()
            prof['manufacturer'] = self._ed_mfr.text().strip()
            prof['series']       = self._ed_series.text().strip()
            prof['type']         = self._cb_type.currentData()
            prof['overlap_dxf']  = self._sp_overlap_dxf.value()
            prof['overlap_user'] = self._sp_overlap_user.value()
            prof['kerf']         = int(round(self._sp_overlap_dxf.value()))
            prof['dxf_file']     = self._ed_dxf.text().strip()
            prof['color']        = self._ed_color.text().strip()
            prof['width_mm']       = self._sp_width_mm.value()
            prof['height_mm']      = self._sp_height_mm.value()
            prof['robot_y']        = self._sp_robot_y.value()
            prof['robot_z']        = self._sp_robot_z.value()
            prof['robot_vertical'] = self._cb_robot_vert.currentData()
            if new_code != self._cur_code:
                if new_code in self._library.get('profiles',{}):
                    QMessageBox.warning(self,'Hata',f'"{new_code}" zaten mevcut.')
                    return
                self._library['profiles'][new_code] = prof
                del self._library['profiles'][self._cur_code]
                for k, v in self._library.get('last_used',{}).items():
                    if v == self._cur_code: self._library['last_used'][k] = new_code
                self._cur_code = new_code
            cg.save_library(self._library)
            self._dirty = False
            self._populate_tree()
            self._select_tree_item(self._cur_code)
            QMessageBox.information(self, 'Kaydedildi',
                f'"{prof["name"]}" profil bilgileri guncellendi ve kaydedildi.')
        except Exception as e:
            import traceback
            QMessageBox.critical(self,'Hata',f'{e}\n\n{traceback.format_exc()}')

    # ─────────────────────────────────────────────────────────
    # Profil CRUD
    # ─────────────────────────────────────────────────────────
    def _new_profile(self):
        code, ok = QInputDialog.getText(self,'Yeni Profil','Stok kodu (orn. PIM_KASA_70):')
        if not ok or not code.strip(): return
        code = code.strip().upper()
        if code in self._library.get('profiles',{}):
            QMessageBox.warning(self,'Hata',f'"{code}" zaten mevcut.'); return
        type_items = [f'{k} - {v}' for k,v in cg.PROFILE_LABEL.items()]
        choice, ok2 = QInputDialog.getItem(self,'Profil Tipi','Tip secin:',type_items,0,False)
        if not ok2: return
        ptype = choice.split(' - ')[0].strip()
        cg.add_profile(self._library, code, cg.new_empty_profile(code, ptype))
        self._dirty = True
        self._populate_tree(); self._select_tree_item(code)

    def _duplicate_profile(self):
        if not self._cur_code: return
        new_code, ok = QInputDialog.getText(self,'Kopyala','Yeni stok kodu:',
                                            text=self._cur_code+'_KOPYA')
        if not ok or not new_code.strip(): return
        new_code = new_code.strip().upper()
        src_prof = cg.get_profile(self._library, self._cur_code)
        new_name = src_prof.get('name',new_code) + ' (kopya)'
        if not cg.duplicate_profile(self._library, self._cur_code, new_code, new_name):
            QMessageBox.warning(self,'Hata',f'"{new_code}" zaten mevcut.'); return
        self._dirty = True
        self._populate_tree(); self._select_tree_item(new_code)

    def _delete_profile(self):
        if not self._cur_code: return
        prof = cg.get_profile(self._library, self._cur_code)
        name = prof.get('name', self._cur_code)
        if QMessageBox.question(self,'Profil Sil',f'"{name}" silinsin mi?',
                                QMessageBox.Yes|QMessageBox.No) != QMessageBox.Yes: return
        cg.delete_profile(self._library, self._cur_code)
        self._cur_code = None; self._dirty = True
        self._populate_tree(); self._set_detail_enabled(False)

    # ─────────────────────────────────────────────────────────
    # Yardimcilar
    # ─────────────────────────────────────────────────────────
    def _pick_dxf(self):
        path, _ = QFileDialog.getOpenFileName(self,'DXF Sec','','DXF (*.dxf)')
        if not path:
            return
        self._ed_dxf.setText(path)
        # DXF sınırlarından profil kesit boyutları + üst-20mm genişliği oku
        try:
            segs = load_dxf(path)
            if segs:
                # Yükseklik: standart | Genişlik: alt 30mm bölgenin en geniş noktası
                h_mm, w_mm = calc_profile_dimensions(segs)
                self._sp_width_mm.setValue(int(round(w_mm)))
                self._sp_height_mm.setValue(int(round(h_mm)))
                # Üst 20mm bölgesinden overlap_dxf
                top_w = self._calc_top_width_from_dxf_segs(segs)
                if top_w > 0:
                    self._sp_overlap_dxf.setValue(round(top_w, 1))
                # Viewport güncelle
                if hasattr(self, '_lib_viewport'):
                    self._lib_viewport.load_segments(segs)
        except Exception:
            pass   # DXF okunamazsa alanlar boş kalır

    @staticmethod
    def _calc_top_width_from_dxf_segs(segs) -> float:
        """DXF segmentlerinin en üst 20mm bölgesindeki yatay genişliği döndürür.

        Segment formatı: (y1, z1, y2, z2)  — Y=yatay, Z=dikey
        Algoritma:
          1. Tüm noktaların max_z (en üst) değerini bul.
          2. max_z - 20 ile max_z arasında kalan noktaları filtrele.
          3. Bu noktaların max_y - min_y değerini döndür (yatay genişlik).
        """
        try:
            if not segs:
                return 0.0
            # Her segment (y1, z1, y2, z2)
            all_zs = [s[1] for s in segs] + [s[3] for s in segs]
            max_z  = max(all_zs)
            z_min  = max_z - 20.0
            # Üst 20mm bölgesindeki Y koordinatları
            top_ys = []
            for y1, z1, y2, z2 in segs:
                if z1 >= z_min:
                    top_ys.append(y1)
                if z2 >= z_min:
                    top_ys.append(y2)
            if not top_ys:
                return 0.0
            return max(top_ys) - min(top_ys)
        except Exception:
            return 0.0

    def _pick_color(self):
        col = QColorDialog.getColor(QColor(self._ed_color.text() or '#808080'), self)
        if col.isValid(): self._ed_color.setText(col.name())

    def _update_color_btn(self):
        c = self._ed_color.text().strip()
        try: self._btn_color.setStyleSheet(f'background:{c};border:1px solid #555;')
        except Exception: pass

    def _set_detail_enabled(self, enabled):
        self._tabs.setEnabled(enabled)

    def _select_tree_item(self, code):
        it = self._tree.invisibleRootItem()
        for i in range(it.childCount()):
            grp = it.child(i)
            for j in range(grp.childCount()):
                child = grp.child(j)
                if child.data(0, Qt.UserRole) == code:
                    self._tree.setCurrentItem(child); return

    def _save_library(self):
        if self._cur_code:
            self._save_general_info_to_profile()   # ← genel bilgi alanlarini da kaydet
            self._save_ops_to_profile()
        try:
            cg.save_library(self._library)
            self._dirty     = False
            self._info_dirty = False
            QMessageBox.information(self,'Kaydedildi','Profil kutuphanesi kaydedildi.')
            self.library_changed.emit()
        except Exception as e:
            QMessageBox.critical(self,'Kayit Hatasi', str(e))

    def _export_excel(self):
        """Kütüphaneyi Excel'e aktar."""
        path, _ = QFileDialog.getSaveFileName(
            self, 'Excel\'e Aktar', cg._XLS_PATH,
            'Excel (*.xlsx);;Tüm Dosyalar (*)')
        if not path: return
        try:
            saved = cg.export_to_excel(self._library, path)
            QMessageBox.information(self, 'Aktarıldı',
                f'Kütüphane Excel\'e aktarıldı:\n{saved}')
        except Exception as e:
            import traceback
            QMessageBox.critical(self, 'Hata', f'{e}\n\n{traceback.format_exc()}')

    def _import_excel(self):
        """Excel'den kütüphane yükle (mevcut kütüphanenin üzerine yazar)."""
        path, _ = QFileDialog.getOpenFileName(
            self, 'Excel\'den Yükle', cg._XLS_PATH,
            'Excel (*.xlsx);;Tüm Dosyalar (*)')
        if not path: return
        reply = QMessageBox.question(self, 'Excel\'den Yükle',
            f'"{path}"\n\ndosyasındaki veriler mevcut kütüphanenin üzerine yazılacak.\n'
            'Devam etmek istiyor musunuz?',
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes: return
        try:
            lib = cg.import_from_excel(path)
            cg.save_library(lib)
            self._library = lib
            self._cur_code = None
            self._populate_tree()
            self._reload_ops_list()
            self._set_detail_enabled(False)
            QMessageBox.information(self, 'Yüklendi',
                f'Kütüphane Excel dosyasından yüklendi.\n'
                f'{len(lib.get("profiles", {}))} profil, '
                f'{len(lib.get("custom_ops", []))} özel işlem.')
            self.library_changed.emit()
        except Exception as e:
            import traceback
            QMessageBox.critical(self, 'Hata', f'{e}\n\n{traceback.format_exc()}')

    def closeEvent(self, ev):
        # Kapanmadan once mevcut profili otomatik kaydet (kullanicidan sormadan)
        if self._cur_code and (self._dirty or self._info_dirty):
            self._save_general_info_to_profile()
            self._save_ops_to_profile(side=self._prev_side)
            try:
                cg.save_library(self._library)
            except Exception:
                pass
        ev.accept()

    def get_library(self): return self._library
