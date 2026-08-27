"""
database.py

Windows : pyodbc + Microsoft Access ODBC Driver → MDB'ye yazar
Mac/Linux: SQLite geliştirme modu → aynı veriler SQLite'a yazar
           + yanında otomatik Excel dosyası oluşturulur/güncellenir

Excel dosyası: seçilen dosyanın yanına _data.xlsx olarak kaydedilir.
Örnek: Winsa70_Kanat.mdb  →  Winsa70_Kanat_data.xlsx
"""

import os
import platform
from typing import List, Dict, Optional, Tuple

from models import COLUMNS


def _pd():
    """Pandas'ı gerektiğinde yükle (başlangıç hızı için)."""
    import pandas as _pandas
    return _pandas

# Sayısal sütunlar
NUMERIC_COLS = {
    'PROGRAM_NO', 'INCH_MM', 'POSE_NO', 'TROLLEY', 'UNIT',
    'LEFT_ANGLE', 'RIGHT_ANGLE', 'SIDE', 'CUTTED', 'HEIGHT',
    'PAIR', 'BAR_NO', 'PICE_NO', 'WIDTH', 'FRAME_NO',
    'ROBOT_Y', 'ROBOT_Z', 'ROBOT_VERTICAL'
}


class MDBError(Exception):
    pass


