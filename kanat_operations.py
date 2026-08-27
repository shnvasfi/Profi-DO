"""
kanat_operations.py  –  Kanat profili grup bazlı işlem tanımları

Her yön (ALT/ÜST/SOL/SAĞ) birden fazla GRUP içerir.
Her grupta aynı Y/Z koordinatını kullanan 1-2 işlem vardır.
Kullanıcı her grup için ayrı ayrı DXF'e tıklar.

Örnek:
  ALT →  Grup 1: İç Su Tahliye (ops 1 + 2, tek tıklama)
          Grup 2: Dış Su Tahliye (ops 3 + 4, tek tıklama)
"""

KANAT_GROUPS = {
    'ALT': [
        {
            'name':    'İç Su Tahliye',
            'y_click': True,
            'z_click': True,
            'ops': [
                {'label': '1', 'op': 'P3', 'tool': 'T60', 'x_formula': 'L-1500', 'params': {'L': 25, 'D': 8}},
                {'label': '2', 'op': 'P3', 'tool': 'T60', 'x_formula': '1500',   'params': {'L': 25, 'D': 8}},
            ],
        },
        {
            'name':    'Dış Su Tahliye',
            'y_click': True,
            'z_click': True,
            'ops': [
                {'label': '1', 'op': 'P3', 'tool': 'T10', 'x_formula': 'L-700', 'params': {'L': 25, 'D': 8}},
                {'label': '2', 'op': 'P3', 'tool': 'T10', 'x_formula': '700',   'params': {'L': 25, 'D': 8}},
            ],
        },
    ],

    'ÜST': [
        {
            'name':    'İç Havalandırma',
            'y_click': True,
            'z_click': True,
            'ops': [
                {'label': '1', 'op': 'P7', 'tool': 'T60', 'x_formula': 'L-1500', 'params': {'D': 8}},
                {'label': '2', 'op': 'P3', 'tool': 'T60', 'x_formula': '1500',   'params': {'D': 8}},
            ],
        },
        {
            'name':    'Dış Havalandırma',
            'y_click': True,
            'z_click': True,
            'ops': [
                {'label': '1', 'op': 'P3', 'tool': 'T10', 'x_formula': 'L-700', 'params': {'D': 8}},
                {'label': '2', 'op': 'P3', 'tool': 'T10', 'x_formula': '700',   'params': {'D': 8}},
            ],
        },
    ],

    'SOL': [
        {
            'name':    'Menteşe (Üst + Alt)',
            'y_fixed': 0,      # Y her zaman 0
            'z_click': True,   # sadece Z tıklanır
            'ops': [
                {'label': 'Üst 1', 'op': 'P7', 'tool': 'T10', 'x_formula': 'L-2000', 'params': {'D': 3}},
                {'label': 'Üst 2', 'op': 'P7', 'tool': 'T10', 'x_formula': 'L-2400', 'params': {'D': 3}},
                {'label': 'Alt 1', 'op': 'P7', 'tool': 'T10', 'x_formula': '2000',   'params': {'D': 3}},
                {'label': 'Alt 2', 'op': 'P7', 'tool': 'T10', 'x_formula': '2400',   'params': {'D': 3}},
            ],
        },
    ],

    'SAĞ': [
        {
            'name':    'Üçlü Kol Yeri',
            'y_fixed': 35,
            'z_fixed': 0,
            'ops': [
                {'label': '', 'op': 'P7', 'tool': 'T71', 'x_formula': 'L/2', 'params': {'D': 35}},
            ],
        },
        {
            'name':    'İspanyolet Kanalı',
            'y_fixed': 20,
            'z_click': True,
            'ops': [
                {'label': '', 'op': 'P2', 'tool': 'T10', 'x_formula': 'L/2',
                 'params': {'L': 60, 'W': 12, 'R': 60, 'D': 32}},
            ],
        },
    ],
}

SIDES = ['ALT', 'ÜST', 'SOL', 'SAĞ']

