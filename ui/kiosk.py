"""
ui/kiosk.py — Uygulama genelinde "kiosk modu" (çerçevesiz, tam ekran,
başlık çubuğu/pencere düğmeleri ve macOS menü çubuğu gizli) davranışını
tek yerden uygulamak için ortak yardımcı fonksiyon.

Tüm ana ekranlar (Ana Pencere, Akıllı Üretim, Siparişler, Ayarlar, Profil
Kütüphanesi, Toplu Kesim Girişi) bu fonksiyonu kullanır.
Küçük/geçici pop-up'lar (şifre girişi, adet sorma, uyarı kutuları vb.)
kasıtlı olarak kiosk moduna alınmaz — normal küçük pencere olarak kalırlar.
"""

from PySide6.QtCore import Qt


def apply_kiosk(widget):
    """Verilen pencereyi (QMainWindow/QDialog) çerçevesiz ve tam ekran yapar.
    Kapatma/gezinme, uygulamanın kendi buton/menülerinden (örn. "🏠 Ana Menü",
    "Kapat") yapılmalıdır — pencerenin native kapat/büyüt düğmeleri olmayacaktır."""
    widget.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
    widget.setWindowState(Qt.WindowFullScreen)
