"""
pdf_report.py  — ProfiDO Sipariş PDF Raporu
"""

import os
import datetime
from collections import defaultdict
from typing import List, Dict

# ── ReportLab ──────────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Unicode font kaydı (Türkçe karakter desteği) ──────────────────────────────
def _register_fonts():
    import reportlab
    rl_fonts = os.path.join(os.path.dirname(reportlab.__file__), 'fonts')
    pairs = [
        ('Vera',    'Vera.ttf'),
        ('VeraBd',  'VeraBd.ttf'),
        ('VeraIt',  'VeraIt.ttf'),
        ('VeraBI',  'VeraBI.ttf'),
    ]
    for name, fname in pairs:
        path = os.path.join(rl_fonts, fname)
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:
                pass
    from reportlab.pdfbase.pdfmetrics import getRegisteredFontNames
    if 'Vera' in getRegisteredFontNames():
        return 'Vera', 'VeraBd'
    return 'Helvetica', 'Helvetica-Bold'

FONT_NORMAL, FONT_BOLD = _register_fonts()

# ── Renkler ────────────────────────────────────────────────────────────────────
C_KASA       = colors.HexColor('#3a8a8a')
C_KANAT      = colors.HexColor('#c8a030')
C_KAPI_KANAT = colors.HexColor('#8060b0')
C_OK         = colors.HexColor('#707070')
C_FIRE       = colors.HexColor('#e8e8e8')
C_KALAN      = colors.HexColor('#fff4c2')   # kalan parça sarımsı
C_BLADE      = colors.HexColor('#333333')
C_HEADER     = colors.HexColor('#1a3a5a')
C_ACCENT     = colors.HexColor('#2a7aaa')
C_TABLE_HDR  = colors.HexColor('#1a3a5a')
C_TABLE_ODD  = colors.HexColor('#f0f4f8')

ROLE_COLORS = {
    'kasa':       C_KASA,
    'kanat':      C_KANAT,
    'kapi_kanat': C_KAPI_KANAT,
    'orta_kayit': C_OK,
}

# ── Bar Diyagramı ─────────────────────────────────────────────────────────────

