#!/usr/bin/env python3
"""
yayinla.py — Tek adimda guncelle + GitHub'a gonder + surum etiketle.

Bu dosyayi elle calistirmana gerek yok: guncelle_ve_yayinla.command
dosyasina cift tikladiginda otomatik olarak bu script calisir.

Ne yapar (sirasiyla):
  1. guncelle.py'yi iki kere calistirir (kod dosyalarini senkronize eder)
  2. Degisen (zaten izlenen) dosyalari 'git add -u' ile ekler
     -> DXF / Excel / resim gibi is verileri ASLA eklenmez, cunku onlar
        zaten git tarafindan izlenmiyor.
  3. version.py'deki surumu okur; bu surume ait bir GitHub etiketi zaten
     varsa otomatik olarak bir ust surume ceker (elle surum degistirmene
     gerek kalmaz).
  4. Kisa bir aciklama sorar, commit eder.
  5. GitHub'a gonderir (push) ve yeni surum etiketini de gonderir.
     -> Etiket push'u, GitHub Actions'ta otomatik Mac+Windows derlemesini
        ve bir Release sayfasi olusturulmasini tetikler.
"""

import os
import re
import subprocess
import sys
from datetime import datetime


def run(cmd, check=True, capture=False):
    print('$ ' + ' '.join(cmd))
    result = subprocess.run(cmd, text=True,
                             capture_output=capture)
    if capture and result.stdout:
        print(result.stdout.rstrip())
    if check and result.returncode != 0:
        print(f'\nHATA: Komut basarisiz oldu -> {" ".join(cmd)}')
        if capture and result.stderr:
            print(result.stderr)
        sys.exit(1)
    return result


def prepare_version() -> str:
    """version.py'yi okur; surum etiketi GitHub'da zaten varsa otomatik
    bir ust surume ceker ve version.py'yi gunceller."""
    with open('version.py', encoding='utf-8') as f:
        content = f.read()

    m = re.search(r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
    if not m:
        print('HATA: version.py icinde surum numarasi bulunamadi.')
        sys.exit(1)
    major, minor, patch = map(int, m.groups())

    tag = f'v{major}.{minor}.{patch}'
    exists = run(['git', 'ls-remote', '--tags', 'origin', f'refs/tags/{tag}'],
                 check=False, capture=True).stdout.strip()

    if exists:
        patch += 1
        new_version = f'{major}.{minor}.{patch}'
        new_content = re.sub(
            r'__version__\s*=\s*"[^"]+"',
            f'__version__ = "{new_version}"',
            content,
        )
        with open('version.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        run(['git', 'add', 'version.py'])
        return new_version

    return f'{major}.{minor}.{patch}'


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print('=' * 52)
    print(' ProfiDO (KSB_ProfilKesim) — Guncelle ve Yayinla')
    print('=' * 52)

    print('\n[1/6] Dosyalar senkronize ediliyor...')
    run([sys.executable, 'guncelle.py'])
    run([sys.executable, 'guncelle.py'])

    print('\n[2/6] Degisen kod dosyalari ekleniyor (git add -u)...')
    run(['git', 'add', '-u'])

    status = run(['git', 'status', '--short'], capture=True).stdout
    if not status.strip():
        print('\nYeni bir degisiklik yok — yayinlanacak bir sey bulunamadi.')
        input('\nKapatmak icin Enter\'a bas...')
        return

    print('\nDegisen dosyalar:')
    print(status)
    print('NOT: Yukarida DXF / Excel / resim gibi is verisi GORUNMEMELI.')
    print('     Sadece kod dosyalari (.py, .bat, .sh, .yml vb.) olmali.')
    ans = input('\nDevam edilsin mi? (Enter = evet, iptal icin "h" yaz): ').strip().lower()
    if ans in ('h', 'hayir', 'n', 'no'):
        print('Iptal edildi. Hicbir sey gonderilmedi.')
        return

    print('\n[3/6] Surum numarasi hazirlaniyor...')
    version = prepare_version()
    print(f'Kullanilacak surum: v{version}')

    print('\n[4/6] Kaydediliyor (commit)...')
    msg = input('Bu guncelleme icin kisa bir aciklama yaz (bos birakabilirsin): ').strip()
    if not msg:
        msg = f'Guncelleme v{version} - {datetime.now().strftime("%d.%m.%Y %H:%M")}'
    run(['git', 'commit', '-m', msg])

    print('\n[5/6] GitHub\'a gonderiliyor...')
    run(['git', 'push'])

    print('\n[6/6] Surum etiketi gonderiliyor...')
    tag = f'v{version}'
    run(['git', 'tag', tag])
    run(['git', 'push', 'origin', tag])

    print('\n' + '=' * 52)
    print(' TAMAMLANDI!')
    print(' GitHub simdi Mac ve Windows programlarini otomatik')
    print(' derliyor. Birkac dakika sonra su adresten indirebilirsin:')
    print(' https://github.com/shnvasfi/Profi-DO/releases/latest')
    print('=' * 52)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nIptal edildi.')
    except Exception as e:
        print(f'\nBeklenmeyen hata: {e}')
    input('\nKapatmak icin Enter\'a bas...')