# ─────────────────────────────────────────────────────────────────
# Kasa işlem grupları
# ─────────────────────────────────────────────────────────────────
KASA_GROUPS = {

    'ALT': [
        {
            'name':    'İç Su Tahliye',
            'y_click': True,
            'z_click': True,
            'ops': [
                {'label': '1', 'op': 'P3', 'tool': 'T40', 'x_formula': 'L-1500', 'params': {'L': 25, 'D': 8}},
                {'label': '2', 'op': 'P3', 'tool': 'T40', 'x_formula': '1500',   'params': {'L': 25, 'D': 8}},
            ],
        },
        {
            'name':    'Dış Su Tahliye',
            'y_click': True,
            'z_fixed': 0,      # Z her zaman 0
            'ops': [
                {'label': '1', 'op': 'P3', 'tool': 'T70', 'x_formula': 'L-700', 'params': {'L': 25, 'D': 8}},
                {'label': '2', 'op': 'P3', 'tool': 'T70', 'x_formula': '700',   'params': {'L': 25, 'D': 8}},
            ],
        },
        {
            'name':    'Montaj Deliği',
            'y_click': True,
            'z_click': True,
            'ops': [
                {'label': '1', 'op': 'P7', 'tool': 'T50', 'x_formula': 'L/2+2000', 'params': {'D': 20}},
                {'label': '2', 'op': 'P7', 'tool': 'T50', 'x_formula': 'L/2-2000', 'params': {'D': 20}},
            ],
        },
    ],

    'ÜST': [
        {
            'name':    'İç Havalandırma',
            'y_click': True,
            'z_click': True,
            'ops': [
                {'label': '1', 'op': 'P7', 'tool': 'T40', 'x_formula': 'L-1500', 'params': {'D': 8}},
                {'label': '2', 'op': 'P7', 'tool': 'T40', 'x_formula': '1500',   'params': {'D': 8}},
            ],
        },
        {
            'name':    'Dış Havalandırma',
            'y_click': True,
            'z_fixed': 0,      # Z her zaman 0
            'ops': [
                {'label': '1', 'op': 'P7', 'tool': 'T70', 'x_formula': 'L-700', 'params': {'D': 8}},
                {'label': '2', 'op': 'P7', 'tool': 'T70', 'x_formula': '700',   'params': {'D': 8}},
            ],
        },
        {
            'name':    'Montaj Deliği',
            'y_click': True,
            'z_click': True,
            'ops': [
                {'label': '1', 'op': 'P7', 'tool': 'T50', 'x_formula': 'L/2+2000', 'params': {'D': 20}},
                {'label': '2', 'op': 'P7', 'tool': 'T50', 'x_formula': 'L/2-2000', 'params': {'D': 20}},
            ],
        },
    ],

    'SOL': [
        {
            'name':    'Menteşe (Üst + Alt)',
            'y_fixed': 10,     # Y her zaman 10 mm
            'z_click': True,   # sadece Z tıklanır
            'ops': [
                {'label': 'Üst 1', 'op': 'P7', 'tool': 'T30', 'x_formula': 'L-1000', 'params': {'D': 3}},
                {'label': 'Üst 2', 'op': 'P7', 'tool': 'T30', 'x_formula': 'L-1400', 'params': {'D': 3}},
                {'label': 'Alt 1', 'op': 'P7', 'tool': 'T30', 'x_formula': '1000',   'params': {'D': 3}},
                {'label': 'Alt 2', 'op': 'P7', 'tool': 'T30', 'x_formula': '1400',   'params': {'D': 3}},
            ],
        },
        {
            'name':    'Montaj Deliği',
            'y_click': True,
            'z_click': True,
            'ops': [
                {'label': '1', 'op': 'P7', 'tool': 'T50', 'x_formula': 'L/2+2000', 'params': {'D': 20}},
                {'label': '2', 'op': 'P7', 'tool': 'T50', 'x_formula': 'L/2-2000', 'params': {'D': 20}},
            ],
        },
    ],

    'SAĞ': [
        {
            'name':    'Montaj Deliği',
            'y_click': True,
            'z_click': True,
            'ops': [
                {'label': '1', 'op': 'P7', 'tool': 'T50', 'x_formula': 'L/2+2000', 'params': {'D': 20}},
                {'label': '2', 'op': 'P7', 'tool': 'T50', 'x_formula': 'L/2-2000', 'params': {'D': 20}},
            ],
        },
    ],
}