class BarDiagram(Flowable):
    BAR_H   = 14   # bar yüksekliği pt (gerçekçi ince görünüm)
    LABEL_H = 10   # alt etiket

    def __init__(self, bar_no, bar_len_mm, pieces, head_mm, tail_mm, blade_mm, width_pt):
        super().__init__()
        self.bar_no  = bar_no
        self.bar_len = bar_len_mm
        self.pieces  = pieces
        self.head_mm = head_mm
        self.tail_mm = tail_mm
        self.blade_mm= blade_mm
        self.w       = width_pt
        self.height  = self.BAR_H + self.LABEL_H + 8

    def _x(self, mm_val):
        return (mm_val / self.bar_len) * self.w

    def draw(self):
        c = self.canv
        yb = self.LABEL_H + 4   # bar alt y

        # ── Bar arka plan (fire) ──
        c.setFillColor(C_FIRE)
        c.setStrokeColor(colors.HexColor('#aaaaaa'))
        c.setLineWidth(0.5)
        c.rect(0, yb, self.w, self.BAR_H, fill=1, stroke=1)

        # ── Baş fire (koyu gri, çizgili) ──
        fw = self._x(self.head_mm)
        c.setFillColor(colors.HexColor('#bbbbbb'))
        c.rect(0, yb, fw, self.BAR_H, fill=1, stroke=0)

        # ── Parçalar ──
        x = fw
        for p in self.pieces:
            pw   = self._x(p['length_mm'])
            clr  = ROLE_COLORS.get(p.get('role', 'kasa'), C_KASA)
            ang  = p.get('angle', 45)

            if ang == 90:
                # 90° — düz dikdörtgen
                c.setFillColor(clr)
                c.setStrokeColor(colors.white)
                c.setLineWidth(0.6)
                c.rect(x, yb, pw, self.BAR_H, fill=1, stroke=1)
            else:
                # 45° — trapezoid
                notch = min(self.BAR_H * 0.7, pw * 0.35)
                pts   = [
                    x,               yb,
                    x + pw,          yb,
                    x + pw - notch,  yb + self.BAR_H,
                    x + notch,       yb + self.BAR_H,
                ]
                c.setFillColor(clr)
                c.setStrokeColor(colors.white)
                c.setLineWidth(0.6)
                p_path = c.beginPath()
                p_path.moveTo(pts[0], pts[1])
                p_path.lineTo(pts[2], pts[3])
                p_path.lineTo(pts[4], pts[5])
                p_path.lineTo(pts[6], pts[7])
                p_path.close()
                c.drawPath(p_path, fill=1, stroke=1)

            # Uzunluk etiketi (beyaz, orta)
            if pw > 14:
                lbl = str(p['length_mm'])
                c.setFillColor(colors.white)
                c.setFont(FONT_BOLD, 6)
                tw = c.stringWidth(lbl, FONT_BOLD, 6)
                cx = x + pw / 2 - tw / 2
                c.drawString(cx, yb + self.BAR_H / 2 - 3, lbl)

            # Testere payı
            x += pw
            bw = self._x(self.blade_mm)
            c.setFillColor(C_BLADE)
            c.rect(x, yb, bw, self.BAR_H, fill=1, stroke=0)
            x += bw

        # ── Kalan alan (sarımsı) ──
        if x < self.w:
            c.setFillColor(C_KALAN)
            c.setStrokeColor(colors.HexColor('#ccaa00'))
            c.setLineWidth(0.4)
            c.rect(x, yb, self.w - x, self.BAR_H, fill=1, stroke=1)
            # Kalan yazısı
            rem_mm = int((self.w - x) / self.w * self.bar_len)
            if (self.w - x) > 20:
                c.setFillColor(colors.HexColor('#665500'))
                c.setFont(FONT_BOLD, 6)
                lbl = f'{rem_mm} mm'
                tw = c.stringWidth(lbl, FONT_BOLD, 6)
                cx = x + (self.w - x) / 2 - tw / 2
                c.drawString(cx, yb + self.BAR_H / 2 - 3, lbl)

        # ── Dış çerçeve ──
        c.setFillColor(colors.Color(0, 0, 0, 0))
        c.setStrokeColor(colors.HexColor('#777777'))
        c.setLineWidth(0.8)
        c.rect(0, yb, self.w, self.BAR_H, fill=0, stroke=1)

        # ── Alt etiket ──
        used    = sum(p['length_mm'] for p in self.pieces)
        n       = len(self.pieces)
        kalan   = max(0, self.bar_len - self.head_mm - self.tail_mm - used
                      - n * self.blade_mm - max(0, n - 1) * 0)
        c.setFont(FONT_NORMAL, 6.5)
        c.setFillColor(colors.HexColor('#333333'))
        c.drawString(0, 1,
            f'Bar {self.bar_no}   |   {self.bar_len} mm   |   '
            f'{n} parça   |   Kalan: {kalan:.0f} mm')


# ── Rapor Üretici ─────────────────────────────────────────────────────────────

