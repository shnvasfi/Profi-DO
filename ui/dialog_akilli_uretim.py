"""
ui/dialog_akilli_uretim.py – Akıllı Üretim Ekranı
Winsa Profil Kesim Programı

Akış:
  1. Üst çubuk: Her profil tipi için "yapışkan" stok kodu seçimi
  2. Çerçeve tanımı: W × H, tip (kasa / kasa+kanat / sadece kanat vb.)
  3. Parça listesi: Hesaplanan 4-8 parça, uzunluklar düzenlenebilir
  4. Kod Üret: Her parça için P-code üretilir, önizleme gösterilir
  5. MDB'ye Kaydet: Tüm parçalar kayıt olarak eklenir
"""

import os
import sys
# ui/ alt klasöründen çalışırken proje kökünü (winsa_profil_kesim/) path'e ekle
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QFrame, QLineEdit,
    QGroupBox, QCheckBox, QMessageBox, QSplitter, QWidget,
    QAbstractItemView, QScrollArea, QSizePolicy, QFileDialog,
    QDialogButtonBox, QRadioButton, QButtonGroup,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QBrush

import code_generator as cg
import settings as st

SIDES = ['ALT', 'ÜST', 'SOL', 'SAĞ']
SIDE_ICONS = {'ALT': '⬇', 'ÜST': '⬆', 'SOL': '⬅', 'SAĞ': '➡'}
# MDB/Excel'e yazılacak kenar numaraları  (1=SOL, 2=ÜST, 3=SAĞ, 4=ALT)
SIDE_NUM = {
    'ALT': 4, 'ÜST': 2, 'SOL': 1, 'SAĞ': 3,
    'DİKEY': 5, 'YATAY': 6,   # orta kayıt
}

# Çerçeve hesap formülleri
# kasa_kerf    = kasanın overlap_dxf değeri  (DXF'ten okunan profil genişliği, mm)
# kasa_ov_user = kasanın overlap_user değeri (kullanıcı üst üste binme payı, mm)
# Kanat/kapı kanat boyutu SADECE kasa değerlerinden hesaplanır (Tip A mantığı):
#   Yatay: W - 2*kasa_kerf + kasa_ov_user
#   Dikey: H - 2*kasa_kerf + kasa_ov_user
# W, H mm cinsinden kullanıcı girişi
FRAME_RECIPES = {
    # Kasa parçaları W ve H ölçüsüne göre tam kesilir (45° bindirme).
    # Kanat, kasa içine oturur; kasa_kerf kadar küçülür, kasa_ov_user kadar uzar.
    'normal':    # Kasa (4 parça) + Kanat (4 parça)
        [
            {'role': 'kasa',  'side': 'ALT', 'len_formula': 'W'},
            {'role': 'kasa',  'side': 'ÜST', 'len_formula': 'W'},
            {'role': 'kasa',  'side': 'SOL', 'len_formula': 'H'},
            {'role': 'kasa',  'side': 'SAĞ', 'len_formula': 'H'},
            {'role': 'kanat', 'side': 'ALT', 'len_formula': 'W - 2*kasa_kerf + kasa_ov_user'},
            {'role': 'kanat', 'side': 'ÜST', 'len_formula': 'W - 2*kasa_kerf + kasa_ov_user'},
            {'role': 'kanat', 'side': 'SOL', 'len_formula': 'H - 2*kasa_kerf + kasa_ov_user'},
            {'role': 'kanat', 'side': 'SAĞ', 'len_formula': 'H - 2*kasa_kerf + kasa_ov_user'},
        ],
    'sadece_kasa':
        [
            {'role': 'kasa', 'side': 'ALT', 'len_formula': 'W'},
            {'role': 'kasa', 'side': 'ÜST', 'len_formula': 'W'},
            {'role': 'kasa', 'side': 'SOL', 'len_formula': 'H'},
            {'role': 'kasa', 'side': 'SAĞ', 'len_formula': 'H'},
        ],
    'sadece_kanat':
        [
            {'role': 'kanat', 'side': 'ALT', 'len_formula': 'W'},
            {'role': 'kanat', 'side': 'ÜST', 'len_formula': 'W'},
            {'role': 'kanat', 'side': 'SOL', 'len_formula': 'H'},
            {'role': 'kanat', 'side': 'SAĞ', 'len_formula': 'H'},
        ],
    'kapi':      # Kasa (4) + Kapı Kanat (4)
        [
            {'role': 'kasa',      'side': 'ALT', 'len_formula': 'W'},
            {'role': 'kasa',      'side': 'ÜST', 'len_formula': 'W'},
            {'role': 'kasa',      'side': 'SOL', 'len_formula': 'H'},
            {'role': 'kasa',      'side': 'SAĞ', 'len_formula': 'H'},
            {'role': 'kapi_kanat','side': 'ALT', 'len_formula': 'W - 2*kasa_kerf + kasa_ov_user'},
            {'role': 'kapi_kanat','side': 'ÜST', 'len_formula': 'W - 2*kasa_kerf + kasa_ov_user'},
            {'role': 'kapi_kanat','side': 'SOL', 'len_formula': 'H - 2*kasa_kerf + kasa_ov_user'},
            {'role': 'kapi_kanat','side': 'SAĞ', 'len_formula': 'H - 2*kasa_kerf + kasa_ov_user'},
        ],
    'sadece_kapi':  # Sadece Kapı Kanat (4)
        [
            {'role': 'kapi_kanat','side': 'ALT', 'len_formula': 'W'},
            {'role': 'kapi_kanat','side': 'ÜST', 'len_formula': 'W'},
            {'role': 'kapi_kanat','side': 'SOL', 'len_formula': 'H'},
            {'role': 'kapi_kanat','side': 'SAĞ', 'len_formula': 'H'},
        ],
}

RECIPE_LABELS = {
    'normal':       'Pencere (Kasa + Kanat)',
    'sadece_kasa':  'Sadece Kasa',
    'sadece_kanat': 'Sadece Kanat',
    'kapi':         'Kapı (Kasa + Kapı Kanat)',
    'sadece_kapi':  'Sadece Kapı',
}

# Rol → kütüphanedeki tip kodu
ROLE_TYPE = {
    'kasa':       'A',
    'kanat':      'B',
    'kapi_kanat': 'J',
}

_STYLE = """
QDialog, QWidget { background:#1e1e2e; color:#ccc; font-size:12px; }
QGroupBox { border:1px solid #444; border-radius:4px; margin-top:8px; color:#aaa; font-size:11px; }
QGroupBox::title { subcontrol-origin:margin; left:8px; padding:0 4px; }
QComboBox, QSpinBox { background:#2e2e42; color:#ddd; border:1px solid #555;
    border-radius:3px; padding:3px 6px; font-size:12px; }
QPushButton { background:#2e2e42; color:#ccc; border:1px solid #444;
    border-radius:4px; padding:5px 12px; font-size:12px; }
QPushButton:hover { background:#3a3a55; }
QPushButton#btn_calc  { background:#1a5c3a; color:white; font-weight:bold; }
QPushButton#btn_calc:hover { background:#226e47; }
QPushButton#btn_gen   { background:#1a4a7a; color:white; font-weight:bold; }
QPushButton#btn_gen:hover  { background:#2060a0; }
QPushButton#btn_save  { background:#7a3a20; color:white; font-weight:bold; }
QPushButton#btn_save:hover { background:#a05030; }
QTableWidget { background:#161625; color:#ddd; border:1px solid #333;
    gridline-color:#2a2a3a; font-size:12px; }
QTableWidget QHeaderView::section { background:#252535; color:#aaa; border:1px solid #333;
    padding:3px; font-size:11px; }
QTextEdit { background:#0d1117; color:#56cfe1; font-family:'Courier New';
    font-size:13px; border:1px solid #333; border-radius:3px; }
QLabel { color:#ccc; }
QLabel#lbl_head { color:#56cfe1; font-size:14px; font-weight:bold; }
QLabel#lbl_sub  { color:#aaa; font-size:11px; }
"""


def compute_cell_bounds_map(mullions_v, mullions_h, inner_w, inner_h):
    """
    Verilen orta kayıt listeleri için geçerli TÜM (yaprak) hücrelerin mm
    cinsinden sınır haritasını döndürür: {(row, col): (x0, x1, y0, y1)}.

    Genel amaçlı, HERHANGİ BİR DERİNLİKTE iç içe bölünmeyi doğru destekleyen
    özyinelemeli bir algoritma kullanır. Her orta kayıt, hangi mm ARALIĞINDA
    geçerli olduğunu mutlak koordinatlarla taşır:
      • dikey (v) kayıt  → 'y_scope': (y0,y1) veya None (tüm yükseklik,
        sadece en üst seviye/boydan-boya kayıtlar için)
      • yatay (h) kayıt → 'x_scope': (x0,x1) veya None (tüm genişlik)

    Bu, eski "sütun-öncelikli / satır-öncelikli" iki-seviyeli yaklaşımın
    yerini alır: eskisi, ekleme SIRASINA ve DERİNLİĞİNE göre yanlış sonuçlar
    üretebiliyordu (örn. bir hücreye özel eklenen 3. seviye bir dikey,
    yanlışlıkla tüm çerçeveyi bölen genel bir sütun sınırı gibi
    işleniyordu). Mutlak mm-aralığı eşleştirmesi bu sınıf hatayı kökten
    ortadan kaldırır: bir kayıt SADECE, oluşturulduğu hücrenin tam
    sınırlarıyla eşleşen bir bölgede geçerli olur.

    Geriye dönük uyumluluk: 'y_scope'/'x_scope' alanı olmayan eski formatlı
    kayıtlar (sadece 'rows'/'cols' index'i olan) en üst seviyede (None
    scope) değerlendirilir — bu, tek seviyeli (basit) senaryolarda önceki
    davranışla birebir aynıdır.

    Bu fonksiyon, FramePreviewWidget (çizim/tıklama) ve AkilliUretimDialog
    (parça hesaplama) tarafından ORTAK olarak kullanılır — tek doğruluk
    kaynağı burasıdır; iki yerde ayrı ayrı (ve tutarsız) yeniden
    yazılmaz.
    """
    EPS = 0.75  # mm tolerans (kapsam/konum eşleşmesi için)

    def _pos(m):
        return float(m['pos'] if isinstance(m, dict) else m)

    def _v_scope(m):
        return m.get('y_scope') if isinstance(m, dict) else None

    def _h_scope(m):
        return m.get('x_scope') if isinstance(m, dict) else None

    def _scope_matches(scope, lo, hi):
        if scope is None:
            return False
        s0, s1 = scope
        return abs(s0 - lo) <= EPS and abs(s1 - hi) <= EPS

    def _split(x0, x1, y0, y1, is_top):
        vs = [m for m in (mullions_v or [])
              if x0 + EPS < _pos(m) < x1 - EPS
              and ((is_top and _v_scope(m) is None) or _scope_matches(_v_scope(m), y0, y1))]
        hs = [m for m in (mullions_h or [])
              if y0 + EPS < _pos(m) < y1 - EPS
              and ((is_top and _h_scope(m) is None) or _scope_matches(_h_scope(m), x0, x1))]

        if not vs and not hs:
            return [(x0, x1, y0, y1)]

        v_pos = sorted(set(round(_pos(m), 3) for m in vs))
        h_pos = sorted(set(round(_pos(m), 3) for m in hs))
        v_bounds = [x0] + v_pos + [x1]
        h_bounds = [y0] + h_pos + [y1]

        leaves = []
        for ci in range(len(v_bounds) - 1):
            for ri in range(len(h_bounds) - 1):
                leaves.extend(_split(v_bounds[ci], v_bounds[ci + 1],
                                      h_bounds[ri], h_bounds[ri + 1], False))
        return leaves

    leaves = _split(0.0, float(inner_w), 0.0, float(inner_h), True)

    # Kararlı (row,col) numaralandırma: y0'a göre satır grubu, o grup
    # içinde x0'a göre sütun sırası. Sadece görüntüleme/anahtar amaçlı —
    # gerçek bölünme mantığı yukarıda mm koordinatlarıyla zaten çözüldü.
    rows_sorted = sorted(set(round(l[2], 1) for l in leaves))
    row_index = {y: i for i, y in enumerate(rows_sorted)}
    by_row = {}
    for l in leaves:
        by_row.setdefault(round(l[2], 1), []).append(l)
    result = {}
    for y, cells in by_row.items():
        cells.sort(key=lambda l: l[0])
        for ci, (x0, x1, y0, y1) in enumerate(cells):
            result[(row_index[y], ci)] = (x0, x1, y0, y1)
    return result


