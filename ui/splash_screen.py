"""
ui/splash_screen.py  —  Animasyonlu Açılış Ekranı

Akıcı partikül animasyonu, neon glow efektleri, profesyonel tipografi.
"""

import math, random, os, sys, datetime
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore    import Qt, QTimer, QPointF, Signal, QRectF
from PySide6.QtGui     import (
    QPainter, QColor, QLinearGradient, QRadialGradient,
    QFont, QPen, QBrush, QPolygonF, QPixmap, QPainterPath
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from version import __version__ as APP_VERSION

# ── Fotoğraf / logo yolları ────────────────────────────────
# Program klasörünün altındaki dosyalar
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTO_PATH = os.path.join(_BASE, 'ProfiDO_IM.png')
LOGO_PATH  = os.path.join(_BASE, 'yilmaz_logo.png')

random.seed(42)


class Particle:
    """Yüzen ışık noktası."""
    def __init__(self, W, H):
        self.reset(W, H)

    def reset(self, W, H):
        self.x   = random.uniform(0, W)
        self.y   = random.uniform(0, H)
        self.vx  = random.uniform(-0.4, 0.4)
        self.vy  = random.uniform(-0.6, -0.1)
        self.r   = random.uniform(1.2, 3.0)
        self.alpha = random.randint(60, 180)
        self.color = random.choice(['#f8c12f', '#5588ff', '#44ccff', '#ffffff'])
        self.life  = random.uniform(0, 1.0)
        self.decay = random.uniform(0.004, 0.012)

    def update(self, W, H):
        self.x    += self.vx
        self.y    += self.vy
        self.life -= self.decay
        if self.life <= 0 or self.y < -10 or self.x < -10 or self.x > W + 10:
            self.reset(W, H)
            self.y = H + 5


PROG_NAME = 'ProfiDO'
PROG_SUB  = 'Art of The Profiling'
COMPANY   = ''
CONTACT   = 'vasfisahin@yilmazmachine.com.tr'


class SplashScreen(QWidget):
    closed = Signal()                    # geriye dönük uyumluluk
    closed_with_action = Signal(bool)    # True=kapat, False=devam et

    def __init__(self, exit_mode: bool = False):
        super().__init__()
        self._exit_mode = exit_mode   # True: 'Programı Kapat' butonu göster
        # Ekran boyutlarını al — kiosk modu: menü çubuğu dahil TAM fiziksel ekran
        screen = QApplication.primaryScreen().geometry()
        self.W = screen.width()
        self.H = screen.height()

        self._tick_count = 0
        self._fade_alpha = 0    # fade-in
        self._ready      = False  # fade tamamlandı mı?
        self._progress   = 0    # ilerleme çubuğu (0-100)
        self._hosgeldiniz_len = 0   # typewriter karakter sayısı
        # exit_mode'da anında tam görünüm
        if exit_mode:
            self._fade_alpha = 255
            self._ready      = True
            self._progress   = 100
            self._hosgeldiniz_len = len('HOŞ GELDİNİZ')

        # Partiküller (daha fazla, tam ekrana dağıt)
        self._particles = [Particle(self.W, self.H) for _ in range(90)]

        # Akan çizgiler
        self._lines = [
            {'y': random.uniform(0, self.H),
             'speed': random.uniform(0.5, 2.5),
             'width': random.uniform(60, 300),
             'x': random.uniform(-300, self.W),
             'alpha': random.randint(12, 45)}
            for _ in range(28)
        ]

        self.setWindowFlags(
            Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setGeometry(screen)   # Tam ekran
        self.setWindowState(Qt.WindowFullScreen)   # Kiosk modu — menü çubuğu/dock da kapansın

        self._timer = QTimer(self)
        self._timer.setInterval(16)   # ~60fps
        self._timer.timeout.connect(self._update)
        self._timer.start()

        # ── exit_mode butonları (Qt native — her zaman tıklanabilir) ──
        if exit_mode:
            from PySide6.QtWidgets import QPushButton as _QPB
            btn_continue = _QPB('▶  Programa Devam Et', self)
            btn_continue.setGeometry(int(self.W // 2 - 220), int(self.H - 110), 200, 44)
            btn_continue.setStyleSheet(
                'QPushButton{background:#1a4a1a;color:#80ff80;border:1px solid #44aa44;'
                'border-radius:8px;font-size:15px;font-weight:bold;}'
                'QPushButton:hover{background:#2a6a2a;}')
            btn_continue.clicked.connect(lambda: self._finish(quit_app=False))
            btn_continue.show()

            btn_quit = _QPB('✕  Programı Kapat', self)
            btn_quit.setGeometry(int(self.W // 2 + 20), int(self.H - 110), 200, 44)
            btn_quit.setStyleSheet(
                'QPushButton{background:#4a1a1a;color:#ff8080;border:1px solid #aa4444;'
                'border-radius:8px;font-size:15px;font-weight:bold;}'
                'QPushButton:hover{background:#6a2a2a;}')
            btn_quit.clicked.connect(lambda: self._finish(quit_app=True))
            btn_quit.show()

    def _update(self):
        self._tick_count += 1

        # Fade-in ilk 40 frame
        self._fade_alpha = min(255, self._fade_alpha + 7)
        if self._fade_alpha >= 255:
            self._ready = True

        # İlerleme çubuğu — 300 frame içinde 0→100
        self._progress = min(100, int(self._tick_count * 100 / 300))

        # Typewriter: her 4 frame'de bir yeni karakter
        HOŞ = 'HOŞ GELDİNİZ'
        if self._tick_count % 4 == 0:
            self._hosgeldiniz_len = min(len(HOŞ), self._hosgeldiniz_len + 1)

        for pt in self._particles:
            pt.update(self.W, self.H)

        for ln in self._lines:
            ln['x'] += ln['speed']
            if ln['x'] > self.W + 300:
                ln['x'] = -random.uniform(60, 300)
                ln['y'] = random.uniform(0, self.H)

        self.update()

    def _finish(self, quit_app: bool = False):
        self._timer.stop()
        self.hide()
        self.closed.emit()              # geriye dönük
        self.closed_with_action.emit(quit_app)

    def mousePressEvent(self, event):
        """exit_mode'da tıklama yok; normal modda devam et."""
        if self._exit_mode:
            return   # exit_mode'da sadece butonlar çalışır
        if self._fade_alpha > 100:
            self._finish(quit_app=False)

    # ── Çizim ────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        W, H = self.width(), self.height()
        fa = self._fade_alpha

        # ── 1. Arka plan ─────────────────────────────────
        bg = QLinearGradient(0, 0, W, H)
        bg.setColorAt(0.0, QColor(4,   4,  18))
        bg.setColorAt(0.4, QColor(8,   8,  30))
        bg.setColorAt(1.0, QColor(2,   2,  12))
        p.fillRect(0, 0, W, H, QBrush(bg))

        # ── 2. Akan yatay çizgiler (profil izleri) ───────
        p.save()
        for ln in self._lines:
            c = QColor('#3366ff')
            c.setAlpha(int(ln['alpha'] * fa / 255))
            pen = QPen(c, 0.7)
            p.setPen(pen)
            x = int(ln['x'])
            y = int(ln['y'])
            p.drawLine(x, y, x + int(ln['width']), y)
        p.restore()

        # ── 3. Partiküller ───────────────────────────────
        p.save()
        for pt in self._particles:
            c = QColor(pt.color)
            alpha = int(pt.alpha * pt.life * fa / 255)
            c.setAlpha(max(0, min(255, alpha)))
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            r = pt.r
            p.drawEllipse(QPointF(pt.x, pt.y), r, r)

            # Glow
            glow = QColor(pt.color)
            glow.setAlpha(max(0, int(alpha * 0.25)))
            p.setBrush(glow)
            p.drawEllipse(QPointF(pt.x, pt.y), r * 2.5, r * 2.5)
        p.restore()

        # ── 4. Sol parlama ───────────────────────────────
        t   = self._tick_count * 0.018
        gx1 = 160 + 20 * math.sin(t)
        gy1 = 200 + 15 * math.cos(t * 0.7)
        rg1 = QRadialGradient(QPointF(gx1, gy1), 220)
        rg1.setColorAt(0, QColor(20, 60, 200, int(55 * fa / 255)))
        rg1.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, W, H, QBrush(rg1))

        # ── 5. Sağ alt parlama ───────────────────────────
        gx2 = W - 180 + 15 * math.cos(t * 0.9)
        gy2 = H - 140 + 12 * math.sin(t * 1.1)
        rg2 = QRadialGradient(QPointF(gx2, gy2), 200)
        rg2.setColorAt(0, QColor(200, 140, 0, int(40 * fa / 255)))
        rg2.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, W, H, QBrush(rg2))

        # ── 6. İçerik merkezi ────────────────────────────
        # Sol bölge %42 genişlikte
        left_w  = int(W * 0.42)
        # Logo: sol bölgenin yarısından küçük VE ekran yüksekliğinin %28'i kadar
        logo_r = min(left_w // 2 - 24, int(H * 0.28), 240)
        cx = left_w // 2
        cy = H // 2
        self._draw_photo_hex(p, cx, cy, logo_r, fa)

        # ── 7. Dikey ayırıcı ─────────────────────────────
        ax = left_w
        lg = QLinearGradient(0, H * 0.12, 0, H * 0.88)
        lg.setColorAt(0,   QColor(255, 255, 255, 0))
        lg.setColorAt(0.5, QColor(255, 255, 255, int(50 * fa / 255)))
        lg.setColorAt(1,   QColor(255, 255, 255, 0))
        p.setPen(QPen(QBrush(lg), 1))
        p.drawLine(ax, int(H * 0.12), ax, int(H * 0.88))

        # ── 8. Metinler ──────────────────────────────────
        tx = ax + 52
        self._draw_texts(p, tx, W, H, fa)

        # ── 9. Alt şerit + logo + imza ────────────────────
        self._draw_bottom(p, W, H, fa)
        self._draw_logo(p, W, H, fa)
        self._draw_signature(p, W, H, fa)

        # ── 10. "Devam etmek için tıklayın" ipucu ────────
        if self._ready:
            f_hint = QFont('Arial', 11)
            p.setFont(f_hint)
            pulse = int(120 + 80 * abs(math.sin(self._tick_count * 0.04)))
            hc = QColor(255, 255, 255, int(pulse * fa / 255))
            p.setPen(hc)
            hint = '▶  Devam etmek için tıklayın'
            fm = p.fontMetrics()
            hw = fm.horizontalAdvance(hint)
            p.drawText((W - hw) // 2, H - 22, hint)

    def _draw_photo_hex(self, p, cx, cy, r, fa):
        """Fotoğrafı altıgen içine kırparak çizer."""
        # Altıgen path
        path = QPainterPath()
        first = True
        for i in range(6):
            a = math.radians(60 * i - 30)
            x = cx + r * math.cos(a)
            y = cy + r * math.sin(a)
            if first:
                path.moveTo(x, y); first = False
            else:
                path.lineTo(x, y)
        path.closeSubpath()

        # Fotoğrafı yükle
        pix = QPixmap(PHOTO_PATH)
        if not pix.isNull():
            p.save()
            p.setClipPath(path)

            # Fotoğrafı altıgene SIĞACAK şekilde ölçekle.
            # PNG içinde alt kısımda yazı var → resmi yukarı kaydır.
            pw, ph = pix.width(), pix.height()
            size  = r * 1.6
            scale = min(size / pw, size / ph)
            nw, nh = pw * scale, ph * scale
            ox = cx - nw / 2
            # Yukarı kaydır: alt yazı hex'in dışında kalır
            oy = cy - nh * 0.62

            p.setOpacity(fa / 255)
            p.drawPixmap(int(ox), int(oy), int(nw), int(nh), pix)
            p.setOpacity(1.0)
            p.restore()

            # ── Beyaz arka planı ezdirmek için güçlü renk katmanları ──
            p.save()
            p.setClipPath(path)

            # 1. Koyu lacivert katman — beyazı bastır
            p.fillPath(path, QBrush(QColor(4, 8, 30, int(195 * fa / 255))))

            # 2. Üstten mavi radyal parlaklık
            rg_top = QRadialGradient(QPointF(cx, cy - r * 0.3), r * 1.1)
            rg_top.setColorAt(0.0, QColor(20, 60, 160, int(90 * fa / 255)))
            rg_top.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillPath(path, QBrush(rg_top))

            # 3. Altın alt parlama
            rg_bot = QRadialGradient(QPointF(cx, cy + r * 0.5), r * 0.8)
            rg_bot.setColorAt(0.0, QColor(180, 120, 0, int(45 * fa / 255)))
            rg_bot.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillPath(path, QBrush(rg_bot))

            p.restore()

            # ── Logo'yu karanlık arka plan üzerine tekrar çiz (blend) ──
            p.save()
            p.setClipPath(path)
            p.setOpacity(0.55 * fa / 255)
            p.drawPixmap(int(ox), int(oy), int(nw), int(nh), pix)
            p.setOpacity(1.0)
            p.restore()
        else:
            # Fotoğraf yoksa eski altıgen logo çiz
            self._draw_hex_logo(p, cx, cy, r, fa)
            return

        # Neon kenar
        t = self._tick_count * 0.012
        glow_alpha = int((130 + 60 * math.sin(t * 3)) * fa / 255)
        p.setPen(QPen(QColor(80, 140, 255, glow_alpha), 2.8))
        p.setBrush(Qt.NoBrush)
        pts = [QPointF(cx + r * math.cos(math.radians(60*i - 30)),
                       cy + r * math.sin(math.radians(60*i - 30)))
               for i in range(6)]
        p.drawPolygon(QPolygonF(pts))

        # Dönen dış halkalar
        p.save()
        p.translate(cx, cy)
        p.rotate(self._tick_count * 0.6)
        for i in range(10):
            a = 2 * math.pi * i / 10
            x = int((r + 14) * math.cos(a))
            y = int((r + 14) * math.sin(a))
            bright = 255 if i % 2 == 0 else 100
            c = QColor(248, 193, bright // 2, int(150 * fa / 255))
            p.setPen(Qt.NoPen); p.setBrush(c)
            dot = 2.5 if i % 2 == 0 else 1.5
            p.drawEllipse(QPointF(x, y), dot, dot)
        p.restore()

    def _draw_hex_logo(self, p, cx, cy, r, fa):
        """Neon kenarlı altıgen + dönen halkalar + profil sembolü."""
        t = self._tick_count * 0.012

        # Dış dönen halka (ince, noktalı)
        p.save()
        p.translate(cx, cy)
        p.rotate(self._tick_count * 0.8)
        dash_n = 12
        for i in range(dash_n):
            a = 2 * math.pi * i / dash_n
            x = int((r + 12) * math.cos(a))
            y = int((r + 12) * math.sin(a))
            alpha = int(180 * fa / 255)
            bright = 255 if i % 3 == 0 else 90
            c = QColor(bright, int(bright * 0.7), 0, alpha)
            p.setPen(Qt.NoPen); p.setBrush(c)
            dot = 2.5 if i % 3 == 0 else 1.2
            p.drawEllipse(QPointF(x, y), dot, dot)
        p.restore()

        # İç dönen halka (mavi, ters)
        p.save()
        p.translate(cx, cy)
        p.rotate(-self._tick_count * 0.5)
        for i in range(8):
            a = 2 * math.pi * i / 8
            x = int((r - 2) * math.cos(a))
            y = int((r - 2) * math.sin(a))
            c = QColor('#5588ff')
            c.setAlpha(int(120 * fa / 255))
            p.setPen(Qt.NoPen); p.setBrush(c)
            p.drawEllipse(QPointF(x, y), 2, 2)
        p.restore()

        # Altıgen dolgu
        pts = [QPointF(cx + r * math.cos(math.radians(60*i - 30)),
                       cy + r * math.sin(math.radians(60*i - 30)))
               for i in range(6)]
        poly = QPolygonF(pts)
        rg = QRadialGradient(QPointF(cx, cy - 15), r)
        rg.setColorAt(0.0, QColor(18, 35, 120, int(220 * fa / 255)))
        rg.setColorAt(1.0, QColor(4,  8,  30, int(240 * fa / 255)))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(rg))
        p.drawPolygon(poly)

        # Neon kenar
        glow_alpha = int((150 + 50 * math.sin(t * 3)) * fa / 255)
        pen_glow = QPen(QColor(80, 130, 255, glow_alpha), 2.5)
        p.setPen(pen_glow)
        p.setBrush(Qt.NoBrush)
        p.drawPolygon(poly)

        # Profil kesit sembolü (3 yatay çizgi + dikey bağlantılar)
        pen_icon = QPen(QColor('#f8c12f'), 2.2)
        pen_icon.setCapStyle(Qt.RoundCap)
        p.setPen(pen_icon)
        for dy in (-13, 0, 13):
            p.drawLine(cx - 24, cy + dy, cx + 24, cy + dy)
        p.setPen(QPen(QColor('#f8c12f'), 1.4))
        p.drawLine(cx - 24, cy - 13, cx - 24, cy + 13)
        p.drawLine(cx + 24, cy - 13, cx + 24, cy + 13)

    def _draw_texts(self, p, tx, W, H, fa):
        """Sağ panel metin bloğu — dikeyde ortalanmış, HOŞ GELDİNİZ typewriter."""
        t = self._tick_count * 0.02

        block_h = 310
        # HOŞ GELDİNİZ'i bloğun üst kısmından biraz daha yukarı al
        y0 = (H - block_h) // 2 - 40

        # ── HOŞ GELDİNİZ — typewriter + büyük + hareketli ──
        HOŞ_FULL = 'HOŞ GELDİNİZ'
        displayed = HOŞ_FULL[:self._hosgeldiniz_len]
        if displayed:
            f1 = QFont('Arial', 26, QFont.Black)
            f1.setLetterSpacing(QFont.AbsoluteSpacing, 8)
            p.setFont(f1)
            fm1 = p.fontMetrics()
            hw1 = fm1.horizontalAdvance(displayed)
            text_h = fm1.height()

            # Parlayan arka plan kutusu — pulse animasyonu
            pulse_bg = int(45 + 35 * abs(math.sin(self._tick_count * 0.05)))
            box_c = QColor(20, 60, 200, pulse_bg)
            p.setPen(Qt.NoPen)
            p.setBrush(box_c)
            p.drawRoundedRect(tx - 10, y0 - text_h + 4, hw1 + 20, text_h + 8, 5, 5)

            # Sol kenar çizgisi (altın)
            bar_pulse = int(180 + 75 * abs(math.sin(self._tick_count * 0.07)))
            p.setPen(QPen(QColor(248, 193, 47, bar_pulse), 3))
            p.drawLine(tx - 10, y0 - text_h + 4, tx - 10, y0 + 8)

            # Metin glow (mavi)
            glow_a = int(140 * fa / 255)
            for dx, dy in ((2,0),(-2,0),(0,2),(0,-2)):
                p.setPen(QColor(80, 140, 255, glow_a))
                p.drawText(tx + dx, y0 + dy, displayed)

            # Metin ana — parlak beyaz
            p.setPen(QColor(240, 248, 255, fa))
            p.drawText(tx, y0, displayed)

            # Yanıp sönen imleç
            if self._hosgeldiniz_len < len(HOŞ_FULL) or (self._tick_count // 18) % 2 == 0:
                cur_c = QColor(248, 193, 47, int(240 * fa / 255))
                p.setPen(cur_c)
                p.drawText(tx + hw1 + 3, y0, '|')

            # ── Hareketli degrade çizgi — HOŞ GELDİNİZ'in hemen altı ──
            line_y = y0 + 14
            # Kayan ofset ile animasyon
            offset = (self._tick_count * 3) % 400
            lg2 = QLinearGradient(tx - offset, 0, tx - offset + 400, 0)
            lg2.setColorAt(0.0, QColor(0, 0, 0, 0))
            lg2.setColorAt(0.3, QColor(248, 193, 47, int(fa * 0.9)))
            lg2.setColorAt(0.6, QColor(100, 180, 255, int(fa * 0.7)))
            lg2.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(QPen(QBrush(lg2), 1.5))
            p.drawLine(tx - 10, line_y, tx + 420, line_y)

        # ── ProfiDO — büyük, shimmer ──
        f2 = QFont('Arial', 48, QFont.Black)
        p.setFont(f2)
        shimmer = int(240 + 15 * math.sin(t * 2))
        c_shadow = QColor(20, 50, 160, int(fa * 0.45))
        p.setPen(c_shadow)
        p.drawText(tx + 2, y0 + 66, PROG_NAME)
        c2 = QColor(shimmer, shimmer, shimmer, fa)
        p.setPen(c2)
        p.drawText(tx, y0 + 64, PROG_NAME)

        # ── PROFİL KESİM SİSTEMİ ──
        f3 = QFont('Arial', 15, QFont.DemiBold)
        f3.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        p.setFont(f3)
        gg = QLinearGradient(tx, 0, tx + 420, 0)
        gg.setColorAt(0, QColor(248, 193, 47, fa))
        gg.setColorAt(1, QColor(220, 140, 0, fa))
        p.setPen(QPen(QBrush(gg), 1))
        p.drawText(tx, y0 + 94, PROG_SUB)

        # Özellik listesi
        features = [
            ('Akıllı Üretim',           'Profil kütüphanesinden otomatik çerçeve oluşturma'),
            ('DXF Profil Görüntüleyici','2D/3D profil kesit ekranı & ekstrüzyon'),
            ('Otomatik P Kodu Üretimi', 'Kanat / Kasa tüm işlemleri otomatik'),
            ('Toplu Kesim & MDB',       'Bar optimizasyonu & Excel/MDB çıktısı'),
        ]
        f4 = QFont('Arial', 11, QFont.Bold)
        f5 = QFont('Arial', 9)
        fy = y0 + 132
        for title, desc in features:
            p.setPen(Qt.NoPen)
            bc = QColor('#f8c12f'); bc.setAlpha(fa)
            p.setBrush(bc)
            p.drawEllipse(tx, fy - 7, 6, 6)
            p.setFont(f4)
            tc = QColor('#e0e0ff'); tc.setAlpha(fa)
            p.setPen(tc)
            p.drawText(tx + 14, fy, title)
            p.setFont(f5)
            dc = QColor('#8080aa'); dc.setAlpha(fa)
            p.setPen(dc)
            p.drawText(tx + 14, fy + 15, desc)
            fy += 42

    def _draw_logo(self, p, W, H, fa):
        """Ekranın sağ üst köşesi — Yılmaz logosu."""
        logo_pix = QPixmap(LOGO_PATH)
        if logo_pix.isNull():
            return
        margin_x = 36
        margin_y = 24
        logo_h   = 44
        logo_w   = int(logo_h * logo_pix.width() / max(1, logo_pix.height()))
        logo_x   = W - margin_x - logo_w
        logo_y   = margin_y
        p.save()
        p.setOpacity(fa / 255)
        p.drawPixmap(logo_x, logo_y, logo_w, logo_h, logo_pix)
        p.setOpacity(1.0)
        p.restore()

    def _draw_signature(self, p, W, H, fa):
        """Ekranın sol alt köşesi — el yazısı imza."""
        from PySide6.QtGui import QFontDatabase
        cursive_fonts = [
            'Snell Roundhand', 'Apple Chancery', 'Bradley Hand ITC',
            'Brush Script MT', 'Noteworthy', 'Zapf Chancery',
            'Segoe Script', 'Comic Sans MS',
        ]
        avail = QFontDatabase.families()
        cf = next((f for f in cursive_fonts if f in avail), 'Arial')

        NAME = 'V.Şahin'
        f_sign = QFont(cf, 14); f_sign.setItalic(True)

        margin_x   = 36   # alt ilerleme çubuğuyla aynı sol boşluk
        bottom_pad = 58   # alt ilerleme çubuğunun (H-44) üstünde kalsın

        sig_x = margin_x
        sig_y = H - bottom_pad   # imza taban çizgisi

        # Gölge
        p.setFont(f_sign)
        p.setPen(QColor(0, 0, 0, int(140 * fa / 255)))
        p.drawText(sig_x + 1, sig_y + 1, NAME)

        # Metin — soluk gri, italik
        p.setPen(QColor(170, 160, 140, int(fa * 0.65)))
        p.drawText(sig_x, sig_y, NAME)

    def _draw_bottom(self, p, W, H, fa):
        """Alt ilerleme çubuğu ve versiyon."""
        bar_y = H - 44
        bar_x, bar_w, bar_h = 36, W - 72, 5

        # Arka plan track
        p.setPen(Qt.NoPen)
        tc = QColor(255, 255, 255, int(18 * fa / 255))
        p.setBrush(tc)
        p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 2.5, 2.5)

        # Fill
        fill = int(bar_w * self._progress / 100)
        if fill > 0:
            pg = QLinearGradient(bar_x, 0, bar_x + fill, 0)
            pg.setColorAt(0.0, QColor(30, 80, 220, fa))
            pg.setColorAt(0.5, QColor(100, 180, 255, fa))
            pg.setColorAt(1.0, QColor(248, 193, 47, fa))
            p.setBrush(QBrush(pg))
            p.drawRoundedRect(bar_x, bar_y, fill, bar_h, 2.5, 2.5)

            # Parlak uç
            glow_x = bar_x + fill - 6
            rg = QRadialGradient(QPointF(glow_x, bar_y + bar_h / 2), 10)
            rg.setColorAt(0, QColor(255, 230, 100, int(180 * fa / 255)))
            rg.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(rg))
            p.drawRect(glow_x - 10, bar_y - 5, 20, bar_h + 10)

        # Versiyon (sol)
        f_pct = QFont('Arial', 9)
        p.setFont(f_pct)
        pc = QColor('#3355aa'); pc.setAlpha(fa)
        p.setPen(pc)
        p.drawText(bar_x, bar_y + 18, f'{COMPANY}  ·  {PROG_NAME}')

        # Versiyon (sağ) — açık renk, koyu arka planda net okunsun
        f_ver = QFont('Arial', 10, QFont.DemiBold)
        p.setFont(f_ver)
        vc = QColor('#c7d2f5'); vc.setAlpha(fa)
        p.setPen(vc)
        yil = datetime.date.today().year
        ver_text = f'v{APP_VERSION}  ·  {yil}'
        fm_v = p.fontMetrics()
        vw = fm_v.horizontalAdvance(ver_text)
        p.drawText(W - vw - 36, bar_y + 18, ver_text)

        # Alt çerçeve çizgisi
        blg = QLinearGradient(0, 0, W, 0)
        blg.setColorAt(0.0, QColor(0, 0, 0, 0))
        blg.setColorAt(0.3, QColor(248, 193, 47, int(120 * fa / 255)))
        blg.setColorAt(0.7, QColor(80, 130, 255, int(100 * fa / 255)))
        blg.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(QPen(QBrush(blg), 1))
        p.drawLine(0, H - 1, W, H - 1)
