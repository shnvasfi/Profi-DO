"""
dxf_loader.py

ezdxf kütüphanesiyle DXF dosyasını okur.
Tüm çizim varlıklarını (LINE, ARC, CIRCLE, LWPOLYLINE, POLYLINE, SPLINE)
2D segment listesine çevirir: [(y1,z1, y2,z2), ...]

Koordinat sistemi:
  DXF'teki X → programdaki Y  (yatay, soldan sağa)
  DXF'teki Y → programdaki Z  (dikey, aşağıdan yukarı)
  Ekstrüzyon yönü → X ekseninde

Sıfır noktası:
  Segmentler yüklendikten sonra, sol-alt köşe (min_y, min_z) sıfır noktasına
  taşınır; böylece kırmızı nokta her zaman (0, 0) olur.
"""

import math
from typing import List, Tuple

# Segment tipi: (y1, z1, y2, z2)
Segment = Tuple[float, float, float, float]


def load_dxf(filepath: str, arc_segments: int = 36) -> List[Segment]:
    """
    DXF dosyasını okur ve normalize edilmiş segment listesi döndürür.
    Önce ezdxf ile dener; başarısız olursa (HEADER eksik, minimal DXF gibi)
    kendi el-parser'ı ile okur.
    arc_segments: ark/çember yaklaşımı için kullanılacak segment sayısı
    """
    try:
        import ezdxf
        doc = ezdxf.readfile(filepath)
        msp = doc.modelspace()
        segs: List[Segment] = []
        for entity in msp:
            t = entity.dxftype()
            try:
                if t == 'LINE':
                    segs.extend(_line(entity))
                elif t == 'ARC':
                    segs.extend(_arc(entity, arc_segments))
                elif t == 'CIRCLE':
                    segs.extend(_circle(entity, arc_segments))
                elif t == 'LWPOLYLINE':
                    segs.extend(_lwpolyline(entity, arc_segments))
                elif t == 'POLYLINE':
                    segs.extend(_polyline(entity))
                elif t == 'SPLINE':
                    segs.extend(_spline(entity, arc_segments))
                elif t == 'ELLIPSE':
                    segs.extend(_ellipse(entity, arc_segments))
            except Exception:
                continue
        if segs:
            return _normalize(segs)
        # Boş gelirse fallback'e düş
    except Exception:
        pass  # ezdxf başarısız — manuel parser'a geç

    # ── Manuel fallback: HEADER'sız minimal DXF ──────────────────
    return _load_dxf_manual(filepath, arc_segments)


def _load_dxf_manual(filepath: str, arc_segments: int = 36) -> List[Segment]:
    """
    Sadece ENTITIES section içeren minimal DXF dosyalarını okur.
    Group-code çiftlerini satır satır okuyarak LINE ve ARC varlıklarını çıkarır.
    """
    segs: List[Segment] = []

    # Dosyayı group-code / value çiftleri olarak oku
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.readlines()
    except Exception:
        return segs

    # Satırları (code, value) çiftlerine dönüştür
    pairs: List[Tuple[int, str]] = []
    i = 0
    while i + 1 < len(raw):
        try:
            code = int(raw[i].strip())
            value = raw[i + 1].strip()
            pairs.append((code, value))
        except ValueError:
            pass
        i += 2

    # Entity blokları çıkar
    idx = 0
    n = len(pairs)
    while idx < n:
        code, value = pairs[idx]
        if code == 0 and value == 'LINE':
            # LINE: 10=x1, 20=y1, 11=x2, 21=y2
            props: dict = {}
            idx += 1
            while idx < n and pairs[idx][0] != 0:
                props[pairs[idx][0]] = pairs[idx][1]
                idx += 1
            try:
                x1 = float(props.get(10, 0))
                y1 = float(props.get(20, 0))
                x2 = float(props.get(11, 0))
                y2 = float(props.get(21, 0))
                if (x1, y1) != (x2, y2):
                    segs.append((x1, y1, x2, y2))
            except Exception:
                pass

        elif code == 0 and value == 'ARC':
            # ARC: 10=cx, 20=cy, 40=r, 50=start_angle, 51=end_angle
            props = {}
            idx += 1
            while idx < n and pairs[idx][0] != 0:
                props[pairs[idx][0]] = pairs[idx][1]
                idx += 1
            try:
                cx  = float(props.get(10, 0))
                cy  = float(props.get(20, 0))
                r   = float(props.get(40, 1))
                sa  = math.radians(float(props.get(50, 0)))
                ea  = math.radians(float(props.get(51, 360)))
                if ea <= sa:
                    ea += 2 * math.pi
                angles = [sa + (ea - sa) * i / arc_segments
                          for i in range(arc_segments + 1)]
                pts = [(cx + r * math.cos(a), cy + r * math.sin(a))
                       for a in angles]
                for i in range(len(pts) - 1):
                    segs.append((pts[i][0], pts[i][1],
                                 pts[i+1][0], pts[i+1][1]))
            except Exception:
                pass

        elif code == 0 and value == 'CIRCLE':
            props = {}
            idx += 1
            while idx < n and pairs[idx][0] != 0:
                props[pairs[idx][0]] = pairs[idx][1]
                idx += 1
            try:
                cx = float(props.get(10, 0))
                cy = float(props.get(20, 0))
                r  = float(props.get(40, 1))
                angles = [2 * math.pi * i / arc_segments
                          for i in range(arc_segments + 1)]
                pts = [(cx + r * math.cos(a), cy + r * math.sin(a))
                       for a in angles]
                for i in range(len(pts) - 1):
                    segs.append((pts[i][0], pts[i][1],
                                 pts[i+1][0], pts[i+1][1]))
            except Exception:
                pass

        else:
            idx += 1

    if not segs:
        return segs
    return _normalize(segs)