class FramePreviewWidget(QWidget):
    """
    Saf QPainter tabanlı çerçeve görsel önizlemesi — matplotlib YOK.
    Kasa/kanat trapez barlarını çizer, seçili parçayı vurgular.
    """

    from PySide6.QtCore import Signal as _Signal
    cellClicked          = _Signal(int, int)   # row, col (0-tabanlı)
    cellClickedForMullion = _Signal(int, int, str)  # row, col, 'v'|'h'

    # Rol renkleri: (fill_hex, edge_hex)  — beyaz alüminyum mimari stil
    _ROLE_COLORS = {
        'kasa':       ('#e8e8e8', '#555555'),
        'kanat':      ('#f2f2f2', '#444444'),
        'kapi_kanat': ('#eeeeee', '#444444'),
        'orta_kayit': ('#d8d8d8', '#555555'),
    }
    _SEL_FILL  = '#d0e8ff'
    _SEL_EDGE  = '#2266cc'
    _BG_COLOR  = '#ffffff'
    _TEXT_DIM  = '#1a5588'
    _TEXT_BAR  = '#333333'
    _TEXT_SEL  = '#000000'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self._pieces     = []
        self._W          = 1200
        self._H          = 1500
        self._sel        = -1
        self._kerf_kasa     = 45
        self._kerf_kanat    = 45
        self._kanat_ov_user = 0.0
        self._kanat_width   = 0.0
        self._library       = {}   # profil renkleri için
        self._mullions_v: list = []
        self._mullions_h: list = []
        self._select_mode   = False          # hücre seçim modu (kanat)
        self._mullion_mode  = None          # 'v' veya 'h' — orta kayıt yerleştirme modu
        self._hovered_cell  = (-1, -1)      # hover edilen hücre
        self._cell_assigns  = {}            # (row,col) → renk hex
        self._kasa_only     = False         # sadece kasa göster (parça yokken)
        self.setMouseTracking(True)

    # ── Dışarıdan çağrılan API ────────────────────────────────

    def update_frame(self, pieces: list, W: int, H: int,
                     kerf_kasa: int = 45, kerf_kanat: int = 45,
                     library: dict = None,
                     kanat_ov_user: float = 0.0,
                     kanat_width_mm: float = 0.0):
        self._pieces        = list(pieces)
        self._W             = W
        self._H             = H
        self._kerf_kasa     = kerf_kasa
        self._kerf_kanat    = kerf_kanat
        self._kanat_ov_user = kanat_ov_user   # üst üste binme payı (mm)
        self._kanat_width   = kanat_width_mm  # kanat profil genişliği (mm)
        self._sel           = -1
        if library is not None:
            self._library = library
        self.update()   # Qt repaint tetikle

    def set_selected(self, row: int):
        if self._sel != row:
            self._sel = row
            self.update()

    def set_mullions(self, mv: list, mh: list):
        self._mullions_v = list(mv)
        self._mullions_h = list(mh)
        self.update()

    def set_select_mode(self, enabled: bool):
        self._select_mode = enabled
        from PySide6.QtCore import Qt as _Qt2
        self.setCursor(_Qt2.CrossCursor if enabled else _Qt2.ArrowCursor)
        self.update()

    def set_mullion_mode(self, mode):   # mode: 'v' | 'h' | None
        self._mullion_mode = mode
        from PySide6.QtCore import Qt as _Qt2
        self.setCursor(_Qt2.CrossCursor if mode else _Qt2.ArrowCursor)
        self.update()

    def set_cell_assign(self, row: int, col: int, color_hex: str):
        self._cell_assigns[(row, col)] = color_hex
        self.update()

    def clear_cell_assigns(self):
        self._cell_assigns.clear()
        self.update()

    def show_kasa_only(self, W: int, H: int, kerf_kasa: float, library: dict = None):
        """Sadece kasayı önizlemede göster (parça hesaplamadan)."""
        self._kasa_only = True
        self._W = W; self._H = H
        self._kerf_kasa = kerf_kasa
        self._kerf_kanat = 0
        self._pieces = []
        if library is not None:
            self._library = library
        self.update()

    def mousePressEvent(self, event):
        if not self._select_mode and not self._mullion_mode:
            return
        cell = self._get_cell_at(event.pos())
        if self._select_mode and cell is not None:
            self.cellClicked.emit(cell[0], cell[1])
        if self._mullion_mode and cell is not None:
            self.cellClickedForMullion.emit(cell[0], cell[1], self._mullion_mode)

    def mouseMoveEvent(self, event):
        if self._select_mode or self._mullion_mode:
            cell = self._get_cell_at(event.pos())
            new_hov = cell if cell else (-1, -1)
            if new_hov != self._hovered_cell:
                self._hovered_cell = new_hov
                self.update()

    def _get_cell_at(self, qpos) -> tuple:
        """Tıklanan piksel konumundan (row, col) döndür. Hücre dışıysa None."""
        W = float(self._W); H = float(self._H)
        tk = float(self._kerf_kasa)

        W_px = self.width(); H_px = self.height()
        PAD_R=72; PAD_B=52; PAD_T=22; PAD_L=14
        draw_w = W_px-PAD_L-PAD_R; draw_h = H_px-PAD_T-PAD_B
        if draw_w < 1 or draw_h < 1: return None
        scale = min(draw_w/W, draw_h/H)
        frame_px_w = W*scale; frame_px_h = H*scale
        ML = max(PAD_L, (W_px - frame_px_w)/2.0)
        MT = max(PAD_T, (H_px - PAD_B - frame_px_h)/2.0)

        x_mm = (qpos.x() - ML) / scale
        y_mm = H - (qpos.y() - MT) / scale

        inner_x0 = tk; inner_x1 = W - tk
        inner_y0 = tk; inner_y1 = H - tk

        if not (inner_x0 <= x_mm <= inner_x1 and inner_y0 <= y_mm <= inner_y1):
            return None

        # İç-koordinatlara çevir (0..inner_w / 0..inner_h) — compute_cell_bounds_map
        # HER YERDE (paintEvent, _calculate_frame, mullion dialogları) bu
        # sistemi kullanır; tek doğruluk kaynağı.
        inner_w = inner_x1 - inner_x0
        inner_h = inner_y1 - inner_y0
        x_rel = x_mm - inner_x0
        y_rel = y_mm - inner_y0

        bounds_map = compute_cell_bounds_map(self._mullions_v, self._mullions_h, inner_w, inner_h)
        for (ri, ci), (x0, x1, y0, y1) in bounds_map.items():
            if x0 <= x_rel <= x1 and y0 <= y_rel <= y1:
                return (ri, ci)
        return None

    # ── QPainter çizimi ───────────────────────────────────────

    def paintEvent(self, event):
        from PySide6.QtGui import (QPainter, QColor, QPolygonF, QPen,
                                   QBrush, QFont, QFontMetrics)
        from PySide6.QtCore import QPointF, QRectF, Qt as _Qt

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W_px = self.width()
        H_px = self.height()

        # Arka plan
        p.fillRect(0, 0, W_px, H_px, QColor(self._BG_COLOR))

        if not self._pieces and not self._kasa_only:
            p.setPen(QColor('#888888'))
            p.setFont(QFont('Arial', 10))
            p.drawText(QRectF(0, 0, W_px, H_px),
                       _Qt.AlignmentFlag.AlignCenter,
                       'Çerçeve Önizlemesi\n\nÇerçeve Hesapla butonuna bas')
            p.end()
            return

        W  = float(self._W)
        H  = float(self._H)
        tk = float(self._kerf_kasa)
        tn = float(self._kerf_kanat)

        # Kenar boşlukları — ölçü okları için sağ/alt pay
        PAD_R = 72   # sağda H oku için
        PAD_B = 52   # altta W oku için
        PAD_T = 22   # üstte başlık
        PAD_L = 14   # solda minimum

        draw_w = W_px - PAD_L - PAD_R
        draw_h = H_px - PAD_T - PAD_B
        if draw_w < 10 or draw_h < 10:
            p.end()
            return

        scale = min(draw_w / W, draw_h / H)

        # Gerçek çizim boyutu (mm × scale)
        frame_px_w = W * scale
        frame_px_h = H * scale

        # Frame'i tam widget genişliğinde ortala
        # H oku frame sağına çizilir — PAD_R frame dışında, merkez tam orta
        ML = max(PAD_L, (W_px - frame_px_w) / 2.0)
        MT = max(PAD_T, (H_px - PAD_B - frame_px_h) / 2.0)

        def mm2qpt(x_mm, y_mm):
            """mm → QPointF  (Y eksen: alt=0 → ekranda aşağı)"""
            px = ML + x_mm * scale
            py = MT + (H - y_mm) * scale
            return QPointF(px, py)

        def miter_poly(side, ox, ot):
            if side == 'ALT':
                pts = [(ox, ox), (W-ox, ox),
                       (W-ox-ot, ox+ot), (ox+ot, ox+ot)]
            elif side == 'ÜST':
                pts = [(ox+ot, H-ox-ot), (W-ox-ot, H-ox-ot),
                       (W-ox, H-ox), (ox, H-ox)]
            elif side == 'SOL':
                pts = [(ox, ox), (ox+ot, ox+ot),
                       (ox+ot, H-ox-ot), (ox, H-ox)]
            elif side == 'SAĞ':
                pts = [(W-ox-ot, ox+ot), (W-ox, ox),
                       (W-ox, H-ox), (W-ox-ot, H-ox-ot)]
            else:
                return None
            return QPolygonF([mm2qpt(x, y) for x, y in pts])

        # (role, side) → (idx, piece)
        # Hücre kanıtları (cell attribute'u olan) — _cell_assigns ile çizilir, buraya eklenmez
        piece_map = {}
        for i, pc in enumerate(self._pieces):
            if pc.get('cell') is not None:
                continue   # hücre kanat parçası — ayrıca çizilecek
            piece_map[(pc['role'], pc['side'])] = (i, pc)

        font_bar = QFont('Arial', 8)
        font_bar.setBold(False)
        font_sel = QFont('Arial', 8)
        font_sel.setBold(True)

        # Dış etiket için her kenar-rol çiftinin ölçüsünü topla
        outside_labels = {}   # side → [(role_short, length_mm, color)]

        # _kasa_only modunda: kasa parçası yoksa çerçeve outline'ı elle çiz
        if self._kasa_only and not any(pc['role'] == 'kasa' for pc in self._pieces):
            kasa_clr = QColor(self._ROLE_COLORS.get('kasa', ('#c0c0c0','#888888'))[0])
            kasa_edge = QColor(self._ROLE_COLORS.get('kasa', ('#c0c0c0','#888888'))[1])
            p.setPen(QPen(kasa_edge, 1.5))
            for side in ('ALT', 'ÜST', 'SOL', 'SAĞ'):
                poly = miter_poly(side, 0, tk)
                if poly:
                    p.setBrush(QBrush(kasa_clr))
                    p.drawPolygon(poly)

        for role in ('kasa', 'kanat', 'kapi_kanat'):
            for side in ('ALT', 'ÜST', 'SOL', 'SAĞ'):
                key = (role, side)
                if key not in piece_map:
                    continue
                idx, pc = piece_map[key]
                is_sel = (idx == self._sel)

                if is_sel:
                    fill_hex = self._SEL_FILL
                    edge_hex = self._SEL_EDGE
                    lw = 2.5
                else:
                    prof_clr = None
                    if self._library:
                        prof = cg.get_profile(self._library, pc.get('stock_code', ''))
                        if prof:
                            prof_clr = prof.get('color') or prof.get('colour')
                    if prof_clr:
                        fill_hex = prof_clr
                        try:
                            r = int(prof_clr[1:3], 16)
                            g = int(prof_clr[3:5], 16)
                            b = int(prof_clr[5:7], 16)
                            edge_hex = '#{:02x}{:02x}{:02x}'.format(
                                max(0, r-40), max(0, g-40), max(0, b-40))
                        except Exception:
                            edge_hex = '#404040'
                    else:
                        fill_hex, edge_hex = self._ROLE_COLORS.get(
                            role, ('#606060', '#404040'))
                    lw = 0.8

                if role == 'kasa':
                    ox = 0.0
                    ot = tk
                else:
                    # Kanat/kapı kanat: kasanın içine üst_üste_binme kadar taşır
                    ov_user = self._kanat_ov_user if self._kanat_ov_user > 0 else 0.0
                    kw_vis  = self._kanat_width if self._kanat_width > 0 else max(tn, tk * 0.85)
                    ox = max(0.0, tk - ov_user)
                    ot = kw_vis

                poly = miter_poly(side, ox, ot)
                if poly is None:
                    continue

                p.setBrush(QBrush(QColor(fill_hex)))
                pen = QPen(QColor(edge_hex))
                pen.setWidthF(lw)
                p.setPen(pen)
                p.drawPolygon(poly)

                # Profil içine sadece küçük kısaltma
                cx = sum(pt.x() for pt in poly) / len(poly)
                cy_lbl = sum(pt.y() for pt in poly) / len(poly)
                rshort = {'kasa': 'K', 'kanat': 'Kn', 'kapi_kanat': 'KpK'}.get(role, role)

                if is_sel:
                    lbl = f'{rshort} {side}\n{pc["length_mm"]} mm'
                    txt_clr = self._TEXT_SEL
                    p.setPen(QColor(txt_clr)); p.setFont(font_sel)
                    fm = QFontMetrics(font_sel)
                    lines = lbl.split('\n'); lh = fm.height()
                    total_h = lh * len(lines)
                    for li, line in enumerate(lines):
                        lw2 = fm.horizontalAdvance(line)
                        p.drawText(QPointF(cx - lw2/2,
                                           cy_lbl - total_h/2 + li*lh + lh*0.8), line)
                else:
                    # Küçük kısaltma içeride
                    p.setPen(QColor('#ffffff' if fill_hex < '#888888' else '#222222'))
                    p.setFont(font_bar)
                    fm2 = QFontMetrics(font_bar)
                    p.drawText(QPointF(cx - fm2.horizontalAdvance(rshort)/2,
                                       cy_lbl + fm2.height()*0.35), rshort)

                # Dış etiket için biriktir
                if side not in outside_labels:
                    outside_labels[side] = []
                outside_labels[side].append((rshort, pc['length_mm'], fill_hex))

        # ── Orta kayıt barları ─────────────────────────────────────────
        if self._mullions_v or self._mullions_h:
            inner_x0 = tk;  inner_x1 = W - tk
            inner_y0 = tk;  inner_y1 = H - tk
            mw = self._get_mullion_top_width() if hasattr(self, '_get_mullion_top_width') else 30
            mull_fill = QColor('#d8d8d8')
            mull_edge = QColor('#555555')
            p.setPen(QPen(mull_edge, 1.0))

            # Dikey orta kayıtlar — kalın bar. Her kayıt kendi y_scope'unu
            # (mm aralığını, iç-göreli) taşır; None ise tüm yükseklik.
            # Mutlak aralık kullanıldığı için derinlik/sıra fark etmez.
            for mv_item in self._mullions_v:
                if isinstance(mv_item, dict):
                    vpos = mv_item['pos']
                    y_scope = mv_item.get('y_scope')
                else:
                    vpos = mv_item  # eski format uyumluluğu
                    y_scope = None

                x_mm = inner_x0 + vpos
                y0_row, y1_row = (inner_y0, inner_y1) if y_scope is None \
                    else (inner_y0 + y_scope[0], inner_y0 + y_scope[1])

                pt_tl = mm2qpt(x_mm - mw/2, y1_row)
                pt_br = mm2qpt(x_mm + mw/2, y0_row)
                r = QRectF(min(pt_tl.x(),pt_br.x()), min(pt_tl.y(),pt_br.y()),
                           abs(pt_br.x()-pt_tl.x()), abs(pt_br.y()-pt_tl.y()))
                p.setBrush(QBrush(mull_fill)); p.setPen(QPen(mull_edge, 1.0))
                p.drawRect(r)

            # Yatay orta kayıtlar — kalın bar. Her kayıt kendi x_scope'unu taşır.
            for mh_item in (self._mullions_h or []):
                if isinstance(mh_item, dict):
                    hpos = mh_item['pos']
                    x_scope = mh_item.get('x_scope')
                else:
                    hpos = mh_item
                    x_scope = None

                y_mm = inner_y0 + hpos - mw / 2
                x0_col, x1_col = (inner_x0, inner_x1) if x_scope is None \
                    else (inner_x0 + x_scope[0], inner_x0 + x_scope[1])

                pt_tl = mm2qpt(x0_col, y_mm + mw)
                pt_br = mm2qpt(x1_col, y_mm)
                r = QRectF(min(pt_tl.x(),pt_br.x()), min(pt_tl.y(),pt_br.y()),
                           abs(pt_br.x()-pt_tl.x()), abs(pt_br.y()-pt_tl.y()))
                p.setBrush(QBrush(mull_fill)); p.setPen(QPen(mull_edge, 1.0))
                p.drawRect(r)

        # ── Hücre atama renkleri + hover ─────────────────────────────
        if self._mullions_v is not None or self._mullions_h is not None:
            _inner_x0 = tk; _inner_x1 = W - tk
            _inner_y0 = tk; _inner_y1 = H - tk
            _EDGE_EPS = 0.75

            # Tek doğruluk kaynağı: compute_cell_bounds_map (bkz. dosya üstü).
            # Herhangi bir derinlikteki iç içe bölünmeyi doğru işler.
            _bounds_map2 = compute_cell_bounds_map(
                self._mullions_v, self._mullions_h,
                _inner_x1 - _inner_x0, _inner_y1 - _inner_y0)
            _cell_iter2 = [
                (ri, ci, _inner_x0 + x0r, _inner_x0 + x1r, _inner_y0 + y0r, _inner_y0 + y1r)
                for (ri, ci), (x0r, x1r, y0r, y1r) in _bounds_map2.items()
            ]

            for (ri, ci, x0c, x1c, y0c, y1c) in _cell_iter2:
                from PySide6.QtCore import QRectF as _QRectF2
                pt0c = mm2qpt(x0c, y0c); pt1c = mm2qpt(x1c, y1c)
                cell_rect = _QRectF2(min(pt0c.x(),pt1c.x()), min(pt0c.y(),pt1c.y()),
                                    abs(pt1c.x()-pt0c.x()), abs(pt1c.y()-pt0c.y()))

                # Atanmış kanat — kasanın üzerine taşan kanat çerçevesi çiz
                if (ri, ci) in self._cell_assigns:
                    fill_hex = self._cell_assigns[(ri, ci)]
                    edge_hex = '#444444'
                    # Kanat kalınlığı: kerf_kanat veya fallback
                    ov = self._kanat_ov_user if self._kanat_ov_user > 0 else 0.0
                    kw_vis = self._kanat_width if self._kanat_width > 0 else max(self._kerf_kanat, tk * 0.85)
                    # Hücre sınırları + overlap (kasanın üzerine taş)
                    # Kasa-komşu kenarlar: overlap kadar dışarı çık
                    # İç kenarlar (orta kayıt komşusu): tam sınırda kal
                    # Kenar tespiti DOĞRUDAN KOORDİNATLA yapılır (index ile
                    # değil) — böylece herhangi bir iç içe bölünme
                    # derinliğinde ve numaralandırma şemasında doğru çalışır.
                    _is_top_edge    = (y1c >= _inner_y1 - _EDGE_EPS)
                    _is_bot_edge    = (y0c <= _inner_y0 + _EDGE_EPS)
                    _is_left_edge   = (x0c <= _inner_x0 + _EDGE_EPS)
                    _is_right_edge  = (x1c >= _inner_x1 - _EDGE_EPS)
                    _ov_top  = ov if _is_top_edge  else 0.0
                    _ov_bot  = ov if _is_bot_edge  else 0.0
                    _ov_left = ov if _is_left_edge else 0.0
                    _ov_right= ov if _is_right_edge else 0.0
                    # Kanat dış kenar pozisyonları (kasanın üzerine taşar)
                    cx0 = x0c - _ov_left;  cx1 = x1c + _ov_right
                    cy0 = y0c - _ov_bot;   cy1 = y1c + _ov_top
                    cW = cx1 - cx0; cH = cy1 - cy0
                    def _cpoly(side, _cx0=cx0, _cy0=cy0, _cW=cW, _cH=cH, _t=kw_vis):
                        ox2, oy2 = _cx0, _cy0
                        if side == 'ALT':
                            pts = [(ox2,oy2),(ox2+_cW,oy2),(ox2+_cW-_t,oy2+_t),(ox2+_t,oy2+_t)]
                        elif side == 'ÜST':
                            pts = [(ox2+_t,oy2+_cH-_t),(ox2+_cW-_t,oy2+_cH-_t),(ox2+_cW,oy2+_cH),(ox2,oy2+_cH)]
                        elif side == 'SOL':
                            pts = [(ox2,oy2),(ox2+_t,oy2+_t),(ox2+_t,oy2+_cH-_t),(ox2,oy2+_cH)]
                        else:
                            pts = [(ox2+_cW-_t,oy2+_t),(ox2+_cW,oy2),(ox2+_cW,oy2+_cH),(ox2+_cW-_t,oy2+_cH-_t)]
                        return QPolygonF([mm2qpt(x,y) for x,y in pts])
                    p.setPen(QPen(QColor(edge_hex), 1.0))
                    p.setBrush(QBrush(QColor(fill_hex)))
                    for s in ('ALT','ÜST','SOL','SAĞ'):
                        p.drawPolygon(_cpoly(s))
                    # Cam alanı
                    g_tl = mm2qpt(cx0 + kw_vis, cy1 - kw_vis)
                    g_br = mm2qpt(cx1 - kw_vis, cy0 + kw_vis)
                    glass_r = QRectF(min(g_tl.x(),g_br.x()), min(g_tl.y(),g_br.y()),
                                     abs(g_br.x()-g_tl.x()), abs(g_br.y()-g_tl.y()))
                    p.setBrush(QBrush(QColor(245, 248, 252, 200)))
                    p.setPen(QPen(QColor(160, 180, 200, 100), 0.5))
                    p.drawRect(glass_r)

                    # ── Hücre menteşe + kol ──────────────────────────
                    # Boyut referansı: glass_r (cam alanı piksel boyutları)
                    gw_px = glass_r.width(); gh_px = glass_r.height()
                    gx_px = glass_r.left();  gy_px = glass_r.top()

                    # ── Menteşeler — kasa/kanat sağ sınırına yayılır ─────
                    if _is_right_edge:
                        # Menteşe merkezi: kanat sağ dış kenarı (cx1) = kasa iç sağ kenar
                        boundary_px = mm2qpt(cx1, 0).x()
                        m_w  = max(kw_vis * scale * 0.30, 4)
                        m_h  = max(gh_px * 0.10, 22)
                        m_x  = boundary_px - m_w / 2
                        margin_c = gh_px * 0.06

                        for hy in (gy_px + margin_c,
                                   gy_px + gh_px - margin_c - m_h):
                            # Gölge
                            p.setBrush(QBrush(QColor(160, 160, 160, 80)))
                            p.setPen(Qt.NoPen)
                            p.drawRoundedRect(QRectF(m_x+1.5, hy+1.5, m_w, m_h), 2, 2)
                            # Ana menteşe gövdesi
                            grad_clr1 = QColor(225, 225, 225)
                            grad_clr2 = QColor(195, 195, 195)
                            p.setBrush(QBrush(grad_clr1))
                            p.setPen(QPen(QColor(140, 140, 140), 0.8))
                            p.drawRoundedRect(QRectF(m_x, hy, m_w, m_h), 2, 2)
                            # Üst parlama şeridi
                            p.setPen(QPen(QColor(255, 255, 255, 150), 0.7))
                            p.drawLine(QPointF(m_x+2,     hy+1.5),
                                       QPointF(m_x+m_w-2, hy+1.5))
                            # Alt gölge şeridi
                            p.setPen(QPen(QColor(120, 120, 120, 100), 0.6))
                            p.drawLine(QPointF(m_x+2,     hy+m_h-1.5),
                                       QPointF(m_x+m_w-2, hy+m_h-1.5))
                            # Vida delikleri — üst ve alt
                            scr_r = max(m_h * 0.10, 1.8)
                            for vy in (hy + m_h*0.25, hy + m_h*0.75):
                                cx_v = m_x + m_w/2
                                p.setBrush(QBrush(QColor(150, 150, 150)))
                                p.setPen(QPen(QColor(100, 100, 100), 0.6))
                                p.drawEllipse(QPointF(cx_v, vy), scr_r, scr_r)
                                p.setPen(QPen(QColor(80, 80, 80), 0.5))
                                p.drawLine(QPointF(cx_v-scr_r*0.65, vy),
                                           QPointF(cx_v+scr_r*0.65, vy))
                                p.drawLine(QPointF(cx_v, vy-scr_r*0.65),
                                           QPointF(cx_v, vy+scr_r*0.65))

                    # ── Pencere kolu — kanat SOL profilinin tam ortasında ──
                    rw2    = max(kw_vis * scale * 0.45, 5)
                    rh2    = max(gh_px * 0.10, 14)
                    arm_w  = max(kw_vis * scale * 0.8, 10)
                    arm_h  = max(rw2 * 0.40, 3)
                    tip_r2 = max(arm_h * 0.85, 3)
                    h_pen4 = QPen(QColor('#888888'), 0.8)
                    strip_mid_x_px = mm2qpt(cx0 + kw_vis/2, 0).x()
                    hdl_x  = strip_mid_x_px - rw2/2
                    hdl_y  = gy_px + gh_px / 2
                    # Rozet
                    p.setBrush(QBrush(QColor(200, 200, 200)))
                    p.setPen(h_pen4)
                    p.drawRoundedRect(QRectF(hdl_x, hdl_y - rh2/2, rw2, rh2), 2, 2)
                    # Kol kolu (yatay, rozetten sağa)
                    p.setBrush(QBrush(QColor(210, 210, 210)))
                    p.drawRoundedRect(
                        QRectF(hdl_x + rw2, hdl_y - arm_h/2, arm_w, arm_h), 2, 2)
                    # Oval uç
                    p.setBrush(QBrush(QColor(195, 195, 195)))
                    p.drawEllipse(
                        QPointF(hdl_x + rw2 + arm_w, hdl_y), tip_r2, tip_r2 * 0.9)
                    # Rozet vida (orta)
                    p.setPen(QPen(QColor('#666666'), 0.6))
                    p.setBrush(QBrush(QColor(160, 160, 160)))
                    p.drawEllipse(QPointF(hdl_x + rw2/2, hdl_y), rw2*0.2, rw2*0.2)

                    # Hover vurgusu
                    if (self._select_mode or self._mullion_mode) and (ri, ci) == self._hovered_cell:
                        hover_clr = QColor(255, 220, 50, 60)
                        p.fillRect(cell_rect, hover_clr)
                        p.setPen(QPen(QColor(255, 180, 0, 200), 2.0))
                        p.drawRect(cell_rect)

        # ── Kanat profili iç ok ölçüleri ─────────────────────
        # Kanat varsa; kanat yatay (ALT/ÜST) ve dikey (SOL/SAĞ) boylarını
        # kanat profil şeridinin ORTASINDA ok+metin olarak göster.
        kanat_role = next(
            (r for r in ('kanat', 'kapi_kanat') if any(r2 == r for r2, _ in piece_map)),
            None)

        if kanat_role:
            # Kanat yatay uzunluğu (ALT veya ÜST)
            kn_w_mm = next(
                (pc['length_mm'] for (r, s), (_, pc) in piece_map.items()
                 if r == kanat_role and s in ('ALT', 'ÜST')), None)
            # Kanat dikey uzunluğu (SOL veya SAĞ)
            kn_h_mm = next(
                (pc['length_mm'] for (r, s), (_, pc) in piece_map.items()
                 if r == kanat_role and s in ('SOL', 'SAĞ')), None)

            # Font ve ölçüler — şerit genişliğine göre dinamik boyut
            kn_strip_px  = max(tn * scale, 14)   # kanat profil şerit kalınlığı (piksel)
            font_sz      = max(7, min(10, int(kn_strip_px * 0.38)))
            dim_fnt      = QFont('Arial', font_sz); dim_fnt.setBold(True)
            dim_fm       = QFontMetrics(dim_fnt)
            dim_clr      = QColor(20, 20, 20)
            dim_pen2     = QPen(dim_clr, 1.0)
            aw2          = max(4, int(kn_strip_px * 0.18))

            # Kanat dış/iç sınırları (piksel) — şerit orta çizgisi
            kn_x0_px   = ML + tk * scale                   # kanat sol dış
            kn_x1_px   = ML + (W - tk) * scale             # kanat sağ dış
            kn_y0_px   = MT + tk * scale                   # kanat üst dış
            kn_y1_px   = MT + (H - tk) * scale             # kanat alt dış
            kn_xi0_px  = ML + (tk + tn) * scale            # kanat sol iç (cam kenarı)
            kn_xi1_px  = ML + (W - tk - tn) * scale        # kanat sağ iç
            kn_yi0_px  = MT + (tk + tn) * scale            # kanat üst iç
            kn_yi1_px  = MT + (H - tk - tn) * scale        # kanat alt iç

            # Şerit orta noktaları
            _lbl_h          = dim_fm.height() + 8                           # etiket kutusu yüksekliği
            strip_mid_y_bot = kn_yi1_px - _lbl_h * 0.75                   # cam içi — alt kenara yakın
            strip_mid_x_sol = kn_xi0_px + _lbl_h * 0.75                   # cam içi — sol kenara yakın

            def _lbl_box(cx, cy, label):
                """Etiket kutusu: beyaz opak, koyu yazı."""
                tw2 = dim_fm.horizontalAdvance(label) + 8
                th2 = dim_fm.height() + 4
                p.setBrush(QBrush(QColor(255, 255, 255, 245)))
                p.setPen(QPen(QColor(80, 100, 160), 1.0))
                p.drawRoundedRect(QRectF(cx - tw2/2, cy - th2/2, tw2, th2), 3, 3)
                p.setFont(dim_fnt)
                p.setPen(dim_clr)
                p.drawText(QPointF(cx - tw2/2 + 4, cy + dim_fm.height()*0.38), label)

            if kn_w_mm is not None:
                # Yatay ok — ALT kanat şeridinin ortasında
                y_mid = strip_mid_y_bot
                cx    = (kn_x0_px + kn_x1_px) / 2
                # Ok çizgisi
                p.setPen(dim_pen2)
                p.drawLine(QPointF(kn_x0_px + aw2*1.5, y_mid),
                           QPointF(kn_x1_px - aw2*1.5, y_mid))
                # Sol ok ucu
                p.drawLine(QPointF(kn_x0_px + aw2*1.5, y_mid),
                           QPointF(kn_x0_px + aw2*1.5 + aw2, y_mid - aw2*0.5))
                p.drawLine(QPointF(kn_x0_px + aw2*1.5, y_mid),
                           QPointF(kn_x0_px + aw2*1.5 + aw2, y_mid + aw2*0.5))
                # Sağ ok ucu
                p.drawLine(QPointF(kn_x1_px - aw2*1.5, y_mid),
                           QPointF(kn_x1_px - aw2*1.5 - aw2, y_mid - aw2*0.5))
                p.drawLine(QPointF(kn_x1_px - aw2*1.5, y_mid),
                           QPointF(kn_x1_px - aw2*1.5 - aw2, y_mid + aw2*0.5))
                # Etiket kutusu ortada
                _lbl_box(cx, y_mid, f'Kn: {kn_w_mm} mm')

            if kn_h_mm is not None:
                # Dikey ok — SOL kanat şeridinin ortasında (döndürülmüş metin)
                x_mid = strip_mid_x_sol
                cy    = (kn_y0_px + kn_y1_px) / 2
                # Ok çizgisi
                p.setPen(dim_pen2)
                p.drawLine(QPointF(x_mid, kn_y0_px + aw2*1.5),
                           QPointF(x_mid, kn_y1_px - aw2*1.5))
                # Üst ok ucu
                p.drawLine(QPointF(x_mid, kn_y0_px + aw2*1.5),
                           QPointF(x_mid - aw2*0.5, kn_y0_px + aw2*1.5 + aw2))
                p.drawLine(QPointF(x_mid, kn_y0_px + aw2*1.5),
                           QPointF(x_mid + aw2*0.5, kn_y0_px + aw2*1.5 + aw2))
                # Alt ok ucu
                p.drawLine(QPointF(x_mid, kn_y1_px - aw2*1.5),
                           QPointF(x_mid - aw2*0.5, kn_y1_px - aw2*1.5 - aw2))
                p.drawLine(QPointF(x_mid, kn_y1_px - aw2*1.5),
                           QPointF(x_mid + aw2*0.5, kn_y1_px - aw2*1.5 - aw2))
                # Etiket kutusu — dikey döndürülmüş
                label   = f'Kn: {kn_h_mm} mm'
                tw2     = dim_fm.horizontalAdvance(label) + 8
                th2     = dim_fm.height() + 4
                p.save()
                p.translate(x_mid, cy)
                p.rotate(-90)
                p.setBrush(QBrush(QColor(255, 255, 255, 245)))
                p.setPen(QPen(QColor(80, 100, 160), 1.0))
                p.drawRoundedRect(QRectF(-tw2/2, -th2/2, tw2, th2), 3, 3)
                p.setFont(dim_fnt)
                p.setPen(dim_clr)
                p.drawText(QPointF(-tw2/2 + 4, dim_fm.height()*0.38), label)
                p.restore()

        # ── Cam + Menteşe + Kol ──────────────────────────────────
        has_sash  = any(r in ('kanat', 'kapi_kanat') for r, _ in piece_map)
        has_door  = any(r == 'kapi_kanat'             for r, _ in piece_map)

        if has_sash:
            # Cam alanı (piksel)
            g_x = ML + (tk + tn) * scale
            g_y = MT + (tk + tn) * scale
            g_w = (W - 2*(tk + tn)) * scale
            g_h = (H - 2*(tk + tn)) * scale

            if g_w > 4 and g_h > 4:
                # Cam dolgu — çok açık gri (neredeyse beyaz)
                p.setBrush(QBrush(QColor(245, 248, 252, 200)))
                p.setPen(QPen(QColor(160, 180, 200, 120), 0.6))
                p.drawRect(QRectF(g_x, g_y, g_w, g_h))

                # İç ölçü etiketi — kaldırıldı (kanat şeridinde gösteriliyor)

                # ── Menteşe (referans: ince yatay plaka) ─────────
                hinge_x_px  = ML + tk * scale
                margin_h_px = min((H - 2*(tk+tn)) * 0.18, 220) * scale
                hy_top_px   = g_y + margin_h_px
                hy_bot_px   = g_y + g_h - margin_h_px
                pw_px       = max(tn * scale, 8)
                pl_w_px     = pw_px * 0.55   # yatay plaka genişliği
                pl_h_px     = max(pw_px * 0.20, 5)  # ince plaka yüksekliği
                scr_r       = max(pw_px * 0.045, 2.0)
                h_pen       = QPen(QColor('#aaaaaa'), 0.8)

                for hy_px in (hy_top_px, hy_bot_px):
                    # Menteşe plakası (ince yatay dikdörtgen)
                    p.setBrush(QBrush(QColor(236, 236, 236)))
                    p.setPen(h_pen)
                    p.drawRoundedRect(
                        QRectF(hinge_x_px - pl_w_px*0.55,
                               hy_px - pl_h_px/2,
                               pl_w_px, pl_h_px), 2, 2)
                    # Parlama çizgisi (üst kenar)
                    p.setPen(QPen(QColor(255,255,255,100), 0.7))
                    p.drawLine(QPointF(hinge_x_px - pl_w_px*0.50, hy_px - pl_h_px/2 + 1.2),
                               QPointF(hinge_x_px + pl_w_px*0.40, hy_px - pl_h_px/2 + 1.2))
                    # Vida delikleri (sol + sağ)
                    p.setPen(QPen(QColor('#888888'), 0.7))
                    for dx in (-pl_w_px*0.28, pl_w_px*0.26):
                        p.setBrush(QBrush(QColor(180, 180, 180)))
                        p.drawEllipse(QPointF(hinge_x_px + dx, hy_px), scr_r, scr_r)
                        # Vida haç
                        p.drawLine(QPointF(hinge_x_px+dx-scr_r*0.65, hy_px),
                                   QPointF(hinge_x_px+dx+scr_r*0.65, hy_px))
                        p.drawLine(QPointF(hinge_x_px+dx, hy_px-scr_r*0.65),
                                   QPointF(hinge_x_px+dx, hy_px+scr_r*0.65))

                # ── Kol (referans: oval spade şekli) ─────────────
                hdl_x_px = ML + (W - tk - tn) * scale
                hdl_y_px = MT + (H / 2) * scale
                rw_px    = max(pw_px * 0.35, 5)
                rh_px    = max(pw_px * 0.85, 12)
                hdl_pen  = QPen(QColor('#bbbbbb'), 0.8)

                # Rozet
                p.setBrush(QBrush(QColor(232, 232, 232)))
                p.setPen(hdl_pen)
                p.drawRoundedRect(QRectF(hdl_x_px - rw_px/2,
                                         hdl_y_px - rh_px/2,
                                         rw_px, rh_px), 2, 2)

                if has_door:
                    # Kapı kolu: yatay yuvarlak bar
                    arm_px = max(pw_px * 1.1, 16)
                    kh_px  = max(pw_px * 0.28, 5)
                    p.setBrush(QBrush(QColor(224, 224, 224)))
                    p.drawRoundedRect(QRectF(hdl_x_px + rw_px/2,
                                             hdl_y_px - kh_px/2,
                                             arm_px, kh_px), 3, 3)
                else:
                    # Pencere kolu: kol + oval uç (referans resmi gibi)
                    kol_w = max(pw_px * 0.95, 14)
                    kol_h = max(pw_px * 0.25, 5)
                    tip_r = max(pw_px * 0.23, 4)
                    p.setBrush(QBrush(QColor(224, 224, 224)))
                    p.drawRoundedRect(QRectF(hdl_x_px + rw_px/2,
                                             hdl_y_px - kol_h/2,
                                             kol_w, kol_h), 2, 2)
                    # Oval uç
                    p.setBrush(QBrush(QColor(216, 216, 216)))
                    p.drawEllipse(QPointF(hdl_x_px + rw_px/2 + kol_w,
                                          hdl_y_px),
                                   tip_r, tip_r * 0.85)

        # ── Boyut okları ─────────────────────────────────────────
        dim_pen = QPen(QColor(self._TEXT_DIM))
        dim_pen.setWidth(1)
        p.setPen(dim_pen)
        p.setFont(QFont('Arial', 9))

        # W oku (alt)
        pt0 = mm2qpt(0, 0)
        ptW = mm2qpt(W, 0)
        arrow_y = pt0.y() + 22
        p.drawLine(QPointF(pt0.x(), arrow_y), QPointF(ptW.x(), arrow_y))
        # ok uçları
        aw = 6
        p.drawLine(QPointF(pt0.x(), arrow_y),
                   QPointF(pt0.x() + aw, arrow_y - aw//2))
        p.drawLine(QPointF(pt0.x(), arrow_y),
                   QPointF(pt0.x() + aw, arrow_y + aw//2))
        p.drawLine(QPointF(ptW.x(), arrow_y),
                   QPointF(ptW.x() - aw, arrow_y - aw//2))
        p.drawLine(QPointF(ptW.x(), arrow_y),
                   QPointF(ptW.x() - aw, arrow_y + aw//2))
        wlbl = f'W={int(W)} mm'
        wfm  = QFontMetrics(QFont('Arial', 9))
        p.setPen(QColor(self._TEXT_DIM))
        p.drawText(QPointF((pt0.x() + ptW.x()) / 2 - wfm.horizontalAdvance(wlbl) / 2,
                            arrow_y + 16), wlbl)

        # H oku (sağ)
        ptH   = mm2qpt(W, H)
        arrow_x = ptW.x() + 14
        p.setPen(dim_pen)
        p.drawLine(QPointF(arrow_x, ptH.y()), QPointF(arrow_x, pt0.y()))
        p.drawLine(QPointF(arrow_x, ptH.y()),
                   QPointF(arrow_x - aw//2, ptH.y() + aw))
        p.drawLine(QPointF(arrow_x, ptH.y()),
                   QPointF(arrow_x + aw//2, ptH.y() + aw))
        p.drawLine(QPointF(arrow_x, pt0.y()),
                   QPointF(arrow_x - aw//2, pt0.y() - aw))
        p.drawLine(QPointF(arrow_x, pt0.y()),
                   QPointF(arrow_x + aw//2, pt0.y() - aw))
        hlbl = f'H={int(H)} mm'
        mid_y = (ptH.y() + pt0.y()) / 2
        p.setPen(QColor(self._TEXT_DIM))
        p.save()
        p.translate(arrow_x + 14, mid_y)
        p.rotate(-90)
        hfm = QFontMetrics(QFont('Arial', 9))
        p.drawText(QPointF(-hfm.horizontalAdvance(hlbl) / 2, 0), hlbl)
        p.restore()

        # Başlık
        p.setPen(QColor('#888888'))
        p.setFont(QFont('Arial', 8))
        p.drawText(QPointF(ML, 14), 'Çerçeve Önizleme')

        p.end()


# ─────────────────────────────────────────────────────────────────

class _RobotDxfPickDialog(QDialog):
    """
    DXF kesit görünümünde tıklayarak robot Y/Z koordinatı seçme diyaloğu.
    Seçilen nokta (y_mm, z_mm) float olarak result_y, result_z'ye yazılır.
    """
    def __init__(self, stock_code: str, dxf_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'Robot Konumu Seç — {stock_code}')
        self.resize(600, 500)
        self.setStyleSheet(_STYLE)

        self.result_y: float = 40.0
        self.result_z: float = 40.0

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8); lay.setSpacing(6)

        info = QLabel(
            f'<b>{stock_code}</b> profili üzerinde robot yakalama noktasını tıklayın.<br>'
            '<small>Y ekseni = yatay (mm),  Z ekseni = dikey (mm).  '
            'Değer ×10 olarak kaydedilir (ör. 40 mm → 400).</small>')
        info.setWordWrap(True)
        lay.addWidget(info)

        # Koordinat göstergesi
        self._lbl_coord = QLabel('Tıklanan nokta: —')
        self._lbl_coord.setStyleSheet('color:#56cfe1; font-weight:bold;')
        lay.addWidget(self._lbl_coord)

        # ViewportWidget
        try:
            from ui.viewport_widget import ViewportWidget
            from dxf_loader import load_dxf
            self._vp = ViewportWidget()
            self._vp.setMinimumHeight(350)
            lay.addWidget(self._vp, 1)
            segs = load_dxf(dxf_path) if dxf_path else []
            self._vp.load_segments(segs)
            self._vp.set_pick_mode(True)
            self._vp.point_selected.connect(self._on_point_selected)
        except Exception as e:
            err = QLabel(f'DXF görüntüleyici yüklenemedi:\n{e}')
            err.setStyleSheet('color:#f55;')
            lay.addWidget(err)
            self._vp = None

        # Alt butonlar
        bar = QHBoxLayout()
        self._btn_ok = QPushButton('Seç ve Kapat')
        self._btn_ok.setEnabled(False)
        btn_cancel = QPushButton('İptal')
        bar.addStretch()
        bar.addWidget(btn_cancel)
        bar.addWidget(self._btn_ok)
        lay.addLayout(bar)

        self._btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

    def _on_point_selected(self, y: float, z: float):
        self.result_y = y
        self.result_z = z
        self._lbl_coord.setText(
            f'Tıklanan nokta:  Y = {y:.2f} mm  |  Z = {z:.2f} mm'
            f'  →  Y×10 = {int(round(y*10))}  |  Z×10 = {int(round(z*10))}')
        self._btn_ok.setEnabled(True)


# ─────────────────────────────────────────────────────────────────

class AkilliUretimDialog(QDialog):
    def __init__(self, parent=None, db=None, order_data: dict = None):
        super().__init__(parent)
        self.setWindowTitle('Akıllı Üretim')
        self.resize(1200, 750)
        self.setStyleSheet(_STYLE)

        self._db      = db
        self._mullions_v: list = []   # dikey orta kayıt x pozisyonları (mm, kasa iç kenarından)
        self._mullions_h: list = []   # yatay orta kayıt y pozisyonları (mm, kasa iç alt kenarından)
        self._undo_stack: list = []      # geri alma yığını
        self._saved_frames: list = []    # [{frame_idx, frame_indices, pieces, W, H, kasa_kerf, kanat_kerf, mullions_v, mullions_h, cell_assigns, kanat_ov_user, kanat_width, frame_type, recipe_key, stock, angle, weld_enabled, weld_mm, qty}]
        self._nav_frame_pos: int = -1   # şu an görüntülenen frame pozisyonu (saved_frames içinde)
        self._editing_frame_pos = None   # düzenleme modunda olan çizimin saved_frames içindeki pozisyonu
        self._order_id = order_data.get('order_id') if order_data else None   # bu oturumun bağlı olduğu kayıtlı sipariş id'si
        self._library = cg.load_library()
        self._pieces  = []   # Hesaplanan parçalar [{'role','side','stock_code','length','bar_no','generated_code'}]
        self._bar_counter = 1
        self._robot_positions = {}  # stock_code → {'y': int, 'z': int, 'vertical': int}
        self._frame_type = 'pencere'
        self._cell_assigns_data = {}

        self._build_ui()
        self._init_profile_selectors()

        if order_data:
            self.load_order_data(order_data)

        # Ctrl+Z — geri al kısayolu
        from PySide6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence('Ctrl+Z'), self).activated.connect(self._undo_last)

    # ─────────────────────────────────────────────────────────
    # UI kurulum
    # ─────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── Başlık ───────────────────────────────────────
        title = QLabel('⚡ ProfiDO — Akıllı Üretim')
        title.setObjectName('lbl_head')
        root.addWidget(title)

        # ── Üst çubuk: yapışkan profil seçimleri ────────
        root.addWidget(self._build_selector_bar())

        # ── Ana içerik (splitter) ────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Sol: çerçeve tanımı + parça listesi
        left = QWidget()
        llay = QVBoxLayout(left)
        llay.setContentsMargins(0, 0, 4, 0)
        llay.setSpacing(6)
        llay.addWidget(self._build_frame_input())
        llay.addWidget(self._build_piece_table(), 1)
        splitter.addWidget(left)

        # Sağ: önizleme (sol) + kodlar (sağ dar şerit) — yatay splitter
        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(4, 0, 0, 0)
        rlay.setSpacing(0)

        right_split = QSplitter(Qt.Horizontal)
        right_split.setChildrenCollapsible(False)

        # Sol: çerçeve görsel önizlemesi + navigasyon
        preview_container = QWidget()
        prev_lay = QVBoxLayout(preview_container)
        prev_lay.setContentsMargins(0, 0, 0, 0); prev_lay.setSpacing(2)

        # Navigasyon çubuğu (üstte)
        nav_row = QHBoxLayout(); nav_row.setSpacing(4)
        self._btn_prev_frame = QPushButton('◀')
        self._btn_prev_frame.setFixedSize(28, 24)
        self._btn_prev_frame.setToolTip('Önceki çerçeve')
        self._btn_prev_frame.clicked.connect(self._show_prev_frame)
        self._btn_prev_frame.setEnabled(False)
        nav_row.addWidget(self._btn_prev_frame)
        self._lbl_frame_nav = QLabel('')
        self._lbl_frame_nav.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_frame_nav.setStyleSheet('color:#888888; font-size:11px;')
        nav_row.addWidget(self._lbl_frame_nav, 1)
        self._btn_next_frame = QPushButton('▶')
        self._btn_next_frame.setFixedSize(28, 24)
        self._btn_next_frame.setToolTip('Sonraki çerçeve')
        self._btn_next_frame.clicked.connect(self._show_next_frame)
        self._btn_next_frame.setEnabled(False)
        nav_row.addWidget(self._btn_next_frame)
        self._btn_edit_frame = QPushButton('✏️')
        self._btn_edit_frame.setFixedSize(28, 24)
        self._btn_edit_frame.setToolTip('Görüntülenen çizimi düzenle')
        self._btn_edit_frame.clicked.connect(lambda: self._edit_frame())
        self._btn_edit_frame.setEnabled(False)
        nav_row.addWidget(self._btn_edit_frame)
        self._btn_delete_frame = QPushButton('🗑')
        self._btn_delete_frame.setFixedSize(28, 24)
        self._btn_delete_frame.setToolTip('Görüntülenen çizimi sil')
        self._btn_delete_frame.clicked.connect(lambda: self._delete_frame())
        self._btn_delete_frame.setEnabled(False)
        nav_row.addWidget(self._btn_delete_frame)
        nav_cont = QWidget(); nav_cont.setLayout(nav_row)
        prev_lay.addWidget(nav_cont)

        self._preview = FramePreviewWidget()
        self._preview.setMinimumWidth(280)
        prev_lay.addWidget(self._preview, 1)
        preview_container.setMinimumWidth(280)
        right_split.addWidget(preview_container)

        # Sağ: P-kod metin görünümü (dar şerit)
        code_pane = QWidget()
        clay = QVBoxLayout(code_pane)
        clay.setContentsMargins(4, 0, 0, 0)
        clay.setSpacing(2)
        lbl_code = QLabel('📋 Üretilen P-Kodları')
        lbl_code.setObjectName('lbl_head')
        clay.addWidget(lbl_code)
        self._code_view = QTextEdit()
        self._code_view.setReadOnly(True)
        self._code_view.setPlaceholderText(
            'Çerçeve hesapla →\nKodları Üret butonuna bas')
        self._code_view.setMinimumWidth(160)
        clay.addWidget(self._code_view, 1)
        right_split.addWidget(code_pane)

        right_split.setSizes([420, 200])
        rlay.addWidget(right_split, 1)

        splitter.addWidget(right)
        splitter.setSizes([560, 620])
        root.addWidget(splitter, 1)

        # ── Alt butonlar ─────────────────────────────────
        root.addWidget(self._build_action_bar())

    # ── Profil seçici çubuğu ─────────────────────────────

    def _build_selector_bar(self) -> QWidget:
        grp = QGroupBox('Aktif Profiller  (değiştirene kadar seçim sabit kalır)')
        lay = QHBoxLayout(grp)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(16)

        self._prof_selectors = {}   # role → QComboBox

        role_defs = [
            ('kasa',      '🔲 Kasa',      'A'),
            ('kanat',     '🟨 Kanat',     'B'),
            ('kapi_kanat','🚪 Kapı Kanat','J'),
            ('orta_kayit', '➕ Orta Kayıt', 'E'),
        ]
        for role, label, ptype in role_defs:
            col = QVBoxLayout()
            col.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet('color:#56cfe1; font-weight:bold;')
            col.addWidget(lbl)
            cb = QComboBox()
            cb.setMinimumWidth(200)
            cb.currentIndexChanged.connect(lambda _idx, r=role: self._on_profile_changed(r))
            self._prof_selectors[role] = cb
            col.addWidget(cb)
            lay.addLayout(col)

        lay.addStretch()
        btn_reload = QPushButton('🔄 Kütüphaneyi Yenile')
        btn_reload.clicked.connect(self._reload_library)
        lay.addWidget(btn_reload)
        return grp

    # ── Çerçeve giriş paneli ──────────────────────────────

    def _build_frame_input(self) -> QWidget:
        grp = QGroupBox('Çerçeve Tanımı')
        lay = QGridLayout(grp)
        lay.setContentsMargins(10, 10, 10, 8)
        lay.setSpacing(8)

        # Gizli recipe combobox (mantık için)
        self._cb_recipe = QComboBox()
        for key, label in RECIPE_LABELS.items():
            self._cb_recipe.addItem(label, key)
        self._cb_recipe.setVisible(False)

        # ── ROW 0: Müşteri Adı | Müşteri Kodu ────────────────────────
        _cfg = st.load_settings()
        lay.addWidget(QLabel('Müşteri Adı:'), 0, 0)
        self._ed_customer_name = QLineEdit()
        self._ed_customer_name.setPlaceholderText('Müşteri adı')
        self._ed_customer_name.setText(_cfg.get('default_customer_name', ''))
        lay.addWidget(self._ed_customer_name, 0, 1)
        lay.addWidget(QLabel('Müşteri Kodu:'), 0, 2)
        self._ed_customer_code = QLineEdit()
        self._ed_customer_code.setPlaceholderText('Kod')
        self._ed_customer_code.setText(_cfg.get('default_customer_code', ''))
        lay.addWidget(self._ed_customer_code, 0, 3)

        # ── ROW 1: Sipariş No | Kesim Açısı ─────────────────────────
        lay.addWidget(QLabel('Sipariş No:'), 1, 0)
        self._ed_order_no = QLineEdit()
        self._ed_order_no.setPlaceholderText('Sipariş No')
        self._ed_order_no.setText(st.current_order_no())
        lay.addWidget(self._ed_order_no, 1, 1)
        lay.addWidget(QLabel('Kesim Açısı:'), 1, 2)
        self._sp_angle = QSpinBox()
        self._sp_angle.setRange(0, 90); self._sp_angle.setValue(45); self._sp_angle.setSuffix('°')
        lay.addWidget(self._sp_angle, 1, 3)

        # ── ROW 2: Kaynak Payı + Bar/Program No (sabit) ──────────────
        fixed_row = QHBoxLayout(); fixed_row.setSpacing(10)
        self._chk_weld = QCheckBox('Kaynak Payı Var')
        self._chk_weld.setStyleSheet('color:#f8c12f; font-size:11px;')
        fixed_row.addWidget(self._chk_weld)
        self._sp_weld_mm = QSpinBox()
        self._sp_weld_mm.setRange(0, 50); self._sp_weld_mm.setValue(6); self._sp_weld_mm.setSuffix(' mm')
        self._sp_weld_mm.setFixedWidth(74); self._sp_weld_mm.setStyleSheet('color:#f8c12f;')
        fixed_row.addWidget(self._sp_weld_mm)
        fixed_row.addSpacing(16)
        fixed_row.addWidget(QLabel('Bar Boyu:'))
        self._sp_bar_len = QSpinBox()
        self._sp_bar_len.setRange(1000, 99999); self._sp_bar_len.setValue(6000); self._sp_bar_len.setSuffix(' mm')
        self._sp_bar_len.setFixedWidth(100)
        fixed_row.addWidget(self._sp_bar_len)
        fixed_row.addWidget(QLabel('Bar No:'))
        self._sp_bar_start = QSpinBox()
        self._sp_bar_start.setRange(1, 9999); self._sp_bar_start.setValue(1); self._sp_bar_start.setFixedWidth(60)
        fixed_row.addWidget(self._sp_bar_start)
        fixed_row.addWidget(QLabel('Prog No:'))
        self._sp_prog_start = QSpinBox()
        self._sp_prog_start.setRange(1, 99999); self._sp_prog_start.setValue(1); self._sp_prog_start.setFixedWidth(70)
        if self._db and getattr(self._db, 'connected', False):
            try:
                self._sp_prog_start.setValue(self._db.get_next_program_no())
            except Exception:
                pass
        fixed_row.addWidget(self._sp_prog_start)
        fixed_row.addStretch()
        fixed_cont = QWidget(); fixed_cont.setLayout(fixed_row)
        lay.addWidget(fixed_cont, 2, 0, 1, 4)

        # ── ROW 3: "Yeni Çerçeve" butonu (başlangıçta tek görünen) ──
        btn_new_frame = QPushButton('🏗  Yeni Çerçeve')
        btn_new_frame.setObjectName('btn_calc')
        btn_new_frame.setFixedHeight(36)
        btn_new_frame.clicked.connect(self._open_new_frame_dialog)
        lay.addWidget(btn_new_frame, 3, 0, 1, 4)

        # ── ROW 4: Ölçü girişi — sadece "Yeni Çerçeve" sonrası görünür ──
        self._frame_dim_widget = QWidget()
        dim_lay = QGridLayout(self._frame_dim_widget)
        dim_lay.setContentsMargins(0, 4, 0, 0); dim_lay.setSpacing(8)
        dim_lay.addWidget(QLabel('Genişlik (W):'), 0, 0)
        self._sp_w = QSpinBox()
        self._sp_w.setRange(100, 9999); self._sp_w.setValue(700); self._sp_w.setSuffix(' mm')
        dim_lay.addWidget(self._sp_w, 0, 1)
        dim_lay.addWidget(QLabel('Yükseklik (H):'), 0, 2)
        self._sp_h = QSpinBox()
        self._sp_h.setRange(100, 9999); self._sp_h.setValue(900); self._sp_h.setSuffix(' mm')
        dim_lay.addWidget(self._sp_h, 0, 3)
        # W/H değişince önizlemeyi güncelle
        def _auto_preview():
            if getattr(self._preview, '_kasa_only', False) or self._preview._kerf_kasa > 0:
                self._init_frame_preview(getattr(self, '_frame_type', 'pencere'))
        self._sp_w.valueChanged.connect(lambda _: _auto_preview())
        self._sp_h.valueChanged.connect(lambda _: _auto_preview())
        self._frame_dim_widget.setVisible(False)
        lay.addWidget(self._frame_dim_widget, 4, 0, 1, 4)

        # ── ROW 5: Akış butonları — ölçü sonrası görünür ─────────────
        self._frame_action_widget = QWidget()
        act_lay = QVBoxLayout(self._frame_action_widget)
        act_lay.setContentsMargins(0, 4, 0, 0); act_lay.setSpacing(4)

        # ── Satır 1: Kanat Ekle | Kapı Ekle | + Dikey OK | + Yatay OK ──
        row1 = QHBoxLayout(); row1.setSpacing(6)

        btn_add_kanat = QPushButton('🪟  Kanat Ekle')
        btn_add_kanat.setFixedHeight(34)
        btn_add_kanat.setStyleSheet('QPushButton{background:#1a4a2a;color:white;}QPushButton:hover{background:#2a6a3a;}')
        btn_add_kanat.clicked.connect(lambda: self._add_sash_to_frame('kanat'))
        row1.addWidget(btn_add_kanat)

        btn_add_kapi = QPushButton('🚪  Kapı Ekle')
        btn_add_kapi.setFixedHeight(34)
        btn_add_kapi.setStyleSheet('QPushButton{background:#2a2a4a;color:white;}QPushButton:hover{background:#3a3a6a;}')
        btn_add_kapi.clicked.connect(lambda: self._add_sash_to_frame('kapi_kanat'))
        row1.addWidget(btn_add_kapi)

        btn_add_v = QPushButton('+ Dikey OK')
        btn_add_v.setFixedHeight(34)
        btn_add_v.clicked.connect(self._add_mullion_v)
        row1.addWidget(btn_add_v)

        btn_add_h = QPushButton('+ Yatay OK')
        btn_add_h.setFixedHeight(34)
        btn_add_h.clicked.connect(self._add_mullion_h)
        row1.addWidget(btn_add_h)

        row1_cont = QWidget(); row1_cont.setLayout(row1)
        act_lay.addWidget(row1_cont)

        # ── Satır 2: Çerçeveyi Tamamla (tam genişlik) ────────────────
        btn_done = QPushButton('✅  Çerçeveyi Tamamla')
        btn_done.setObjectName('btn_add_frame')
        btn_done.setFixedHeight(38)
        btn_done.clicked.connect(self._finish_frame)
        act_lay.addWidget(btn_done)
        self._btn_finish_frame = btn_done

        # ── Orta kayıt durum + yardımcı butonlar (küçük satır) ───────
        aux_row = QHBoxLayout(); aux_row.setSpacing(4)
        lbl_ok = QLabel('Orta Kayıt:')
        lbl_ok.setStyleSheet('color:#aaaaaa; font-size:10px;')
        aux_row.addWidget(lbl_ok)
        self._lbl_mullions = QLabel('Yok')
        self._lbl_mullions.setStyleSheet('color:#f8c12f; font-size:10px; font-weight:bold;')
        aux_row.addWidget(self._lbl_mullions)
        aux_row.addStretch()
        btn_undo = QPushButton('↩ Geri Al')
        btn_undo.setFixedHeight(24)
        btn_undo.setToolTip('Son işlemi geri al  (Ctrl+Z)')
        btn_undo.setStyleSheet(
            'QPushButton{background:#2a3a5a;color:#aaccff;font-size:10px;border:1px solid #4466aa;border-radius:3px;}'
            'QPushButton:hover{background:#3a4a7a;}')
        btn_undo.clicked.connect(self._undo_last)
        aux_row.addWidget(btn_undo)
        btn_clr_ok = QPushButton('✕ OK Temizle')
        btn_clr_ok.setFixedHeight(24)
        btn_clr_ok.setStyleSheet('QPushButton{background:#5a1a1a;color:#ffaaaa;font-size:10px;}QPushButton:hover{background:#7a2a2a;}')
        btn_clr_ok.clicked.connect(self._clear_mullions)
        aux_row.addWidget(btn_clr_ok)
        aux_cont = QWidget(); aux_cont.setLayout(aux_row)
        act_lay.addWidget(aux_cont)

        self._frame_action_widget.setVisible(False)
        lay.addWidget(self._frame_action_widget, 5, 0, 1, 4)

        return grp

    # ── Parça listesi tablosu ─────────────────────────────

    def _build_piece_table(self) -> QWidget:
        grp = QGroupBox('Parça Listesi  (uzunluklara çift tıkla → düzenle)')
        lay = QVBoxLayout(grp)
        lay.setContentsMargins(4, 8, 4, 4)

        self._tbl = QTableWidget()
        self._tbl.setColumnCount(8)
        self._tbl.setHorizontalHeaderLabels(
            ['Prog No', 'Poz No', 'Bar', 'Rol', 'Kenar', 'Stok Kodu', 'Uzunluk (mm)', 'Kod Var?'])
        hdr = self._tbl.horizontalHeader()
        # Sütun sırası: Prog No | Poz No | Bar | Rol | Kenar | Stok Kodu | Uzunluk | Kod Var?
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Prog No
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Poz No
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Bar
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Rol
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Kenar
        hdr.setSectionResizeMode(5, QHeaderView.Stretch)           # Stok Kodu
        hdr.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Uzunluk
        hdr.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Kod Var?
        self._tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setStyleSheet('alternate-background-color:#1a1a2a;')
        self._tbl.itemDoubleClicked.connect(self._on_cell_dclick)
        self._tbl.selectionModel().currentRowChanged.connect(
            lambda cur, _prev: self._on_row_changed(cur.row()))
        lay.addWidget(self._tbl)
        return grp

    # ── Robot yakalama konumları ──────────────────────────

    def _build_robot_section(self) -> QWidget:
        grp = QGroupBox('🤖 Robot Yakalama Konumları  (çerçeve hesaplanınca stok kodları görünür)')
        lay = QVBoxLayout(grp)
        lay.setContentsMargins(4, 8, 4, 4)

        self._tbl_robot = QTableWidget()
        self._tbl_robot.setColumnCount(5)
        self._tbl_robot.setHorizontalHeaderLabels(
            ['Stok Kodu', 'Robot Y (×10)', 'Robot Z (×10)', 'Pozisyon', 'DXF Seç'])
        hdr = self._tbl_robot.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._tbl_robot.setMaximumHeight(130)
        self._tbl_robot.setMinimumHeight(56)
        self._tbl_robot.setAlternatingRowColors(True)
        self._tbl_robot.setStyleSheet('alternate-background-color:#1a1a2a;')
        lay.addWidget(self._tbl_robot)

        hint = QLabel('Y/Z: mm × 10  (ör. 40 mm → 400).  Değerler bir sonraki hesaplamada da korunur.')
        hint.setObjectName('lbl_sub')
        lay.addWidget(hint)
        return grp

    def _refresh_robot_table(self):
        """Parça listesindeki benzersiz stok kodları için robot tablosunu günceller."""
        # Mevcut tablo değerlerini kaydet
        for r in range(self._tbl_robot.rowCount()):
            itm = self._tbl_robot.item(r, 0)
            if not itm:
                continue
            sc   = itm.text()
            sp_y = self._tbl_robot.cellWidget(r, 1)
            sp_z = self._tbl_robot.cellWidget(r, 2)
            cb_v = self._tbl_robot.cellWidget(r, 3)
            self._robot_positions[sc] = {
                'y': sp_y.value() if sp_y else 400,
                'z': sp_z.value() if sp_z else 400,
                'vertical': cb_v.currentData() if cb_v else 0,
            }
        # Benzersiz stok kodları (eklenme sırasıyla)
        seen = []; seen_set = set()
        for p in self._pieces:
            sc = p['stock_code']
            if sc not in seen_set:
                seen.append(sc); seen_set.add(sc)

        _sp_style = 'background:#2e2e42;color:#ddd;border:1px solid #555;'
        self._tbl_robot.blockSignals(True)
        self._tbl_robot.setRowCount(0)
        for sc in seen:
            r = self._tbl_robot.rowCount()
            self._tbl_robot.insertRow(r)
            self._tbl_robot.setRowHeight(r, 28)
            itm = QTableWidgetItem(sc)
            itm.setFlags(itm.flags() & ~Qt.ItemIsEditable)
            self._tbl_robot.setItem(r, 0, itm)
            saved = self._robot_positions.get(sc, {})
            sp_y = QSpinBox(); sp_y.setRange(-99999, 99999); sp_y.setValue(saved.get('y', 400))
            sp_y.setStyleSheet(_sp_style)
            self._tbl_robot.setCellWidget(r, 1, sp_y)
            sp_z = QSpinBox(); sp_z.setRange(-99999, 99999); sp_z.setValue(saved.get('z', 400))
            sp_z.setStyleSheet(_sp_style)
            self._tbl_robot.setCellWidget(r, 2, sp_z)
            cb_v = QComboBox()
            cb_v.addItem('Yatay (0)', 0); cb_v.addItem('Dikey (1)', 1)
            if saved.get('vertical', 0) == 1:
                cb_v.setCurrentIndex(1)
            self._tbl_robot.setCellWidget(r, 3, cb_v)
            # DXF seçim butonu
            btn_dxf = QPushButton('📍 DXF')
            btn_dxf.setFixedWidth(70)
            btn_dxf.setToolTip(f'{sc} profilinin DXF kesitinde robot noktasını tıkla')
            btn_dxf.clicked.connect(lambda _checked=False, _sc=sc, _spy=sp_y, _spz=sp_z:
                                    self._pick_robot_from_dxf(_sc, _spy, _spz))
            self._tbl_robot.setCellWidget(r, 4, btn_dxf)
        self._tbl_robot.blockSignals(False)

    def _get_robot_for_stock(self, stock_code: str) -> dict:
        """
        Robot Y/Z/Vertical değerlerini döner.
        Öncelik sırası:
          1. Profil kütüphanesinde kayıtlı robot_y / robot_z / robot_vertical
          2. Akıllı Üretim robot tablosundaki anlık değerler
          3. Varsayılan (400, 400, 0)
        """
        # 1. Profil kütüphanesi
        prof = cg.get_profile(self._library, stock_code) or {}
        if 'robot_y' in prof or 'robot_z' in prof:
            return {
                'y':        int(prof.get('robot_y',        400)),
                'z':        int(prof.get('robot_z',        400)),
                'vertical': int(prof.get('robot_vertical', 0)),
            }
        # 2. Robot tablosu
        for r in range(self._tbl_robot.rowCount()):
            itm = self._tbl_robot.item(r, 0)
            if itm and itm.text() == stock_code:
                sp_y = self._tbl_robot.cellWidget(r, 1)
                sp_z = self._tbl_robot.cellWidget(r, 2)
                cb_v = self._tbl_robot.cellWidget(r, 3)
                return {
                    'y': sp_y.value() if sp_y else 400,
                    'z': sp_z.value() if sp_z else 400,
                    'vertical': cb_v.currentData() if cb_v else 0,
                }
        return self._robot_positions.get(stock_code, {'y': 400, 'z': 400, 'vertical': 0})

    def _pick_robot_from_dxf(self, stock_code: str, sp_y: QSpinBox, sp_z: QSpinBox):
        """DXF tıklama diyaloğunu açar ve seçilen noktayı Y/Z spinbox'lara yazar."""
        prof = cg.get_profile(self._library, stock_code) or {}
        dxf_path = prof.get('dxf_file', '').strip()
        if not dxf_path:
            QMessageBox.information(
                self, 'DXF Yok',
                f'"{stock_code}" profiline tanımlı DXF dosyası yok.\n'
                'Profil Kütüphanesi\'nden DXF ekleyin.')
            return
        dlg = _RobotDxfPickDialog(stock_code, dxf_path, self)
        if dlg.exec() == QDialog.Accepted:
            sp_y.setValue(int(round(dlg.result_y * 10)))
            sp_z.setValue(int(round(dlg.result_z * 10)))

    # ── Alt aksiyon çubuğu ────────────────────────────────

    def _build_action_bar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet('background:#151525; border-top:1px solid #333;')
        bar.setFixedHeight(50)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(10)

        self._lbl_status = QLabel('Çerçeve hesapla ve kodları üret.')
        self._lbl_status.setObjectName('lbl_sub')
        lay.addWidget(self._lbl_status, 1)

        # X=0 test modu
        self._chk_x0 = QCheckBox('X=0 Test Modu')
        self._chk_x0.setToolTip(
            'İşaretlenince tüm X değerleri 0 olarak üretilir.\n'
            'Gerçek X formülleri hazır olduğunda işareti kaldırın.')
        self._chk_x0.setStyleSheet('color:#f8c12f; font-size:11px;')
        lay.addWidget(self._chk_x0)

        btn_gen = QPushButton('⚡  Kodları Üret')
        btn_gen.setObjectName('btn_gen')
        btn_gen.setFixedHeight(36)
        btn_gen.clicked.connect(self._generate_codes)
        lay.addWidget(btn_gen)

        btn_save = QPushButton('🚀  Kaydet ve Makineye Gönder')
        btn_save.setObjectName('btn_save')
        btn_save.setFixedHeight(36)
        btn_save.clicked.connect(self._send_to_machine)
        lay.addWidget(btn_save)

        btn_save_order = QPushButton('💾  Siparişi Kaydet')
        btn_save_order.setFixedHeight(36)
        btn_save_order.setToolTip(
            'Tüm çizimleri tek bir sipariş olarak diske kaydeder.\n'
            'Daha sonra "📁 Siparişler" listesinden tekrar açıp düzenleyebilirsiniz.')
        btn_save_order.setStyleSheet(
            'QPushButton{background:#1a3a4a;color:#9fd8ff;border:1px solid #2a5a7a;'
            'border-radius:4px;padding:4px 10px;font-size:12px;}'
            'QPushButton:hover{background:#2a5a7a;}')
        btn_save_order.clicked.connect(lambda: self._save_order(silent=False))
        lay.addWidget(btn_save_order)

        btn_clear_list = QPushButton('🗑  Listeyi Temizle')
        btn_clear_list.setFixedHeight(36)
        btn_clear_list.setStyleSheet(
            'QPushButton{background:#5a1a1a;color:#ffaaaa;border:1px solid #7a2a2a;'
            'border-radius:4px;padding:4px 10px;font-size:12px;}'
            'QPushButton:hover{background:#7a2a2a;}')
        btn_clear_list.setToolTip('Tüm parça listesini temizler (MDB\'ye kaydetmeden)')
        btn_clear_list.clicked.connect(self._clear_pieces)
        lay.addWidget(btn_clear_list)

        btn_close = QPushButton('Kapat')
        btn_close.setFixedHeight(36)
        btn_close.clicked.connect(self.close)
        lay.addWidget(btn_close)

        return bar

    # ─────────────────────────────────────────────────────────
    # Profil seçici başlatma
    # ─────────────────────────────────────────────────────────

    def _init_profile_selectors(self):
        """Her rol için kütüphanedeki profilleri combo'ya doldur, last_used seç."""
        role_type_map = {'kasa': 'A', 'kanat': 'B', 'kapi_kanat': 'J', 'orta_kayit': 'E'}
        for role, ptype in role_type_map.items():
            cb = self._prof_selectors[role]
            cb.blockSignals(True)
            cb.clear()
            profiles = cg.get_profiles_by_type(self._library, ptype)
            last = cg.get_last_used(self._library, ptype)
            sel_idx = 0
            for i, p in enumerate(profiles):
                cb.addItem(f'{p["name"]}  [{p["stock_code"]}]', p['stock_code'])
                if p['stock_code'] == last:
                    sel_idx = i
            if profiles:
                cb.setCurrentIndex(sel_idx)
            cb.blockSignals(False)

    def _reload_library(self):
        self._library = cg.load_library()
        self._init_profile_selectors()
        self._lbl_status.setText('Kütüphane yenilendi.')

    def _on_profile_changed(self, role: str):
        cb = self._prof_selectors[role]
        stock_code = cb.currentData()
        if not stock_code:
            return
        ptype = ROLE_TYPE.get(role, '')
        cg.set_last_used(self._library, ptype, stock_code)
        cg.save_library(self._library)

    # ─────────────────────────────────────────────────────────
    # Çerçeve hesaplama
    # ─────────────────────────────────────────────────────────

    def _get_kasa_top_width(self) -> float:
        """Kasa profilinin üst yüzey genişliğini döndürür (mm)."""
        sc = self._prof_selectors.get('kasa')
        if sc:
            sc = sc.currentData()
        prof = cg.get_profile(self._library, sc) if sc else {}
        return float(prof.get('top_width_mm') or prof.get('width_mm') or 37)

    def _get_mullion_top_width(self) -> float:
        """Orta kayıt profilinin üst yüzey genişliğini döndürür (mm)."""
        sc = self._prof_selectors.get('orta_kayit')
        if sc:
            sc = sc.currentData()
        prof = cg.get_profile(self._library, sc) if sc else {}
        return float(prof.get('top_width_mm') or prof.get('width_mm') or 30)

    def _update_mullion_label(self):
        v = len(self._mullions_v)
        h = len(self._mullions_h)
        parts = []
        if v: parts.append(f'{v} Dikey')
        if h: parts.append(f'{h} Yatay')
        text = ', '.join(parts) if parts else 'Yok'
        self._lbl_mullions.setText(text)
        # Tıklanabilir yap — varsa edit popup açar
        if v or h:
            self._lbl_mullions.setStyleSheet(
                'color:#f8c12f; font-size:11px; font-weight:bold; text-decoration:underline; cursor:pointer;')
            try:
                self._lbl_mullions.mousePressEvent = lambda e: self._edit_mullions_popup()
            except Exception:
                pass
        else:
            self._lbl_mullions.setStyleSheet('color:#f8c12f; font-size:11px; font-weight:bold;')

    def _edit_mullions_popup(self):
        """Mevcut orta kayıtları listeler, düzenleme/silme sağlar."""
        W = self._sp_w.value(); H = self._sp_h.value()
        kw = self._get_kasa_top_width()
        inner_w = W - 2*kw; inner_h = H - 2*kw

        dlg = QDialog(self)
        dlg.setWindowTitle('Orta Kayıtları Düzenle')
        dlg.setMinimumWidth(320)
        lay = QVBoxLayout(dlg)

        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        lst = QListWidget()

        def _refresh_list():
            lst.clear()
            for i, mv in enumerate(self._mullions_v):
                if isinstance(mv, dict):
                    pos = mv['pos']
                    rows_c = mv.get('rows')
                    row_str = f' (Satır {[r+1 for r in rows_c]})' if rows_c else ' (Tüm yükseklik)'
                else:
                    pos = mv; row_str = ''
                lst.addItem(f'Dikey #{i+1}  →  {pos} mm{row_str}')
            for i, mh in enumerate(self._mullions_h):
                if isinstance(mh, dict):
                    pos = mh['pos']
                    cols_c = mh.get('cols')
                    col_str = f' (Sütun {[c+1 for c in cols_c]})' if cols_c else ' (Tüm genişlik)'
                else:
                    pos = mh; col_str = ''
                lst.addItem(f'Yatay #{i+1}  →  {pos} mm{col_str}')

        _refresh_list()
        lay.addWidget(lst)

        btn_row = QHBoxLayout()
        btn_edit = QPushButton('✏️  Düzenle')
        btn_del  = QPushButton('🗑  Sil')
        btn_del.setStyleSheet('QPushButton{background:#5a1a1a;color:#ffaaaa;}')
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_del)
        lay.addLayout(btn_row)
        lay.addWidget(QDialogButtonBox(QDialogButtonBox.Close, accepted=dlg.accept, rejected=dlg.reject))

        _EPS_EDIT = 0.75

        def _v_edit_range(idx):
            """idx'teki dikey kayıt yokmuş GİBİ hesaplanan hücre haritasında,
            bu kaydın (y_scope'u eşleşen) ait olduğu hücrenin x aralığını
            döndürür. Yeniden konumlandırma SADECE bu aralıkta yapılabilir —
            komşu (örn. kanat atanmış) hücreleri bozmaz."""
            mv_item = self._mullions_v[idx]
            y_scope = mv_item.get('y_scope') if isinstance(mv_item, dict) else None
            old_pos = mv_item['pos'] if isinstance(mv_item, dict) else mv_item
            others_v = [m for i, m in enumerate(self._mullions_v) if i != idx]
            merged = self._cell_bounds_map(others_v, self._mullions_h, inner_w, inner_h)
            for (x0, x1, y0, y1) in merged.values():
                y_ok = (y_scope is None and y0 <= _EPS_EDIT and y1 >= inner_h - _EPS_EDIT) \
                    or (y_scope is not None and abs(y0 - y_scope[0]) <= _EPS_EDIT
                        and abs(y1 - y_scope[1]) <= _EPS_EDIT)
                if y_ok and x0 - _EPS_EDIT <= old_pos <= x1 + _EPS_EDIT:
                    return x0, x1
            return 0.0, inner_w   # güvenli varsayılan

        def _h_edit_range(hi):
            """Yatay kayıt için simetrik: bu kaydın ait olduğu hücrenin y aralığı."""
            mh_item = self._mullions_h[hi]
            x_scope = mh_item.get('x_scope') if isinstance(mh_item, dict) else None
            old_pos = mh_item['pos'] if isinstance(mh_item, dict) else mh_item
            others_h = [m for i, m in enumerate(self._mullions_h) if i != hi]
            merged = self._cell_bounds_map(self._mullions_v, others_h, inner_w, inner_h)
            for (x0, x1, y0, y1) in merged.values():
                x_ok = (x_scope is None and x0 <= _EPS_EDIT and x1 >= inner_w - _EPS_EDIT) \
                    or (x_scope is not None and abs(x0 - x_scope[0]) <= _EPS_EDIT
                        and abs(x1 - x_scope[1]) <= _EPS_EDIT)
                if x_ok and y0 - _EPS_EDIT <= old_pos <= y1 + _EPS_EDIT:
                    return y0, y1
            return 0.0, inner_h   # güvenli varsayılan

        def _edit():
            idx = lst.currentRow()
            if idx < 0: return
            nv = len(self._mullions_v)
            if idx < nv:
                # Dikey
                mv_item = self._mullions_v[idx]
                old_pos = mv_item['pos'] if isinstance(mv_item, dict) else mv_item
                r0, r1 = _v_edit_range(idx)
                lo2 = max(1, int(round(r0)) + 1); hi2 = max(lo2, int(round(r1)) - 1)
                sp2 = QSpinBox(); sp2.setRange(lo2, hi2)
                sp2.setValue(min(max(int(old_pos), lo2), hi2)); sp2.setSuffix(' mm')
                d2 = QDialog(dlg); d2.setWindowTitle(f'Dikey #{idx+1} Konumu')
                l2 = QVBoxLayout(d2)
                if r1 - r0 < inner_w - 1:
                    l2.addWidget(QLabel(f'(Bu kayıt yalnızca {r0:.0f}–{r1:.0f} mm aralığında taşınabilir)'))
                l2.addWidget(sp2)
                def _lu2(v):
                    tmp = list(self._mullions_v)
                    if isinstance(tmp[idx], dict):
                        tmp[idx] = dict(tmp[idx]); tmp[idx]['pos'] = v
                    else:
                        tmp[idx] = v
                    tmp.sort(key=lambda m: m['pos'] if isinstance(m, dict) else m)
                    self._preview.set_mullions(tmp, self._mullions_h)
                    self._preview_live_cell_assigns(tmp, self._mullions_h)
                    self._preview.update()
                sp2.valueChanged.connect(_lu2)
                bb2 = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                bb2.accepted.connect(d2.accept); bb2.rejected.connect(d2.reject)
                l2.addWidget(bb2)
                if d2.exec() == QDialog.Accepted:
                    self._push_undo()
                    old_v = list(self._mullions_v); old_h = list(self._mullions_h)
                    if isinstance(self._mullions_v[idx], dict):
                        self._mullions_v[idx] = dict(self._mullions_v[idx])
                        self._mullions_v[idx]['pos'] = sp2.value()
                    else:
                        self._mullions_v[idx] = sp2.value()
                    self._mullions_v.sort(key=lambda m: m['pos'] if isinstance(m, dict) else m)
                    lost = self._remap_cell_assigns_after_mullion_change(old_v, old_h)
                    if lost:
                        self._lbl_status.setText(
                            f'Dikey orta kayıt taşındı. {lost} hücredeki kanat/kapı kanat '
                            f'bölündüğü için kaldırıldı — o hücreye yeniden atama yapın.')
                else:
                    self._preview.set_mullions(self._mullions_v, self._mullions_h)
                    self._redraw_preview_cell_assigns()
            else:
                # Yatay
                hi = idx - nv
                mh_item = self._mullions_h[hi]
                old_pos = mh_item['pos'] if isinstance(mh_item, dict) else mh_item
                r0, r1 = _h_edit_range(hi)
                lo2 = max(1, int(round(r0)) + 1); hi2 = max(lo2, int(round(r1)) - 1)
                sp2 = QSpinBox(); sp2.setRange(lo2, hi2)
                sp2.setValue(min(max(int(old_pos), lo2), hi2)); sp2.setSuffix(' mm')
                d2 = QDialog(dlg); d2.setWindowTitle(f'Yatay #{hi+1} Konumu')
                l2 = QVBoxLayout(d2)
                if r1 - r0 < inner_h - 1:
                    l2.addWidget(QLabel(f'(Bu kayıt yalnızca {r0:.0f}–{r1:.0f} mm aralığında taşınabilir)'))
                l2.addWidget(sp2)
                def _lu2h(v, _hi=hi):
                    tmp = list(self._mullions_h)
                    if isinstance(tmp[_hi], dict):
                        tmp[_hi] = dict(tmp[_hi]); tmp[_hi]['pos'] = v
                    else:
                        tmp[_hi] = v
                    tmp.sort(key=lambda m: m['pos'] if isinstance(m, dict) else m)
                    self._preview.set_mullions(self._mullions_v, tmp)
                    self._preview_live_cell_assigns(self._mullions_v, tmp)
                    self._preview.update()
                sp2.valueChanged.connect(_lu2h)
                bb2 = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                bb2.accepted.connect(d2.accept); bb2.rejected.connect(d2.reject)
                l2.addWidget(bb2)
                if d2.exec() == QDialog.Accepted:
                    self._push_undo()
                    old_v = list(self._mullions_v); old_h = list(self._mullions_h)
                    if isinstance(self._mullions_h[hi], dict):
                        self._mullions_h[hi] = dict(self._mullions_h[hi])
                        self._mullions_h[hi]['pos'] = sp2.value()
                    else:
                        self._mullions_h[hi] = sp2.value()
                    self._mullions_h.sort(key=lambda m: m['pos'] if isinstance(m, dict) else m)
                    lost = self._remap_cell_assigns_after_mullion_change(old_v, old_h)
                    if lost:
                        self._lbl_status.setText(
                            f'Yatay orta kayıt taşındı. {lost} hücredeki kanat/kapı kanat '
                            f'bölündüğü için kaldırıldı — o hücreye yeniden atama yapın.')
                else:
                    self._preview.set_mullions(self._mullions_v, self._mullions_h)
                    self._redraw_preview_cell_assigns()
            self._preview.set_mullions(self._mullions_v, self._mullions_h)
            self._preview.update()
            _refresh_list()

        def _delete():
            idx = lst.currentRow()
            if idx < 0: return
            self._push_undo()
            old_v = list(self._mullions_v); old_h = list(self._mullions_h)
            nv = len(self._mullions_v)
            if idx < nv:
                del self._mullions_v[idx]
            else:
                del self._mullions_h[idx - nv]
            lost = self._remap_cell_assigns_after_mullion_change(old_v, old_h)
            self._preview.set_mullions(self._mullions_v, self._mullions_h)
            self._preview.update()
            self._update_mullion_label()
            if lost:
                self._lbl_status.setText(
                    f'Orta kayıt silindi. {lost} hücredeki kanat/kapı kanat '
                    f'artık geçersiz olduğu için kaldırıldı.')
            _refresh_list()

        btn_edit.clicked.connect(_edit)
        btn_del.clicked.connect(_delete)

        # Close butonu
        close_btn = QPushButton('Kapat')
        close_btn.clicked.connect(dlg.accept)
        lay.addWidget(close_btn)
        dlg.exec()

    def _init_frame_preview(self, frame_type: str = 'pencere'):
        """Kasayı anlık olarak önizlemede göster, parça hesaplamaz."""
        W = self._sp_w.value()
        H = self._sp_h.value()
        kasa_sc = self._prof_selectors['kasa'].currentData() or ''
        prof = cg.get_profile(self._library, kasa_sc) or {}
        kasa_kerf = float(prof.get('overlap_dxf') or prof.get('kerf') or 45)

        self._frame_type = frame_type  # 'pencere' veya 'kapi'
        # Recipe'yi otomatik ayarla
        recipe_map = {'pencere': 'sadece_kasa', 'kapi': 'sadece_kasa'}
        idx = self._cb_recipe.findData(recipe_map.get(frame_type, 'sadece_kasa'))
        if idx >= 0:
            self._cb_recipe.setCurrentIndex(idx)
        self._preview.clear_cell_assigns()
        self._cell_assigns_data = {}   # (row,col) → {'role': 'kanat'/'kapi_kanat', 'sc': stock_code}
        # Orta kayıtları sıfırla
        self._mullions_v.clear()
        self._mullions_h.clear()
        self._undo_stack.clear()
        self._update_mullion_label()

        self._preview.show_kasa_only(W, H, kasa_kerf, self._library)
        self._preview.set_mullions(self._mullions_v, self._mullions_h)
        self._lbl_status.setText(f'Kasa önizlemede. Orta kayıt veya kanat ekleyin.')

    @staticmethod
    def _cell_bounds_map(mullions_v, mullions_h, inner_w, inner_h):
        """
        {(row,col): (x0,x1,y0,y1)} hücre sınır haritası.
        Gerçek uygulama modül seviyesindeki compute_cell_bounds_map()
        içinde — FramePreviewWidget ile TEK ORTAK kaynaktan paylaşılır
        (bkz. dosyanın üstü). Burada sadece geriye dönük uyumlu ince bir
        sarmalayıcı olarak tutulur.
        """
        return compute_cell_bounds_map(mullions_v, mullions_h, inner_w, inner_h)

    def _inner_wh(self):
        """(inner_w, inner_h) — kasa iç ölçüleri (mm), pozisyon dialogları/
        önizleme ile AYNI kw kaynağını kullanır."""
        W = self._sp_w.value(); H = self._sp_h.value()
        kw = self._preview._kerf_kasa if self._preview._kerf_kasa > 0 else self._get_kasa_top_width()
        return W - 2 * kw, H - 2 * kw

    @staticmethod
    def _compute_remapped_assigns(old_assigns, old_mullions_v, old_mullions_h,
                                   new_mullions_v, new_mullions_h, inner_w, inner_h):
        """
        SAF (yan etkisiz) fonksiyon: old_assigns'ı ({(row,col):{'role','sc'}})
        eski orta kayıt düzeninden yeni düzene geometrik olarak taşır.
        Etkilenmeyen hücreler yeni indekslerine korunarak taşınır; yeni orta
        kayıt tarafından bölünen hücrelerin ataması kaldırılır.
        Döndürür: (yeni_assigns_dict, kaldırılan_sayısı).

        Hem gerçek commit (mullion eklendi/silindi/taşındı) hem de CANLI
        ÖNİZLEME (kullanıcı henüz OK'e basmadan pozisyon spinbox'ını
        sürüklerken) için kullanılır — önizlemede self._cell_assigns_data
        DEĞİŞTİRİLMEZ, sadece ekranda geçici olarak gösterilir.
        """
        if not old_assigns:
            return {}, 0

        old_map = AkilliUretimDialog._cell_bounds_map(old_mullions_v, old_mullions_h, inner_w, inner_h)
        new_map = AkilliUretimDialog._cell_bounds_map(new_mullions_v, new_mullions_h, inner_w, inner_h)

        EPS = 0.5  # mm tolerans
        new_assigns = {}
        lost = 0
        for (ri, ci), assign in old_assigns.items():
            old_bbox = old_map.get((ri, ci))
            if old_bbox is None:
                lost += 1
                continue
            ox0, ox1, oy0, oy1 = old_bbox
            cx, cy = (ox0 + ox1) / 2.0, (oy0 + oy1) / 2.0

            match = None
            for (nri, nci), (nx0, nx1, ny0, ny1) in new_map.items():
                if nx0 - EPS <= cx <= nx1 + EPS and ny0 - EPS <= cy <= ny1 + EPS:
                    match = (nri, nci, nx0, nx1, ny0, ny1)
                    break
            if match is None:
                lost += 1
                continue
            nri, nci, nx0, nx1, ny0, ny1 = match
            # Hücre bölünmüş mü? Yeni sınırlar eski sınırı tam kapsamıyorsa
            # (yani yeni orta kayıt bu hücrenin ortasından geçmişse) atama
            # artık geçersiz — hangi yarıya ait olduğu belirsiz.
            if (nx0 <= ox0 + EPS and nx1 >= ox1 - EPS and
                    ny0 <= oy0 + EPS and ny1 >= oy1 - EPS):
                new_assigns[(nri, nci)] = assign
            else:
                lost += 1
        return new_assigns, lost

    def _remap_cell_assigns_after_mullion_change(self, old_mullions_v, old_mullions_h):
        """
        Yeni bir orta kayıt EKLENDİKTEN/DEĞİŞTİRİLDİKTEN SONRA çağrılır
        (mullions_v/h zaten güncel). self._cell_assigns_data'yı GERÇEKTEN
        günceller (bkz. _compute_remapped_assigns) ve önizlemeye yansıtır.
        Döndürür: kaldırılan atama sayısı (int).
        """
        old_assigns = getattr(self, '_cell_assigns_data', None) or {}
        if not old_assigns:
            self._preview.clear_cell_assigns()
            return 0

        inner_w, inner_h = self._inner_wh()
        new_assigns, lost = self._compute_remapped_assigns(
            old_assigns, old_mullions_v, old_mullions_h,
            self._mullions_v, self._mullions_h, inner_w, inner_h)

        self._cell_assigns_data = new_assigns
        self._preview.clear_cell_assigns()
        colors = {'kanat': '#f2f2f2', 'kapi_kanat': '#eeeeee'}
        for (ri, ci), assign in new_assigns.items():
            self._preview.set_cell_assign(ri, ci, colors.get(assign.get('role', 'kanat'), '#f2f2f2'))
        return lost

    def _redraw_preview_cell_assigns(self):
        """self._cell_assigns_data'yı OLDUĞU GİBİ (hiçbir eşleme yapmadan)
        önizlemeye yeniden çizer. Pozisyon dialogu iptal edildiğinde, canlı
        önizleme sırasında geçici olarak değiştirilmiş olabilecek önizleme
        renklerini gerçek (değişmemiş) veriye geri döndürmek için kullanılır.
        """
        assigns = getattr(self, '_cell_assigns_data', None) or {}
        self._preview.clear_cell_assigns()
        colors = {'kanat': '#f2f2f2', 'kapi_kanat': '#eeeeee'}
        for (ri, ci), assign in assigns.items():
            self._preview.set_cell_assign(ri, ci, colors.get(assign.get('role', 'kanat'), '#f2f2f2'))

    def _preview_live_cell_assigns(self, tentative_v, tentative_h):
        """
        Orta kayıt pozisyon dialogundaki CANLI ÖNİZLEME sırasında çağrılır
        (kullanıcı henüz OK'e basmadı). self._cell_assigns_data'ya
        DOKUNMAZ — sadece self._preview üzerinde, eklenecek orta kayıt
        varmış GİBİ hücre atamalarını geçici olarak yeniden çizer. Böylece
        önizleme, OK'e basıldığında oluşacak nihai sonucu doğru gösterir
        (aksi halde kanat/kapı kanat rengi yanlış hücrede/konumda görünürdü).
        """
        assigns = getattr(self, '_cell_assigns_data', None) or {}
        self._preview.clear_cell_assigns()
        if not assigns:
            return
        inner_w, inner_h = self._inner_wh()
        new_assigns, _lost = self._compute_remapped_assigns(
            assigns, self._mullions_v, self._mullions_h,
            tentative_v, tentative_h, inner_w, inner_h)
        colors = {'kanat': '#f2f2f2', 'kapi_kanat': '#eeeeee'}
        for (ri, ci), assign in new_assigns.items():
            self._preview.set_cell_assign(ri, ci, colors.get(assign.get('role', 'kanat'), '#f2f2f2'))

    def _add_mullion_v(self):
        """Dikey orta kayıt ekle."""
        n_rows = len(self._mullions_h) + 1
        if n_rows > 1:
            # Yatay bölme var → kullanıcı tıklayarak bölmeyi seçsin
            self._preview.set_mullion_mode('v')
            self._lbl_status.setText('Dikey orta kayıt eklemek istediğiniz bölmeye tıklayın.')
            try:
                self._preview.cellClickedForMullion.disconnect()
            except Exception:
                pass
            self._preview.cellClickedForMullion.connect(self._on_cell_for_mullion_v)
        else:
            # Tek bölme → direkt pozisyon sor
            self._open_mullion_v_pos_dialog(row_constraint=None)

    def _on_cell_for_mullion_v(self, row: int, col: int, mode: str):
        """Kullanıcı dikey OK için bölmeye tıkladı."""
        self._preview.set_mullion_mode(None)
        try:
            self._preview.cellClickedForMullion.disconnect()
        except Exception:
            pass
        # Tıklanan hücrenin gerçek mm sınırlarını bul — yeni dikey SADECE bu
        # hücrenin içine sınırlandırılacak, komşu hücreleri yanlışlıkla
        # bölmeyecek. y_scope = bu hücrenin dikey uzanımı; yeni orta kayıt
        # SADECE bu aralıkta geçerli olacak şekilde damgalanır (derinlik
        # ne olursa olsun doğru çalışması için — bkz. _cell_bounds_map).
        W = self._sp_w.value(); H = self._sp_h.value()
        kw = self._preview._kerf_kasa if self._preview._kerf_kasa > 0 else self._get_kasa_top_width()
        inner_w = W - 2 * kw; inner_h = H - 2 * kw
        bounds_map = self._cell_bounds_map(self._mullions_v, self._mullions_h, inner_w, inner_h)
        bbox = bounds_map.get((row, col))
        x_range = (bbox[0], bbox[1]) if bbox else None
        y_scope = (bbox[2], bbox[3]) if bbox else None
        self._open_mullion_v_pos_dialog(row_constraint=[row], x_range=x_range, y_scope=y_scope)

    def _open_mullion_v_pos_dialog(self, row_constraint, x_range=None, y_scope=None):
        """Dikey orta kayıt pozisyon dialog'unu aç.

        x_range verilirse (tıklanan hücrenin mm sınırları), yeni orta kayıt
        SADECE bu aralığa yerleştirilebilir — böylece aynı satırdaki komşu
        hücreler (örn. önceden atanmış bir kanat) yanlışlıkla bölünmez.

        y_scope verilirse, yeni orta kayıt kaydına damgalanır: bu kayıt
        SADECE bu dikey (y) aralığında geçerli olur. Bu, iç içe (3. seviye
        ve ötesi) bölmelerde, başka bir yerdeki tam-yükseklik orta kayıt
        yüzünden yanlışlıkla tüm çerçeveyi bölen bir sınır haline gelmesini
        engeller (bkz. _cell_bounds_map).
        """
        W = self._sp_w.value()
        kw = self._preview._kerf_kasa if self._preview._kerf_kasa > 0 else self._get_kasa_top_width()
        inner_w = W - 2 * kw

        range_min, range_max = (0.0, float(inner_w)) if x_range is None else x_range
        range_min = max(0.0, range_min); range_max = min(float(inner_w), range_max)
        if range_max - range_min < 2:
            range_min, range_max = 0.0, float(inner_w)   # dejenere aralık — güvenli varsayılan

        n_existing = sum(1 for m in self._mullions_v
                         if (isinstance(m, dict) and m.get('rows') == row_constraint)
                         or (not isinstance(m, dict) and row_constraint is None))
        # İlk orta kayıt: bölmenin tam ortası; n+1. orta kayıt: eşit dağılım
        default_pos = range_min + (range_max - range_min) * (n_existing+1) / (n_existing+2)
        default_pos = int(max(range_min+1, min(range_max-1, round(default_pos))))

        lo = max(1, int(round(range_min)) + 1)
        hi = max(lo, int(round(range_max)) - 1)

        dlg = QDialog(self)
        dlg.setWindowTitle('Dikey Orta Kayıt Konumu')
        l = QVBoxLayout(dlg)
        info = (f'Kasa iç genişliği: {inner_w:.0f} mm\n'
                f'Orta kayıt merkezinin konumu\n(kasa iç sol kenarından, mm):')
        if x_range is not None and (range_max - range_min) < inner_w - 1:
            info += f'\n(Seçilen bölme aralığı: {range_min:.0f}–{range_max:.0f} mm)'
        l.addWidget(QLabel(info))
        sp = QSpinBox()
        sp.setRange(lo, hi); sp.setValue(default_pos); sp.setSuffix(' mm')
        l.addWidget(sp)

        def _live(val):
            tmp = list(self._mullions_v) + [{'pos': val, 'rows': row_constraint, 'y_scope': y_scope}]
            self._preview.set_mullions(tmp, self._mullions_h)
            # Hücre atamalarını (kanat/kapı kanat) da eklenecekmiş GİBİ
            # geçici olarak yeniden çiz — aksi halde OK'e basmadan önce
            # yanlış hücrede/konumda görünürler (bkz. _preview_live_cell_assigns).
            self._preview_live_cell_assigns(tmp, self._mullions_h)
            self._preview.update()
        sp.valueChanged.connect(_live)
        _live(default_pos)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        l.addWidget(btns)

        if dlg.exec() == QDialog.Accepted:
            self._push_undo()
            old_v = list(self._mullions_v)
            old_h = list(self._mullions_h)
            self._mullions_v.append({'pos': sp.value(), 'rows': row_constraint, 'y_scope': y_scope})
            self._mullions_v.sort(key=lambda m: m['pos'] if isinstance(m, dict) else m)
            lost = self._remap_cell_assigns_after_mullion_change(old_v, old_h)
            if lost:
                self._lbl_status.setText(
                    f'Dikey orta kayıt eklendi. {lost} hücredeki kanat/kapı kanat '
                    f'bölündüğü için kaldırıldı — o hücreye yeniden atama yapın.')
        else:
            # İptal — canlı önizlemede geçici gösterilen renkleri gerçek
            # (değişmemiş) veriye geri döndür.
            self._redraw_preview_cell_assigns()
        self._preview.set_mullions(self._mullions_v, self._mullions_h)
        self._update_mullion_label()
        self._preview.update()

    def _add_mullion_h(self):
        """Yatay orta kayıt ekle — canlı önizleme ile."""
        n_cols = len([m for m in self._mullions_v]) + 1
        if n_cols > 1:
            # Dikey bölme var → kullanıcı tıklayarak sütunu seçsin
            self._preview.set_mullion_mode('h')
            self._lbl_status.setText('Yatay orta kayıt eklemek istediğiniz bölmeye tıklayın.')
            try:
                self._preview.cellClickedForMullion.disconnect()
            except Exception:
                pass
            self._preview.cellClickedForMullion.connect(self._on_cell_for_mullion_h)
        else:
            self._open_mullion_h_pos_dialog()

    def _on_cell_for_mullion_h(self, row: int, col: int, mode: str):
        """Kullanıcı yatay OK için bölmeye tıkladı."""
        self._preview.set_mullion_mode(None)
        try:
            self._preview.cellClickedForMullion.disconnect()
        except Exception:
            pass
        # Tıklanan hücrenin gerçek mm sınırlarını bul — yeni yatay SADECE bu
        # hücrenin içine sınırlandırılacak, aynı sütundaki komşu hücreleri
        # (örn. daha önce atanmış bir kanat) yanlışlıkla bölmeyecek. x_scope
        # = bu hücrenin yatay uzanımı; yeni orta kayıt SADECE bu aralıkta
        # geçerli olacak şekilde damgalanır (bkz. _cell_bounds_map).
        W = self._sp_w.value(); H = self._sp_h.value()
        kw = self._preview._kerf_kasa if self._preview._kerf_kasa > 0 else self._get_kasa_top_width()
        inner_w = W - 2 * kw; inner_h = H - 2 * kw
        bounds_map = self._cell_bounds_map(self._mullions_v, self._mullions_h, inner_w, inner_h)
        bbox = bounds_map.get((row, col))
        y_range = (bbox[2], bbox[3]) if bbox else None
        x_scope = (bbox[0], bbox[1]) if bbox else None
        self._open_mullion_h_pos_dialog(col_constraint=[col], y_range=y_range, x_scope=x_scope)

    def _open_mullion_h_pos_dialog(self, col_constraint=None, y_range=None, x_scope=None):
        """Yatay orta kayıt pozisyon dialogu.

        Not: Boydan boya (rows=None) dikey orta kayıt varken yatay eklemek
        artık sorunsuz — adaptif hücre sistemi (_get_cell_at / paintEvent /
        _calculate_frame) tüm derinliklerde bunu mm-aralığı temelli olarak
        doğru işler (bkz. _cell_bounds_map).

        y_range verilirse (tıklanan hücrenin mm sınırları — kasa iç alt
        kenarından ölçülü), yeni orta kayıt SADECE bu aralığa yerleştirilir.
        x_scope verilirse, yeni kayıt SADECE bu yatay aralıkta geçerli
        olacak şekilde damgalanır — komşu sütunları etkilemez.
        """
        H = self._sp_h.value()
        kw = self._preview._kerf_kasa if self._preview._kerf_kasa > 0 else self._get_kasa_top_width()
        inner_h = H - 2 * kw

        range_min, range_max = (0.0, float(inner_h)) if y_range is None else y_range
        range_min = max(0.0, range_min); range_max = min(float(inner_h), range_max)
        if range_max - range_min < 2:
            range_min, range_max = 0.0, float(inner_h)   # dejenere aralık — güvenli varsayılan

        # Aynı kolon kısıtına sahip mevcut h-mullion sayısı
        n_existing = sum(1 for m in self._mullions_h
                         if (isinstance(m, dict) and m.get('cols') == col_constraint)
                         or (not isinstance(m, dict) and col_constraint is None))
        default_pos = range_min + (range_max - range_min) * (n_existing+1) / (n_existing+2)
        default_pos = int(max(range_min+1, min(range_max-1, round(default_pos))))

        lo = max(1, int(round(range_min)) + 1)
        hi = max(lo, int(round(range_max)) - 1)

        dlg = QDialog(self)
        dlg.setWindowTitle('Yatay Orta Kayıt Konumu')
        dlg_lay = QVBoxLayout(dlg)
        info = (f'Kasa iç yüksekliği: {inner_h:.0f} mm\n'
                f'Orta kayıt merkezinin konumu\n(kasa iç alt kenarından, mm):')
        if y_range is not None and (range_max - range_min) < inner_h - 1:
            info += f'\n(Seçilen bölme aralığı: {range_min:.0f}–{range_max:.0f} mm)'
        dlg_lay.addWidget(QLabel(info))
        sp = QSpinBox()
        sp.setRange(lo, hi); sp.setValue(default_pos); sp.setSuffix(' mm')
        dlg_lay.addWidget(sp)

        def _live(val):
            tmp_h = sorted(
                [m if isinstance(m, dict) else {'pos': m, 'cols': None, 'x_scope': None} for m in self._mullions_h]
                + [{'pos': val, 'cols': col_constraint, 'x_scope': x_scope}],
                key=lambda x: x['pos']
            )
            self._preview.set_mullions(self._mullions_v, tmp_h)
            # Hücre atamalarını da eklenecekmiş GİBİ geçici olarak yeniden
            # çiz — aksi halde OK'e basmadan önce yanlış hücrede/konumda
            # görünürler (bkz. _preview_live_cell_assigns).
            self._preview_live_cell_assigns(self._mullions_v, tmp_h)
            self._preview.update()
        sp.valueChanged.connect(_live)
        _live(default_pos)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        dlg_lay.addWidget(btns)

        if dlg.exec() == QDialog.Accepted:
            self._push_undo()
            old_v = list(self._mullions_v)
            old_h = list(self._mullions_h)
            self._mullions_h.append({'pos': sp.value(), 'cols': col_constraint, 'x_scope': x_scope})
            self._mullions_h.sort(key=lambda m: m['pos'] if isinstance(m, dict) else m)
            lost = self._remap_cell_assigns_after_mullion_change(old_v, old_h)
            if lost:
                self._lbl_status.setText(
                    f'Yatay orta kayıt eklendi. {lost} hücredeki kanat/kapı kanat '
                    f'bölündüğü için kaldırıldı — o hücreye yeniden atama yapın.')
        else:
            # İptal — canlı önizlemede geçici gösterilen renkleri gerçek
            # (değişmemiş) veriye geri döndür.
            self._redraw_preview_cell_assigns()
        self._preview.set_mullions(self._mullions_v, self._mullions_h)
        self._update_mullion_label()
        self._preview.update()

    def _add_sash_to_frame(self, role: str = 'kanat'):
        """
        Orta kayıt VARSA → hücre seçim moduna gir (mevcut davranış)
        Orta kayıt YOKSA → tüm çerçeveyi doğrudan ata, önizlemeyi güncelle
        """
        if self._mullions_v or self._mullions_h:
            # Hücre seçim moduna gir
            self._preview.set_select_mode(True)
            self._lbl_status.setText('Kanat eklenecek hücreye tıklayın. ESC ile iptal.')
            try:
                self._preview.cellClicked.disconnect()
            except Exception:
                pass
            self._preview.cellClicked.connect(self._on_cell_clicked_for_kanat)
            # role bilgisini geçici sakla
            self._pending_sash_role = role
        else:
            # Orta kayıt yok → tüm çerçeveyi direkt ata
            self._push_undo()
            color = '#f2f2f2' if role == 'kanat' else '#eeeeee'
            sc_key = 'kapi_kanat' if role == 'kapi_kanat' else 'kanat'
            sc = self._prof_selectors.get(sc_key)
            sc = sc.currentData() if sc else ''
            self._cell_assigns_data[(0, 0)] = {'role': role, 'sc': sc}
            self._preview.set_cell_assign(0, 0, color)
            role_label = 'Kapı Kanat' if role == 'kapi_kanat' else 'Kanat'
            self._lbl_status.setText(f'{role_label} atandı. "Çerçeveyi Tamamla" ile listeye ekleyin.')

    def _open_new_frame_dialog(self):
        """Ölçü alanını ve aksiyon butonlarını göster, önizlemeyi hemen başlat."""
        self._frame_dim_widget.setVisible(True)
        self._frame_action_widget.setVisible(True)
        # Önizlemeyi hemen göster
        self._init_frame_preview('pencere')

        # W/H değişince önizlemeyi güncelle
        def _auto():
            if getattr(self._preview, '_kasa_only', False) or self._preview._kerf_kasa > 0:
                self._init_frame_preview(getattr(self, '_frame_type', 'pencere'))
        try: self._sp_w.valueChanged.disconnect()
        except Exception: pass
        try: self._sp_h.valueChanged.disconnect()
        except Exception: pass
        self._sp_w.valueChanged.connect(lambda _: _auto())
        self._sp_h.valueChanged.connect(lambda _: _auto())

    def _finish_frame(self):
        """Adet sor, çerçeveyi listeye ekle (yeni çizim) ya da düzenlenmekte
        olan çizimi güncelle."""
        if not getattr(self, '_preview', None):
            return
        has_kasa = self._preview._kerf_kasa > 0 or self._preview._kasa_only
        if not has_kasa:
            QMessageBox.information(self, 'Uyarı', 'Önce "Yeni Çerçeve" ile kasa oluşturun.')
            return

        editing_pos = getattr(self, '_editing_frame_pos', None)
        is_editing = editing_pos is not None and 0 <= editing_pos < len(self._saved_frames)

        # Adet sorusu
        dlg = QDialog(self)
        dlg.setWindowTitle('Adet')
        dlg_lay = QVBoxLayout(dlg)
        dlg_lay.addWidget(QLabel('Bu çerçeveden kaç adet üretilecek?'))
        sp_qty = QSpinBox(); sp_qty.setRange(1, 999)
        sp_qty.setValue(self._saved_frames[editing_pos].get('qty', 1) if is_editing else 1)
        sp_qty.setSuffix(' adet')
        sp_qty.setMinimumWidth(120)
        dlg_lay.addWidget(sp_qty)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        dlg_lay.addWidget(btns)
        if dlg.exec() != QDialog.Accepted:
            return
        qty = sp_qty.value()

        # Düzenleme modundaysak: önce eski çizime ait parçaları listeden çıkar
        # (yeni hesaplanan parçalar temiz bir zeminde frame_index alsın)
        if is_editing:
            old_entry = self._saved_frames[editing_pos]
            old_indices = set(old_entry.get(
                'frame_indices',
                [old_entry['frame_idx']] if old_entry.get('frame_idx') is not None else []))
            self._pieces = [p for p in self._pieces if p.get('frame_index') not in old_indices]

        existing_indices = set(p.get('frame_index', 1) for p in self._pieces)

        try:
            for i in range(qty):
                self._calculate_frame(append=(i > 0 or bool(self._pieces)))
        except Exception as e:
            import traceback
            QMessageBox.critical(self, 'Hesaplama Hatası',
                f'Çerçeve hesaplanamadı:\n{e}\n\n{traceback.format_exc()[:600]}')
            return

        new_indices = sorted(set(p.get('frame_index', 1) for p in self._pieces) - existing_indices)
        if not new_indices:
            new_indices = [max((p.get('frame_index', 1) for p in self._pieces), default=1)]

        # Tamamlanan/güncellenen frame'i kaydet (önizleme + kalıcı sipariş verisi için)
        import copy
        frame_pieces = [p for p in self._pieces if p.get('frame_index') in new_indices]
        stock_snapshot = {role: (cb.currentData() or '')
                           for role, cb in self._prof_selectors.items()}
        frame_entry = {
            'frame_idx':     new_indices[-1],   # geriye dönük uyumluluk
            'frame_indices': new_indices,        # adet>1 dahil bu çizime ait TÜM frame_index'ler
            'pieces':        copy.deepcopy(frame_pieces),
            'W':             self._sp_w.value(),
            'H':             self._sp_h.value(),
            'kasa_kerf':     self._preview._kerf_kasa,
            'kanat_kerf':    self._preview._kerf_kanat,
            'kanat_ov_user': self._preview._kanat_ov_user,
            'kanat_width':   self._preview._kanat_width,
            'mullions_v':    copy.deepcopy(self._mullions_v),
            'mullions_h':    copy.deepcopy(self._mullions_h),
            'cell_assigns':  copy.deepcopy(getattr(self, '_cell_assigns_data', {})),
            'frame_type':    getattr(self, '_frame_type', 'pencere'),
            'recipe_key':    self._cb_recipe.currentData(),
            'stock':         stock_snapshot,
            'angle':         self._sp_angle.value(),
            'weld_enabled':  self._chk_weld.isChecked(),
            'weld_mm':       self._sp_weld_mm.value(),
            'qty':           qty,
        }

        if is_editing:
            self._saved_frames[editing_pos] = frame_entry
            self._nav_frame_pos = editing_pos
            self._lbl_status.setText(f'Çizim güncellendi. Toplam {len(self._pieces)} parça.')
        else:
            self._saved_frames.append(frame_entry)
            self._nav_frame_pos = len(self._saved_frames) - 1
            self._lbl_status.setText(f'{qty} adet çerçeve eklendi. Toplam {len(self._pieces)} parça.')

        self._editing_frame_pos = None
        self._btn_finish_frame.setText('✅  Çerçeveyi Tamamla')

        # Prog no'ları tüm parça listesi için yeniden sırala (düzenle/sil sonrası tutarlılık)
        start_no = self._sp_prog_start.value()
        for i, p in enumerate(self._pieces):
            p['prog_no'] = start_no + i
        self._run_bar_packing()
        self._render_piece_table()

        # Ölçü ve aksiyon alanlarını kapat
        self._frame_dim_widget.setVisible(False)
        self._frame_action_widget.setVisible(False)
        self._mullions_v.clear(); self._mullions_h.clear()
        self._cell_assigns_data = {}
        self._undo_stack.clear()
        self._update_mullion_label()

        # Tamamlanan/güncellenen frame'i önizlemede göster
        self._show_saved_frame(self._nav_frame_pos)
        self._update_nav_buttons()

    def _edit_frame(self, pos: int = None):
        """Görüntülenen (veya belirtilen) çizimi düzenleme moduna alır: ölçüler,
        orta kayıtlar, kanat/kapı kanat atamaları ve profil seçimleri o çizimin
        kayıtlı haline geri yüklenir; kullanıcı değişiklik yapıp "Çizimi Güncelle"
        ile onaylar."""
        if pos is None:
            pos = self._nav_frame_pos
        if pos < 0 or pos >= len(self._saved_frames):
            return
        f = self._saved_frames[pos]

        for role, sc in f.get('stock', {}).items():
            self._set_profile_selector(role, sc)

        self._sp_w.setValue(int(f.get('W', self._sp_w.value())))
        self._sp_h.setValue(int(f.get('H', self._sp_h.value())))
        self._sp_angle.setValue(int(f.get('angle', 45)))
        self._chk_weld.setChecked(bool(f.get('weld_enabled', False)))
        self._sp_weld_mm.setValue(int(f.get('weld_mm', 6)))

        recipe_key = f.get('recipe_key')
        if recipe_key:
            idx = self._cb_recipe.findData(recipe_key)
            if idx >= 0:
                self._cb_recipe.setCurrentIndex(idx)
        self._frame_type = f.get('frame_type', 'pencere')

        import copy
        self._mullions_v = copy.deepcopy(f.get('mullions_v', []))
        self._mullions_h = copy.deepcopy(f.get('mullions_h', []))
        self._cell_assigns_data = copy.deepcopy(f.get('cell_assigns', {}))
        self._undo_stack.clear()

        kasa_kerf = f.get('kasa_kerf') or self._get_kasa_top_width()
        self._preview.show_kasa_only(f.get('W', 700), f.get('H', 900), kasa_kerf, self._library)
        self._preview.set_mullions(self._mullions_v, self._mullions_h)
        self._redraw_preview_cell_assigns()
        self._update_mullion_label()

        self._frame_dim_widget.setVisible(True)
        self._frame_action_widget.setVisible(True)

        self._editing_frame_pos = pos
        self._btn_finish_frame.setText('💾  Çizimi Güncelle')
        self._lbl_status.setText(
            f'{pos+1}. çizim düzenleniyor. Değişiklik yapıp "Çizimi Güncelle" butonuna basın.')

    def _delete_frame(self, pos: int = None):
        """Belirtilen (veya görüntülenen) çizimi ve ona ait tüm parçaları siler."""
        if pos is None:
            pos = self._nav_frame_pos
        if pos < 0 or pos >= len(self._saved_frames):
            return
        reply = QMessageBox.question(
            self, 'Çizimi Sil',
            f'{pos+1}. çizimi ve ona ait tüm parçaları silmek istediğinize emin misiniz?',
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        entry = self._saved_frames.pop(pos)
        old_indices = set(entry.get(
            'frame_indices',
            [entry['frame_idx']] if entry.get('frame_idx') is not None else []))
        self._pieces = [p for p in self._pieces if p.get('frame_index') not in old_indices]

        start_no = self._sp_prog_start.value()
        for i, p in enumerate(self._pieces):
            p['prog_no'] = start_no + i
        self._run_bar_packing()
        self._render_piece_table()

        if getattr(self, '_editing_frame_pos', None) == pos:
            self._editing_frame_pos = None
            self._btn_finish_frame.setText('✅  Çerçeveyi Tamamla')
            self._frame_dim_widget.setVisible(False)
            self._frame_action_widget.setVisible(False)

        if self._saved_frames:
            self._nav_frame_pos = min(pos, len(self._saved_frames) - 1)
            self._show_saved_frame(self._nav_frame_pos)
        else:
            self._nav_frame_pos = -1
            self._preview.clear_cell_assigns()
            self._preview.set_mullions([], [])
            self._preview._kasa_only = False
            self._preview._pieces = []
            self._preview.update()
        self._update_nav_buttons()
        self._lbl_status.setText(
            f'Çizim silindi. {len(self._saved_frames)} çizim, {len(self._pieces)} parça kaldı.')

    def _set_profile_selector(self, role: str, stock_code: str):
        """Belirtilen role ait profil seçici kutusunu verilen stok koduna ayarlar
        (bir çizim düzenlemeye açılırken profil seçimlerini geri yüklemek için)."""
        cb = self._prof_selectors.get(role)
        if not cb or not stock_code:
            return
        idx = cb.findData(stock_code)
        if idx >= 0:
            cb.blockSignals(True)
            cb.setCurrentIndex(idx)
            cb.blockSignals(False)

    # ─────────────────────────────────────────────────────────
    # Sipariş kaydetme / yükleme (JSON tabanlı kalıcılık)
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _frame_entry_to_jsonable(f: dict) -> dict:
        """Bir çizim kaydını (saved_frames elemanı) JSON'a yazılabilir hale
        getirir — cell_assigns sözlüğündeki (row, col) tuple anahtarlarını
        liste-of-dict formuna çevirir."""
        import copy
        out = copy.deepcopy(f)
        ca = out.get('cell_assigns', {}) or {}
        out['cell_assigns'] = [
            {'row': key[0], 'col': key[1],
             'role': val.get('role', ''), 'sc': val.get('sc', '')}
            for key, val in ca.items()
        ]
        return out

    @staticmethod
    def _frame_entry_from_jsonable(d: dict) -> dict:
        """_frame_entry_to_jsonable ile üretilen kaydı bellek-içi (tuple
        anahtarlı) formata geri çevirir."""
        import copy
        out = copy.deepcopy(d)
        ca_list = out.get('cell_assigns', []) or []
        out['cell_assigns'] = {
            (item['row'], item['col']): {'role': item.get('role', ''), 'sc': item.get('sc', '')}
            for item in ca_list
        }
        return out

    def _gather_order_dict(self) -> dict:
        """Şu anki oturumdaki tüm çizimleri + sipariş üst bilgilerini tek bir
        JSON-uyumlu sözlükte toplar."""
        return {
            'order_id':      getattr(self, '_order_id', None),
            'order_no':      self._ed_order_no.text().strip(),
            'customer_name': self._ed_customer_name.text().strip(),
            'customer_code': self._ed_customer_code.text().strip(),
            'bar_len_mm':    self._sp_bar_len.value(),
            'bar_start':     self._sp_bar_start.value(),
            'prog_start':    self._sp_prog_start.value(),
            'frames':        [self._frame_entry_to_jsonable(f) for f in self._saved_frames],
        }

    def _save_order(self, silent: bool = False):
        """Şu anki siparişi (tüm çizimleriyle) diske kaydeder / günceller."""
        if not self._saved_frames:
            if not silent:
                QMessageBox.information(
                    self, 'Uyarı',
                    'Kaydedilecek çizim yok. Önce en az bir çerçeveyi\n'
                    '"✅ Çerçeveyi Tamamla" ile tamamlayın.')
            return None
        try:
            import order_store as ordst
            data = self._gather_order_dict()
            order_id = ordst.save_order(data)
        except Exception as e:
            import traceback
            QMessageBox.critical(self, 'Sipariş Kaydedilemedi',
                f'{e}\n\n{traceback.format_exc()[:600]}')
            return None
        self._order_id = order_id
        if not silent:
            QMessageBox.information(
                self, '✅ Sipariş Kaydedildi',
                f'Sipariş No: {data["order_no"] or "(boş)"}\n'
                f'Müşteri: {data["customer_name"] or "(boş)"}\n'
                f'Çizim sayısı: {len(self._saved_frames)}\n\n'
                f'"📁 Siparişler" listesinden daha sonra tekrar açıp düzenleyebilirsiniz.')
        self._lbl_status.setText(f'Sipariş kaydedildi ({len(self._saved_frames)} çizim).')
        return order_id

    def load_order_data(self, order_dict: dict):
        """Diskten yüklenen bir siparişi bu diyaloğa yükler (görüntüleme /
        yeni çizim ekleme / mevcut çizimleri düzenleme amacıyla)."""
        import copy
        self._order_id = order_dict.get('order_id')
        self._ed_order_no.setText(order_dict.get('order_no', '') or '')
        self._ed_customer_name.setText(order_dict.get('customer_name', '') or '')
        self._ed_customer_code.setText(order_dict.get('customer_code', '') or '')
        self._sp_bar_len.setValue(int(order_dict.get('bar_len_mm', 6000) or 6000))
        self._sp_bar_start.setValue(int(order_dict.get('bar_start', 1) or 1))
        self._sp_prog_start.setValue(int(order_dict.get('prog_start', 1) or 1))

        self._saved_frames = [self._frame_entry_from_jsonable(f) for f in order_dict.get('frames', [])]
        self._pieces = []
        for f in self._saved_frames:
            self._pieces.extend(copy.deepcopy(f.get('pieces', [])))

        # Yapışkan profil seçimini son çizimin kullandığı stok kodlarına ayarla
        if self._saved_frames:
            last_stock = self._saved_frames[-1].get('stock', {})
            for role, sc in last_stock.items():
                self._set_profile_selector(role, sc)

        self._run_bar_packing()
        self._render_piece_table()

        self._nav_frame_pos = len(self._saved_frames) - 1 if self._saved_frames else -1
        if self._saved_frames:
            self._show_saved_frame(self._nav_frame_pos)
        self._update_nav_buttons()
        self._lbl_status.setText(
            f'Sipariş yüklendi: {len(self._saved_frames)} çizim, {len(self._pieces)} parça. '
            f'Yeni çizim eklemek için "Yeni Çerçeve", düzenlemek için "✏️" kullanın.')

    def _show_saved_frame(self, pos: int):
        """Kaydedilen frame'i önizlemede göster."""
        if pos < 0 or pos >= len(self._saved_frames):
            return
        f = self._saved_frames[pos]
        self._preview._kasa_only = False
        self._preview.update_frame(
            f['pieces'], f['W'], f['H'],
            kerf_kasa=f['kasa_kerf'], kerf_kanat=f['kanat_kerf'],
            library=self._library,
            kanat_ov_user=f.get('kanat_ov_user', 0),
            kanat_width_mm=f.get('kanat_width', 0))
        self._preview.set_mullions(f['mullions_v'], f['mullions_h'])
        # Hücre atamaları
        self._preview.clear_cell_assigns()
        colors = {'kanat': '#f2f2f2', 'kapi_kanat': '#eeeeee'}
        for (ri, ci), assign in f['cell_assigns'].items():
            self._preview.set_cell_assign(ri, ci, colors.get(assign.get('role','kanat'), '#f2f2f2'))
        self._preview.update()

    def _update_nav_buttons(self):
        """Navigasyon butonlarını ve etiketini güncelle."""
        n = len(self._saved_frames)
        pos = self._nav_frame_pos
        self._btn_prev_frame.setEnabled(pos > 0)
        self._btn_next_frame.setEnabled(pos < n - 1)
        has_current = 0 <= pos < n
        if hasattr(self, '_btn_edit_frame'):
            self._btn_edit_frame.setEnabled(has_current)
        if hasattr(self, '_btn_delete_frame'):
            self._btn_delete_frame.setEnabled(has_current)
        if n > 0:
            self._lbl_frame_nav.setText(f'Çerçeve {pos+1} / {n}')
        else:
            self._lbl_frame_nav.setText('')

    def _show_prev_frame(self):
        if self._nav_frame_pos > 0:
            self._nav_frame_pos -= 1
            self._show_saved_frame(self._nav_frame_pos)
            self._update_nav_buttons()

    def _show_next_frame(self):
        if self._nav_frame_pos < len(self._saved_frames) - 1:
            self._nav_frame_pos += 1
            self._show_saved_frame(self._nav_frame_pos)
            self._update_nav_buttons()

    def _on_cell_clicked_for_kanat(self, row: int, col: int):
        """Hücreye tıklandığında kanat tipini sor ve ata."""
        self._push_undo()
        self._preview.set_select_mode(False)
        try:
            self._preview.cellClicked.disconnect()
        except Exception:
            pass

        role = getattr(self, '_pending_sash_role',
                       'kapi_kanat' if getattr(self, '_frame_type', 'pencere') == 'kapi' else 'kanat')
        role_label = 'Kapı Kanat' if role == 'kapi_kanat' else 'Kanat'

        # Renk ata
        colors = {'kanat': '#f2f2f2', 'kapi_kanat': '#eeeeee'}
        self._preview.set_cell_assign(row, col, colors.get(role, '#f2f2f2'))

        if not hasattr(self, '_cell_assigns_data'):
            self._cell_assigns_data = {}

        sc_key = 'kapi_kanat' if role == 'kapi_kanat' else 'kanat'
        sc = self._prof_selectors.get(sc_key, self._prof_selectors.get('kanat'))
        sc = sc.currentData() if sc else ''
        self._cell_assigns_data[(row, col)] = {'role': role, 'sc': sc}

        n_cols = len(self._mullions_v) + 1
        n_rows = len(self._mullions_h) + 1
        assigned = len(self._cell_assigns_data)
        total = n_cols * n_rows
        self._lbl_status.setText(
            f'{role_label} → hücre ({row+1},{col+1}) atandı. '
            f'{assigned}/{total} hücre dolu. Listeye eklemek için ✅ butonuna bas.')

    def _push_undo(self):
        """Mevcut durumu undo yığınına ekle."""
        import copy
        self._undo_stack.append({
            'mullions_v':       list(self._mullions_v),
            'mullions_h':       list(self._mullions_h),
            'cell_assigns_data': copy.deepcopy(getattr(self, '_cell_assigns_data', {})),
        })

    def _undo_last(self):
        """Son işlemi geri al."""
        if not self._undo_stack:
            self._lbl_status.setText('Geri alınacak işlem yok.')
            return
        state = self._undo_stack.pop()
        self._mullions_v       = state['mullions_v']
        self._mullions_h       = state['mullions_h']
        self._cell_assigns_data = state['cell_assigns_data']
        # Önizlemeyi restore et
        self._preview.set_mullions(self._mullions_v, self._mullions_h)
        self._preview.clear_cell_assigns()
        colors = {'kanat': '#f2f2f2', 'kapi_kanat': '#eeeeee'}
        for (ri, ci), assign in self._cell_assigns_data.items():
            self._preview.set_cell_assign(ri, ci, colors.get(assign.get('role','kanat'), '#f2f2f2'))
        self._update_mullion_label()
        self._preview.update()
        remaining = len(self._undo_stack)
        self._lbl_status.setText(f'↩ Geri alındı. ({remaining} adım daha geri alınabilir)')

    def _clear_mullions(self):
        self._mullions_v.clear()
        self._mullions_h.clear()
        # Kanat atamalarını da temizle (eski atamalar karışıklık yaratır)
        self._cell_assigns_data = {}
        self._preview.clear_cell_assigns()
        self._update_mullion_label()
        self._preview.set_mullions([], [])
        self._preview.update()

    def _ask_quantity_and_calculate(self, append: bool = False):
        """
        Adet popup'ı göster, ardından _calculate_frame'i 'adet' kez çağır.
        • append=False → ilk adet normal (listeyi değiştir), kalanlar ekle modunda
        • append=True  → tümü ekle modunda
        """
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton
        from PySide6.QtGui import QFont

        W = self._sp_w.value()
        H = self._sp_h.value()

        dlg = QDialog(self)
        dlg.setWindowTitle('Adet Gir')
        dlg.setFixedSize(320, 160)
        dlg.setStyleSheet("""
            QDialog { background:#1e1e2e; color:#e0e0e0; }
            QLabel  { color:#ddd; font-size:13px; }
            QSpinBox { background:#252540; color:#fff; border:1px solid #556;
                       border-radius:4px; padding:4px; font-size:16px; font-weight:bold; }
            QPushButton { background:#2e2e42; color:#ddd; border:1px solid #444;
                          border-radius:4px; padding:6px 18px; font-size:13px; }
            QPushButton:hover { background:#3a3a55; }
        """)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        lbl = QLabel(f'Bu çerçeveden ({W:.0f} × {H:.0f} mm) kaç adet üretilecek?')
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        sp = QSpinBox()
        sp.setRange(1, 999)
        sp.setValue(1)
        sp.setAlignment(Qt.AlignCenter)
        sp.setFixedHeight(38)
        lay.addWidget(sp)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton('✅  Tamam')
        btn_ok.setStyleSheet(
            'QPushButton{background:#1a5c3a;color:#fff;font-weight:bold;border-radius:4px;}'
            'QPushButton:hover{background:#27804f;}')
        btn_ok.setFixedHeight(34)
        btn_cancel = QPushButton('İptal')
        btn_cancel.setFixedHeight(34)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)

        # Enter tuşuyla da onayla
        sp.returnPressed = None  # QSpinBox'ta yok ama ok bağlı

        if dlg.exec() != QDialog.Accepted:
            return

        qty = sp.value()

        if qty == 1:
            # Tek adet — doğrudan
            self._calculate_frame(append=append)
            return

        # Çoklu adet
        for i in range(qty):
            if i == 0 and not append:
                # İlk adet: listeyi temizle
                self._calculate_frame(append=False)
            else:
                # Sonraki adetler: hep ekle modunda
                self._calculate_frame(append=True)

    def _calculate_frame(self, append: bool = False):
        W = self._sp_w.value()
        H = self._sp_h.value()
        recipe_key = self._cb_recipe.currentData()
        recipe = FRAME_RECIPES.get(recipe_key, [])

        # Seçili stok kodları
        stock = {}
        for role in ('kasa', 'kanat', 'kapi_kanat'):
            cb = self._prof_selectors[role]
            stock[role] = cb.currentData() or ''

        # Üst üste binme değerleri (mm cinsinden)
        def _overlap(role):
            """Rol için (overlap_dxf, overlap_user) döndürür."""
            code = stock.get(role, '')
            if not code:
                return 45.0, 0.0
            prof = cg.get_profile(self._library, code)
            if not prof:
                return 45.0, 0.0
            old_kerf = float(prof.get('kerf', 45))
            ov_dxf  = float(prof.get('overlap_dxf',  old_kerf))
            ov_user = float(prof.get('overlap_user', 0.0))
            return ov_dxf, ov_user

        kasa_ov_dxf,  kasa_ov_user  = _overlap('kasa')
        kanat_ov_dxf, kanat_ov_user = _overlap('kanat')
        kapi_ov_dxf,  kapi_ov_user  = _overlap('kapi_kanat')

        # eval_ctx değişkenleri
        kasa_kerf  = kasa_ov_dxf    # kasa profil genişliği (DXF'ten)
        kanat_kerf = kanat_ov_dxf
        kapi_kerf  = kapi_ov_dxf

        eval_ctx = {
            'W': W, 'H': H,
            # Kasa
            'kasa_kerf':    kasa_kerf,     # overlap_dxf  (profil genişliği)
            'kasa_ov_user': kasa_ov_user,  # overlap_user (üst üste binme payı)
            # Kanat / kapı kanat (formüllerde kullanılmaz ama erişilebilir kalsın)
            'kanat_kerf':   kanat_kerf,
            'kapi_kerf':    kapi_kerf,
        }

        # Kaynak payı sadece parça uzunluğuna eklenir; FRAME_X/Y'ye dokunmaz.
        weld_adj = self._sp_weld_mm.value() if self._chk_weld.isChecked() else 0

        # Her rol için FRAME_X / FRAME_Y: o rolün tarifte kullandığı
        # yatay (ALT/ÜST) ve dikey (SOL/SAĞ) formülden kaynaksız hesaplanır.
        # Kasa → W×10, H×10.  Kanat/kapı kanat → iç açıklık boyutu.
        def _role_frame_dims(role: str):
            role_items = [it for it in recipe if it['role'] == role]
            h_item = next((it for it in role_items if it['side'] in ('ALT', 'ÜST')), None)
            v_item = next((it for it in role_items if it['side'] in ('SOL', 'SAĞ')), None)
            try:
                fx = int(eval(h_item['len_formula'], {}, eval_ctx)) * 10 if h_item else W * 10
            except Exception:
                fx = W * 10
            try:
                fy = int(eval(v_item['len_formula'], {}, eval_ctx)) * 10 if v_item else H * 10
            except Exception:
                fy = H * 10
            return fx, fy

        # Rol başına önbellek (her parçada yeniden hesaplamayı önler)
        _frame_cache: dict = {}
        _name_cache: dict = {}   # stock_code → stok adı (profil kütüphanesinden)

        def _stock_name(sc: str) -> str:
            if sc not in _name_cache:
                prof = cg.get_profile(self._library, sc) or {}
                _name_cache[sc] = prof.get('name', '')
            return _name_cache[sc]

        # POSE_NO için: yeni bu çerçevenin kaçıncı çerçeve olduğunu belirle
        # Ekle modunda mevcut listenin max frame_index'inden +1, yoksa 1'den başla
        if not append or not self._pieces:
            new_frame_idx = 1
        else:
            new_frame_idx = max(p.get('frame_index', 1) for p in self._pieces) + 1

        # Rol içindeki sıra (kasa=1, kanat=2, kapi_kanat=3)
        _role_index = {'kasa': 1, 'kanat': 2, 'kapi_kanat': 3}

        raw_pieces = []
        prog_no = self._sp_prog_start.value()

        # Orta kayıtlı hücre kanıtı varsa recipe'deki kanatları atla
        has_cell_kanats = bool(self._mullions_v or self._mullions_h) and bool(getattr(self, '_cell_assigns_data', {}))

        for item in recipe:
            role = item['role']
            side = item['side']
            sc   = stock.get(role, '')
            if not sc:
                continue
            # Hücre kanıtı varsa recipe'deki kanat/kapi_kanat rollerini atla
            if has_cell_kanats and role in ('kanat', 'kapi_kanat'):
                continue
            try:
                length_mm = int(eval(item['len_formula'], {}, eval_ctx))
            except Exception:
                length_mm = 0
            # Kaynak payı parça uzunluğuna eklenir
            length_mm = max(0, length_mm + weld_adj)
            # Rol için FRAME boyutlarını önbellekten al veya hesapla
            if role not in _frame_cache:
                _frame_cache[role] = _role_frame_dims(role)
            fx, fy = _frame_cache[role]
            raw_pieces.append({
                'prog_no':        prog_no,
                'bar_no':         0,       # paketleme adımında doldurulur
                'role':           role,
                'side':           side,
                'stock_code':     sc,
                'stock_name':     _stock_name(sc),
                'length_mm':      length_mm,
                'length_x10':     length_mm * 10,
                'frame_x':        fx,
                'frame_y':        fy,
                'generated_code': '',
                'frame_index':    new_frame_idx,
                'role_index':     _role_index.get(role, 1),
            })
            prog_no += 1

        # ── Orta kayıt parçaları ────────────────────────────────────────
        frame_idx = new_frame_idx
        if self._mullions_v or self._mullions_h:
            ok_sc   = self._prof_selectors['orta_kayit'].currentData() or ''
            ok_prof = cg.get_profile(self._library, ok_sc) or {}
            ok_name = ok_prof.get('name', 'Orta Kayıt')
            kw      = self._get_kasa_top_width()
            weld    = self._sp_weld_mm.value() if self._chk_weld.isChecked() else 0

            # Dikey orta kayıtlar: uzunluk = H - 2×kasa_top_w (üst seviye) veya
            # kendi y_scope'unun (mm aralığı) uzunluğu (iç içe/nested kayıtlar).
            # y_scope, bu kaydın OLUŞTURULDUĞU hücrenin tam dikey uzanımıdır —
            # bu yüzden herhangi bir derinlikte doğru sonuç verir (eski
            # 'rows' index → global h-listesi eşleştirmesi yanlış olabiliyordu).
            for mv_item in self._mullions_v:
                if isinstance(mv_item, dict):
                    vpos = mv_item['pos']
                    y_scope = mv_item.get('y_scope')
                else:
                    vpos = mv_item
                    y_scope = None

                if y_scope is None:
                    length_mm = max(1, int(H - 2 * kw))   # orta kayıt kaynak olmaz
                else:
                    length_mm = max(1, int(y_scope[1] - y_scope[0]))   # orta kayıt kaynak olmaz

                raw_pieces.append({
                    'prog_no':        prog_no,
                    'role':           'orta_kayit',
                    'side':           'DİKEY',
                    'stock_code':     ok_sc,
                    'stock_name':     ok_name,
                    'length_mm':      length_mm,
                    'length_x10':     length_mm * 10,
                    'frame_x':        0,
                    'frame_y':        0,
                    'bar_no':         1,
                    'generated_code': '',
                    'frame_index':    frame_idx,
                    'role_index':     3,
                    'op_names':       [],
                    'pice_no':        1,
                    'remaining_length_mm': 0,
                    'mullion_pos':    vpos,
                })
                prog_no += 1

            # Yatay orta kayıtlar: uzunluk = W - 2×kasa_top_w (üst seviye) veya
            # kendi x_scope'unun uzunluğu (iç içe/nested kayıtlar) — bkz. yukarıdaki
            # dikey orta kayıt bloğundaki gerekçe.
            for mh_item in self._mullions_h:
                if isinstance(mh_item, dict):
                    hpos = mh_item['pos']
                    x_scope = mh_item.get('x_scope')
                else:
                    hpos = mh_item
                    x_scope = None

                if x_scope is None:
                    length_mm = max(1, int(W - 2 * kw))   # orta kayıt kaynak olmaz
                else:
                    length_mm = max(1, int(x_scope[1] - x_scope[0]))   # orta kayıt kaynak olmaz

                raw_pieces.append({
                    'prog_no':        prog_no,
                    'role':           'orta_kayit',
                    'side':           'YATAY',
                    'stock_code':     ok_sc,
                    'stock_name':     ok_name,
                    'length_mm':      length_mm,
                    'length_x10':     length_mm * 10,
                    'frame_x':        0,
                    'frame_y':        0,
                    'bar_no':         1,
                    'generated_code': '',
                    'frame_index':    frame_idx,
                    'role_index':     4,
                    'op_names':       [],
                    'pice_no':        1,
                    'remaining_length_mm': 0,
                    'mullion_pos':    hpos,
                })
                prog_no += 1

        # ── Hücre kanat parçaları ───────────────────────────────────────
        if hasattr(self, '_cell_assigns_data') and self._cell_assigns_data:
            # kasa_kerf: orta kayıt pozisyon dialoguyla AYNI değeri kullan
            kw = kasa_kerf   # kasa_ov_dxf — _calculate_frame başında hesaplandı
            mw = self._get_mullion_top_width()
            weld = self._sp_weld_mm.value() if self._chk_weld.isChecked() else 0

            inner_w = W - 2 * kw
            inner_h = H - 2 * kw

            # Orta kayıt overlap_dxf ve alt çıkıntı
            ok_sc   = self._prof_selectors['orta_kayit'].currentData() or ''
            ok_prof = cg.get_profile(self._library, ok_sc) or {}
            mullion_ov_dxf = float(ok_prof.get('overlap_dxf') or ok_prof.get('kerf') or 45)
            mullion_shoulder = (mw - mullion_ov_dxf) / 2

            # Tek doğruluk kaynağı: compute_cell_bounds_map — herhangi bir
            # iç içe bölünme derinliğinde doğru hücre geometrisini verir.
            # Kasa/orta-kayıt kenar tespiti DOĞRUDAN KOORDİNATLA yapılır
            # (eski ci==0/ci==n_v index kontrolleri yerine) — bu yüzden
            # numaralandırma şemasından ve derinlikten bağımsız çalışır.
            _EPS_CALC = 0.75
            bounds_map_calc = compute_cell_bounds_map(self._mullions_v, self._mullions_h, inner_w, inner_h)

            for (ri, ci), assign in self._cell_assigns_data.items():
                bbox = bounds_map_calc.get((ri, ci))
                if bbox is None:
                    continue
                x0, x1, y0, y1 = bbox

                touches_kasa_left  = x0 <= _EPS_CALC
                touches_kasa_right = x1 >= inner_w - _EPS_CALC
                touches_kasa_bot   = y0 <= _EPS_CALC
                touches_kasa_top   = y1 >= inner_h - _EPS_CALC

                raw_cw = x1 - x0
                loss_cw = (0.0 if touches_kasa_left else mw/2) + (0.0 if touches_kasa_right else mw/2)
                cell_w = max(1, raw_cw - loss_cw)

                raw_rh = y1 - y0
                loss_rh = (0.0 if touches_kasa_bot else mw/2) + (0.0 if touches_kasa_top else mw/2)
                cell_h = max(1, raw_rh - loss_rh)

                role = assign['role']; sc = assign['sc']
                prof = cg.get_profile(self._library, sc) or {}
                name = prof.get('name', '')

                for side in ('ALT', 'ÜST', 'SOL', 'SAĞ'):
                    if side in ('ALT', 'ÜST'):
                        left_ext  = kasa_ov_user if touches_kasa_left  else mullion_shoulder
                        right_ext = kasa_ov_user if touches_kasa_right else mullion_shoulder
                        length_mm = max(1, int(cell_w + left_ext + right_ext + weld))
                    else:
                        if touches_kasa_bot and touches_kasa_top:
                            # Bu hücrenin yüksekliğinde hiç yatay orta kayıt
                            # yok — kasa_ov_user TEK SEFER eklenir (kullanıcı
                            # tanımına göre 8+8=16mm gibi birleşik bir pay).
                            length_mm = max(1, int(cell_h + kasa_ov_user + weld))
                        else:
                            bot_ext = kasa_ov_user if touches_kasa_bot else mullion_shoulder
                            top_ext = kasa_ov_user if touches_kasa_top else mullion_shoulder
                            length_mm = max(1, int(cell_h + bot_ext + top_ext + weld))

                    fx = int(cell_w * 10); fy = int(cell_h * 10)
                    raw_pieces.append({
                        'role': role, 'side': side, 'stock_code': sc, 'stock_name': name,
                        'length_mm': length_mm, 'length_x10': length_mm * 10,
                        'frame_x': fx, 'frame_y': fy, 'bar_no': 1, 'prog_no': prog_no,
                        'generated_code': '', 'frame_index': frame_idx, 'role_index': 2,
                        'op_names': [], 'pice_no': 1, 'remaining_length_mm': 0, 'cell': (ri, ci),
                    })
                    prog_no += 1

        # ── Parça listesini güncelle (değiştir veya ekle) ───────────────
        _role_order = {'kasa': 0, 'kanat': 1, 'kapi_kanat': 2, 'orta_kayit': 3}

        if not append:
            # ── Normal mod: listeyi tamamen değiştir ─────────────────────
            self._pieces = raw_pieces
        else:
            # ── Ekle modu: listeye ekle, ardından rol+stok koduna göre sırala
            # Yeni parçaların prog_no'sunu mevcut listenin sonundan devam ettir
            if self._pieces:
                next_prog = max(p['prog_no'] for p in self._pieces) + 1
                for p in raw_pieces:
                    p['prog_no'] = next_prog
                    next_prog += 1
            self._pieces.extend(raw_pieces)
            # Sıralama: rol önceliği (kasa→kanat→kapı), sonra stok kodu
            self._pieces.sort(key=lambda p: (
                _role_order.get(p['role'], 99),
                p['stock_code'],
            ))
            # Prog_no'ları yeniden numaralandır (sıralama sonrası)
            start_no = self._sp_prog_start.value()
            for i, p in enumerate(self._pieces):
                p['prog_no'] = start_no + i

        # ── Bar paketleme (her iki modda da çalışır) ─────────────────────
        self._run_bar_packing()

        self._render_piece_table()
        self._code_view.clear()

        # Görsel önizlemeyi güncelle (profil renkleriyle)
        # Kanat profil genişliği ve overlap değerlerini hesapla
        _kanat_sc   = stock.get('kanat') or stock.get('kapi_kanat', '')
        _kanat_prof = cg.get_profile(self._library, _kanat_sc) or {}
        _kanat_w    = float(_kanat_prof.get('width_mm') or _kanat_prof.get('height_mm') or 0)
        self._preview.update_frame(
            self._pieces, W, H,
            kerf_kasa=kasa_kerf, kerf_kanat=kanat_kerf,
            library=self._library,
            kanat_ov_user=kanat_ov_user,
            kanat_width_mm=_kanat_w)
        self._preview.set_mullions(self._mullions_v, self._mullions_h)

        # Hücre kanat atamalarını görsel olarak yeniden yükle
        self._preview.clear_cell_assigns()
        if hasattr(self, '_cell_assigns_data'):
            colors = {'kanat': '#f2f2f2', 'kapi_kanat': '#eeeeee'}
            for (ri, ci), assign in self._cell_assigns_data.items():
                role = assign.get('role', 'kanat')
                self._preview.set_cell_assign(ri, ci, colors.get(role, '#f2f2f2'))
        self._preview._kasa_only = False

        mode_str = '  (ekleme modu)' if append else ''
        self._lbl_status.setText(
            f'{len(self._pieces)} parça{mode_str} — "Kodları Üret" butonuna bas.')

    # ─────────────────────────────────────────────────────────
    # Bar paketleme + liste temizleme
    # ─────────────────────────────────────────────────────────

    def _run_bar_packing(self):
        """
        FFD (First Fit Decreasing) bar paketleme optimizasyonu.

        Ayarlardan alınan parametreler:
          blade_mm      : Testere kalınlığı — parçalar arası fire (mm)
          head_waste_mm : Bar başı temizlik fire payı (mm)
          tail_waste_mm : Bar sonu temizlik fire payı (mm)
          gap_mm        : Parçalar arası ek boşluk (handling vb., mm)

        Trolley/UNIT ataması (POSE_NO bazlı):
          Her benzersiz POSE_NO sırayla bir raf slotuna atanır.
          Örn: 10 raf/trolley ile:
            POSE 1/1 → T1/U1,  POSE 1/2 → T1/U2,  POSE 2/1 → T1/U3, ...
            POSE 6/1 → T2/U1,  POSE 6/2 → T2/U2, ...
          Aynı POSE_NO'ya sahip tüm parçalar (farklı barlarda da olsa)
          aynı trolley/unit değerini alır.
        """
        cfg      = st.load_settings()
        bar_len  = self._sp_bar_len.value()
        bar_start= self._sp_bar_start.value()

        blade    = cfg.get('blade_mm',       4)
        head     = cfg.get('head_waste_mm', 20)
        tail     = cfg.get('tail_waste_mm', 20)
        gap      = cfg.get('gap_mm',         0)
        n_trol   = cfg.get('trolley_count',       5)
        n_shelf  = cfg.get('shelves_per_trolley', 6)

        # Parçalar arası toplam pay: testere + ek boşluk
        piece_gap = blade + gap
        # Bar içinde kullanılabilir uzunluk (baş + son fire düşülür)
        usable    = max(0, bar_len - head - tail)

        # ── Stok koduna göre gruplama ─────────────────────────────────────
        # Her stok kodu ayrı gruba, grup içinde parçalar büyükten küçüğe (FFD)
        from collections import defaultdict, OrderedDict
        groups: dict = defaultdict(list)
        for p in self._pieces:
            groups[p['stock_code']].append(p)
        # Ekleme sırasını koru (rol sırasına göre gelir)
        ordered_groups = OrderedDict()
        for p in self._pieces:
            sc = p['stock_code']
            if sc not in ordered_groups:
                ordered_groups[sc] = groups[sc]

        # ── FFD: her grup için ayrı bar seti ─────────────────────────────
        bar_no = bar_start
        # bar_no → kalan alan (mm)
        bar_remaining: dict = {}
        # bar_no → bu bardaki parça sayısı (gap hesabı için)
        bar_count: dict = {}
        # bar_no → bar'daki toplam kesilen uzunluk (remaining_length için)
        bar_used: dict = {}

        for sc, grp_pieces in ordered_groups.items():
            # Bu grup için yeni bar seti başlat (farklı stok → farklı bar)
            group_bars: list = []   # bu gruba ait (bar_no, remaining) çiftleri

            # FFD: uzun parçayı önce yerleştir
            sorted_pieces = sorted(grp_pieces, key=lambda x: x['length_mm'], reverse=True)

            for p in sorted_pieces:
                length = p['length_mm']
                placed = False

                # Mevcut barlarda yer var mı?
                for i, (bn, rem) in enumerate(group_bars):
                    n_in_bar = bar_count.get(bn, 0)
                    needed   = length + (piece_gap if n_in_bar > 0 else 0)
                    if rem >= needed:
                        group_bars[i] = (bn, rem - needed)
                        bar_count[bn] = n_in_bar + 1
                        bar_used[bn]  = bar_used.get(bn, 0) + length
                        p['bar_no']   = bn
                        placed = True
                        break

                if not placed:
                    # Yeni bar aç
                    new_bn = bar_no
                    bar_no += 1
                    needed = length   # ilk parça: gap yok
                    rem    = usable - needed
                    group_bars.append((new_bn, rem))
                    bar_remaining[new_bn] = rem
                    bar_count[new_bn]     = 1
                    bar_used[new_bn]      = length
                    p['bar_no']           = new_bn

            # Kalan alanı kaydet
            for bn, rem in group_bars:
                bar_remaining[bn] = rem

        # ── Kalan uzunluk ataması — açık formülle, sadece son parça satırına ──
        # remaining = bar_boyu - baş_fire - son_fire
        #             - Σ(parça_boyları) - N×testere - (N-1)×gap
        from collections import defaultdict as _dd
        bar_pieces_map: dict = _dd(list)
        for p in self._pieces:
            bar_pieces_map[p['bar_no']].append(p)

        bar_remaining_calc: dict = {}
        for bn, bpieces in bar_pieces_map.items():
            n            = len(bpieces)
            total_length = sum(pp['length_mm'] for pp in bpieces)
            remaining    = max(0, bar_len - head - tail - total_length
                               - n * blade - max(0, n - 1) * gap)
            bar_remaining_calc[bn] = remaining

        # Her bar'ın PROG_NO en büyük parçasını bul → kalan ona yazılır
        bar_last_piece: dict = {}
        for p in self._pieces:
            bn = p['bar_no']
            if bn not in bar_last_piece or p['prog_no'] > bar_last_piece[bn]['prog_no']:
                bar_last_piece[bn] = p

        for p in self._pieces:
            bn = p['bar_no']
            if bar_last_piece.get(bn) is p:
                p['remaining_length_mm'] = bar_remaining_calc.get(bn, 0)
            else:
                p['remaining_length_mm'] = 0

        # ── Trolley / Unit ataması (POSE_NO bazlı) ───────────────────────
        # Her benzersiz POSE_NO, parça listesindeki görünüm sırasına göre
        # bir slot alır. Slot → trolley/unit hesabı:
        #   slot 0 → T1/U1,  slot 1 → T1/U2, ..., slot n_shelf-1 → T1/Un
        #   slot n_shelf → T2/U1, ...
        seen_poses: list = []
        seen_poses_set: set = set()
        for p in self._pieces:
            pose = f"{p.get('frame_index', 1)}/{p.get('role_index', 1)}"
            if pose not in seen_poses_set:
                seen_poses.append(pose)
                seen_poses_set.add(pose)

        pose_to_slot = {pose: idx for idx, pose in enumerate(seen_poses)}

        for p in self._pieces:
            pose = f"{p.get('frame_index', 1)}/{p.get('role_index', 1)}"
            slot = pose_to_slot.get(pose, 0)
            trolley_no = slot // n_shelf + 1
            unit_no    = slot %  n_shelf + 1
            # Trolley kapasitesi aşılırsa son trolley'e sıkıştır
            if trolley_no > n_trol:
                trolley_no = n_trol
            p['trolley_no'] = trolley_no
            p['unit_no']    = unit_no

        # ── Bar içinde parça numarası (PICE_NO) ──────────────────────────
        bar_pice_counters: dict = {}
        for p in self._pieces:
            bn = p['bar_no']
            bar_pice_counters.setdefault(bn, 0)
            bar_pice_counters[bn] += 1
            p['pice_no'] = bar_pice_counters[bn]

        # ── Listeyi BAR_NO → PICE_NO sırasıyla yeniden sırala ────────────
        # Örnek listedeki gibi: bar 1 parçaları önce (1,2,3...), sonra bar 2 vb.
        self._pieces.sort(key=lambda p: (p['bar_no'], p['pice_no']))

        # ── PROGRAM_NO'yu yeniden numaralandır (sıralama sonrası) ─────────
        start_no = self._sp_prog_start.value()
        for i, p in enumerate(self._pieces):
            p['prog_no'] = start_no + i

    def _clear_pieces(self):
        """Parça listesini temizle."""
        if not self._pieces:
            return
        reply = QMessageBox.question(
            self, 'Listeyi Temizle',
            f'{len(self._pieces)} parça listeden kaldırılacak.\nEmin misiniz?',
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._pieces = []
            self._tbl.setRowCount(0)
            self._code_view.clear()
            self._lbl_status.setText('Liste temizlendi.')
            # Önizlemeyi ve kayıtlı frame'leri sıfırla
            self._saved_frames.clear()
            self._nav_frame_pos = -1
            self._editing_frame_pos = None
            self._order_id = None
            self._btn_finish_frame.setText('✅  Çerçeveyi Tamamla')
            self._preview._pieces = []
            self._preview._kasa_only = False
            self._preview.clear_cell_assigns()
            self._preview.set_mullions([], [])
            self._preview.update()
            self._update_nav_buttons()
            self._frame_dim_widget.setVisible(False)
            self._frame_action_widget.setVisible(False)

    # ─────────────────────────────────────────────────────────
    # Parça tablosu
    # ─────────────────────────────────────────────────────────

    def _render_piece_table(self):
        self._tbl.setRowCount(0)
        role_colors = {
            'kasa':      '#4a8080',
            'kanat':     '#8a6a1a',
            'kapi_kanat':'#6a4a90',
        }
        for i, p in enumerate(self._pieces):
            self._tbl.insertRow(i)
            self._tbl.setRowHeight(i, 26)
            col = role_colors.get(p['role'], '#333')

            pose_no = f"{p.get('frame_index', '')}/{p.get('role_index', '')}" \
                      if p.get('frame_index') else ''
            cells = [
                str(p['prog_no']),                             # 0 Prog No
                pose_no,                                       # 1 Poz No
                str(p['bar_no']),                              # 2 Bar
                _role_label(p['role']),                        # 3 Rol
                f'{SIDE_ICONS.get(p["side"],"")}{p["side"]}', # 4 Kenar
                p['stock_code'],                               # 5 Stok Kodu
                str(p['length_mm']),                           # 6 Uzunluk
                '✔' if p['generated_code'] else '',            # 7 Kod Var?
            ]
            for c, val in enumerate(cells):
                itm = QTableWidgetItem(val)
                itm.setBackground(QBrush(QColor(col)))
                if c == 7 and val == '✔':
                    itm.setForeground(QBrush(QColor('#50fa7b')))
                    itm.setFont(QFont('', 11, QFont.Bold))
                self._tbl.setItem(i, c, itm)

    def _on_cell_dclick(self, item):
        """Uzunluk sütununa çift tıklayınca QSpinBox aç."""
        if item.column() != 6:   # sütun 6 = Uzunluk (mm)
            return
        row = item.row()
        if row >= len(self._pieces):
            return

        sp = QSpinBox()
        sp.setRange(1, 99999)
        sp.setValue(self._pieces[row]['length_mm'])
        sp.setSuffix(' mm')
        sp.setStyleSheet('background:#2e2e42; color:#ddd; font-size:12px;')
        self._tbl.setCellWidget(row, 5, sp)
        sp.editingFinished.connect(lambda r=row, s=sp: self._commit_length(r, s))
        sp.setFocus()

    def _commit_length(self, row: int, sp: QSpinBox):
        val = sp.value()
        self._pieces[row]['length_mm']  = val
        self._pieces[row]['length_x10'] = val * 10
        self._pieces[row]['generated_code'] = ''  # Kod sıfırla
        self._tbl.removeCellWidget(row, 6)
        self._tbl.setItem(row, 6, QTableWidgetItem(str(val)))

    def _on_row_changed(self, row: int):
        """Satır seçilince sağ panelde o parçanın kodunu göster ve önizlemede vurgula."""
        if row < 0 or row >= len(self._pieces):
            return
        # Önizlemede seçili parçayı sarı ile vurgula
        self._preview.set_selected(row)
        p = self._pieces[row]
        code = p.get('generated_code', '')
        # İşlem adları — varsa piece dict'ten, yoksa kütüphaneden al
        op_names = p.get('op_names') or cg.get_side_op_names(
            p['stock_code'], p['side'], self._library)
        op_str = ('  '.join(f'{j+1}. {n}' for j, n in enumerate(op_names))
                  if op_names else '(tanımsız)')
        header = (f'─── Parça {row+1}: {_role_label(p["role"])} {p["side"]} '
                  f'| {p["stock_code"]} | {p["length_mm"]}mm ───')
        if code:
            self._code_view.setPlainText(
                f'{header}\nİşlemler: {op_str}\n\n{code}')
        else:
            self._code_view.setPlainText(
                f'{header}\nİşlemler: {op_str}\n\n[Henüz kod üretilmedi]')

    # ─────────────────────────────────────────────────────────
    # Kod üretimi
    # ─────────────────────────────────────────────────────────

    def _generate_codes(self):
        if not self._pieces:
            QMessageBox.information(self, 'Uyarı', 'Önce çerçeve hesaplayın.')
            return

        x0 = self._chk_x0.isChecked()

        for p in self._pieces:
            p['generated_code'] = cg.generate_side_code(
                p['stock_code'], p['length_x10'], p['side'],
                self._library, x0_mode=x0)
            # İşlem adlarını kaydet (UI gösterimi + EXPLANATION2 için)
            p['op_names'] = cg.get_side_op_names(
                p['stock_code'], p['side'], self._library)

        # Tabloyu güncelle (sütun 7 = Kod Var?)
        for i, p in enumerate(self._pieces):
            itm = QTableWidgetItem('✔' if p['generated_code'] else '—')
            if p['generated_code']:
                itm.setForeground(QBrush(QColor('#50fa7b')))
                itm.setFont(QFont('', 11, QFont.Bold))
            self._tbl.setItem(i, 7, itm)

        # Başlık: test modu uyarısı
        mode_note = '  ⚠ X=0 TEST MODU — gerçek X formülleri kullanılmadı' if x0 else ''

        # Tüm kodları sağda göster
        lines = []
        if mode_note:
            lines.append(mode_note)
            lines.append('')
        for i, p in enumerate(self._pieces):
            lines.append(
                f'─── Parça {i+1}: {_role_label(p["role"])} {p["side"]} '
                f'| {p["stock_code"]} | {p["length_mm"]}mm ───')
            # İşlem adları sırası
            op_names = p.get('op_names', [])
            if op_names:
                op_str = '  '.join(f'{j+1}. {n}' for j, n in enumerate(op_names))
                lines.append(f'İşlemler: {op_str}')
            else:
                lines.append('İşlemler: (tanımsız)')
            lines.append(p['generated_code'] if p['generated_code'] else '(işlem tanımsız)')
            lines.append('')
        self._code_view.setPlainText('\n'.join(lines))

        total = sum(1 for p in self._pieces if p['generated_code'])
        self._lbl_status.setText(
            f'{total}/{len(self._pieces)} parça için kod üretildi. MDB\'ye kaydedebilirsiniz.')

    # ─────────────────────────────────────────────────────────
    # Makineye Gönder (yeni ana akış)
    # ─────────────────────────────────────────────────────────

    def _send_to_machine(self):
        """
        1. Parça var mı kontrol et
        2. Makine seç (ayarlardaki seçili makineler)
        3. Makine grubuna göre akış
        """
        import exporter as exp

        if not self._pieces:
            QMessageBox.information(self, 'Uyarı', 'Önce çerçeve hesaplayın.')
            return

        # ── 1. Makine seçimi ──────────────────────────────────────────
        cfg      = st.load_settings()
        machines = cfg.get('selected_machines', ['DC 421'])
        if not machines:
            QMessageBox.warning(self, 'Makine Yok',
                'Ayarlar\'da hiçbir makine seçili değil.')
            return

        if len(machines) == 1:
            selected_machine = machines[0]
        else:
            dlg = _MachineSelectDialog(machines, self)
            if dlg.exec() != QDialog.Accepted:
                return
            selected_machine = dlg.selected_machine()

        grp = exp.machine_group(selected_machine)

        # ── 2. PIM / ALM → kod kontrolü ──────────────────────────────
        if grp in ('PIM', 'ALM'):
            has_codes = any(p.get('generated_code', '') for p in self._pieces)
            if not has_codes:
                msg = QMessageBox(self)
                msg.setWindowTitle('Kod Üretilmedi')
                msg.setIcon(QMessageBox.Question)
                msg.setText(f'<b>{selected_machine}</b> için işlem kodları henüz üretilmedi.')
                msg.setInformativeText('Ne yapmak istersiniz?')
                btn_gen  = msg.addButton('⚡  Kod Oluştur ve Gönder',   QMessageBox.AcceptRole)
                btn_skip = msg.addButton('📋  Kodsuz Gönder',            QMessageBox.ActionRole)
                btn_cancel = msg.addButton('İptal',                       QMessageBox.RejectRole)
                msg.exec()
                clicked = msg.clickedButton()
                if clicked == btn_cancel or clicked is None:
                    return
                if clicked == btn_gen:
                    self._generate_codes()
                    has_codes = any(p.get('generated_code', '') for p in self._pieces)
                    if not has_codes:
                        QMessageBox.warning(self, 'Kod Üretilemedi',
                            'Kodlar üretilemedi. Lütfen profil işlemlerini kontrol edin.')
                        return
                # btn_skip → has_codes False kalır, önizleme atlanır, kod boş gider

            # Kod önizleme penceresi (sadece kod varsa)
            if has_codes:
                dlg_prev = _CodePreviewDialog(self._pieces, selected_machine, self)
                if dlg_prev.exec() != QDialog.Accepted:
                    return

        # ── 3. Müşteri / sipariş bilgileri ───────────────────────────
        cust_name = self._ed_customer_name.text().strip()
        cust_code = self._ed_customer_code.text().strip()
        order_no  = self._ed_order_no.text().strip()

        # ── 4. Görsel üret — preview widget'ından ekran görüntüsü ───
        try:
            frame_images = self._grab_saved_frame_images(
                exp.image_dir(cust_name, order_no))
        except Exception as e:
            frame_images = {}
            print(f'[IMG] Görsel üretme hatası: {e}')

        try:
            records = [self._build_record(p, frame_images) for p in self._pieces]
        except Exception as e:
            QMessageBox.critical(self, 'Kayıt Hatası', f'Parça kaydı oluşturulamadı:\n{e}')
            return

        # ── 5. CSV'ye yaz ────────────────────────────────────────────
        try:
            out_path = exp.export(records, selected_machine, cust_name, order_no)
        except Exception as e:
            QMessageBox.critical(self, 'Dışa Aktarım Hatası', str(e))
            return

        # ── 5b. PDF raporu oluştur ────────────────────────────────────
        pdf_path = None
        try:
            import pdf_report as pr
            cfg = st.load_settings()
            settings_for_pdf = {
                'bar_len_mm':    self._sp_bar_len.value(),
                'head_waste_mm': cfg.get('head_waste_mm', 20),
                'tail_waste_mm': cfg.get('tail_waste_mm', 20),
                'blade_mm':      cfg.get('blade_mm', 4),
            }
            pdf_path = pr.generate_report(
                pieces        = self._pieces,
                records       = records,
                settings      = settings_for_pdf,
                out_dir       = exp.order_dir(cust_name, order_no),
                customer_name = cust_name,
                order_no      = order_no,
                frame_images  = frame_images,
            )
        except Exception as e:
            import traceback
            pdf_path = None
            QMessageBox.warning(self, 'PDF Hatası',
                f'PDF oluşturulamadı:\n{e}\n\n{traceback.format_exc()[:400]}')

        # ── 6. Sipariş no güncelle, bilgi ver ────────────────────────
        next_no = st.next_order_no()
        self._ed_order_no.setText(next_no)
        self._lbl_status.setText(
            f'{len(records)} parça → {os.path.basename(out_path)}')
        pdf_info = f'\nRapor: {os.path.basename(pdf_path)}' if pdf_path else ''
        QMessageBox.information(self, '✅ Gönderildi',
            f'{len(records)} parça kaydedildi.\n\n'
            f'CSV: {out_path}{pdf_info}\n\n'
            f'Sonraki sipariş no: {next_no}')

    # MDB'ye kaydet (eski, geriye dönük bırakıldı)
    # ─────────────────────────────────────────────────────────

    def _save_to_mdb(self):
        if not self._pieces:
            QMessageBox.information(self, 'Uyarı', 'Önce çerçeve hesaplayın.')
            return

        has_codes = any(p['generated_code'] for p in self._pieces)
        if not has_codes:
            reply = QMessageBox.question(self, 'Kod Üretilmedi',
                'Hiçbir parça için kod üretilmedi. Yine de kaydetmek istiyor musunuz?',
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return

        if not (self._db and self._db.connected):
            msg = QMessageBox(self)
            msg.setWindowTitle('MDB Bağlı Değil')
            msg.setIcon(QMessageBox.Warning)
            msg.setText('Veritabanı bağlantısı yok.')
            msg.setInformativeText(
                'Ana pencereden "💾 MDB Bağlan" ile bağlanabilir\n'
                'ya da buradan doğrudan MDB dosyasını seçebilirsiniz.')
            btn_sel = msg.addButton('📂  MDB Dosyası Seç…', QMessageBox.ActionRole)
            msg.addButton('İptal', QMessageBox.RejectRole)
            msg.exec()
            if msg.clickedButton() == btn_sel:
                self._try_connect_mdb_and_save()
            return

        # ── Kayıt modu seç ───────────────────────────────────────────
        msg_mode = QMessageBox(self)
        msg_mode.setWindowTitle('Kayıt Modu')
        msg_mode.setIcon(QMessageBox.Question)
        msg_mode.setText('Bu parçalar MDB\'ye nasıl kaydedilsin?')
        msg_mode.setInformativeText(
            '<b>⚠️ Üzerine Yaz</b>: Aynı program no\'lu kayıtlar silinir, yeniler eklenir.<br><br>'
            '<b>🗑 Temizle ve Baştan Yaz</b>: MDB\'deki TÜM kayıtlar silinir, liste baştan yazılır.<br><br>'
            '<b>➕ Ekle (Devam Et)</b>: Mevcut kayıtların üstüne ekler.')
        btn_overwrite = msg_mode.addButton('⚠️  Üzerine Yaz',        QMessageBox.DestructiveRole)
        btn_clear     = msg_mode.addButton('🗑  Temizle ve Baştan Yaz', QMessageBox.DestructiveRole)
        btn_append    = msg_mode.addButton('➕  Ekle (Devam Et)',       QMessageBox.AcceptRole)
        msg_mode.addButton('İptal', QMessageBox.RejectRole)
        msg_mode.exec()
        clicked = msg_mode.clickedButton()
        if clicked not in (btn_overwrite, btn_clear, btn_append):
            return   # İptal

        # Üzerine yaz: sadece aynı prog_no'ları sil
        if clicked == btn_overwrite:
            prog_nos = {p['prog_no'] for p in self._pieces}
            for pno in sorted(prog_nos):
                self._db.delete_record(pno)
        # Temizle: tablodaki TÜM kayıtları sil
        elif clicked == btn_clear:
            ok, err = self._db.clear_all_records()
            if not ok:
                QMessageBox.critical(self, 'Temizleme Hatası',
                    f'Kayıtlar silinemedi:\n{err}')
                return

        # Çerçeve BMP görsellerini üret (IMAGE klasörüne kaydet)
        frame_images = self._generate_frame_images()

        errors = []
        saved  = 0
        self._db.begin_batch()          # Excel sync'i sona ertele
        try:
            for p in self._pieces:
                rec = self._build_record(p, frame_images)
                ok, err_msg = self._db.insert_record(rec)
                if ok:
                    saved += 1
                else:
                    errors.append(f'Parça {p["prog_no"]}: {err_msg}')
        finally:
            self._db.end_batch()        # Tek seferlik Excel sync

        if errors:
            QMessageBox.warning(self, 'Kısmi Hata',
                f'{saved} kayıt başarılı, {len(errors)} hatalı:\n' + '\n'.join(errors[:5]))
        else:
            if clicked == btn_clear:
                mod_str = 'MDB temizlendi ve baştan yazıldı'
            elif clicked == btn_overwrite:
                mod_str = 'üzerine yazıldı'
            else:
                mod_str = 'eklendi'
            # Bir sonraki sipariş numarasını üret ve alanda göster
            next_no = st.next_order_no()
            self._ed_order_no.setText(next_no)
            QMessageBox.information(self, '✅ Kaydedildi',
                f'{saved} parça MDB\'ye {mod_str}.\n'
                f'Sonraki sipariş no: {next_no}')
            self._lbl_status.setText(f'{saved} parça MDB\'ye {mod_str}.')

    def _grab_saved_frame_images(self, image_dir: str) -> dict:
        """
        Her kayıtlı frame için preview widget'ını göster, QPixmap.grab() ile
        ekran görüntüsü al ve PNG olarak kaydet.
        Döndürür: {frame_index: dosya_yolu}
        """
        from PySide6.QtCore import QTimer
        import os
        os.makedirs(image_dir, exist_ok=True)
        result = {}

        # Mevcut nav pozisyonunu sakla
        orig_pos = self._nav_frame_pos

        for pos, f in enumerate(self._saved_frames):
            fidx = f.get('frame_idx', pos + 1)
            self._show_saved_frame(pos)
            # Qt'nin render etmesi için process events
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

            # Preview widget'ını yakala
            pixmap = self._preview.grab()
            fname  = f'frame_{fidx}.png'
            fpath  = os.path.join(image_dir, fname)
            pixmap.save(fpath, 'PNG')
            result[fidx] = fpath

        # Orijinal frame'i geri yükle
        if orig_pos >= 0:
            self._show_saved_frame(orig_pos)
            self._update_nav_buttons()

        return result

    def _generate_frame_images(self) -> dict:
        """Eski çağrılar için geriye dönük uyumluluk — MDB klasörüne kaydeder."""
        if self._db and getattr(self._db, 'db_path', None):
            target = os.path.join(os.path.dirname(self._db.db_path), 'IMAGE')
        else:
            # Dinamik yol: bu dosyanın bulunduğu klasör
            target = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'IMAGE')
        return self._generate_frame_images_to(target)

    def _generate_frame_images_to(self, image_dir: str) -> dict:
        """
        Her benzersiz frame_index için çerçeve görselini sadece Pillow ile
        çizer ve verilen image_dir klasörüne BMP olarak kaydeder.
        Matplotlib KULLANILMAZ — Qt önizleme canvas'ını etkilememek için.
        Döndürür: {frame_index: tam_dosya_yolu}
        """
        try:
            from PIL import Image as _PIL_Image, ImageDraw as _ImageDraw, ImageFont as _ImageFont
        except ImportError:
            print('[FRAME IMG] Pillow yüklü değil — pip install Pillow')
            return {}

        from collections import defaultdict

        cust_name = self._ed_customer_name.text().strip()
        safe_name = ''.join(
            c for c in cust_name if c.isalnum() or c in (' ', '_', '-')
        ).strip().replace(' ', '_')
        if not safe_name:
            safe_name = 'frame'

        os.makedirs(image_dir, exist_ok=True)

        # frame_index → parçalar
        frame_pieces = defaultdict(list)
        for p in self._pieces:
            frame_pieces[p.get('frame_index', 1)].append(p)

        # Rol renkleri (R,G,B) — fill, edge (profil rengine fallback)
        _ROLE_CLR_DEFAULT = {
            'kasa':       ((232, 232, 232), (80,  80,  80)),
            'kanat':      ((242, 242, 242), (60,  60,  60)),
            'kapi_kanat': ((238, 238, 238), (60,  60,  60)),
            'orta_kayit': ((216, 216, 216), (80,  80,  80)),
        }

        def _hex_to_rgb(h):
            h = h.lstrip('#')
            if len(h) == 6:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            return None

        def _get_clr(role, stock_code):
            """Profil rengini kütüphaneden al, yoksa rol varsayılanı döndür."""
            if self._library and stock_code:
                prof = cg.get_profile(self._library, stock_code)
                if prof:
                    clr_hex = prof.get('color') or prof.get('colour')
                    if clr_hex:
                        rgb = _hex_to_rgb(clr_hex)
                        if rgb:
                            edge = tuple(max(0, c - 40) for c in rgb)
                            return rgb, edge
            return _ROLE_CLR_DEFAULT.get(role, ((96, 96, 96), (60, 60, 60)))
        BG_CLR    = (255, 255, 255)
        DIM_CLR   = (26,  106, 138)
        LBL_CLR   = (17,  17,  17)
        EDGE_CLR  = (170, 170, 170)

        # Görsel boyutu (piksel)
        IMG_W, IMG_H = 900, 1050
        MARGIN_L = 60   # sol
        MARGIN_R = 110  # sağ (H boyut oku için)
        MARGIN_T = 50   # üst (başlık)
        MARGIN_B = 80   # alt (W boyut oku)

        # Varsayılan font (Pillow yerleşik)
        try:
            _font_lbl = _ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 18)
            _font_dim = _ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 20)
            _font_ttl = _ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 24)
        except Exception:
            _font_lbl = _ImageFont.load_default()
            _font_dim = _font_lbl
            _font_ttl = _font_lbl

        result = {}
        for frame_idx, pieces in sorted(frame_pieces.items()):
            try:
                # W ve H (mm)
                kasa_h = next((p for p in pieces
                               if p['role'] == 'kasa' and p['side'] in ('ALT', 'ÜST')), None)
                kasa_v = next((p for p in pieces
                               if p['role'] == 'kasa' and p['side'] in ('SOL', 'SAĞ')), None)
                first  = pieces[0]
                W = max((kasa_h or first).get('frame_x', 7000) / 10.0, 1.0)
                H = max((kasa_v or first).get('frame_y', 9000) / 10.0, 1.0)

                # Kerf / overlap
                tk = tn = 45.0
                for p in pieces:
                    prof = cg.get_profile(self._library, p['stock_code']) or {}
                    kerf = float(prof.get('kerf', 45))
                    ov   = float(prof.get('overlap_dxf', kerf))
                    if p['role'] == 'kasa':
                        tk = ov
                    elif p['role'] in ('kanat', 'kapi_kanat'):
                        tn = ov

                piece_map = {(p['role'], p['side']): p for p in pieces}

                # mm → piksel dönüşüm
                draw_w = IMG_W - MARGIN_L - MARGIN_R
                draw_h = IMG_H - MARGIN_T - MARGIN_B
                scale  = min(draw_w / W, draw_h / H)

                def mm2px(x_mm, y_mm, _s=scale, _H=H):
                    px = MARGIN_L + x_mm * _s
                    py = MARGIN_T + (_H - y_mm) * _s
                    return (int(px), int(py))

                def _miter_px(side, ox, ot, _W=W, _H=H):
                    if side == 'ALT':
                        pts = [(ox, ox), (_W-ox, ox),
                               (_W-ox-ot, ox+ot), (ox+ot, ox+ot)]
                    elif side == 'ÜST':
                        pts = [(ox+ot, _H-ox-ot), (_W-ox-ot, _H-ox-ot),
                               (_W-ox, _H-ox), (ox, _H-ox)]
                    elif side == 'SOL':
                        pts = [(ox, ox), (ox+ot, ox+ot),
                               (ox+ot, _H-ox-ot), (ox, _H-ox)]
                    elif side == 'SAĞ':
                        pts = [(_W-ox-ot, ox+ot), (_W-ox, ox),
                               (_W-ox, _H-ox), (_W-ox-ot, _H-ox-ot)]
                    else:
                        return []
                    return [mm2px(x, y) for x, y in pts]

                img  = _PIL_Image.new('RGB', (IMG_W, IMG_H), BG_CLR)
                draw = _ImageDraw.Draw(img)

                # Başlık
                title = f'Cerceve #{frame_idx}   W={int(W)} x H={int(H)} mm'
                draw.text((IMG_W // 2, 14), title, fill=LBL_CLR,
                          font=_font_ttl, anchor='mt')

                # Profil barları
                for role in ('kasa', 'kanat', 'kapi_kanat'):
                    for side in ('ALT', 'UST', 'SOL', 'SAG'):
                        # Türkçe karakter eşleştirmesi
                        side_tr = {'UST': 'ÜST', 'SAG': 'SAĞ'}.get(side, side)
                        key = (role, side_tr)
                        if key not in piece_map:
                            continue
                        p = piece_map[key]
                        fill_clr, _ = _get_clr(role, p.get('stock_code', ''))
                        ox, ot = (0, tk) if role == 'kasa' else (tk, tn)
                        pts = _miter_px(side_tr, ox, ot)
                        if not pts:
                            continue
                        draw.polygon(pts, fill=fill_clr, outline=EDGE_CLR)
                        cx = sum(x for x, y in pts) // len(pts)
                        cy = sum(y for x, y in pts) // len(pts)
                        rshort = {'kasa': 'K', 'kanat': 'Kn',
                                  'kapi_kanat': 'Kp'}.get(role, role)
                        lbl = f'{rshort} {side_tr}\n{p["length_mm"]} mm'
                        draw.text((cx, cy), lbl, fill=BG_CLR,
                                  font=_font_lbl, anchor='mm', align='center')

                # W boyut oku (alt)
                arrow_y = MARGIN_T + int(H * scale) + 30
                ax0, _  = mm2px(0, 0)
                axW, _  = mm2px(W, 0)
                draw.line([(ax0, arrow_y), (axW, arrow_y)], fill=DIM_CLR, width=2)
                draw.polygon([(ax0, arrow_y), (ax0+10, arrow_y-5), (ax0+10, arrow_y+5)],
                             fill=DIM_CLR)
                draw.polygon([(axW, arrow_y), (axW-10, arrow_y-5), (axW-10, arrow_y+5)],
                             fill=DIM_CLR)
                draw.text(((ax0+axW)//2, arrow_y + 16),
                          f'W = {int(W)} mm', fill=DIM_CLR,
                          font=_font_dim, anchor='mt')

                # H boyut oku (sağ)
                arrow_x = MARGIN_L + int(W * scale) + 30
                _, ay0  = mm2px(0, 0)
                _, ayH  = mm2px(0, H)
                draw.line([(arrow_x, ay0), (arrow_x, ayH)], fill=DIM_CLR, width=2)
                draw.polygon([(arrow_x, ay0), (arrow_x-5, ay0-10), (arrow_x+5, ay0-10)],
                             fill=DIM_CLR)
                draw.polygon([(arrow_x, ayH), (arrow_x-5, ayH+10), (arrow_x+5, ayH+10)],
                             fill=DIM_CLR)
                mid_y = (ay0 + ayH) // 2
                draw.text((arrow_x + 16, mid_y),
                          f'H = {int(H)} mm', fill=DIM_CLR,
                          font=_font_dim, anchor='lm')

                filename = f'{safe_name}_{frame_idx}.bmp'
                filepath = os.path.join(image_dir, filename)
                img.save(filepath, format='BMP')
                result[frame_idx] = filepath
                print(f'[FRAME IMG] Kaydedildi: {filepath}')

            except Exception as draw_err:
                import traceback
                print(f'[FRAME IMG] Hata frame={frame_idx}: {draw_err}')
                traceback.print_exc()

        print(f'[FRAME IMG] Toplam {len(result)} gorsel uretildi.')
        return result

    def _build_record(self, p: dict, frame_images=None) -> dict:
        """Parça dict'inden MDB kayıt dict'i oluşturur."""
        prof  = cg.get_profile(self._library, p['stock_code']) or {}
        ptype = prof.get('type', 'A')

        # Müşteri / sipariş
        cust_name = self._ed_customer_name.text().strip()
        cust_code = self._ed_customer_code.text().strip()
        order_no  = self._ed_order_no.text().strip()

        # Kesim açısı (×10 için MDB formatı: 45° → 450)
        # Orta kayıt: her zaman 90° → 900
        angle_x10 = 900 if p.get('role') == 'orta_kayit' else self._sp_angle.value() * 10

        # Çerçeve boyutları: _calculate_frame()'de hesaplanıp piece dict'ine
        # kaydedildi; yoksa dış W/H kullan (kaynak payı FRAME_X/Y'ye dahil değil).
        W = self._sp_w.value()
        H = self._sp_h.value()
        frame_x   = p.get('frame_x', W * 10)
        frame_y   = p.get('frame_y', H * 10)

        # Bar boyu (×10)
        total_size = self._sp_bar_len.value() * 10

        # Profil kesit boyutları (DXF'ten veya elle girilen, ×10)
        w_mm = int(prof.get('width_mm',  0))
        h_mm = int(prof.get('height_mm', 0))
        if (w_mm == 0 or h_mm == 0):
            # Kütüphanede 0 ise DXF'ten otomatik oku
            dxf_path = prof.get('dxf_file', '').strip()
            if dxf_path:
                try:
                    from dxf_loader import load_dxf as _load_dxf
                    segs = _load_dxf(dxf_path)
                    if segs:
                        xs = [pt[0] for seg in segs for pt in seg]
                        ys = [pt[1] for seg in segs for pt in seg]
                        w_mm = int(round(max(xs) - min(xs)))
                        h_mm = int(round(max(ys) - min(ys)))
                        prof['width_mm']  = w_mm
                        prof['height_mm'] = h_mm
                        # Profil kütüphanesine kalıcı kaydet
                        try:
                            cg.save_library(self._library)
                        except Exception:
                            pass
                except Exception:
                    pass
        width_x10  = w_mm * 10
        height_x10 = h_mm * 10

        # Robot konumu
        robot = self._get_robot_for_stock(p['stock_code'])

        # İşlem adları (piece dict'ten veya kütüphaneden)
        op_names = p.get('op_names') or cg.get_side_op_names(
            p['stock_code'], p['side'], self._library)
        # EXPLANATION1: rol + kenar kısaltması (max 10 kar)  ör: "Kasa ALT"
        exp1 = f'{_role_label(p["role"])} {p["side"]}'[:10]
        # EXPLANATION2: işlem adları "/" ile birleştirilmiş (max 24 kar)
        exp2 = '/'.join(op_names)[:24] if op_names else ''

        # POSE_NO: "çerçeve_no/rol_no"  →  ör: "1/1" (kasa), "1/2" (kanat)
        pose_no = f"{p.get('frame_index', 1)}/{p.get('role_index', 1)}"

        rec = {
            'PROGRAM_NO':       p['prog_no'],
            'CUSTOMER_CODE':    cust_code,
            'CUSTOMER_NAME':    cust_name,
            'STOCK_CODE':       p['stock_code'],
            'STOCK_NAME':       prof.get('name', ''),
            'ORDER_NO':         order_no,
            'EXPLANATION1':     exp1,
            'EXPLANATION2':     exp2,
            'LENGTH':           p['length_x10'],
            'INCH_MM':          0,
            'FRAME_X':          frame_x,
            'FRAME_Y':          frame_y,
            'POSE_NO':          pose_no,
            'TROLLEY':          p.get('trolley_no', 1),
            'UNIT':             p.get('unit_no',    1),
            'LEFT_ANGLE':       angle_x10,
            'RIGHT_ANGLE':      angle_x10,
            'SIDE':             SIDE_NUM.get(p['side'], 0),
            'CUTTED':           0,
            'BAR_NO':           p['bar_no'],
            'TOTAL_SIZE':       total_size,
            'PICE_NO':          p.get('pice_no', 1),
            'REMAINING_LENGTH': p.get('remaining_length_mm', 0) * 10,
            'WIDTH':            width_x10,
            'HEIGHT':           height_x10,
            'TYPE':             ptype,
            'COLOR_CODE':       prof.get('color_code', ''),
            'CODE':             p.get('generated_code', ''),
            'IMAGE':            (frame_images or {}).get(p.get('frame_index', 1), ''),
            'GRUP':             prof.get('dxf_file', ''),
            'ROBOT_Y':          robot['y'],
            'ROBOT_Z':          robot['z'],
            'ROBOT_VERTICAL':   robot['vertical'],
        }
        return rec

    def _try_connect_mdb_and_save(self):
        """MDB dosyası seç, bağlan ve kaydet işlemini tekrar dene."""
        path, _ = QFileDialog.getOpenFileName(
            self, 'MDB Dosyası Seç', '',
            'Access Veritabanı (*.mdb *.accdb);;Tüm Dosyalar (*)')
        if not path:
            return
        if not self._db:
            QMessageBox.warning(self, 'DB Nesnesi Yok',
                'Veritabanı nesnesi oluşturulmamış.\n'
                'Ana pencereden "💾 MDB Bağlan" ile bağlanın.')
            return
        try:
            self._db.connect(path)
            if getattr(self._db, 'connected', False):
                self._save_to_mdb()
            else:
                QMessageBox.warning(self, 'Bağlantı Başarısız',
                    f'{path}\n\nDosyaya bağlanılamadı.')
        except Exception as e:
            QMessageBox.critical(self, 'Bağlantı Hatası', str(e))

    # ─────────────────────────────────────────────────────────
    # Kütüphane erişimi (dışarıdan reload için)
    # ─────────────────────────────────────────────────────────

    def reload_library(self):
        self._reload_library()


# ─────────────────────────────────────────────────────────────────

def _role_label(role: str) -> str:
    return {'kasa': 'Kasa', 'kanat': 'Kanat', 'kapi_kanat': 'Kapı Kanat'}.get(role, role)


# ─────────────────────────────────────────────────────────────────────────────
# Makine Seçim Dialogu
# ─────────────────────────────────────────────────────────────────────────────

class _MachineSelectDialog(QDialog):
    """Ayarlarda seçili makineler arasından tek makine seçtir."""

    def __init__(self, machines: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Makine Seç')
        self.setMinimumWidth(300)
        self._machines = machines
        self._radio_group = []

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel('<b>Gönderilecek makineyi seçin:</b>'))

        self._btn_group = QButtonGroup(self)
        for i, m in enumerate(machines):
            rb = QRadioButton(m)
            if i == 0:
                rb.setChecked(True)
            self._btn_group.addButton(rb, i)
            lay.addWidget(rb)

        lay.addSpacing(8)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def selected_machine(self) -> str:
        idx = self._btn_group.checkedId()
        return self._machines[idx] if idx >= 0 else self._machines[0]


# ─────────────────────────────────────────────────────────────────────────────
# Kod Önizleme Dialogu (PIM / ALM)
# ─────────────────────────────────────────────────────────────────────────────

class _CodePreviewDialog(QDialog):
    """Üretilen kodları gösterir, kullanıcı onaylarsa CSV'ye gönderir."""

    def __init__(self, pieces: list, machine_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'Kod Önizleme — {machine_name}')
        self.resize(700, 500)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            f'<b>{machine_name}</b> için aşağıdaki kodlar CSV\'ye yazılacak.<br>'
            'Onaylıyorsanız <b>Gönder</b>\'e tıklayın.'))

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setFont(QFont('Courier New', 9))
        lines = []
        for p in pieces:
            code = p.get('generated_code', '')
            if code:
                role = _role_label(p.get('role', ''))
                side = p.get('side', '')
                pno  = p.get('prog_no', '')
                lines.append(f'── #{pno}  {role} {side} ──')
                lines.append(code)
                lines.append('')
        txt.setPlainText('\n'.join(lines) if lines else '(Kod yok)')
        lay.addWidget(txt)

        btns = QDialogButtonBox()
        btn_send   = btns.addButton('🚀  Gönder',  QDialogButtonBox.AcceptRole)
        btn_cancel = btns.addButton('İptal',        QDialogButtonBox.RejectRole)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)
