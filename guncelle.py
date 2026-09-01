import shutil, os

SRC = os.path.expanduser(
    '~/Library/Application Support/Claude/local-agent-mode-sessions'
    '/81e31e2a-3794-4ef6-93d0-79f80e3218cc'
    '/1e7f0199-a307-40a5-a4dd-7ae24e5a57e1'
    '/local_80f59e8b-6a38-447b-b3c4-7cda94edc855'
    '/outputs/winsa_profil_kesim'
)

files = [
    ('models.py',                              'models.py'),
    ('paths.py',                               'paths.py'),
    ('version.py',                             'version.py'),
    ('settings.py',                            'settings.py'),
    ('database.py',                            'database.py'),
    ('kanat_operations.py',                    'kanat_operations.py'),
    ('code_generator.py',                      'code_generator.py'),
    # NOT: profile_library.json / .xlsx KOPYALANMIYOR — kullanici verisi ezilmesin
    ('ui/kiosk.py',                            'ui/kiosk.py'),
    ('ui/panel_operations.py',                 'ui/panel_operations.py'),
    ('ui/panel_tools.py',                      'ui/panel_tools.py'),
    ('ui/main_window.py',                      'ui/main_window.py'),
    ('ui/dialog_batch.py',                     'ui/dialog_batch.py'),
    ('ui/dialog_kanat_auto.py',                'ui/dialog_kanat_auto.py'),
    ('ui/splash_screen.py',                    'ui/splash_screen.py'),
    ('main.py',                                'main.py'),
    ('ui/viewport_widget.py',                  'ui/viewport_widget.py'),
    ('ui/dialog_profil_kutuphanesi.py',        'ui/dialog_profil_kutuphanesi.py'),
    ('ui/dialog_akilli_uretim.py',             'ui/dialog_akilli_uretim.py'),
    ('ui/dialog_siparis_listesi.py',           'ui/dialog_siparis_listesi.py'),
    ('order_store.py',                         'order_store.py'),
    ('ui/dialog_ayarlar.py',                   'ui/dialog_ayarlar.py'),
    ('dxf_loader.py',                          'dxf_loader.py'),
    ('p_code_icons.py',                        'p_code_icons.py'),
    ('setup_mdb_mac.py',                       'setup_mdb_mac.py'),
    ('mdb_bridge.py',                          'mdb_bridge.py'),
    ('java_libs/MdbHelper.java',               'java_libs/MdbHelper.java'),
    ('exporter.py',                            'exporter.py'),
    ('pdf_report.py',                          'pdf_report.py'),
    ('requirements.txt',                       'requirements.txt'),
    ('.gitignore',                             '.gitignore'),
    ('.github/workflows/build.yml',            '.github/workflows/build.yml'),
    ('build_exe.bat',                          'build_exe.bat'),
    ('setup_windows.bat',                      'setup_windows.bat'),
    ('setup_mac.sh',                           'setup_mac.sh'),
    ('yayinla.py',                             'yayinla.py'),
    ('guncelle_ve_yayinla.command',            'guncelle_ve_yayinla.command'),
    ('guncelle.py',                            'guncelle.py'),   # kendini de guncelle
]

for src_rel, dst_rel in files:
    src = os.path.join(SRC, src_rel)
    try:
        os.makedirs(os.path.dirname(os.path.abspath(dst_rel)) if os.path.dirname(dst_rel) else '.', exist_ok=True)
        shutil.copy(src, dst_rel)
        print('Kopyalandi:', dst_rel)
    except FileNotFoundError:
        # Kaynakta artik olmayan (kaldirilmis) bir dosya - atla, devam et.
        print('Atlandi (kaynakta yok, kaldirilmis olabilir):', dst_rel)

print('Tamamlandi!')