# ─────────────────────────────────────────────────────────
# Varlık dönüştürücüler
# ─────────────────────────────────────────────────────────

def _pt(v) -> Tuple[float, float]:
    """ezdxf vertex'ten (y, z) çıkar (DXF X→Y, DXF Y→Z)."""
    return float(v.x), float(v.y)


def _line(e) -> List[Segment]:
    y1, z1 = _pt(e.dxf.start)
    y2, z2 = _pt(e.dxf.end)
    if (y1, z1) == (y2, z2):
        return []
    return [(y1, z1, y2, z2)]


def _arc(e, n: int) -> List[Segment]:
    cx, cy = _pt(e.dxf.center)
    r = float(e.dxf.radius)
    sa = math.radians(float(e.dxf.start_angle))
    ea = math.radians(float(e.dxf.end_angle))
    if ea < sa:
        ea += 2 * math.pi
    angles = [sa + (ea - sa) * i / n for i in range(n + 1)]
    pts = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in angles]
    return [(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]) for i in range(len(pts)-1)]


def _circle(e, n: int) -> List[Segment]:
    cx, cy = _pt(e.dxf.center)
    r = float(e.dxf.radius)
    angles = [2 * math.pi * i / n for i in range(n + 1)]
    pts = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in angles]
    return [(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]) for i in range(len(pts)-1)]


def _lwpolyline(e, n: int) -> List[Segment]:
    """LWPOLYLINE — yay parçaları dahil."""
    segs = []
    pts_raw = list(e.get_points(format='xyb'))  # x, y, bulge
    if not pts_raw:
        return segs
    closed = e.is_closed
    if closed:
        pts_raw = pts_raw + [pts_raw[0]]

    for i in range(len(pts_raw) - 1):
        x1, y1, bulge = pts_raw[i]
        x2, y2, _     = pts_raw[i + 1]
        if abs(bulge) < 1e-9:
            segs.append((x1, y1, x2, y2))
        else:
            segs.extend(_bulge_arc(x1, y1, x2, y2, bulge, n))
    return segs


def _bulge_arc(x1, y1, x2, y2, bulge, n) -> List[Segment]:
    """DXF bulge değerinden ark segment listesi üretir."""
    d = math.hypot(x2 - x1, y2 - y1)
    r = d * (1 + bulge**2) / (4 * abs(bulge))
    a = 4 * math.atan(abs(bulge))
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    s = math.copysign(1, bulge)
    px, py = -s * dy / d, s * dx / d
    f = math.sqrt(max(r**2 - (d/2)**2, 0))
    cx, cy = mx + px * f, my + py * f
    sa = math.atan2(y1 - cy, x1 - cx)
    ea = sa + s * a
    angles = [sa + (ea - sa) * i / n for i in range(n + 1)]
    pts = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in angles]
    return [(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]) for i in range(len(pts)-1)]


def _polyline(e) -> List[Segment]:
    segs = []
    verts = list(e.vertices)
    for i in range(len(verts) - 1):
        x1, y1 = float(verts[i].dxf.location.x), float(verts[i].dxf.location.y)
        x2, y2 = float(verts[i+1].dxf.location.x), float(verts[i+1].dxf.location.y)
        segs.append((x1, y1, x2, y2))
    return segs


