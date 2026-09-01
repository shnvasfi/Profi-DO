#!/bin/bash
# mac_derle.command
# ProfiDO (KSB_ProfilKesim) — Mac'te tek tikla yerel derleme.
# Bu dosyaya cift tikla, GitHub'i beklemeden yerel .app uretir.
# GitHub'in macOS runner kuyrugu yavas oldugunda bu, en hizli yoldur.

cd "$(dirname "$0")"

echo "===================================================="
echo " ProfiDO (KSB_ProfilKesim) — Mac Derleme"
echo "===================================================="
echo ""

if [ ! -d "venv" ]; then
    echo "[1/4] Sanal ortam olusturuluyor..."
    python3 -m venv venv
else
    echo "[1/4] Sanal ortam zaten mevcut, atlaniyor..."
fi

source venv/bin/activate

echo ""
echo "[2/4] Kutuphaneler yukleniyor..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

echo ""
echo "[3/4] Derleniyor (birkac dakika surebilir)..."
python3 -m PyInstaller --noconfirm --onefile --windowed \
  --name "KSB_ProfilKesim" \
  --add-data "ui:ui" \
  --add-data "ProfiDO_IM.png:." \
  --add-data "yilmaz_logo.png:." \
  main.py

echo ""
echo "[4/4] Guvenlik izni temizleniyor ve aciliyor..."
xattr -cr "dist/KSB_ProfilKesim.app"

echo ""
echo "===================================================="
echo " TAMAMLANDI!"
echo " Uygulama: dist/KSB_ProfilKesim.app"
echo "===================================================="
open dist/
open "dist/KSB_ProfilKesim.app"

echo ""
read -p "Kapatmak icin Enter'a bas..."
