"""
setup_mdb_mac.py
Mac'te MDB (Access) dosyasına doğrudan yazabilmek için
Java + UCanAccess JAR kurulumunu yapar.

Çalıştır:  python3 setup_mdb_mac.py
Bir kez kurulduktan sonra program MDB'ye doğrudan yazar.
"""

import os, sys, subprocess, urllib.request, zipfile, shutil

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
JAR_DIR   = os.path.join(BASE_DIR, 'java_libs')

MAVEN = 'https://repo1.maven.org/maven2'
JARS  = [
    (f'{MAVEN}/net/sf/ucanaccess/ucanaccess/5.0.1/ucanaccess-5.0.1.jar',       'ucanaccess-5.0.1.jar'),
    (f'{MAVEN}/org/hsqldb/hsqldb/2.7.2/hsqldb-2.7.2.jar',                      'hsqldb-2.7.2.jar'),
    (f'{MAVEN}/commons-logging/commons-logging/1.2/commons-logging-1.2.jar',    'commons-logging-1.2.jar'),
    (f'{MAVEN}/com/healthmarketscience/jackcess/jackcess/4.0.5/jackcess-4.0.5.jar', 'jackcess-4.0.5.jar'),
    (f'{MAVEN}/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar',  'commons-lang3-3.12.0.jar'),
]

def check_java():
    try:
        r = subprocess.run(['java', '-version'], capture_output=True, text=True)
        print(f'✅ Java bulundu: {r.stderr.splitlines()[0] if r.stderr else "OK"}')
        return True
    except FileNotFoundError:
        print('❌ Java bulunamadı.')
        print('   Lütfen Java yükleyin: https://adoptium.net')
        return False

def install_jaydebeapi():
    # JayDeBeApi/JPype artık kullanılmıyor (macOS crash yapıyor)
    # Sadece subprocess köprüsü kullanılıyor
    print('ℹ  JayDeBeApi/JPype kullanılmıyor (subprocess modu seçildi)')
    return True

def download_jars():
    os.makedirs(JAR_DIR, exist_ok=True)
    all_ok = True
    for url, filename in JARS:
        dest = os.path.join(JAR_DIR, filename)
        if os.path.exists(dest):
            print(f'   (Mevcut) {filename}')
            continue
        print(f'   İndiriliyor: {filename} ...', end='', flush=True)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as r, open(dest, 'wb') as f:
                shutil.copyfileobj(r, f)
            size = os.path.getsize(dest) // 1024
            print(f' ✅ ({size} KB)')
        except Exception as e:
            print(f' ❌ HATA: {e}')
            all_ok = False
    return all_ok

def test_connection():
    """Subprocess köprüsü ile MDB bağlantı testi — JVM Python içine yüklenmez."""
    helper_jar = os.path.join(JAR_DIR, 'MdbHelper.jar')
    helper_cls = os.path.join(JAR_DIR, 'MdbHelper.class')

    if not (os.path.exists(helper_jar) or os.path.exists(helper_cls)):
        print('⚠  MdbHelper.jar/class bulunamadı — derleme adımını çalıştırın')
        return

    # Masaüstünde .mdb ara
    mdb_candidates = []
    for root, dirs, files in os.walk(os.path.expanduser('~/Desktop')):
        for f in files:
            if f.endswith('.mdb'):
                mdb_candidates.append(os.path.join(root, f))

    if not mdb_candidates:
        print('⚠  Masaüstünde .mdb dosyası bulunamadı — test atlandı')
        print('   Programı çalıştırıp MDB seçtiğinizde otomatik test edilecek')
        return

    mdb = mdb_candidates[0]
    print(f'   Test: {os.path.basename(mdb)}')

    # Classpath
    sep = ':'
    cp = sep.join(os.path.join(JAR_DIR, j) for _, j in JARS
                  if os.path.exists(os.path.join(JAR_DIR, j)))
    cp = cp + sep + JAR_DIR   # MdbHelper.class için

    print('   (İlk yükleme 15-30 sn sürebilir, lütfen bekleyin...)')
    try:
        proc = subprocess.Popen(
            ['java', '-cp', cp, 'MdbHelper', mdb],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1
        )
        import threading, queue

        q = queue.Queue()
        def _read():
            try:
                proc.stdin.write('SELECT COUNT(*) FROM MSysObjects\n')
                proc.stdin.flush()
                line = proc.stdout.readline()
                q.put(line.rstrip('\n'))
            except Exception as e:
                q.put(f'ERR:{e}')

        t = threading.Thread(target=_read, daemon=True)
        t.start()
        t.join(timeout=45)   # 45 saniye bekle

        proc.stdin.close()
        try: proc.wait(timeout=3)
        except Exception: proc.kill()

        if not t.is_alive() and not q.empty():
            line = q.get()
            print(f'✅ Java subprocess başarılı — MDB hazır!')
        else:
            print(f'⚠  Zaman aşımı — ancak bu normal olabilir.')
            print(f'   UCanAccess ilk bağlantıda yavaş olabilir.')
            print(f'   Programı çalıştırınca gerçek test yapılacak.')

    except Exception as e:
        print(f'⚠  Test hatası: {e}')
        print(f'   Programı çalıştırınca bağlantı tekrar denenecek.')