def generate_report(pieces, records, settings, out_dir,
                    customer_name, order_no, frame_images=None):
    os.makedirs(out_dir, exist_ok=True)
    from exporter import versioned_path, _safe
    fname    = f'Rapor_{_safe(customer_name)}_{_safe(order_no)}.pdf'
    pdf_path = versioned_path(out_dir, fname)

    bar_len  = settings.get('bar_len_mm',    6000)
    head_mm  = settings.get('head_waste_mm',   20)
    tail_mm  = settings.get('tail_waste_mm',   20)
    blade_mm = settings.get('blade_mm',         4)

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    W = A4[0] - 30*mm

    def S(txt, font=FONT_NORMAL, size=9, color=colors.black,
          align=TA_LEFT, bold=False):
        f = FONT_BOLD if bold else font
        return ParagraphStyle('_', fontName=f, fontSize=size,
                              textColor=color, alignment=align)

    story = []

    # ── Başlık ─────────────────────────────────────────────────────────────────
    hdr_style = ParagraphStyle('hdr', fontName=FONT_BOLD, fontSize=13,
                               textColor=colors.white, alignment=TA_LEFT)
    hdr2_style= ParagraphStyle('hdr2', fontName=FONT_BOLD, fontSize=10,
                               textColor=colors.white, alignment=TA_RIGHT)
    hdr_data  = [[Paragraph('ProfiDO', hdr_style),
                  Paragraph('KESİM RAPORU', hdr2_style)]]
    hdr_tbl   = Table(hdr_data, colWidths=[W*0.65, W*0.35])
    hdr_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), C_HEADER),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0),(-1,-1), 7),
        ('BOTTOMPADDING', (0,0),(-1,-1), 7),
        ('LEFTPADDING',   (0,0),(-1,-1), 10),
        ('RIGHTPADDING',  (0,0),(-1,-1), 10),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Müşteri bilgileri ──────────────────────────────────────────────────────
    today = datetime.date.today().strftime('%d.%m.%Y')
    lbl_s = ParagraphStyle('lbl', fontName=FONT_BOLD, fontSize=8,
                           textColor=C_HEADER)
    val_s = ParagraphStyle('val', fontName=FONT_NORMAL, fontSize=8)
    info_data = [
        [Paragraph('Müşteri Adı:', lbl_s), Paragraph(customer_name, val_s),
         Paragraph('Sipariş No:',  lbl_s), Paragraph(order_no, val_s)],
        [Paragraph('Tarih:', lbl_s),       Paragraph(today, val_s),
         Paragraph('Toplam Parça:', lbl_s),Paragraph(str(len(pieces)), val_s)],
    ]
    info_tbl = Table(info_data, colWidths=[W*0.18, W*0.32, W*0.18, W*0.32])
    info_tbl.setStyle(TableStyle([
        ('FONTSIZE',  (0,0),(-1,-1), 8),
        ('BACKGROUND',(0,0),(-1,-1), colors.HexColor('#f0f4f8')),
        ('BOX',       (0,0),(-1,-1), 0.5, colors.HexColor('#aaaaaa')),
        ('GRID',      (0,0),(-1,-1), 0.3, colors.HexColor('#cccccc')),
        ('TOPPADDING',(0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 3*mm))

    # ── Profil özeti (rol bazında bar ve parça sayısı) ─────────────────────────
    role_map = {
        'kasa':       'Kasa',
        'kanat':      'Kanat',
        'kapi_kanat': 'Kapı Kanat',
        'orta_kayit': 'Orta Kayıt',
    }
    # Her rol için: parça sayısı ve kullandığı bar sayısı
    role_counts  = defaultdict(int)   # role → parça adedi
    role_bars    = defaultdict(set)   # role → bar_no set
    for p in pieces:
        role = p.get('role', 'kasa')
        role_counts[role] += 1
        role_bars[role].add(p.get('bar_no', 1))

    if role_counts:
        sum_h = ParagraphStyle('sh', fontName=FONT_BOLD, fontSize=7,
                               textColor=colors.white, alignment=TA_CENTER)
        sum_v = ParagraphStyle('sv', fontName=FONT_NORMAL, fontSize=7,
                               alignment=TA_CENTER)
        sum_l = ParagraphStyle('sl', fontName=FONT_BOLD, fontSize=7,
                               textColor=C_HEADER)
        sum_hdr = [Paragraph('Profil Tipi', sum_h),
                   Paragraph('Parça Adedi', sum_h),
                   Paragraph('Bar Adedi',   sum_h)]
        sum_rows = [sum_hdr]
        for role, label in role_map.items():
            if role in role_counts:
                sum_rows.append([
                    Paragraph(label, sum_l),
                    Paragraph(str(role_counts[role]), sum_v),
                    Paragraph(str(len(role_bars[role])), sum_v),
                ])
        sum_tbl = Table(sum_rows,
                        colWidths=[W*0.35, W*0.20, W*0.20],
                        hAlign='LEFT')
        sum_sty = [
            ('BACKGROUND',    (0,0),(-1,0), C_TABLE_HDR),
            ('FONTSIZE',      (0,0),(-1,-1), 7),
            ('FONTNAME',      (0,0),(-1,-1), FONT_NORMAL),
            ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
            ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',    (0,0),(-1,-1), 3),
            ('BOTTOMPADDING', (0,0),(-1,-1), 3),
            ('GRID',          (0,0),(-1,-1), 0.3, colors.HexColor('#cccccc')),
            ('BOX',           (0,0),(-1,-1), 0.5, colors.HexColor('#888888')),
        ]
        for i in range(1, len(sum_rows)):
            bg = C_TABLE_ODD if i % 2 == 1 else colors.white
            sum_sty.append(('BACKGROUND', (0,i),(-1,i), bg))
        sum_tbl.setStyle(TableStyle(sum_sty))
        story.append(sum_tbl)

    story.append(Spacer(1, 4*mm))

    # ── Çerçeve görselleri ─────────────────────────────────────────────────────
    imgs = []
    if frame_images:
        max_col_w = W / 5 - 2*mm   # 5 görsel yan yana sığar
        max_col_h = 48*mm          # kompakt yükseklik
        for fidx, img_path in sorted(frame_images.items()):
            if img_path and os.path.exists(img_path):
                try:
                    from PIL import Image as _PI
                    with _PI.open(img_path) as pil_img:
                        pw, ph = pil_img.size
                    ratio  = min(max_col_w/pw, max_col_h/ph)
                    imgs.append(RLImage(img_path, width=pw*ratio, height=ph*ratio))
                except Exception:
                    pass

    if imgs:
        sec_s = ParagraphStyle('sec', fontName=FONT_BOLD, fontSize=9,
                               textColor=C_ACCENT, spaceBefore=2, spaceAfter=3)
        story.append(Paragraph('Çerçeve Görselleri', sec_s))
        chunk = 5   # 5 görsel yan yana
        for i in range(0, len(imgs), chunk):
            row = imgs[i:i+chunk]
            while len(row) < chunk:
                row.append('')
            col_w = W / 5
            t = Table([row], colWidths=[col_w]*chunk)
            t.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),
                                   ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
            story.append(t)
        story.append(Spacer(1, 3*mm))

    # ── Bar Diyagramları ───────────────────────────────────────────────────────
    sec_s = ParagraphStyle('sec', fontName=FONT_BOLD, fontSize=9,
                           textColor=C_ACCENT, spaceBefore=2, spaceAfter=4)
    story.append(Paragraph('Bar Paketleme Diyagramı', sec_s))

    # Açı bilgisini rec'ten al
    rec_map = {r.get('PROGRAM_NO'): r for r in records}
    for p in pieces:
        rec = rec_map.get(p.get('prog_no'), {})
        try:
            ang = int(rec.get('LEFT_ANGLE', 450)) // 10
        except Exception:
            ang = 45
        p['angle'] = ang

    bar_groups = defaultdict(list)
    for p in pieces:
        bar_groups[p.get('bar_no', 1)].append(p)

    for bn in sorted(bar_groups):
        bp = sorted(bar_groups[bn], key=lambda x: x.get('prog_no', 0))
        diag = BarDiagram(bn, bar_len, bp, head_mm, tail_mm, blade_mm, W)
        story.append(KeepTogether([diag, Spacer(1, 2*mm)]))

    story.append(Spacer(1, 4*mm))

    # ── Kesim Listesi Tablosu ─────────────────────────────────────────────────
    story.append(Paragraph('Kesim Listesi', sec_s))

    th_s = ParagraphStyle('th', fontName=FONT_BOLD, fontSize=7,
                          textColor=colors.white, alignment=TA_CENTER)
    hdr_row = [
        Paragraph('No',          th_s),
        Paragraph('Stok Kodu',   th_s),
        Paragraph('Stok Adı',    th_s),
        Paragraph('Uzunluk(mm)', th_s),
        Paragraph('Sol Açı',     th_s),
        Paragraph('Sağ Açı',     th_s),
        Paragraph('Bar',         th_s),
        Paragraph('Adet',        th_s),
    ]
    cw = [W*0.07, W*0.12, W*0.27, W*0.13, W*0.10, W*0.10, W*0.10, W*0.11]
    tbl_data = [hdr_row]
    sty = [
        ('BACKGROUND', (0,0),(-1,0), C_TABLE_HDR),
        ('FONTSIZE',   (0,0),(-1,-1), 7),
        ('FONTNAME',   (0,0),(-1,-1), FONT_NORMAL),
        ('ALIGN',      (0,0),(-1,-1), 'CENTER'),
        ('VALIGN',     (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0),(-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1), 3),
        ('GRID',       (0,0),(-1,-1), 0.3, colors.HexColor('#cccccc')),
        ('BOX',        (0,0),(-1,-1), 0.5, colors.HexColor('#888888')),
    ]

    # Gruplama: rol + stok + uzunluk + açılar
    # Not: rol de anahtara dahil edilir ki sıralama, profil özeti ile aynı
    # mantıksal sıraya (Kasa → Kanat/Kapı Kanat → Orta Kayıt) göre yapılsın.
    # Salt stok koduna göre alfabetik sıralama (eski davranış) "101" < "200"
    # olduğundan Kanat'ı Kasa'nın önüne alıyor ve uzun listelerde Kasa
    # satırları sayfalarca aşağıda kalıp "raporda görünmüyor" izlenimi
    # veriyordu.
    _ROLE_ORDER = {'kasa': 0, 'kanat': 1, 'kapi_kanat': 1, 'orta_kayit': 2}
    groups = defaultdict(lambda: {'count':0,'piece':None,'bar':1,'la':45,'ra':45})
    for p in pieces:
        rec = rec_map.get(p.get('prog_no'), {})
        try: la = int(rec.get('LEFT_ANGLE',  450)) // 10
        except: la = 45
        try: ra = int(rec.get('RIGHT_ANGLE', 450)) // 10
        except: ra = 45
        role = p.get('role', 'kasa')
        key = (role, p.get('stock_code',''), p.get('length_mm', 0), la, ra)
        g = groups[key]
        g['count'] += 1
        if g['piece'] is None:
            g['piece'] = p
            g['bar']   = p.get('bar_no', 1)
            g['la']    = la
            g['ra']    = ra

    def _sort_key(item):
        (role, stock_code, length_mm, la, ra), _g = item
        return (_ROLE_ORDER.get(role, 9), stock_code, length_mm, la, ra)

    for i, (key, g) in enumerate(sorted(groups.items(), key=_sort_key)):
        p   = g['piece']
        bg  = C_TABLE_ODD if i % 2 == 0 else colors.white
        sty.append(('BACKGROUND', (0, i+1), (-1, i+1), bg))
        tbl_data.append([
            str(i+1),
            key[1],
            p.get('stock_name','') if p else '',
            str(key[2]),
            f'{g["la"]}°',
            f'{g["ra"]}°',
            str(g['bar']),
            str(g['count']),
        ])

    tbl = Table(tbl_data, colWidths=cw, repeatRows=1)
    tbl.setStyle(TableStyle(sty))
    story.append(tbl)

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width=W, thickness=0.5,
                            color=colors.HexColor('#cccccc')))
    ft_s = ParagraphStyle('ft', fontName=FONT_NORMAL, fontSize=7,
                          textColor=colors.HexColor('#888888'),
                          alignment=TA_CENTER, spaceBefore=2)
    story.append(Paragraph(
        f'ProfiDO  |  {today}  |  {order_no}', ft_s))

    doc.build(story)
    return pdf_path