def _spline(e, n: int) -> List[Segment]:
    try:
        pts = list(e.flattening(0.01))
        segs = []
        for i in range(len(pts) - 1):
            segs.append((float(pts[i].x), float(pts[i].y),
                         float(pts[i+1].x), float(pts[i+1].y)))
        return segs
    except Exception:
        return []


def _ellipse(e, n: int) -> List[Segment]:
    try:
        pts = list(e.flattening(0.01))
        segs = []
        for i in range(len(pts) - 1):
            segs.append((float(pts[i].x), float(pts[i].y),
                         float(pts[i+1].x), float(pts[i+1].y)))
        return segs
    except Exception:
        return []


# ─────────────────────────────────────────────────────────
# Normalleştirme: sol-alt köşe → (0, 0)
# ─────────────────────────────────────────────────────────

def _normalize(segs: List[Segment]) -> List[Segment]:
    """En küçük Y ve Z değerini bulup tüm koordinatları kaydırır."""
    ys = [s[0] for s in segs] + [s[2] for s in segs]
    zs = [s[1] for s in segs] + [s[3] for s in segs]
    min_y, min_z = min(ys), min(zs)
    return [(y1 - min_y, z1 - min_z, y2 - min_y, z2 - min_z) for y1, z1, y2, z2 in segs]


# ─────────────────────────────────────────────────────────
# Dönüşüm yardımcıları (ayna, döndürme)
# ─────────────────────────────────────────────────────────

def apply_transform(
    segs: List[Segment],
    mirror_y: bool = False,
    mirror_z: bool = False,
    rotate_deg: float = 0.0,
) -> List[Segment]:
    """
    Segmentlere ayna ve döndürme uygular.
    mirror_y : Y ekseninde ayna (Y = -Y)
    mirror_z : Z ekseninde ayna (Z = -Z)
    rotate_deg: saat yönü dönüş (derece)
    """
    out = []
    angle = math.radians(-rotate_deg)  # saat yönü için negatif
    cos_a, sin_a = math.cos(angle), math.sin(angle)

    for y1, z1, y2, z2 in segs:
        if mirror_y:
            y1, y2 = -y1, -y2
        if mirror_z:
            z1, z2 = -z1, -z2
        if rotate_deg:
            ny1 =  y1 * cos_a + z1 * sin_a
            nz1 = -y1 * sin_a + z1 * cos_a
            ny2 =  y2 * cos_a + z2 * sin_a
            nz2 = -y2 * sin_a + z2 * cos_a
            y1, z1, y2, z2 = ny1, nz1, ny2, nz2
        out.append((y1, z1, y2, z2))

    # Döndükten / aynalayınca yine sıfır noktasını düzelt
    return _normalize(out) if out else out


def get_bounds(segs: List[Segment]) -> Tuple[float, float, float, float]:
    """min_y, max_y, min_z, max_z döndürür."""
    if not segs:
        return 0, 1, 0, 1
    ys = [s[0] for s in segs] + [s[2] for s in segs]
    zs = [s[1] for s in segs] + [s[3] for s in segs]
    return min(ys), max(ys), min(zs), max(zs)


def calc_profile_dimensions(segs: List[Segment]) -> Tuple[float, float]:
    """
    DXF segmentlerinden profil boyutlarını hesaplar.

    Dönüş: (height_mm, width_mm)
      height_mm : profilin tamamının yüksekliği (max_Z - min_Z)
      width_mm  : profilin alt 30mm'lik dilimindeki maksimum genişlik (max_Y - min_Y)
    """
    if not segs:
        return 0.0, 0.0

    min_y, max_y, min_z, max_z = get_bounds(segs)
    height_mm = max_z - min_z

    # Alt 30mm bölgede (Z = min_z .. min_z+30) Y genişliği
    z_limit = min_z + 30.0
    ys_bottom = []
    for y1, z1, y2, z2 in segs:
        if min(z1, z2) <= z_limit:   # en az bir uç alt bölgedeyse
            if z1 <= z_limit:
                ys_bottom.append(y1)
            if z2 <= z_limit:
                ys_bottom.append(y2)

    if ys_bottom:
        width_mm = max(ys_bottom) - min(ys_bottom)
    else:
        width_mm = max_y - min_y   # Yedek: toplam genişlik

    return round(height_mm, 1), round(width_mm, 1)