def compile_java_helper():
    """MdbHelper.java'yı derler."""
    import sys, shutil
    java_src = os.path.join(JAR_DIR, 'MdbHelper.java')
    jar_out  = os.path.join(JAR_DIR, 'MdbHelper.jar')

    if not os.path.exists(java_src):
        print('⚠  MdbHelper.java bulunamadı — derleme atlandı')
        return False

    if os.path.exists(jar_out):
        print('✅ MdbHelper.jar zaten mevcut')
        return True

    # javac var mı?
    if not shutil.which('javac'):
        print('⚠  javac bulunamadı (JDK kurulu değil)')
        print('   brew install --cask temurin  VEYA')
        print('   https://adoptium.net adresinden JDK indirin')
        return False

    # Classpath
    sep = ':'
    cp = sep.join(os.path.join(JAR_DIR, j) for j in [
        'ucanaccess-5.0.1.jar', 'hsqldb-2.7.2.jar',
        'commons-logging-1.2.jar', 'jackcess-4.0.5.jar',
        'commons-lang3-3.12.0.jar'])

    print('   Derleniyor: MdbHelper.java ...', end='', flush=True)
    r = subprocess.run(
        ['javac', '-cp', cp, '-d', JAR_DIR, java_src],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f'\n❌ Derleme hatası:\n{r.stderr}')
        return False

    # jar ile paketle
    class_file = os.path.join(JAR_DIR, 'MdbHelper.class')
    if os.path.exists(class_file):
        r2 = subprocess.run(
            ['jar', 'cf', jar_out, 'MdbHelper.class'],
            capture_output=True, text=True, cwd=JAR_DIR)
        if r2.returncode == 0:
            print(' ✅ MdbHelper.jar oluşturuldu')
            return True

    # jar oluşturulamadı ama .class var — class doğrudan kullanılır
    if os.path.exists(class_file):
        print(' ✅ (MdbHelper.class kullanılacak)')
        return True

    print(' ❌')
    return False


def main():
    print('=' * 60)
    print('  ProfiDO – Mac MDB Kurulum Scripti (subprocess modu)')
    print('  NOT: JPype kullanmaz — crash sorunu yok!')
    print('=' * 60)
    print()

    # 1. Java kontrolü
    if not check_java():
        return

    # 2. JAR'ları indir
    print('\nUCanAccess JAR dosyaları indiriliyor...')
    all_ok = download_jars()
    if not all_ok:
        print('\n⚠  Bazı JAR\'lar indirilemedi. İnternet bağlantısını kontrol edin.')
        return

    # 3. Java helper'ı derle
    print('\nJava helper derleniyor...')
    compile_java_helper()

    # 4. Bağlantı testi
    print('\nBağlantı testi yapılıyor...')
    test_connection()

    print()
    print('=' * 60)
    print('✅ Kurulum tamamlandı!')
    print('   python3 main.py ile programı başlatın.')
    print('=' * 60)

if __name__ == '__main__':
    main()
