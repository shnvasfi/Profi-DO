"""
models.py
MDB dosyasının 37 sütunlu veri modeli tanımları.
"""

# Sayısal sütunlar (float/int olarak kaydedilecek)
NUMERIC_COLS = {
    'PROGRAM_NO', 'INCH_MM', 'TROLLEY', 'UNIT',
    'LEFT_ANGLE', 'RIGHT_ANGLE', 'SIDE', 'CUTTED', 'HEIGHT',
    'PAIR', 'BAR_NO', 'PICE_NO', 'WIDTH', 'FRAME_NO',
    'ROBOT_Y', 'ROBOT_Z', 'ROBOT_VERTICAL'
}
# POSE_NO artık "çerçeve_no/rol_no" formatında string (ör: "1/1", "2/2")

# Sütun sırası (MDB'deki sıraya göre)
COLUMNS = [
    'PROGRAM_NO', 'CUSTOMER_CODE', 'CUSTOMER_NAME', 'STOCK_CODE',
    'STOCK_NAME', 'ORDER_NO', 'EXPLANATION1', 'EXPLANATION2',
    'LENGTH', 'INCH_MM', 'FRAME_X', 'FRAME_Y', 'POSE_NO',
    'TROLLEY', 'UNIT', 'LEFT_ANGLE', 'RIGHT_ANGLE', 'SIDE',
    'CUTTED', 'HEIGHT', 'SELLER', 'IMAGE', 'PAIR', 'BAR_NO',
    'TOTAL_SIZE', 'PICE_NO', 'GRUP', 'WIDTH', 'TYPE',
    'COLOR_CODE', 'STIL_LENGTH', 'FRAME_NO', 'REMAINING_LENGTH',
    'CODE', 'ROBOT_Y', 'ROBOT_Z', 'ROBOT_VERTICAL'
]

# Profil tipleri
PROFILE_TYPES = {
    'A': 'A – Kasa',
    'B': 'B – Kanat',
    'C': 'C – Damlalıklı Kanat',
    'D': 'D – Dış Açılım Kanat',
    'E': 'E – Orta Kayıt',
    'F': 'F – Sürme Kasa',
    'G': 'G – Sürme Kanat',
    'H': 'H – Pervazlı Kasa',
    'I': 'I – Denizlikli Kasa',
    'J': 'J – Kapı Kanat',
}

# Kasa tipleri (su tahliye takım seçimi için)
FRAME_TYPES = {'A', 'F', 'H', 'I'}
# Kanat tipleri
SASH_TYPES  = {'B', 'C', 'D', 'G'}

# Renk kodları
COLOR_CODES = {
    '':   '– Seçiniz –',
    '05': '05 – Contasız Beyaz',
    '06': '06 – Contasız Renkli',
    '07': '07 – Contasız Üst Renkli / Alt Beyaz',
    '08': '08 – Contasız Üst Beyaz / Alt Renkli',
    '95': '95 – Contalı Beyaz',
    '96': '96 – Contalı Renkli',
    '97': '97 – Contalı Üst Renkli / Alt Beyaz',
    '98': '98 – Contalı Üst Beyaz / Alt Renkli',
}

# Taraf tanımları
SIDES = {
    '1': '1 – Sol',
    '2': '2 – Üst',
    '3': '3 – Sağ',
    '4': '4 – Alt',
}

