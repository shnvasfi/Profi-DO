"""
settings.py
ProfiDO (KSB_ProfilKesim) – uygulama geneli kalıcı ayarlar.

Dosya konumu: ~/.ksb_profil/settings.json
"""

import json
import os
import paths

_SETTINGS_DIR  = paths.app_data_dir()
_SETTINGS_PATH = os.path.join(_SETTINGS_DIR, 'settings.json')

# ── Varsayılan değerler ────────────────────────────────────────────────────────
DEFAULTS: dict = {
    # ── Kesim optimizasyonu ───────────────────────────────────────────
    'blade_mm':        4,    # Testere kalınlığı (mm) — her kesite çıkan fire
    'head_waste_mm':  20,    # Profil başı temizlik fire payı (mm)
    'tail_waste_mm':  20,    # Profil sonu temizlik + tutma payı (mm)
    'gap_mm':          0,    # İki parça arası ek pay (mm) — sabitleyici/handling

    # ── Trolley / raf ─────────────────────────────────────────────────
    'trolley_count':        5,   # Mevcut trolley sayısı
    'unit_count':           6,   # Unit sayısı (trolley başına raf/göz)
    'shelves_per_trolley':  6,   # (geriye dönük uyumluluk — unit_count ile aynı)

    # ── Makine seçimi (Master ayarı) ──────────────────────────────────
    'selected_machines': ['DC 421'],   # Aktif makineler listesi

    # ── Makine program seçimi (Master ayarı) ──────────────────────────
    # 'PIM_DC' → şu anki mevcut çalışma şekli. 'NCR' → ilave çalışma gerektirir.
    'machine_program': 'PIM_DC',

    # ── Şifreler ──────────────────────────────────────────────────────
    'master_password': '12345678',    # Tam yetkili şifre
    'user_password':   '1234',        # Kısıtlı kullanıcı şifresi

    # ── Varsayılan müşteri bilgileri ──────────────────────────────────
    'default_customer_name': 'Vas',
    'default_customer_code': 'V100',
    'default_order_prefix':  'S',    # Sipariş no ön eki  (S9, S10, ...)
    'last_order_number':     9,      # Son kullanılan sipariş numarası
}

# Bilinen tüm makine modelleri
ALL_MACHINES = [
    'DC 421', 'DC 550', 'DC 600',
    'PCC 6505', 'PIM 6508 SE', 'PIM 6509',
    'ALM 6510', 'ALM 6515',
]


def load_settings() -> dict:
    """Disk'ten ayarları yükle; eksik anahtarları varsayılan ile tamamla."""
    os.makedirs(_SETTINGS_DIR, exist_ok=True)
    result = dict(DEFAULTS)          # önce varsayılanlar
    if os.path.exists(_SETTINGS_PATH):
        try:
            with open(_SETTINGS_PATH, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            result.update(saved)    # tüm kaydedilmiş anahtarları yükle
        except Exception:
            pass
    return result


def save_settings(settings: dict):
    """Ayarları diske kaydet."""
    os.makedirs(_SETTINGS_DIR, exist_ok=True)
    # Mevcut ayarları yükle, üzerine yaz (bilmediğimiz anahtarları koru)
    existing = {}
    if os.path.exists(_SETTINGS_PATH):
        try:
            with open(_SETTINGS_PATH, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except Exception:
            pass
    existing.update(settings)
    with open(_SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def next_order_no() -> str:
    """
    Bir sonraki sipariş numarasını üretir ve kaydeder.
    Örn: S9 → S10 → S11 ...
    """
    cfg = load_settings()
    prefix = cfg.get('default_order_prefix', 'S')
    num    = int(cfg.get('last_order_number', 9)) + 1
    cfg['last_order_number'] = num
    save_settings(cfg)
    return f'{prefix}{num}'


def current_order_no() -> str:
    """Mevcut (son üretilen) sipariş numarasını döndürür, artırmaz."""
    cfg    = load_settings()
    prefix = cfg.get('default_order_prefix', 'S')
    num    = int(cfg.get('last_order_number', 9))
    return f'{prefix}{num}'
