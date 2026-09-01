#!/bin/bash
# guncelle_ve_yayinla.command
# Cift tikla — guncelle.py + git add/commit/push + surum etiketleme
# adimlarinin tumunu tek seferde calistirir. Terminal otomatik acilir.

cd "$(dirname "$0")"
python3 yayinla.py