# Her sütunun ayrıntılı tanımı
COLUMN_INFO = {
    'PROGRAM_NO':       {'label': 'Program No',         'type': 'int',    'max': 5,   'req': True,  'grp': 'Genel',    'note': '1\'den başlar'},
    'CUSTOMER_CODE':    {'label': 'Müşteri Kodu',        'type': 'str',    'max': 16,  'req': False, 'grp': 'Müşteri'},
    'CUSTOMER_NAME':    {'label': 'Müşteri Adı',         'type': 'str',    'max': 24,  'req': False, 'grp': 'Müşteri'},
    'STOCK_CODE':       {'label': 'Stok Kodu',           'type': 'str',    'max': 16,  'req': True,  'grp': 'Profil',   'note': 'Tam 16 karakter'},
    'STOCK_NAME':       {'label': 'Stok Adı',            'type': 'str',    'max': 24,  'req': True,  'grp': 'Profil'},
    'ORDER_NO':         {'label': 'Sipariş No',          'type': 'str',    'max': 6,   'req': False, 'grp': 'Genel'},
    'EXPLANATION1':     {'label': 'Açıklama 1',          'type': 'str',    'max': 10,  'req': False, 'grp': 'Genel'},
    'EXPLANATION2':     {'label': 'Açıklama 2',          'type': 'str',    'max': 24,  'req': False, 'grp': 'Genel'},
    'LENGTH':           {'label': 'Kesim Boyu',          'type': 'str',    'max': 8,   'req': True,  'grp': 'Kesim',    'note': '×10  (1050mm → 10500)'},
    'INCH_MM':          {'label': 'Birim',               'type': 'choice', 'choices': [('0','mm'),('1','inch')], 'req': True, 'grp': 'Kesim', 'def': '0'},
    'FRAME_X':          {'label': 'Çerçeve X',           'type': 'str',    'max': 8,   'req': False, 'grp': 'Çerçeve'},
    'FRAME_Y':          {'label': 'Çerçeve Y',           'type': 'str',    'max': 8,   'req': False, 'grp': 'Çerçeve'},
    'POSE_NO':          {'label': 'Poz No',              'type': 'str',    'max': 7,   'req': False, 'grp': 'Çerçeve', 'note': 'çerçeve/rol (ör: 1/1)'},
    'TROLLEY':          {'label': 'Araba No',            'type': 'float',  'max': 3,   'req': False, 'grp': 'Lojistik'},
    'UNIT':             {'label': 'Göz No',              'type': 'float',  'max': 3,   'req': False, 'grp': 'Lojistik'},
    'LEFT_ANGLE':       {'label': 'Sol Kesim Açısı',     'type': 'float',  'max': 4,   'req': True,  'grp': 'Kesim',    'note': '×10  (45° → 450)', 'def': 450},
    'RIGHT_ANGLE':      {'label': 'Sağ Kesim Açısı',    'type': 'float',  'max': 4,   'req': True,  'grp': 'Kesim',    'note': '×10  (45° → 450)', 'def': 450},
    'SIDE':             {'label': 'Taraf',               'type': 'choice', 'choices': [('1','Sol'),('2','Üst'),('3','Sağ'),('4','Alt')], 'req': True, 'grp': 'Kesim'},
    'CUTTED':           {'label': 'Kesildi mi',          'type': 'float',  'max': 1,   'req': True,  'grp': 'Durum',    'def': 0},
    'HEIGHT':           {'label': 'Yükseklik',           'type': 'float',  'max': 8,   'req': True,  'grp': 'Profil',   'note': '×10  (65mm → 650)'},
    'SELLER':           {'label': 'Bayi',                'type': 'str',    'max': 24,  'req': False, 'grp': 'Müşteri'},
    'IMAGE':            {'label': 'Resim Yolu',          'type': 'str',    'max': 50,  'req': False, 'grp': 'Genel'},
    'PAIR':             {'label': 'Çift No',             'type': 'float',  'max': 4,   'req': False, 'grp': 'Bar'},
    'BAR_NO':           {'label': 'Bar No',              'type': 'float',  'max': 4,   'req': True,  'grp': 'Bar'},
    'TOTAL_SIZE':       {'label': 'Bar Boyu',            'type': 'str',    'max': 8,   'req': True,  'grp': 'Bar',      'note': '×10  (6000mm → 60000)'},
    'PICE_NO':          {'label': 'Parça No',            'type': 'float',  'max': 4,   'req': True,  'grp': 'Bar'},
    'GRUP':             {'label': 'Grup',                'type': 'str',    'max': 50,  'req': False, 'grp': 'Bar'},
    'WIDTH':            {'label': 'Genişlik',            'type': 'float',  'max': 8,   'req': True,  'grp': 'Profil',   'note': '×10  (65mm → 650)'},
    'TYPE':             {'label': 'Tip',                 'type': 'choice',
                         'choices': [(k, v) for k, v in PROFILE_TYPES.items()],
                         'req': True, 'grp': 'Profil'},
    'COLOR_CODE':       {'label': 'Renk Kodu',           'type': 'choice',
                         'choices': [(k, v) for k, v in COLOR_CODES.items()],
                         'req': False, 'grp': 'Profil'},
    'STIL_LENGTH':      {'label': 'Destek Sacı Boyu',    'type': 'str',    'max': 8,   'req': False, 'grp': 'Profil'},
    'FRAME_NO':         {'label': 'Çerçeve No',          'type': 'float',  'max': 4,   'req': False, 'grp': 'Çerçeve'},
    'REMAINING_LENGTH': {'label': 'Kalan Boy',           'type': 'str',    'max': 8,   'req': False, 'grp': 'Bar'},
    'CODE':             {'label': 'İşlem Kodu (CODE)',   'type': 'text',   'max': 500, 'req': False, 'grp': 'İşlem'},
    'ROBOT_Y':          {'label': 'Robot Y',             'type': 'float',  'max': 4,   'req': False, 'grp': 'Robot',    'def': 400},
    'ROBOT_Z':          {'label': 'Robot Z',             'type': 'float',  'max': 8,   'req': False, 'grp': 'Robot',    'def': 400},
    'ROBOT_VERTICAL':   {'label': 'Robot Pozisyon',      'type': 'choice', 'choices': [('0','Yatay (0)'),('1','Dikey (1)')], 'req': False, 'grp': 'Robot', 'def': '0'},
}