# ─────────────────────────────────────────────────────────────────
# Profil tipi → işlem grubu haritası
# ─────────────────────────────────────────────────────────────────
PROFILE_LABEL = {
    'A': 'Kasa',
    'B': 'Kanat',
    'C': 'Damlalıklı Kanat',
    'D': 'Dış Açılım Kanat',
    'E': 'Orta Kayıt',
    'F': 'Sürme Kasa',
    'G': 'Sürme Kanat',
    'H': 'Pervazlı Kasa',
    'I': 'Denizlikli Kasa',
    'J': 'Kapı Kanat',
}

# ─────────────────────────────────────────────────────────────────
# Kapı Kanat işlem grupları
# ALT ve ÜST: Kanat ile aynı
# SOL: Kanat ile aynı ama Y de tıklanır (y_fixed=0 değil)
# SAĞ: Kol Deliği + Barel + Kilit Kanalı (tamamen farklı)
# ─────────────────────────────────────────────────────────────────
KAPI_KANAT_GROUPS = {

    'ALT': KANAT_GROUPS['ALT'],   # Aynı: İç/Dış Su Tahliye
    'ÜST': KANAT_GROUPS['ÜST'],   # Aynı: İç/Dış Havalandırma

    'SOL': [
        {   # Kanat SOL ile aynı ama Y tıklanır (y_fixed=0 değil)
            'name':    'Menteşe (Üst + Alt)',
            'y_click': True,
            'z_click': True,
            'ops': [
                {'label': 'Üst 1', 'op': 'P7', 'tool': 'T10', 'x_formula': 'L-2000', 'params': {'D': 3}},
                {'label': 'Üst 2', 'op': 'P7', 'tool': 'T10', 'x_formula': 'L-2400', 'params': {'D': 3}},
                {'label': 'Alt 1', 'op': 'P7', 'tool': 'T10', 'x_formula': '2000',   'params': {'D': 3}},
                {'label': 'Alt 2', 'op': 'P7', 'tool': 'T10', 'x_formula': '2400',   'params': {'D': 3}},
            ],
        },
    ],

    'SAĞ': [
        {
            # X = L/2,  Y = 35mm (sabit),  Z = Profil Yüksekliği (tıkla)
            'name':    'Kol Deliği + Barel Üst',
            'y_fixed': 35,
            'z_click': True,
            'ops': [
                # Kol Deliği Üst: P6 T30
                {'label': 'Kol Üst',   'op': 'P6', 'tool': 'T30',
                 'x_formula': 'L/2',       'params': {'C': 18, 'D': 35}},
                # Barel Üst: P4 T30, X = L/2 - 89.5mm = L/2-895
                {'label': 'Barel Üst', 'op': 'P4', 'tool': 'T30',
                 'x_formula': 'L/2-895',   'params': {'L': 33, 'W': 10, 'C': 18, 'R': 5, 'D': 35}},
            ],
        },
        {
            # X = L/2,  Y = 35mm (sabit),  Z = 0 (sabit — alt yüzey)
            'name':    'Kol Deliği + Barel Alt',
            'y_fixed': 35,
            'z_fixed': 0,
            'ops': [
                # Kol Deliği Alt: P6 T70
                {'label': 'Kol Alt',   'op': 'P6', 'tool': 'T70',
                 'x_formula': 'L/2',       'params': {'C': 18, 'D': 35}},
                # Barel Alt: P4 T70
                {'label': 'Barel Alt', 'op': 'P4', 'tool': 'T70',
                 'x_formula': 'L/2-895',   'params': {'L': 33, 'W': 10, 'C': 18, 'R': 5, 'D': 35}},
            ],
        },
        {
            # X = L/2 - 21mm = L/2-210,  Y = 20mm (sabit),  Z = tıkla
            'name':    'Kilit Kanalı',
            'y_fixed': 20,
            'z_click': True,
            'ops': [
                {'label': '', 'op': 'P1', 'tool': 'T10',
                 'x_formula': 'L/2-210',   'params': {'L': 230, 'W': 16, 'D': 35}},
            ],
        },
    ],
}


