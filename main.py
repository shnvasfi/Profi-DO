"""
main.py – Giriş noktası
ProfiDO

Kapatma akışı:
  - Program sadece intro/splash ekranından kapatılabilir.
  - Diğer pencerelerden 🏠 butonu ile intro'ya dönülür.
  - MainWindow.closeEvent intro'yu göstererek kapanmayı engeller.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore    import Qt
from ui.splash_screen  import SplashScreen
from ui.main_window    import MainWindow


_app    = None
_window = None
_splash = None


def _show_splash(exit_mode: bool = False):
    """Yeni bir splash ekranı göster. exit_mode=True ise 'Programı Kapat' butonu aktif."""
    global _splash
    if _splash is not None:
        try:
            _splash.closed.disconnect()
        except Exception:
            pass
        _splash.close()
        _splash = None

    _splash = SplashScreen(exit_mode=exit_mode)

    def _on_splash_closed(quit_app: bool):
        if quit_app:
            _app.quit()
        else:
            _window.show()
            _window.raise_()
            _window.activateWindow()

    _splash.closed_with_action.connect(_on_splash_closed)
    _splash.show()


def main():
    global _app, _window, _splash

    _app = QApplication(sys.argv)
    _app.setApplicationName('ProfiDO')
    _app.setOrganizationName('Yılmaz Makine')
    _app.setStyle('Fusion')

    # Ana pencere oluştur
    _window = MainWindow(go_home_callback=lambda: _go_home())
    # Pencere kapanmasını engelle — sadece intro'dan kapatılır
    _window.set_app_quit_blocked(True)

    # İlk açılış splash
    _show_splash(exit_mode=False)

    sys.exit(_app.exec())


def _go_home():
    """MainWindow 'Ana Menüye Dön' butonuna basıldı."""
    _window.hide()
    _show_splash(exit_mode=True)


if __name__ == '__main__':
    main()