class Database:
    """
    MDB / SQLite veritabanı yöneticisi.
    Her yazma işleminin ardından yanındaki .xlsx dosyasını da günceller.
    """

    def __init__(self):
        self.conn        = None
        self.cursor      = None
        self.db_path     = None
        self.table_name  = None
        self._is_sqlite  = False
        self._excel_path = None   # otomatik Excel çıktısı
        self._batch_mode = False  # toplu yazma sırasında Excel sync atlanır

    # ─────────────────────────────────────────────────────
    # Bağlantı
    # ─────────────────────────────────────────────────────

    def connect(self, db_path: str) -> Tuple[bool, str]:
        self.db_path = db_path
        if platform.system() == 'Windows':
            return self._connect_mdb(db_path)
        else:
            return self._connect_sqlite(db_path)

    def _connect_mdb(self, db_path: str) -> Tuple[bool, str]:
        try:
            import pyodbc
        except ImportError:
            return False, "pyodbc kütüphanesi bulunamadı.\npip install pyodbc"

        drivers = [
            r'Microsoft Access Driver (*.mdb, *.accdb)',
            r'Microsoft Access Driver (*.mdb)',
        ]
        conn = None
        for drv in drivers:
            try:
                conn = pyodbc.connect(f'DRIVER={{{drv}}};DBQ={db_path};')
                break
            except Exception:
                continue

        if conn is None:
            return False, (
                "Microsoft Access ODBC sürücüsü bulunamadı.\n\n"
                "Çözüm: Microsoft Access Database Engine 2016 Redistributable\n"
                "https://www.microsoft.com/en-us/download/details.aspx?id=54920"
            )

        self.conn   = conn
        self.cursor = conn.cursor()
        self._is_sqlite = False
        self._setup_excel_path()

        ok, msg = self._detect_table()
        if not ok:
            return False, msg
        return True, f"Bağlandı: {os.path.basename(db_path)}  |  Tablo: {self.table_name}"

    def _connect_sqlite(self, db_path: str) -> Tuple[bool, str]:
        """Mac/Linux: SQLite ile çalışır, yan Excel dosyası oluşturur."""
        import sqlite3
        sqlite_path = db_path.replace('.mdb', '_data.sqlite').replace('.accdb', '_data.sqlite')
        if sqlite_path == db_path:
            sqlite_path = db_path + '.sqlite'

        self.conn = sqlite3.connect(sqlite_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._is_sqlite = True
        self.table_name = 'KANAT'
        self._setup_excel_path()

        # Tabloyu oluştur
        cols_def = []
        for col in COLUMNS:
            if col in NUMERIC_COLS:
                cols_def.append(f'"{col}" REAL')
            else:
                cols_def.append(f'"{col}" TEXT')
        self.cursor.execute(
            f'CREATE TABLE IF NOT EXISTS "{self.table_name}" ({", ".join(cols_def)})')
        self.conn.commit()

        base  = os.path.basename(sqlite_path)
        excel = self._excel_path or '—'
        # Konsolda tam yolu göster
        print(f'[DB] SQLite  : {sqlite_path}')
        print(f'[DB] Excel   : {excel}')
        return True, (
            f"[Mac modu] SQLite: {base}  |  Tablo: {self.table_name}\n"
            f"Excel çıktısı: {os.path.basename(excel)}\n"
            f"Konum: {os.path.dirname(excel)}"
        )

    def _setup_excel_path(self):
        """Seçilen dosyanın yanına Excel yolu belirler."""
        if self.db_path:
            base = os.path.splitext(self.db_path)[0]
            # SQLite için sqlite yolunu kullan
            if self._is_sqlite:
                sqlite_path = self.db_path.replace('.mdb', '_data.sqlite')
                base = os.path.splitext(sqlite_path)[0].replace('_data', '')
            self._excel_path = base + '_data.xlsx'

    def _detect_table(self) -> Tuple[bool, str]:
        try:
            tables = [
                row.table_name
                for row in self.cursor.tables(tableType='TABLE')
                if not row.table_name.startswith('MSys')
            ]
            if not tables:
                return False, "MDB dosyasında kullanıcı tablosu bulunamadı."
            self.table_name = tables[0]
            return True, ""
        except Exception as e:
            return False, f"Tablo tespiti hatası: {e}"

    def disconnect(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        self.conn = self.cursor = self.table_name = None

    @property
    def connected(self) -> bool:
        return self.conn is not None and self.table_name is not None

    # ─────────────────────────────────────────────────────
    # Excel senkronizasyonu
    # ─────────────────────────────────────────────────────

    def begin_batch(self):
        """Toplu yazma modu: insert/update/delete sırasında Excel sync atlanır."""
        self._batch_mode = True

    def end_batch(self):
        """Toplu yazma modunu kapat ve tek seferlik Excel sync yap."""
        self._batch_mode = False
        self._sync_excel()

    def _sync_excel(self):
        """Tüm kayıtları Excel dosyasına yazar (her değişiklikte çağrılır)."""
        if not self._excel_path or self._batch_mode:
            return
        try:
            pd = _pd()
            records = self.get_all_records()
            df = pd.DataFrame(records, columns=COLUMNS)
            df.to_excel(self._excel_path, index=False)
        except Exception as e:
            import sys
            print(f'[Excel UYARI] {self._excel_path}: {e}', file=sys.stderr)

    # ─────────────────────────────────────────────────────
    # Okuma
    # ─────────────────────────────────────────────────────

    def get_all_records(self) -> List[Dict]:
        self._check()
        sql = f'SELECT * FROM "{self.table_name}" ORDER BY PROGRAM_NO'
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        if self._is_sqlite:
            cols = [d[0] for d in self.cursor.description]
            return [dict(zip(cols, row)) for row in rows]
        else:
            cols = [d[0] for d in self.cursor.description]
            return [dict(zip(cols, row)) for row in rows]

    def get_next_program_no(self) -> int:
        self._check()
        sql = f'SELECT MAX(PROGRAM_NO) FROM "{self.table_name}"'
        self.cursor.execute(sql)
        val = self.cursor.fetchone()[0]
        return 1 if val is None else int(val) + 1

    # ─────────────────────────────────────────────────────
    # Yazma
    # ─────────────────────────────────────────────────────

    def insert_record(self, record: Dict) -> Tuple[bool, str]:
        self._check()
        try:
            cols = [c for c in COLUMNS if c in record]
            placeholders = ','.join(['?'] * len(cols))
            col_str = ', '.join(f'"{c}"' for c in cols)
            sql = f'INSERT INTO "{self.table_name}" ({col_str}) VALUES ({placeholders})'
            vals = [record.get(c) for c in cols]
            self.cursor.execute(sql, vals)
            self.conn.commit()
            self._sync_excel()
            return True, "Kayıt eklendi."
        except Exception as e:
            return False, f"Kayıt eklenemedi: {e}"

    def update_record(self, program_no: int, record: Dict) -> Tuple[bool, str]:
        self._check()
        try:
            cols = [c for c in COLUMNS if c in record and c != 'PROGRAM_NO']
            set_str = ', '.join(f'"{c}"=?' for c in cols)
            sql = f'UPDATE "{self.table_name}" SET {set_str} WHERE "PROGRAM_NO"=?'
            vals = [record.get(c) for c in cols] + [program_no]
            self.cursor.execute(sql, vals)
            self.conn.commit()
            self._sync_excel()
            return True, "Kayıt güncellendi."
        except Exception as e:
            return False, f"Güncelleme hatası: {e}"

    def delete_record(self, program_no: int) -> Tuple[bool, str]:
        self._check()
        try:
            self.cursor.execute(
                f'DELETE FROM "{self.table_name}" WHERE "PROGRAM_NO"=?', (program_no,))
            self.conn.commit()
            self._sync_excel()
            return True, f"Kayıt #{program_no} silindi."
        except Exception as e:
            return False, f"Silme hatası: {e}"

    def clear_all_records(self) -> Tuple[bool, str]:
        self._check()
        try:
            self.cursor.execute(f'DELETE FROM "{self.table_name}"')
            self.conn.commit()
            self._sync_excel()
            return True, "Tablo temizlendi."
        except Exception as e:
            return False, f"Temizleme hatası: {e}"

    def update_robot_position(self, program_no: int,
                              robot_y_x10: int, robot_z_x10: int,
                              robot_vertical: int = 0) -> Tuple[bool, str]:
        """PROGRAM_NO'ya sahip kaydın ROBOT_Y, ROBOT_Z, ROBOT_VERTICAL alanlarını günceller."""
        self._check()
        try:
            self.cursor.execute(
                f'UPDATE "{self.table_name}" '
                f'SET "ROBOT_Y"=?, "ROBOT_Z"=?, "ROBOT_VERTICAL"=? '
                f'WHERE "PROGRAM_NO"=?',
                (robot_y_x10, robot_z_x10, robot_vertical, program_no))
            self.conn.commit()
            self._sync_excel()   # Excel'i de güncelle
            return True, f"#{program_no} robot konumu güncellendi."
        except Exception as e:
            return False, f"Güncelleme hatası: {e}"

    def update_robot_all_same_stock(self, stock_code: str,
                                     robot_y: int, robot_z: int,
                                     robot_vertical: int = 0) -> Tuple[bool, str]:
        """Aynı STOCK_CODE'a sahip TÜM kayıtların robot konumunu günceller."""
        self._check()
        try:
            self.cursor.execute(
                f'UPDATE "{self.table_name}" '
                f'SET "ROBOT_Y"=?, "ROBOT_Z"=?, "ROBOT_VERTICAL"=? '
                f'WHERE "STOCK_CODE"=?',
                (robot_y, robot_z, robot_vertical, stock_code))
            count = self.cursor.rowcount
            self.conn.commit()
            self._sync_excel()
            return True, f'Stok {stock_code[:8]} → {count} kayıt güncellendi.'
        except Exception as e:
            return False, f'Güncelleme hatası: {e}'

    def replace_code_in_record(self, program_no: int, code_str: str) -> Tuple[bool, str]:
        self._check()
        try:
            self.cursor.execute(
                f'UPDATE "{self.table_name}" SET "CODE"=? WHERE "PROGRAM_NO"=?',
                (code_str, program_no))
            self.conn.commit()
            self._sync_excel()
            return True, f"#{program_no} CODE alanı yenilendi."
        except Exception as e:
            return False, f"Güncelleme hatası: {e}"

    def append_code_to_record(self, program_no: int, code_str: str) -> Tuple[bool, str]:
        self._check()
        try:
            self.cursor.execute(
                f'SELECT "CODE" FROM "{self.table_name}" WHERE "PROGRAM_NO"=?',
                (program_no,))
            row = self.cursor.fetchone()
            if row is None:
                return False, f"Program No {program_no} bulunamadı."
            existing = (row[0] or '').strip()
            new_code = existing + code_str
            self.cursor.execute(
                f'UPDATE "{self.table_name}" SET "CODE"=? WHERE "PROGRAM_NO"=?',
                (new_code, program_no))
            self.conn.commit()
            self._sync_excel()
            return True, f"#{program_no} kaydına kod eklendi."
        except Exception as e:
            return False, f"Kod yazma hatası: {e}"

    # ─────────────────────────────────────────────────────
    # Excel ile içe / dışa aktarım
    # ─────────────────────────────────────────────────────

    def export_to_excel(self, out_path: str) -> Tuple[bool, str]:
        self._check()
        try:
            pd = _pd()
            records = self.get_all_records()
            df = pd.DataFrame(records, columns=COLUMNS)
            df.to_excel(out_path, index=False)
            return True, f"{len(df)} kayıt dışa aktarıldı."
        except Exception as e:
            return False, f"Dışa aktarım hatası: {e}"

    def import_from_excel(self, xlsx_path: str, clear_first: bool = True) -> Tuple[bool, str]:
        self._check()
        try:
            pd = _pd()
            df = pd.read_excel(xlsx_path, dtype=str)
            df = df.where(pd.notna(df), None)
            df.columns = [c.strip().upper() for c in df.columns]

            if clear_first:
                ok, msg = self.clear_all_records()
                if not ok:
                    return False, msg

            count = 0
            for _, row in df.iterrows():
                record = {}
                for col in COLUMNS:
                    if col in df.columns:
                        val = row[col]
                        if col in NUMERIC_COLS and val is not None:
                            try:
                                val = float(val)
                            except (ValueError, TypeError):
                                val = None
                        record[col] = val
                ok, msg = self.insert_record(record)
                if ok:
                    count += 1
            return True, f"{count} kayıt aktarıldı."
        except Exception as e:
            return False, f"İçe aktarım hatası: {e}"

    # ─────────────────────────────────────────────────────
    # Yardımcı
    # ─────────────────────────────────────────────────────

    def _check(self):
        if not self.connected:
            raise MDBError("Veritabanı bağlantısı yok.")

    @property
    def excel_path(self) -> Optional[str]:
        return self._excel_path
