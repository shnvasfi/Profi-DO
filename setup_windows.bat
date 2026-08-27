@echo off
REM ================================================
REM Windows Kurulum Scripti
REM ================================================
echo === Winsa Profil Kesim - Windows Kurulum ===
echo.

REM Python kontrolu
python --version
if errorlevel 1 (
    echo HATA: Python bulunamadi.
    echo https://python.org adresinden Python 3.11+ kurun.
    pause
    exit /b 1
)

echo [1/3] Sanal ortam olusturuluyor...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/3] Kutuphaneler yukleniyor...
pip install --upgrade pip
pip install PySide6 matplotlib ezdxf numpy pandas openpyxl pyodbc

echo [3/3] Kurulum tamamlandi!
echo.
echo Programi baslatmak icin:
echo   run_windows.bat
echo.
echo NOT: MDB baglanabilmesi icin Microsoft Access Database Engine
echo      yuklenmis olmalidir. Yoksa suradari indirin:
echo      https://www.microsoft.com/en-us/download/details.aspx?id=54920
echo.
pause
