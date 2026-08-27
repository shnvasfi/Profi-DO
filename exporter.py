"""
exporter.py
ProfiDO — makineye gönder / CSV dışa aktarım modülü.

Makine grupları:
  DC  → DC 421, DC 550, DC 600
  PCC → PCC 6505
  PIM → PIM 6508 SE, PIM 6509
  ALM → ALM 6510, ALM 6515

Klasör yapısı:
  ~/Desktop/kesim listeleri/
    └── {MüşteriAdı}_{SiparişNo}/       ← sipariş klasörü
          ├── DC_MüşteriAdı_SiparişNo.csv
          └── IMAGE/
"""

import csv
import os
from typing import List, Dict, Optional

# ── Makine grubu tespiti ───────────────────────────────────────────────────────

def machine_group(machine_name: str) -> str:
    """'DC 421' → 'DC',  'PIM 6508 SE' → 'PIM', vb."""
    n = machine_name.strip().upper()
    if n.startswith('DC'):
        return 'DC'
    if n.startswith('PCC'):
        return 'PCC'
    if n.startswith('PIM'):
        return 'PIM'
    if n.startswith('ALM'):
        return 'ALM'
    return 'DC'   # fallback

def machine_prefix(machine_name: str) -> str:
    """Dosya adı ön eki: 'DC 421' → 'DC',  'PIM 6508 SE' → 'PIM' vb."""
    return machine_group(machine_name)

# ── Klasör / dosya yardımcıları ────────────────────────────────────────────────

def _root_dir() -> str:
    """Ana kesim listeleri klasörü."""
    return os.path.join(os.path.expanduser('~'), 'Desktop', 'kesim listeleri')

def order_dir(customer_name: str, order_no: str) -> str:
    """
    Sipariş klasörü: ~/Desktop/kesim listeleri/{MüşteriAdı}_{SiparişNo}/
    Örn: .../Vas_S15/
    """
    cust  = _safe(customer_name) or 'MUSTERI'
    order = _safe(order_no)      or 'S0'
    return os.path.join(_root_dir(), f'{cust}_{order}')

def output_dir(customer_name: str = '', order_no: str = '') -> str:
    """Geriye dönük uyumluluk — sipariş klasörünü döndür."""
    if customer_name or order_no:
        return order_dir(customer_name, order_no)
    return _root_dir()

def image_dir(customer_name: str = '', order_no: str = '') -> str:
    """IMAGE klasörü sipariş klasörünün içinde."""
    return os.path.join(output_dir(customer_name, order_no), 'IMAGE')

def _safe(text: str) -> str:
    """Dosya adı için güvenli karakter filtresi."""
    return ''.join(c for c in str(text) if c.isalnum() or c in ('_', '-')).strip()

def build_filename(machine_name: str, customer_name: str, order_no: str) -> str:
    """
    Örn: 'DC 421', 'VAS1', 'S15' → 'DC_VAS1_S15.csv'
    """
    prefix  = machine_prefix(machine_name)
    cust    = _safe(customer_name) or 'MUSTERI'
    order   = _safe(order_no)      or 'S0'
    return f'{prefix}_{cust}_{order}.csv'

def versioned_path(directory: str, filename: str) -> str:
    """
    Dosya varsa sona _v2, _v3 ... ekler.
    'DC_VAS1_S15.csv' → 'DC_VAS1_S15_v2.csv' → 'DC_VAS1_S15_v3.csv'
    """
    base, ext = os.path.splitext(filename)
    path = os.path.join(directory, filename)
    if not os.path.exists(path):
        return path
    v = 2
    while True:
        candidate = os.path.join(directory, f'{base}_v{v}{ext}')
        if not os.path.exists(candidate):
            return candidate
        v += 1

# ── DC CSV sütunları (değerler ×10 çarpılmadan) ───────────────────────────────

DC_COLUMNS = [
    'PROGRAM_NO', 'CUSTOMER_CODE', 'CUSTOMER_NAME', 'STOCK_CODE', 'STOCK_NAME',
    'ORDER_NO', 'EXPLANATION1', 'EXPLANATION2',
    'LENGTH', 'INCH_MM', 'FRAME_X', 'FRAME_Y', 'POSE_NO',
    'TROLLEY', 'UNIT',
    'LEFT_ANGLE', 'RIGHT_ANGLE',
    'SIDE', 'CUTTED', 'HEIGHT',
    'SELLER', 'IMAGE', 'PAIR',
]

