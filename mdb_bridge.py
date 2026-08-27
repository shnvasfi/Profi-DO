"""
mdb_bridge.py

Mac'te MDB dosyasına yazmak için JPype/JNI kullanmayan köprü.
Python → subprocess → Java (MdbHelper.jar) → MDB

Avantaj: JPype crash yok, stable çalışır.
"""

import os
import subprocess
import io
from typing import List, Dict, Tuple, Optional

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
JAR_DIR   = os.path.join(BASE_DIR, 'java_libs')
HELPER_JAR = os.path.join(JAR_DIR, 'MdbHelper.jar')

JAR_NAMES = [
    'ucanaccess-5.0.1.jar',
    'hsqldb-2.7.2.jar',
    'commons-logging-1.2.jar',
    'jackcess-4.0.5.jar',
    'commons-lang3-3.12.0.jar',
    'MdbHelper.jar',
]


def _classpath() -> str:
    sep = ':' if os.name != 'nt' else ';'
    return sep.join(os.path.join(JAR_DIR, j) for j in JAR_NAMES
                    if os.path.exists(os.path.join(JAR_DIR, j)))


def is_available() -> bool:
    """Java ve MdbHelper.jar mevcut mu?"""
    if not os.path.exists(HELPER_JAR):
        return False
    try:
        r = subprocess.run(['java', '-version'], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def compile_helper() -> Tuple[bool, str]:
    """MdbHelper.java'yı derler → MdbHelper.jar oluşturur."""
    java_src = os.path.join(JAR_DIR, 'MdbHelper.java')
    if not os.path.exists(java_src):
        return False, f'MdbHelper.java bulunamadı: {java_src}'

    # Derleme classpath (jar'lar gerekli)
    cp = _classpath_without_helper()
    if not cp:
        return False, 'UCanAccess JAR dosyaları bulunamadı. setup_mdb_mac.py çalıştırın.'

    class_out = JAR_DIR

    # javac ile derle
    r_compile = subprocess.run(
        ['javac', '-cp', cp, '-d', class_out, java_src],
        capture_output=True, text=True
    )
    if r_compile.returncode != 0:
        return False, f'Derleme hatası:\n{r_compile.stderr}'

    # jar ile paketле
    class_file = os.path.join(JAR_DIR, 'MdbHelper.class')
    r_jar = subprocess.run(
        ['jar', 'cf', HELPER_JAR, '-C', class_out, 'MdbHelper.class'],
        capture_output=True, text=True, cwd=JAR_DIR
    )
    if r_jar.returncode != 0:
        # Alternatif: .class dosyasını kullan
        if os.path.exists(class_file):
            return True, 'JAR oluşturulamadı ama .class dosyası kullanılacak'
        return False, f'JAR hatası:\n{r_jar.stderr}'

    return True, 'MdbHelper.jar derlendi.'


def _classpath_without_helper() -> str:
    sep = ':' if os.name != 'nt' else ';'
    return sep.join(os.path.join(JAR_DIR, j) for j in JAR_NAMES[:-1]
                    if os.path.exists(os.path.join(JAR_DIR, j)))


class MdbBridge:
    """
    Mac'te MDB dosyasıyla subprocess üzerinden iletişim kurar.
    JPype kullanmaz → crash yok.
    """

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self.db_path: Optional[str] = None
        self.table_name: Optional[str] = None

    def connect(self, db_path: str) -> Tuple[bool, str]:
        if not is_available():
            return False, 'MdbHelper.jar bulunamadı. setup_mdb_mac.py çalıştırın.'

        self.db_path = db_path
        cp = _classpath()

        try:
            self._proc = subprocess.Popen(
                ['java', '-cp', cp, 'MdbHelper', db_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                bufsize=1
            )
        except Exception as e:
            return False, f'Java başlatılamadı: {e}'

        # Tablo tespiti
        ok, msg = self._detect_table()
        if not ok:
            return False, msg

        return True, (f'MDB bağlandı (Java/subprocess): '
                      f'{os.path.basename(db_path)}  |  Tablo: {self.table_name}')

    def _detect_table(self) -> Tuple[bool, str]:
        """Sistem tablosundan kullanıcı tablolarını listeler."""
        sql = ("SELECT Name FROM MSysObjects WHERE Type=1 "
               "AND Name NOT LIKE 'MSys%'")
        rows = self._query(sql)
        if rows is None:
            # Yeni boş MDB — tabloyu oluştur
            self.table_name = 'KANAT'
            self._create_table()
            return True, ''
        names = [r[0] for r in rows if r]
        if not names:
            self.table_name = 'KANAT'
            self._create_table()
            return True, ''
        self.table_name = names[0]
        return True, ''

    def _create_table(self):
        from models import COLUMNS, NUMERIC_COLS
        cols = []
        for col in COLUMNS:
            if col == 'PROGRAM_NO':
                cols.append(f'[{col}] INTEGER PRIMARY KEY')
            elif col in NUMERIC_COLS:
                cols.append(f'[{col}] DOUBLE')
            else:
                cols.append(f'[{col}] TEXT(500)')
        ddl = f'CREATE TABLE [{self.table_name}] ({", ".join(cols)})'
        self._execute(ddl)
        self._execute('COMMIT')

    # ─── Temel SQL ─────────────────────────────────────────

    def _send(self, sql: str) -> str:
        """SQL gönderir, yanıt satırını döndürür."""
        if not self._proc or self._proc.poll() is not None:
            return 'ERR:Süreç çalışmıyor'
        try:
            self._proc.stdin.write(sql.replace('\n', ' ') + '\n')
            self._proc.stdin.flush()
            return self._proc.stdout.readline().rstrip('\n')
        except Exception as e:
            return f'ERR:{e}'

    def _execute(self, sql: str) -> Tuple[bool, str]:
        resp = self._send(sql)
        if resp.startswith('ERR:'):
            return False, resp[4:]
        return True, resp

    def _query(self, sql: str) -> Optional[List[List]]:
        """SELECT sorgusundan satır listesi döndürür."""
        if not self._proc or self._proc.poll() is not None:
            return None
        try:
            self._proc.stdin.write(sql.replace('\n', ' ') + '\n')
            self._proc.stdin.flush()
        except Exception:
            return None

        cols = []
        rows = []
        while True:
            line = self._proc.stdout.readline().rstrip('\n')
            if line.startswith('COLS:'):
                cols = line[5:].split('\t')
            elif line.startswith('ROW:'):
                vals = [None if v == '\\N' else v
                        for v in line[4:].split('\t')]
                rows.append(vals)
            elif line == 'END':
                break
            elif line.startswith('ERR:') or line == '':
                return None
        return rows

    # ─── Database API (database.py ile uyumlu) ────────────

    def get_all_records(self) -> List[Dict]:
        from models import COLUMNS
        rows = self._query(f'SELECT * FROM [{self.table_name}] ORDER BY PROGRAM_NO')
        if rows is None:
            return []
        # Sütun adlarını al
        self._proc.stdin.write(
            f'SELECT * FROM [{self.table_name}] WHERE 1=0\n')
        self._proc.stdin.flush()
        col_line = self._proc.stdout.readline().rstrip('\n')
        end_line = self._proc.stdout.readline()  # END
        if col_line.startswith('COLS:'):
            cols = col_line[5:].split('\t')
        else:
            cols = COLUMNS
        return [dict(zip(cols, r)) for r in rows]

    def get_next_program_no(self) -> int:
        resp = self._send(
            f'SELECT COUNT(*) FROM [{self.table_name}]')
        if resp.startswith('COUNT:'):
            count = int(resp[6:])
            if count == 0:
                return 1
        # MAX sorgusu
        rows = self._query(
            f'SELECT MAX(PROGRAM_NO) FROM [{self.table_name}]')
        if rows and rows[0] and rows[0][0] not in (None, '\\N', ''):
            try:
                return int(float(rows[0][0])) + 1
            except Exception:
                pass
        return 1

    def insert_record(self, record: Dict) -> Tuple[bool, str]:
        from models import COLUMNS, NUMERIC_COLS
        cols = [c for c in COLUMNS if c in record]
        vals = []
        for c in cols:
            v = record.get(c)
            if v is None or str(v).strip() in ('', 'None'):
                vals.append('NULL')
            elif c in NUMERIC_COLS:
                try:
                    vals.append(str(float(v)))
                except Exception:
                    vals.append('NULL')
            else:
                escaped = str(v).replace("'", "''")
                vals.append(f"'{escaped}'")

        col_str = ', '.join(f'[{c}]' for c in cols)
        val_str = ', '.join(vals)
        sql = f'INSERT INTO [{self.table_name}] ({col_str}) VALUES ({val_str})'
        ok, msg = self._execute(sql)
        if ok:
            self._execute('COMMIT')
        return ok, msg or 'Kayıt eklendi.'

    def update_record(self, program_no: int, record: Dict) -> Tuple[bool, str]:
        from models import COLUMNS, NUMERIC_COLS
        cols = [c for c in COLUMNS if c in record and c != 'PROGRAM_NO']
        parts = []
        for c in cols:
            v = record.get(c)
            if v is None or str(v).strip() in ('', 'None'):
                parts.append(f'[{c}]=NULL')
            elif c in NUMERIC_COLS:
                try:
                    parts.append(f'[{c}]={float(v)}')
                except Exception:
                    parts.append(f'[{c}]=NULL')
            else:
                escaped = str(v).replace("'", "''")
                parts.append(f"[{c}]='{escaped}'")
        sql = (f'UPDATE [{self.table_name}] SET '
               f'{", ".join(parts)} WHERE [PROGRAM_NO]={program_no}')
        ok, msg = self._execute(sql)
        if ok:
            self._execute('COMMIT')
        return ok, msg or 'Güncellendi.'

    def delete_record(self, program_no: int) -> Tuple[bool, str]:
        ok, msg = self._execute(
            f'DELETE FROM [{self.table_name}] WHERE [PROGRAM_NO]={program_no}')
        if ok:
            self._execute('COMMIT')
        return ok, msg or f'#{program_no} silindi.'

    def clear_all_records(self) -> Tuple[bool, str]:
        ok, msg = self._execute(f'DELETE FROM [{self.table_name}]')
        if ok:
            self._execute('COMMIT')
        return ok, msg or 'Temizlendi.'

    def append_code_to_record(self, program_no: int, code_str: str) -> Tuple[bool, str]:
        rows = self._query(
            f'SELECT [CODE] FROM [{self.table_name}] WHERE [PROGRAM_NO]={program_no}')
        if not rows:
            return False, f'#{program_no} bulunamadı.'
        existing = (rows[0][0] or '') if rows[0][0] not in (None, '\\N') else ''
        new_code = (existing + code_str).replace("'", "''")
        ok, msg = self._execute(
            f"UPDATE [{self.table_name}] SET [CODE]='{new_code}' "
            f"WHERE [PROGRAM_NO]={program_no}")
        if ok:
            self._execute('COMMIT')
        return ok, f'#{program_no} CODE güncellendi.'

    def replace_code_in_record(self, program_no: int, code_str: str) -> Tuple[bool, str]:
        escaped = code_str.replace("'", "''")
        ok, msg = self._execute(
            f"UPDATE [{self.table_name}] SET [CODE]='{escaped}' "
            f"WHERE [PROGRAM_NO]={program_no}")
        if ok:
            self._execute('COMMIT')
        return ok, f'#{program_no} CODE yenilendi.'

    def disconnect(self):
        if self._proc:
            try:
                self._proc.stdin.close()
                self._proc.wait(timeout=3)
            except Exception:
                self._proc.kill()
        self._proc = None

    @property
    def connected(self) -> bool:
        return self._proc is not None and self._proc.poll() is None
