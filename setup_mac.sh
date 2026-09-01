#!/bin/bash
# ================================================
# Mac'te Geliştirme Ortamı Kurulum Scripti
# ================================================

echo "=== ProfiDO (KSB_ProfilKesim) — Mac Kurulum ==="
echo ""

# Python versiyonu kontrol
python3 --version || { echo "HATA: Python 3 bulunamadı. https://python.org adresinden kurun."; exit 1; }

# Sanal ortam oluştur
echo "[1/3] Sanal ortam oluşturuluyor..."
python3 -m venv venv
source venv/bin/activate

# Kütüphaneler
echo "[2/3] Kütüphaneler yükleniyor..."
pip install --upgrade pip
pip install PySide6 matplotlib ezdxf numpy pandas openpyxl

echo "[3/3] Kurulum tamamlandı!"
echo ""
echo "Programı başlatmak için:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "NOT: Mac'te MDB bağlantısı çalışmaz (sadece Windows)."
echo "     Geliştirme sırasında SQLite modu otomatik devreye girer."