def _dc_row(rec: dict) -> dict:
    """
    MDB kayıt dict'inden DC CSV satırı üret.
    LENGTH, FRAME_X/Y, LEFT/RIGHT_ANGLE, WIDTH, HEIGHT ×10 bölünür.
    """
    def _d10(val):
        try:
            return round(int(val) / 10, 1) if val not in ('', None) else ''
        except Exception:
            return val

    img_val = rec.get('IMAGE', '')
    if img_val:
        img_val = 'IMAGE/' + os.path.basename(img_val)

    # EXPLANATION1 sonuna (B<bar_no>) ekle
    exp1_base = rec.get('EXPLANATION1', '')
    bar_no    = rec.get('BAR_NO', rec.get('bar_no', ''))
    exp1 = f'{exp1_base} (B{bar_no})' if bar_no != '' else exp1_base

    return {
        'PROGRAM_NO':    rec.get('PROGRAM_NO', ''),
        'CUSTOMER_CODE': rec.get('CUSTOMER_CODE', ''),
        'CUSTOMER_NAME': rec.get('CUSTOMER_NAME', ''),
        'STOCK_CODE':    rec.get('STOCK_CODE', ''),
        'STOCK_NAME':    rec.get('STOCK_NAME', ''),
        'ORDER_NO':      rec.get('ORDER_NO', ''),
        'EXPLANATION1':  exp1,
        'EXPLANATION2':  rec.get('EXPLANATION2', ''),
        'LENGTH':        _d10(rec.get('LENGTH', 0)),
        'INCH_MM':       rec.get('INCH_MM', 0),
        'FRAME_X':       _d10(rec.get('FRAME_X', 0)),
        'FRAME_Y':       _d10(rec.get('FRAME_Y', 0)),
        'POSE_NO':       rec.get('POSE_NO', ''),
        'TROLLEY':       rec.get('TROLLEY', ''),
        'UNIT':          rec.get('UNIT', ''),
        'LEFT_ANGLE':    _d10(rec.get('LEFT_ANGLE', 450)),
        'RIGHT_ANGLE':   _d10(rec.get('RIGHT_ANGLE', 450)),
        'SIDE':          rec.get('SIDE', ''),
        'CUTTED':        0,
        'HEIGHT':        _d10(rec.get('HEIGHT', 0)),
        'SELLER':        '',
        'IMAGE':         img_val,
        'PAIR':          '',
    }

# ── PCC / PIM / ALM CSV sütunları (mevcut yapı, ×10 olduğu gibi) ─────────────

from models import COLUMNS as _ALL_COLS

PCC_COLUMNS = [c for c in _ALL_COLS if c != 'CODE']   # CODE yok
PIM_COLUMNS = list(_ALL_COLS)                          # CODE dahil

def _full_row(rec: dict, include_code: bool) -> dict:
    cols = PIM_COLUMNS if include_code else PCC_COLUMNS
    row  = {}
    for c in cols:
        val = rec.get(c, '')
        if c == 'CODE' and not include_code:
            continue
        if c == 'IMAGE':
            img = rec.get('IMAGE', '')
            val = ('IMAGE/' + os.path.basename(img)) if img else ''
        row[c] = val
    return row

# ── Ana dışa aktarım fonksiyonları ────────────────────────────────────────────

def export_dc(records: List[dict], machine_name: str,
              customer_name: str, order_no: str) -> str:
    """DC makinesi için CSV üret. Döndürür: dosyanın tam yolu."""
    out = order_dir(customer_name, order_no)
    img = os.path.join(out, 'IMAGE')
    os.makedirs(out, exist_ok=True)
    os.makedirs(img, exist_ok=True)

    fname = build_filename(machine_name, customer_name, order_no)
    path  = versioned_path(out, fname)

    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=DC_COLUMNS)
        writer.writeheader()
        for rec in records:
            writer.writerow(_dc_row(rec))
    return path


def export_pcc(records: List[dict], machine_name: str,
               customer_name: str, order_no: str) -> str:
    """PCC makinesi için CSV üret (CODE yok). Döndürür: dosyanın tam yolu."""
    out = order_dir(customer_name, order_no)
    img = os.path.join(out, 'IMAGE')
    os.makedirs(out, exist_ok=True)
    os.makedirs(img, exist_ok=True)

    fname = build_filename(machine_name, customer_name, order_no)
    path  = versioned_path(out, fname)

    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=PCC_COLUMNS)
        writer.writeheader()
        for rec in records:
            writer.writerow(_full_row(rec, include_code=False))
    return path


def export_pim_alm(records: List[dict], machine_name: str,
                   customer_name: str, order_no: str) -> str:
    """PIM / ALM makinesi için CSV üret (CODE dahil). Döndürür: dosyanın tam yolu."""
    out = order_dir(customer_name, order_no)
    img = os.path.join(out, 'IMAGE')
    os.makedirs(out, exist_ok=True)
    os.makedirs(img, exist_ok=True)

    fname = build_filename(machine_name, customer_name, order_no)
    path  = versioned_path(out, fname)

    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=PIM_COLUMNS)
        writer.writeheader()
        for rec in records:
            writer.writerow(_full_row(rec, include_code=True))
    return path


def export(records: List[dict], machine_name: str,
           customer_name: str, order_no: str) -> str:
    """
    Makine adına göre doğru dışa aktarım fonksiyonunu çağırır.
    Döndürür: oluşturulan dosyanın tam yolu.
    """
    grp = machine_group(machine_name)
    if grp == 'DC':
        return export_dc(records, machine_name, customer_name, order_no)
    elif grp == 'PCC':
        return export_pcc(records, machine_name, customer_name, order_no)
    else:  # PIM, ALM
        return export_pim_alm(records, machine_name, customer_name, order_no)
