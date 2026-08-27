"""
p_code_icons.py

P1–P7 CNC işlem kodları için küçük ikon/pixmap üretir.
QPainter ile çizilir — harici kaynak gerekmez.

Her ikon: 52×36 piksel, koyu arka plan, açık renk şekil.
"""

from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QFont, QIcon
from PySide6.QtCore import Qt, QRect, QPoint, QPointF, QRectF

# ──────────────────────────────────────────────
# Renk paleti (ana uygulama temasıyla uyumlu)
# ──────────────────────────────────────────────
_BG      = QColor('#1e1e2e')   # arka plan (şeffaf bırakıyoruz)
_BORDER  = QColor('#556070')   # profil/kontur çizgisi
_FILL    = QColor('#2a3a50')   # boşaltılmış alan dolgusu
_SHAPE   = QColor('#56cfe1')   # operasyon şekli (cyan)
_DRILL   = QColor('#a8e6a3')   # delik / matkap (yeşil)
_MILL    = QColor('#ffd166')   # freze kanalı (sarı)

W, H = 52, 36   # ikon boyutu (piksel)


def _new_pm() -> QPixmap:
    pm = QPixmap(W, H)
    pm.fill(Qt.transparent)
    return pm


def _draw_profile_bar(p: QPainter, color: QColor = _BORDER):
    """Altta profil kesitini temsil eden ince bar."""
    p.setPen(QPen(color, 1))
    p.setBrush(QBrush(QColor(40, 50, 65)))
    p.drawRect(2, H - 10, W - 4, 8)


# ──────────────────────────────────────────────
# P1  Dikdörtgen Freze Kanalı
#     Uzun yatay kanal (L×W×D)
# ──────────────────────────────────────────────
def _p1() -> QPixmap:
    pm = _new_pm()
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    _draw_profile_bar(p)
    # Üstten kanal açılmış — geniş ve orta derinlikte
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(_MILL))
    p.drawRect(6, 8, W - 12, H - 20)
    # kenar çizgileri
    p.setPen(QPen(_MILL.lighter(130), 1))
    p.drawLine(6, 8, 6, H - 12)
    p.drawLine(W - 6, 8, W - 6, H - 12)
    p.drawLine(6, H - 12, W - 6, H - 12)
    # ok yukarı (freze yönü)
    p.setPen(QPen(QColor('#fff'), 1))
    mx = W // 2
    p.drawLine(mx, 4, mx, 10)
    p.drawLine(mx - 3, 7, mx, 4)
    p.drawLine(mx + 3, 7, mx, 4)
    p.end()
    return pm


# ──────────────────────────────────────────────
# P2  Oval Freze Kanalı
#     Oval (stadium) şekil
# ──────────────────────────────────────────────
def _p2() -> QPixmap:
    pm = _new_pm()
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    _draw_profile_bar(p)
    # Oval kanal
    r = 7
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(_MILL))
    p.drawRoundedRect(5, 7, W - 10, H - 19, r, r)
    p.setPen(QPen(_MILL.lighter(140), 1))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(5, 7, W - 10, H - 19, r, r)
    p.end()
    return pm


# ──────────────────────────────────────────────
# P3  Su Tahliye Deliği
#     Dar uzun dikdörtgen, yuvarlak uçlu
# ──────────────────────────────────────────────
def _p3() -> QPixmap:
    pm = _new_pm()
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    _draw_profile_bar(p)
    # Dar uzun slot — su tahliye
    slot_h = 6
    sy = (H - 10 - slot_h) // 2
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(_DRILL))
    p.drawRoundedRect(4, sy, W - 8, slot_h, 3, 3)
    # damlacık sembolü
    p.setPen(QPen(QColor('#fff'), 1))
    drop_x, drop_y = W // 2, 4
    p.drawLine(drop_x, drop_y, drop_x, sy - 1)
    p.end()
    return pm


# ──────────────────────────────────────────────
# P4  Kilit Deliği: küçük yuva (sol) + büyük daire (sağ)
#     Resim 1: büyük daire sağda, küçük yuvarlatılmış yuva solda
# ──────────────────────────────────────────────
def _p4() -> QPixmap:
    pm = _new_pm()
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    cy  = H // 2       # merkez y = 18
    # Büyük daire (SAĞ)
    cx2, r2 = 37, 13
    # Küçük daire / yuva (SOL)
    cx1, r1 = 13, 6

    # — Dolgu (küçük daire + bağlantı dikdörtgeni + büyük daire) —
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(_FILL))
    p.drawEllipse(QPointF(cx1, cy), r1, r1)
    p.drawRect(QRectF(cx1, cy - r1, cx2 - cx1, r1 * 2))
    p.drawEllipse(QPointF(cx2, cy), r2, r2)

    # — Kontur —
    pen = QPen(_SHAPE, 1.5)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    # Sol küçük dairenin sol yarısı (180° yay)
    p.drawArc(QRectF(cx1 - r1, cy - r1, r1 * 2, r1 * 2), 90 * 16, 180 * 16)
    # Üst bağlantı çizgisi
    p.drawLine(QPointF(cx1, cy - r1), QPointF(cx2, cy - r1))
    # Sağ büyük daire (tam)
    p.drawEllipse(QPointF(cx2, cy), r2, r2)
    # Alt bağlantı çizgisi
    p.drawLine(QPointF(cx1, cy + r1), QPointF(cx2, cy + r1))

    # — Büyük daire merkezinden çapraz kesik çizgiler —
    dash_pen = QPen(QColor('#aaa'), 1, Qt.DashLine)
    dash_pen.setDashPattern([3, 3])
    p.setPen(dash_pen)
    # Yatay: şeklin tüm genişliği boyunca
    p.drawLine(QPointF(cx1 - r1 - 1, cy), QPointF(cx2 + r2 + 1, cy))
    # Dikey: büyük daire merkezi
    p.drawLine(QPointF(cx2, cy - r2 - 1), QPointF(cx2, cy + r2 + 1))

    p.end()
    return pm


