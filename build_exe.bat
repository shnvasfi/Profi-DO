@echo off
REM ================================================
REM ProfiDO (KSB_ProfilKesim) - Windows'ta tek tikla derleme
REM Bu dosyaya cift tikla, GitHub'i beklemeden yerel .exe uretir.
REM ================================================
cd /d "%~dp0"

echo ====================================================
echo  ProfiDO (KSB_ProfilKesim) - Windows Derleme
echo ====================================================
echo.

if not exist venv (
    echo [1/4] Sanal ortam olusturuluyor...
    python -m venv venv
) else (
    echo [1/4] Sanal ortam zaten mevcut, atlaniyor...
)

call venv\Scripts\activate.bat

echo.
echo [2/4] Kutuphaneler yukleniyor...
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo.
echo [3/4] Derleniyor (birkac dakika surebilir)...
pyinstaller --noconfirm --onefile --windowed --name "KSB_ProfilKesim" ^
  --add-data "ui;ui" ^
  main.py

echo.
echo [4/4] Tamamlandi!
echo .exe dosyasi: dist\KSB_ProfilKesim.exe
start "" explorer "dist"
pause
