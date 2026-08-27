"""
ui/viewport_widget.py

DXF 2D / 3D Ekstrüzyon görüntüleyici.

2D mod  : DXF kesit görünümü (Y-Z düzlemi).
           • Sol-alt köşede kırmızı nokta = (0,0)
           • Tıklama ile Y,Z koordinatı alınır  (Qt native mousePressEvent)
           • Ayna / döndürme butonları çalışır

3D mod  : X ekseninde ekstrüde edilmiş katı model.
           • Matplotlib 3D eksenlerle interaktif döndürme
           • Koordinat eksenleri gösterilir

Tıklama notu:
  macOS'ta dialog içinde mpl_connect('button_press_event') güvenilmez.
  Bu nedenle Qt'nin native mousePressEvent'i override edildi; koordinat
  dönüşümü ax.transData.inverted() ile yapılıyor.
"""

import math
from typing import List, Tuple, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QLabel
from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtGui import QMouseEvent

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

from dxf_loader import Segment, get_bounds


class ViewportWidget(QWidget):
    """
    Sinyaller
    ---------
    point_selected(y, z)  : 2D modda tıklanan nokta koordinatları
    """
    point_selected = Signal(float, float)
    mouse_moved    = Signal(float, float)   # fare DXF üzerinde hareket ederken canlı Y/Z

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._segments: List[Segment] = []
        self._raw_segs: List[Segment] = []
        self._extrude_len: float = 0.0
        self._pick_mode: bool = False
        self._ax = None          # _draw_2d sonrası geçerli axes referansı

        # Matplotlib figür + canvas
        self._fig = Figure(facecolor='#1e1e2e')
        self._canvas = FigureCanvas(self._fig)

        # macOS dialog içinde de fare olayı alabilmesi için
        self._canvas.setFocusPolicy(Qt.ClickFocus)
        self._canvas.setMouseTracking(True)

        # Event filter: tıklama FigureCanvas'a gidiyor, parent'a değil.
        # installEventFilter ile canvas'ın mouse event'lerini biz yakalıyoruz.
        self._canvas.installEventFilter(self)

        # mpl_connect fallback (axes-içi tıklama doğrulama için)
        self._canvas.mpl_connect('button_press_event', self._mpl_on_click)

        # Fare hareketi → canlı koordinat gösterimi
        self._canvas.mpl_connect('motion_notify_event', self._mpl_on_move)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._canvas, 1)

        # ── Koordinat gösterge çubuğu (canvas'ın hemen altında) ──
        self._lbl_coords = QLabel('Y: –    Z: –')
        self._lbl_coords.setAlignment(Qt.AlignCenter)
        self._lbl_coords.setFixedHeight(22)
        self._lbl_coords.setStyleSheet(
            'background:#111120;'
            'color:#56cfe1;'
            'font-family:"Courier New",monospace;'
            'font-size:12px;'
            'font-weight:bold;'
            'padding:2px 8px;'
            'border-top:1px solid #2a2a45;'
            'letter-spacing:1px;'
        )
        lay.addWidget(self._lbl_coords)

        self._draw_empty()

    # ─────────────────────────────────────────────────────
    # Dışarıdan çağrılan API
    # ─────────────────────────────────────────────────────

    def load_segments(self, segs: List[Segment]):
        """Yeni DXF yüklendiğinde çağrılır."""
        self._raw_segs = list(segs)
        self._segments = list(segs)
        self._extrude_len = 0.0
        self.refresh()

    def set_segments(self, segs: List[Segment]):
        self._segments = list(segs)
        self.refresh()

    def set_extrude(self, length_mm: float):
        self._extrude_len = length_mm
        self.refresh()

    def set_pick_mode(self, active: bool):
        """Tıklama modunu açar / kapatır. Başlığı günceller."""
        self._pick_mode = active
        self._canvas.setCursor(Qt.CrossCursor if active else Qt.ArrowCursor)
        if active:
            self._canvas.setFocus(Qt.OtherFocusReason)
        # Başlığı pick moduna göre güncelle (sadece 2D iken)
        if self._ax is not None and self._extrude_len == 0:
            if active:
                self._ax.set_title(
                    '📍 Tıklayın — Y / Z koordinatı alınacak',
                    color='#f8c12f', fontsize=9, pad=4)
            else:
                self._ax.set_title(
                    '2D Kesit  |  Y-Z Düzlemi', color='#888', fontsize=9, pad=4)
            self._canvas.draw_idle()

    def refresh(self):
        self._fig.clear()
        self._ax = None
        if not self._segments:
            self._draw_empty()
        elif self._extrude_len > 0:
            self._draw_3d()
        else:
            self._draw_2d()
        self._canvas.draw_idle()

    # ─────────────────────────────────────────────────────
    # Event filter – canvas'a gelen tıklamayı yakala (macOS dialog fix)
    # ─────────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        """canvas.installEventFilter(self) ile kuruldu.
        Pick modu aktifken fare olayını tüketmeyiz; matplotlib kendi
        button_press_event'ini işlesin (_mpl_on_click).  Sadece focus
        veriyoruz ki matplotlib olayı alabilsin.
        """
        if (obj is self._canvas
                and event.type() == QEvent.MouseButtonPress
                and self._pick_mode):
            self._canvas.setFocus(Qt.MouseFocusReason)
        return False   # olayı canvas'a ilet — matplotlib işlesin

    # ─────────────────────────────────────────────────────
    # Qt native tıklama (ana yöntem – macOS dialog içinde çalışır)
    # ─────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if (self._pick_mode
                and self._ax is not None
                and self._extrude_len == 0
                and event.button() == Qt.LeftButton):
            try:
                # Canvas widget'in ViewportWidget içindeki konumuna çevir
                canvas_local = self._canvas.mapFrom(self, event.pos())
                x_px = float(canvas_local.x())
                y_px = float(canvas_local.y())

                # Matplotlib: (0,0) sol-ALT;  Qt: (0,0) sol-ÜST → flip
                y_mpl = float(self._canvas.height()) - y_px

                # Display (pixel) → data koordinatı
                pts = self._ax.transData.inverted().transform([[x_px, y_mpl]])
                y_data = round(float(pts[0][0]), 2)
                z_data = round(float(pts[0][1]), 2)

                self.set_pick_mode(False)
                self.point_selected.emit(y_data, z_data)
                event.accept()
                return
            except Exception:
                pass  # axes dışı tıklama vb.
        super().mousePressEvent(event)

    # ─────────────────────────────────────────────────────
    # Matplotlib fallback tıklama (axes içinde daha hassas kontrol)
    # ─────────────────────────────────────────────────────

    def _mpl_on_click(self, event):
        """Matplotlib button_press_event — xdata/ydata DPR'yi zaten çözer.
        emit + widget değişiklikleri QTimer ile ertelenir (matplotlib callback
        içinden doğrudan Qt widget'larına dokunmak donmaya yol açar).
        """
        if not self._pick_mode:
            return
        if event.inaxes is None or self._extrude_len > 0:
            return
        if event.xdata is None or event.ydata is None:
            return
        y = round(float(event.xdata), 2)
        z = round(float(event.ydata), 2)
        self.set_pick_mode(False)
        # Sinyal + olası resize işlemlerini bir sonraki event-loop turuna ertele
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.point_selected.emit(y, z))

    # ─────────────────────────────────────────────────────
    # Matplotlib fare hareketi → canlı koordinat
    # ─────────────────────────────────────────────────────

    def _mpl_on_move(self, event):
        """Fare DXF üzerinde gezinirken Y/Z'yi canlı günceller."""
        if self._ax is None or self._extrude_len > 0:
            return
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            # Axes dışına çıkıldı — son değeri sil
            self._lbl_coords.setText('Y: –    Z: –')
            self._lbl_coords.setStyleSheet(
                'background:#111120;color:#56cfe1;'
                'font-family:"Courier New",monospace;font-size:12px;font-weight:bold;'
                'padding:2px 8px;border-top:1px solid #2a2a45;letter-spacing:1px;')
            return
        y = round(float(event.xdata), 2)
        z = round(float(event.ydata), 2)
        self._lbl_coords.setText(f'Y:  {y:>8.2f} mm      Z:  {z:>8.2f} mm')
        # Pick modunda rengi sarıya çevir — "seçiliyor" hissi ver
        color = '#f8c12f' if self._pick_mode else '#56cfe1'
        self._lbl_coords.setStyleSheet(
            f'background:#111120;color:{color};'
            f'font-family:"Courier New",monospace;font-size:12px;font-weight:bold;'
            f'padding:2px 8px;border-top:1px solid #2a2a45;letter-spacing:1px;')
        self.mouse_moved.emit(y, z)

    # ─────────────────────────────────────────────────────
    # Çizim – 2D
    # ─────────────────────────────────────────────────────

    def _draw_empty(self):
        ax = self._fig.add_subplot(111)
        ax.set_facecolor('#2a2a3e')
        ax.text(0.5, 0.5, 'DXF dosyası yükleyin\n(Dosya → DXF Aç)',
                ha='center', va='center', fontsize=13,
                color='#a0a0c0', transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_edgecolor('#555')

    def _draw_2d(self):
        ax = self._fig.add_subplot(111)
        self._ax = ax          # koordinat dönüşümü için sakla
        ax.set_facecolor('#1a1a2e')
        ax.set_aspect('equal')

        for y1, z1, y2, z2 in self._segments:
            ax.plot([y1, y2], [z1, z2], color='#56cfe1', linewidth=1.0,
                    solid_capstyle='round')

        ax.plot(0, 0, 'o', color='#ff3333', markersize=4, zorder=10,
                label='YZ: 0')

        min_y, max_y, min_z, max_z = get_bounds(self._segments)
        margin_y = (max_y - min_y) * 0.08 + 1
        margin_z = (max_z - min_z) * 0.08 + 1
        ax.set_xlim(min_y - margin_y, max_y + margin_y)
        ax.set_ylim(min_z - margin_z, max_z + margin_z)
        ax.set_xlabel('Y  →', color='#aaa', fontsize=9)
        ax.set_ylabel('Z  ↑', color='#aaa', fontsize=9)
        ax.tick_params(colors='#888', labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor('#444')
        ax.grid(True, color='#333', linestyle='--', linewidth=0.4, alpha=0.7)

        title = ('📍 Tıklayın — Y / Z koordinatı alınacak'
                 if self._pick_mode else '2D Kesit  |  Y-Z Düzlemi')
        title_color = '#f8c12f' if self._pick_mode else '#888'
        ax.set_title(title, color=title_color, fontsize=9, pad=4)

        ax.legend(loc='lower right', fontsize=7, facecolor='#333',
                  labelcolor='white', framealpha=0.6)

    # ─────────────────────────────────────────────────────
    # Çizim – 3D
    # ─────────────────────────────────────────────────────

    def _draw_3d(self):
        ax = self._fig.add_subplot(111, projection='3d')
        ax.set_facecolor('#1a1a2e')
        self._fig.patch.set_facecolor('#1e1e2e')

        L = self._extrude_len
        segs = self._segments

        faces = []
        for y1, z1, y2, z2 in segs:
            face = [(0,y1,z1),(L,y1,z1),(L,y2,z2),(0,y2,z2)]
            faces.append(face)

        if faces:
            poly = Poly3DCollection(
                faces, alpha=0.25,
                facecolor='#56cfe1', edgecolor='#2a8faf', linewidth=0.3)
            ax.add_collection3d(poly)

        for y1, z1, y2, z2 in segs:
            ax.plot([0,0],[y1,y2],[z1,z2], color='#56cfe1', linewidth=0.8)
            ax.plot([L,L],[y1,y2],[z1,z2], color='#90e0ef', linewidth=0.8)

        min_y, max_y, min_z, max_z = get_bounds(segs)
        ay = (max_y-min_y)*0.25; az = (max_z-min_z)*0.25; ax_x = L*0.15
        ax.quiver(0,0,0,ax_x,0,0, color='red',     linewidth=1.5, arrow_length_ratio=0.15)
        ax.quiver(0,0,0,0,ay,0,   color='#44cc44',  linewidth=1.5, arrow_length_ratio=0.15)
        ax.quiver(0,0,0,0,0,az,   color='#4488ff',  linewidth=1.5, arrow_length_ratio=0.15)
        ax.text(ax_x*1.1,0,0,'X', color='red',     fontsize=8)
        ax.text(0,ay*1.1,0,'Y',   color='#44cc44', fontsize=8)
        ax.text(0,0,az*1.1,'Z',   color='#4488ff', fontsize=8)
        ax.scatter([0],[0],[0], c='red', s=40, zorder=10)

        ax.set_xlabel('X (Ekstrüzyon)', color='#ccc', fontsize=8, labelpad=4)
        ax.set_ylabel('Y', color='#ccc', fontsize=8, labelpad=4)
        ax.set_zlabel('Z', color='#ccc', fontsize=8, labelpad=4)
        ax.tick_params(colors='#888', labelsize=6)
        ax.set_title(f'3D Görünüm  |  Ekstrüzyon = {L:.1f} mm',
                     color='#ccc', fontsize=9, pad=6)

        ax.xaxis.pane.fill = False; ax.yaxis.pane.fill = False; ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor('#333')
        ax.yaxis.pane.set_edgecolor('#333')
        ax.zaxis.pane.set_edgecolor('#333')
        ax.grid(True, color='#333', linewidth=0.3)