# ──────────────────────────────────────────────
# P5  Kilit Deliği: büyük daire (sol) + uzun yuva (sağ)
#     Resim 2: büyük daire solda, küçük yuvarlatılmış yuva sağda
# ──────────────────────────────────────────────
def _p5() -> QPixmap:
    pm = _new_pm()
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    cy  = H // 2       # 18
    # Büyük daire (SOL)
    cx1, r1 = 15, 13
    # Küçük daire / yuva (SAĞ)
    cx2, r2 = 39, 6

    # — Dolgu —
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(_FILL))
    p.drawEllipse(QPointF(cx1, cy), r1, r1)
    p.drawRect(QRectF(cx1, cy - r2, cx2 - cx1, r2 * 2))
    p.drawEllipse(QPointF(cx2, cy), r2, r2)

    # — Kontur —
    pen = QPen(_SHAPE, 1.5)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    # Sol büyük daire (tam)
    p.drawEllipse(QPointF(cx1, cy), r1, r1)
    # Üst bağlantı çizgisi
    p.drawLine(QPointF(cx1, cy - r2), QPointF(cx2, cy - r2))
    # Sağ küçük dairenin sağ yarısı (180° yay)
    p.drawArc(QRectF(cx2 - r2, cy - r2, r2 * 2, r2 * 2), -90 * 16, 180 * 16)
    # Alt bağlantı çizgisi
    p.drawLine(QPointF(cx1, cy + r2), QPointF(cx2, cy + r2))

    # — Büyük daire merkezinden çapraz kesik çizgiler —
    dash_pen = QPen(QColor('#aaa'), 1, Qt.DashLine)
    dash_pen.setDashPattern([3, 3])
    p.setPen(dash_pen)
    # Yatay: şeklin tüm genişliği boyunca
    p.drawLine(QPointF(cx1 - r1 - 1, cy), QPointF(cx2 + r2 + 1, cy))
    # Dikey: büyük daire merkezi
    p.drawLine(QPointF(cx1, cy - r1 - 1), QPointF(cx1, cy + r1 + 1))

    p.end()
    return pm


# ──────────────────────────────────────────────
# P6  Dairesel Delik
#     Çap (C) ve derinlik (D) olan daire
# ──────────────────────────────────────────────
def _p6() -> QPixmap:
    pm = _new_pm()
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    _draw_profile_bar(p)
    cx, cy, r = W // 2, (H - 10) // 2, 9
    # dış halka
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(_FILL))
    p.drawEllipse(QPoint(cx, cy), r, r)
    p.setPen(QPen(_DRILL, 2))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPoint(cx, cy), r, r)
    # merkez nokta
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(_DRILL))
    p.drawEllipse(QPoint(cx, cy), 2, 2)
    # çap oku
    p.setPen(QPen(_DRILL.lighter(120), 1))
    p.drawLine(cx - r + 2, cy, cx + r - 2, cy)
    p.end()
    return pm


# ──────────────────────────────────────────────
# P7  Nokta Deliği
#     Tek nokta matkap
# ──────────────────────────────────────────────
def _p7() -> QPixmap:
    pm = _new_pm()
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    _draw_profile_bar(p)
    cx, cy = W // 2, (H - 10) // 2
    # matkap oku
    p.setPen(QPen(_DRILL, 1, Qt.DashLine))
    p.drawLine(cx, 2, cx, cy - 3)
    # Matkap ucu (üçgen)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(_DRILL))
    pts = [QPoint(cx, cy + 5), QPoint(cx - 5, cy - 3), QPoint(cx + 5, cy - 3)]
    from PySide6.QtGui import QPolygon
    p.drawPolygon(QPolygon(pts))
    # dış halka (delik çevresinde)
    p.setPen(QPen(_DRILL.darker(120), 1))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPoint(cx, cy), 6, 6)
    p.end()
    return pm


# ──────────────────────────────────────────────
# Ortak erişim
# ──────────────────────────────────────────────
_DRAW_FN = {
    'P1': _p1, 'P2': _p2, 'P3': _p3, 'P4': _p4,
    'P5': _p5, 'P6': _p6, 'P7': _p7,
}

_CACHE: dict = {}


def get_p_code_pixmap(p_code: str) -> QPixmap:
    """P kodu için QPixmap döndürür. Önbellek kullanır."""
    if p_code not in _CACHE:
        fn = _DRAW_FN.get(p_code)
        _CACHE[p_code] = fn() if fn else _new_pm()
    return _CACHE[p_code]


def get_p_code_icon(p_code: str) -> QIcon:
    """P kodu için QIcon döndürür (QComboBox / QPushButton için)."""
    return QIcon(get_p_code_pixmap(p_code))
