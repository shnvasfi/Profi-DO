@echo off
REM ================================================
REM PyInstaller ile .exe olustur
REM ================================================
call venv\Scripts\activate.bat
pip install pyinstaller

pyinstaller --onefile --windowed --name "KSB_ProfilKesim" ^
  --add-data "ui;ui" ^
  main.py

echo.
echo .exe dosyasi: dist\KSB_ProfilKesim.exe
pause