def get_groups_for_type(profile_type: str) -> dict:
    """
    Profil tipine göre işlem grubu sözlüğünü döndürür.
    Henüz tanımlanmamış tipler için boş dict döner.
    """
    t = profile_type.upper()
    if t in ('B', 'C', 'D', 'G'):   # Kanat tipleri
        return KANAT_GROUPS
    if t in ('A', 'F', 'H', 'I'):   # Kasa tipleri
        return KASA_GROUPS
    if t == 'J':                     # Kapı Kanat
        return KAPI_KANAT_GROUPS
    return {}                        # E (Orta Kayıt) vb. — henüz yok

def is_type_implemented(profile_type: str) -> bool:
    return bool(get_groups_for_type(profile_type))


# ─────────────────────────────────────────────────────────────────

def calc_x(formula: str, L: int) -> int:
    try:
        return max(0, int(eval(formula.replace('L', str(L)))))
    except Exception:
        return 0


def build_group_code(group_def: dict, length_x10: int,
                     y_mm: float, z_mm: float) -> str:
    """Bir grubun tüm op'larını tek kod string'ine çevirir."""
    result = ''
    for op_def in group_def['ops']:
        result += _build_op(op_def, group_def, length_x10, y_mm, z_mm)
    return result


def _build_op(op_def: dict, group_def: dict,
              length_x10: int, y_mm: float, z_mm: float) -> str:
    op   = op_def['op']
    tool = op_def['tool']
    x    = calc_x(op_def['x_formula'], length_x10)

    # Sabit değerler mm cinsinden → ×10 çevir
    # Tıklanan değerler zaten mm → ×10 çevrilir
    y = int(group_def['y_fixed'] * 10) if 'y_fixed' in group_def else int(round(y_mm * 10))
    z = int(group_def['z_fixed'] * 10) if 'z_fixed' in group_def else int(round(z_mm * 10))

    # Params mm cinsinden → ×10 çevir
    def x10(k): return int(op_def.get('params', {}).get(k, 0) * 10)

    base = f'{op}{tool}X{x}Y{y}Z{z}'

    if op == 'P7':
        return f'{base}D{x10("D")}//'
    if op == 'P3':
        if 'L' in op_def.get('params', {}):
            return f'{base}L{x10("L")}D{x10("D")}//'
        return f'{base}D{x10("D")}//'
    if op == 'P2':
        L_val = x10("L")
        W_val = x10("W")
        R_val = W_val // 2   # R = W / 2 (otomatik)
        D_val = x10("D")
        return f'{base}L{L_val}W{W_val}R{R_val}D{D_val}//'
    if op == 'P1':
        return f'{base}L{x10("L")}W{x10("W")}D{x10("D")}//'
    if op in ('P4', 'P5'):
        L_v = x10("L"); W_v = x10("W"); C_v = x10("C"); D_v = x10("D")
        r_mm = op_def.get('params', {}).get('R', 0)
        R_v  = int(r_mm * 10) if r_mm else W_v // 2
        return f'{base}L{L_v}W{W_v}C{C_v}R{R_v}D{D_v}//'
    if op == 'P6':
        return f'{base}C{x10("C")}D{x10("D")}//'
    return f'{base}//'


def group_needs_click(group_def: dict) -> dict:
    return {
        'y': group_def.get('y_click', False),
        'z': group_def.get('z_click', False),
    }
