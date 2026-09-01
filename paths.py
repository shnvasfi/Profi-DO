"""
paths.py — Uygulama verilerinin saklandığı klasörün tek, ortak kaynağı.

Eski sürümlerde bu klasör ~/.winsa_profil idi. Marka/telif bağımsızlığı için
~/.ksb_profil olarak değiştirildi. Bu modül, kullanıcının bilgisayarında hâlâ
eski klasör varsa (ve yenisi henüz oluşturulmamışsa) içeriğini otomatik olarak
yeni klasöre taşır — böylece ayarlar, profil kütüphanesi ve sipariş verisi
kaybolmaz.
"""

import os
import shutil

_OLD_DIR_NAME = '.winsa_profil'
_NEW_DIR_NAME = '.ksb_profil'


def app_data_dir() -> str:
    """Uygulama verilerinin (ayarlar, profil kütüphanesi, siparişler)
    saklandığı klasörün tam yolunu döndürür; gerekiyorsa eski klasörden
    otomatik taşıma yapar."""
    home = os.path.expanduser('~')
    new_dir = os.path.join(home, _NEW_DIR_NAME)
    old_dir = os.path.join(home, _OLD_DIR_NAME)

    if not os.path.exists(new_dir) and os.path.exists(old_dir):
        try:
            shutil.copytree(old_dir, new_dir)
        except Exception:
            # Taşıma başarısız olursa en azından klasörü oluştur, veri kaybı olmasın
            os.makedirs(new_dir, exist_ok=True)

    os.makedirs(new_dir, exist_ok=True)
    return new_dir
