"""
ui/dialog_batch.py

Toplu Kesim Listesi Giriş Formu
--------------------------------
1. Üstte ortak bilgiler (stok, müşteri, bar boyu, tip…)
2. 15 satırlık kesim tablosu  (boy, sol/sağ açı, taraf, açıklama)
3. "MDB'ye Yaz" → temizle/devam sor → barlara böl → kaydet

Bar atama mantığı:
  - Kesim payı (testere eni) 6 mm = 60 (×10)
  - Her bar dolduğunda yeni bara geç
  - Son parçanın fire boyu hesaplanır
"""

import os
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QSizePolicy, QAbstractItemView, QFrame, QSplitter, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtGui import QFont, QColor

from models import PROFILE_TYPES, COLOR_CODES, SIDES
from ui.kiosk import apply_kiosk

SAW_KERF = 60   # testere payı ×10 (6 mm)


class BatchEntryDialog(QDialog):
    """
    Sinyaller
    ---------
    records_ready(list[dict])  : oluşturulan kayıt listesi
    """
    records_ready = Signal(list)

    def __init__(self, parent=None, db=None, next_program_no: int = 1,
                 existing_records: list = None):
        super().__init__(parent)
        self._db = db                       # Database nesnesi (bağlı olabilir)
        self._next_no = next_program_no
        self.setWindowTitle("Toplu Kesim Listesi Girişi")
        self.setMinimumSize(860, 680)
        self.resize(980, 740)
        apply_kiosk(self)   # tam ekran, çerçevesiz kiosk modu
        self._setup_ui()
        self._apply_style()

        # Mevcut kayıtları tabloya yükle
        if existing_records:
            self._load_existing_records(existing_records)

    # ─────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── MDB durum satırı ─────────────────────────────
        mdb_row = QHBoxLayout()
        self._lbl_mdb = QLabel("MDB: bağlı değil")
        self._lbl_mdb.setStyleSheet("color:#ff6666; font-size:12px;")
        mdb_row.addWidget(QLabel("💾 Veritabanı:"))
        mdb_row.addWidget(self._lbl_mdb, 1)
        self._update_mdb_label()
        root.addLayout(mdb_row)

        left_w = QWidget()
        main = QVBoxLayout(left_w)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(6)
        root.addWidget(left_w, 1)

        # ── Ortak bilgiler ───────────────────────────────
        grp_common = QGroupBox("Ortak Bilgiler")
        grid = QGridLayout(grp_common)
        grid.setSpacing(8)

        # Satır 0
        grid.addWidget(QLabel("Stok Kodu (16 kr):"), 0, 0)
        self._ed_stock_code = QLineEdit(self._gen_stock_code())
        self._ed_stock_code.setMaxLength(16)
        self._ed_stock_code.setToolTip("Tam 16 karakter olmalıdır")
        grid.addWidget(self._ed_stock_code, 0, 1)

        grid.addWidget(QLabel("Stok Adı:"), 0, 2)
        self._ed_stock_name = QLineEdit()
        self._ed_stock_name.setMaxLength(24)
        grid.addWidget(self._ed_stock_name, 0, 3)

        # Satır 1
        grid.addWidget(QLabel("Müşteri Kodu:"), 1, 0)
        self._ed_cust_code = QLineEdit()
        self._ed_cust_code.setMaxLength(16)
        grid.addWidget(self._ed_cust_code, 1, 1)

        grid.addWidget(QLabel("Müşteri Adı:"), 1, 2)
        self._ed_cust_name = QLineEdit()
        self._ed_cust_name.setMaxLength(24)
        grid.addWidget(self._ed_cust_name, 1, 3)

        # Satır 2
        grid.addWidget(QLabel("Sipariş No:"), 2, 0)
        self._ed_order = QLineEdit()
        self._ed_order.setMaxLength(6)
        grid.addWidget(self._ed_order, 2, 1)

        grid.addWidget(QLabel("Tip:"), 2, 2)
        self._cb_type = QComboBox()
        for k, v in PROFILE_TYPES.items():
            self._cb_type.addItem(v, k)
        grid.addWidget(self._cb_type, 2, 3)

        # Satır 3
        grid.addWidget(QLabel("Bar Boyu (mm):"), 3, 0)
        self._sp_bar = QDoubleSpinBox()
        self._sp_bar.setRange(100, 20000)
        self._sp_bar.setValue(6000)
        self._sp_bar.setDecimals(0)
        self._sp_bar.setSuffix(" mm")
        self._sp_bar.setToolTip("Varsayılan 6000 mm — değiştirilebilir")
        grid.addWidget(self._sp_bar, 3, 1)

        grid.addWidget(QLabel("Profil Yüksekliği (mm):"), 3, 2)
        h3 = QHBoxLayout()
        self._sp_height = QDoubleSpinBox()
        self._sp_height.setRange(0, 500)
        self._sp_height.setValue(70)
        self._sp_height.setDecimals(1)
        self._sp_height.setSuffix(" mm")
        h3.addWidget(self._sp_height, 1)
        btn_dxf_dims = QPushButton("📐 DXF")
        btn_dxf_dims.setFixedWidth(55)
        btn_dxf_dims.setFixedHeight(30)
        btn_dxf_dims.setToolTip("DXF'ten profil yükseklik ve genişliğini otomatik hesapla")
        btn_dxf_dims.setStyleSheet(
            "QPushButton{background:#1a3a6a;color:#fff;border-radius:4px;font-size:11px;}"
            "QPushButton:hover{background:#265098;}")
        btn_dxf_dims.clicked.connect(self._auto_dims_from_dxf)
        h3.addWidget(btn_dxf_dims)
        grid.addLayout(h3, 3, 3)

        # Satır 4
        grid.addWidget(QLabel("Profil Genişliği (mm):"), 4, 0)
        self._sp_width = QDoubleSpinBox()
        self._sp_width.setRange(0, 500)
        self._sp_width.setValue(66)
        self._sp_width.setDecimals(0)
        self._sp_width.setSuffix(" mm")
        grid.addWidget(self._sp_width, 4, 1)

        grid.addWidget(QLabel("Renk Kodu:"), 4, 2)
        self._cb_color = QComboBox()
        for k, v in COLOR_CODES.items():
            self._cb_color.addItem(v, k)
        grid.addWidget(self._cb_color, 4, 3)

        # ── Dikey ayırıcı ───────────────────────────────
        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.VLine)
        sep_v.setStyleSheet("color:#3a3a55;")
        grid.addWidget(sep_v, 0, 4, 5, 1)   # 5 satır boyunca

        # ── Robot Yakalama Noktası (sağ blok) ────────────
        lbl_robot = QLabel("🤖  Robot Yakalama")
        lbl_robot.setStyleSheet(
            "color:#f8c12f; font-size:12px; font-weight:bold;")
        grid.addWidget(lbl_robot, 0, 5, 1, 2)

        self._btn_robot_pick = QPushButton("📍  DXF'ten Al  (Y, Z)")
        self._btn_robot_pick.setMinimumHeight(36)
        self._btn_robot_pick.setStyleSheet(
            "QPushButton{background:#1a4aaa;color:#fff;border-radius:5px;"
            "font-size:12px;font-weight:bold;}"
            "QPushButton:hover{background:#2a5acc;}"
        )
        self._btn_robot_pick.clicked.connect(self._pick_robot_yz)
        grid.addWidget(self._btn_robot_pick, 1, 5, 1, 2)

        # Y gösterge
        grid.addWidget(QLabel("Robot Y (mm):"), 2, 5)
        self._lbl_robot_y = QLabel("—")
        self._lbl_robot_y.setStyleSheet(
            "background:#252540; color:#f8c12f; font-size:13px; font-weight:bold;"
            " border:1px solid #3a3a55; border-radius:4px; padding:4px 8px;")
        grid.addWidget(self._lbl_robot_y, 2, 6)

        # Z gösterge
        grid.addWidget(QLabel("Robot Z (mm):"), 3, 5)
        self._lbl_robot_z = QLabel("—")
        self._lbl_robot_z.setStyleSheet(
            "background:#252540; color:#f8c12f; font-size:13px; font-weight:bold;"
            " border:1px solid #3a3a55; border-radius:4px; padding:4px 8px;")
        grid.addWidget(self._lbl_robot_z, 3, 6)

        # ROBOT_VERTICAL seçimi
        grid.addWidget(QLabel("Yönelim:"), 4, 5)
        self._cb_robot_vert = QComboBox()
        self._cb_robot_vert.addItem("Yatay (0)", "0")
        self._cb_robot_vert.addItem("Dikey (1)", "1")
        grid.addWidget(self._cb_robot_vert, 4, 6)

        # İç değişkenler
        self._robot_y_mm: float = 0.0
        self._robot_z_mm: float = 0.0

        # DXF yüklüyse boyutları otomatik al
        self._try_auto_dims()

        # Satır 5: Bar No
        main.addWidget(grp_common)

        # ── Kesim tablosu ────────────────────────────────
        grp_table = QGroupBox("Kesim Listesi")
        tbl_lay = QVBoxLayout(grp_table)

        # Tablo başlık toolbar — Bar No burada
        tbl_top = QHBoxLayout()
        btn_add_row = QPushButton("➕ Satır Ekle")
        btn_add_row.clicked.connect(self._add_row)
        btn_del_row = QPushButton("🗑 Seçili Sil")
        btn_del_row.clicked.connect(self._del_row)
        btn_fill_angles = QPushButton("↺ Açıları Doldur (450)")
        btn_fill_angles.setToolTip("Tüm boş açı hücrelerini 450 yap")
        btn_fill_angles.clicked.connect(self._fill_angles)
        tbl_top.addWidget(btn_add_row)
        tbl_top.addWidget(btn_del_row)
        tbl_top.addWidget(btn_fill_angles)

        tbl_top.addStretch()
        lbl_hint = QLabel("💡 Kesim boylarını mm olarak girin  (örn: 1050)")
        lbl_hint.setStyleSheet("color:#888; font-size:11px;")
        tbl_top.addWidget(lbl_hint)
        tbl_lay.addLayout(tbl_top)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            "Bar No", "Kesim Boyu (mm)", "Sol Açı (°)", "Sağ Açı (°)",
            "Taraf", "Açıklama 1", "Açıklama 2"
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._table.setColumnWidth(0, 66)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setMinimumHeight(300)
        tbl_lay.addWidget(self._table)
        main.addWidget(grp_table, 1)

        # 15 başlangıç satırı
        for _ in range(15):
            self._add_row()

        # ── Alt butonlar (sol panel) ──────────────────────
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#444;")
        main.addWidget(sep)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_write = QPushButton("✅  MDB'ye Yaz")
        self._btn_write.setFixedHeight(40)
        self._btn_write.setMinimumWidth(160)
        self._btn_write.setStyleSheet(
            "QPushButton{background:#226622;color:white;border-radius:6px;"
            "font-size:13px;font-weight:bold;}"
            "QPushButton:hover{background:#338833;}"
        )
        self._btn_write.clicked.connect(self._on_write)
        btn_row.addWidget(self._btn_write)
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedHeight(40); btn_cancel.setMinimumWidth(90)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        main.addLayout(btn_row)

        # Kayıt tablosu artık Profil İşlemleri penceresinde

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background:#1e1e2e; color:#e0e0e0; }
            QGroupBox { color:#f8c12f; font-size:12px; font-weight:bold;
                        border:1px solid #444; border-radius:5px;
                        margin-top:8px; padding-top:10px; }
            QGroupBox::title { subcontrol-origin:margin; left:8px; }
            QLabel { color:#e0e0e0; font-size:13px; }
            QLineEdit { background:#252540; color:#ffffff; border:1px solid #556;
                        border-radius:4px; padding:5px; font-size:13px; }
            QDoubleSpinBox { background:#252540; color:#ffffff; border:1px solid #556;
                             border-radius:4px; padding:4px; font-size:13px; }
            QComboBox { background:#252540; color:#ffffff; border:1px solid #556;
                        border-radius:4px; padding:4px; font-size:13px; }
            QComboBox QAbstractItemView { background:#252540; color:#ffffff; }
            QPushButton { background:#2e2e42; color:#e0e0e0; border:1px solid #555;
                          border-radius:5px; padding:6px 14px; font-size:13px; }
            QPushButton:hover { background:#3a3a55; color:#ffffff; }
            QTableWidget {
                background:#16162a; color:#ffffff;
                font-size:13px; gridline-color:#2a2a45;
                border:1px solid #3a3a55;
                alternate-background-color:#1e1e35;
            }
            QTableWidget::item { color:#ffffff; padding:4px; }
            QTableWidget::item:alternate { color:#ffffff; background:#1e1e35; }
            QTableWidget::item:selected { background:#4a30a0; color:#ffffff; }
            QHeaderView::section {
                background:#252540; color:#f8c12f;
                font-size:12px; font-weight:bold;
                border:none; border-bottom:1px solid #3a3a55;
                padding:6px;
            }
        """)

    # ─────────────────────────────────────────────────────
    # Tablo yönetimi
    # ─────────────────────────────────────────────────────

    @staticmethod
    def _white_item(text: str, align=Qt.AlignCenter) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(align)
        item.setForeground(QColor("#ffffff"))
        return item

    def _current_bar_no(self) -> int:
        """Tablodaki son satırın Bar No'sunu döndürür (yoksa 1)."""
        r = self._table.rowCount()
        if r > 0:
            sp = self._table.cellWidget(r - 1, 0)
            if sp:
                return sp.value()
        return 1

    def _add_row(self):
        r = self._table.rowCount()
        self._table.insertRow(r)

        # Col 0: Bar No — QSpinBox (artık ilk sütun)
        sp_bar = QSpinBox()
        sp_bar.setRange(1, 9999)
        sp_bar.setValue(self._current_bar_no())
        sp_bar.setStyleSheet(
            "QSpinBox{background:#252540;color:#f8c12f;border:1px solid #556;"
            "border-radius:3px;padding:2px;font-size:12px;font-weight:bold;}"
        )
        self._table.setCellWidget(r, 0, sp_bar)

        # Col 1: Kesim boyu
        length_item = QTableWidgetItem("")
        length_item.setForeground(QColor("#ffffff"))
        length_item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(r, 1, length_item)

        # Col 2: Sol açı
        self._table.setItem(r, 2, self._white_item("45"))

        # Col 3: Sağ açı
        self._table.setItem(r, 3, self._white_item("45"))

        # Col 4: Taraf combobox
        cb = QComboBox()
        for k, v in SIDES.items():
            cb.addItem(v, k)
        cb.setStyleSheet(
            "QComboBox{background:#252540;color:#ffffff;border:1px solid #556;"
            "border-radius:3px;padding:3px;font-size:13px;}"
            "QComboBox QAbstractItemView{background:#252540;color:#ffffff;}"
        )
        self._table.setCellWidget(r, 4, cb)

        # Col 5-6: Açıklamalar
        self._table.setItem(r, 5, self._white_item("", Qt.AlignLeft))
        self._table.setItem(r, 6, self._white_item("", Qt.AlignLeft))

        self._table.setRowHeight(r, 36)

    def _del_row(self):
        rows = sorted({i.row() for i in self._table.selectedItems()}, reverse=True)
        for r in rows:
            self._table.removeRow(r)

    def _fill_angles(self):
        for r in range(self._table.rowCount()):
            for col in (2, 3):
                item = self._table.item(r, col)
                if item and item.text().strip() == "":
                    item.setText("45")

    # ─────────────────────────────────────────────────────
    # Mevcut kayıt yükleme
    # ─────────────────────────────────────────────────────

    def _load_existing_records(self, records: list):
        """
        MDB'den okunan kayıtları tabloya yükler.
        Ortak bilgileri (stok, müşteri, bar boyu…) ilk kayıttan alır.
        Her satır: boy (LENGTH/10), açılar, taraf, açıklamalar.
        """
        if not records:
            return

        # Mevcut boş satırları temizle
        self._table.setRowCount(0)

        # ── Ortak bilgileri ilk kayıttan doldur ──────────
        first = records[0]
        self._ed_stock_code.setText(str(first.get('STOCK_CODE', '') or ''))
        self._ed_stock_name.setText(str(first.get('STOCK_NAME', '') or ''))
        self._ed_cust_code.setText( str(first.get('CUSTOMER_CODE', '') or ''))
        self._ed_cust_name.setText( str(first.get('CUSTOMER_NAME', '') or ''))
        self._ed_order.setText(     str(first.get('ORDER_NO', '') or ''))

        # Bar boyu
        try:
            total_x10 = float(first.get('TOTAL_SIZE', 0) or 0)
            if total_x10 > 0:
                self._sp_bar.setValue(total_x10 / 10)
        except Exception:
            pass

        # Profil yüksekliği / genişliği
        try:
            self._sp_height.setValue(float(first.get('HEIGHT', 0) or 0) / 10)
        except Exception:
            pass
        try:
            self._sp_width.setValue(float(first.get('WIDTH', 0) or 0) / 10)
        except Exception:
            pass

        # Tip
        type_val = str(first.get('TYPE', '') or '')
        idx = self._cb_type.findData(type_val)
        if idx >= 0:
            self._cb_type.setCurrentIndex(idx)

        # Robot Y/Z
        try:
            self._robot_y_mm = float(first.get('ROBOT_Y', 0) or 0) / 10
            self._robot_z_mm = float(first.get('ROBOT_Z', 0) or 0) / 10
        except Exception:
            pass

        # ── Her kayıt için satır ekle ─────────────────────
        for rec in records:
            # LENGTH ×10 formatından mm'e çevir
            try:
                length_mm = float(rec.get('LENGTH', 0) or 0) / 10
            except Exception:
                continue
            if length_mm <= 0:
                continue

            try:
                left_angle  = float(rec.get('LEFT_ANGLE',  450) or 450) / 10
                right_angle = float(rec.get('RIGHT_ANGLE', 450) or 450) / 10
            except Exception:
                left_angle = right_angle = 45.0

            side_val = str(rec.get('SIDE', '1') or '1')
            expl1    = str(rec.get('EXPLANATION1', '') or '')
            expl2    = str(rec.get('EXPLANATION2', '') or '')
            bar_no   = int(rec.get('BAR_NO', 1) or 1)

            # Satır ekle
            self._add_row()
            r = self._table.rowCount() - 1

            # Bar no spinbox
            sp = self._table.cellWidget(r, 0)
            if sp:
                sp.setValue(bar_no)

            # Boy (sadece okunabilir stil)
            item = self._table.item(r, 1)
            if item:
                item.setText(f"{length_mm:.0f}")

            # Açılar
            la = self._table.item(r, 2)
            ra = self._table.item(r, 3)
            if la: la.setText(f"{left_angle:.1f}")
            if ra: ra.setText(f"{right_angle:.1f}")

            # Taraf
            cb = self._table.cellWidget(r, 4)
            if cb:
                idx2 = cb.findData(side_val)
                if idx2 >= 0:
                    cb.setCurrentIndex(idx2)

            # Açıklama
            e1 = self._table.item(r, 5)
            e2 = self._table.item(r, 6)
            if e1: e1.setText(expl1)
            if e2: e2.setText(expl2)

        # Yüklenen kayıt sayısını göster
        n = self._table.rowCount()
        self._lbl_mdb.setText(
            f"✅ {n} kayıt yüklendi — üzerine yazabilir veya yeni satır ekleyebilirsiniz")
        self._lbl_mdb.setStyleSheet("color:#80ff80; font-size:12px; font-weight:bold;")

    # ─────────────────────────────────────────────────────
    # MDB
    # ─────────────────────────────────────────────────────

    def _refresh_records(self):
        """Artık batch'te tablo yok — Profil İşlemleri penceresinde."""
        pass

    def _refresh_records_unused(self):
        """(Kullanılmıyor — taşındı)"""
        if not self._db or not self._db.connected:
            return
        try:
            records = self._db.get_all_records()
        except Exception:
            return
        for rec in records:
            r = self._rec_table.rowCount()
            self._rec_table.insertRow(r)

            # Prog# tam sayı olarak göster
            pno = rec.get('PROGRAM_NO', '')
            try:
                prog = str(int(float(pno)))
            except (TypeError, ValueError):
                prog = str(pno)

            # Yön: sadece numara (1,2,3,4)
            side_val = rec.get('SIDE', '')
            try:
                side_name = str(int(float(side_val))) if side_val not in ('', None) else '–'
            except (TypeError, ValueError):
                side_name = str(side_val) if side_val else '–'
            stok = str(rec.get('STOCK_NAME', '') or '')[:12]
            code = str(rec.get('CODE', '') or '')
            code_preview = code[:40] + ('…' if len(code) > 40 else '') if code else '–'

            items = [prog, side_name, stok, code_preview]
            for c, txt in enumerate(items):
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignCenter if c < 2 else Qt.AlignLeft | Qt.AlignVCenter)
                item.setForeground(QColor('#ffffff'))
                if c == 3:
                    item.setForeground(QColor('#56cfe1' if code else '#555'))
                    item.setFont(QFont('Courier New', 10))
                self._rec_table.setItem(r, c, item)
            self._rec_table.setRowHeight(r, 28)

        self._lbl_rec_count.setText(f"{len(records)} kayıt")

    # ─────────────────────────────────────────────────────
    # Robot Yakalama Noktası — DXF pick
    # ─────────────────────────────────────────────────────

    def _try_auto_dims(self):
        """Dialog açılınca DXF yüklüyse sessizce boyutları doldurur."""
        mw = self.parent()
        if not mw or not hasattr(mw, '_cur_segs') or not mw._cur_segs:
            return
        try:
            from dxf_loader import calc_profile_dimensions
            h, w = calc_profile_dimensions(mw._cur_segs)
            if h > 0:
                self._sp_height.setValue(h)
            if w > 0:
                self._sp_width.setValue(w)
        except Exception:
            pass

    def _auto_dims_from_dxf(self):
        """DXF'ten profil yükseklik ve genişliğini otomatik hesaplar."""
        mw = self.parent()
        if not mw or not hasattr(mw, '_cur_segs') or not mw._cur_segs:
            QMessageBox.information(self, 'DXF Yok',
                'Ana pencereden önce bir DXF dosyası yükleyin.')
            return
        from dxf_loader import calc_profile_dimensions
        h, w = calc_profile_dimensions(mw._cur_segs)
        self._sp_height.setValue(h)
        self._sp_width.setValue(w)
        QMessageBox.information(self, 'DXF\'ten Alındı',
            f'Profil Yüksekliği: {h} mm\n'
            f'Profil Genişliği (alt 30mm): {w} mm')

    def _pick_robot_yz(self):
        """DXF üzerinden Robot Y ve Z koordinatlarını al."""
        from PySide6.QtWidgets import QApplication
        mw = self.parent()
        if not mw or not hasattr(mw, '_viewport'):
            QMessageBox.information(self, 'Uyarı',
                'Ana pencereden DXF yükleyin, sonra bu butonu kullanın.')
            return
        if not mw._cur_segs:
            QMessageBox.information(self, 'Uyarı', 'Önce bir DXF dosyası yükleyin.')
            return

        # Dialog'u gizle, main window öne gelsin
        self.hide()
        mw.raise_()
        mw.activateWindow()
        QApplication.setActiveWindow(mw)

        mw._viewport.set_pick_mode(True)
        try:
            mw._viewport.point_selected.disconnect(self._on_robot_point_received)
        except Exception:
            pass
        mw._viewport.point_selected.connect(self._on_robot_point_received)
        mw.statusBar().showMessage(
            '📍  Robot Yakalama Noktası için DXF üzerine tıklayın (Y, Z alınacak)…', 0)

        self._btn_robot_pick.setText('⏳  DXF\'e tıklayın…')
        self._btn_robot_pick.setEnabled(False)

    def _on_robot_point_received(self, y: float, z: float):
        """Viewport tıklamasından robot Y ve Z koordinatını alır."""
        from PySide6.QtWidgets import QApplication
        mw = self.parent()
        if mw and hasattr(mw, '_viewport'):
            try:
                mw._viewport.point_selected.disconnect(self._on_robot_point_received)
            except Exception:
                pass
            mw.statusBar().showMessage('✅  Robot koordinatları alındı.', 3000)

        self._robot_y_mm = y
        self._robot_z_mm = z

        # ×10 formatında göster
        self._lbl_robot_y.setText(f'{y:.2f} mm  →  {int(round(y*10))}')
        self._lbl_robot_z.setText(f'{z:.2f} mm  →  {int(round(z*10))}')

        self._btn_robot_pick.setText('📍  DXF\'ten Al  (Y, Z)')
        self._btn_robot_pick.setEnabled(True)

        # Dialog'u tekrar göster ve öne getir
        self.show()
        self.raise_()
        self.activateWindow()
        QApplication.setActiveWindow(self)

    def _update_mdb_label(self):
        if self._db and self._db.connected:
            self._lbl_mdb.setText(f"✅ {os.path.basename(self._db.db_path)}")
            self._lbl_mdb.setStyleSheet("color:#44cc88; font-size:12px;")
        else:
            self._lbl_mdb.setText("❌ bağlı değil — ana pencereden MDB seçin")
            self._lbl_mdb.setStyleSheet("color:#ff6666; font-size:12px;")

    # ─────────────────────────────────────────────────────
    # Yaz
    # ─────────────────────────────────────────────────────

    def _on_write(self):
        if not self._db or not self._db.connected:
            QMessageBox.warning(self, "Uyarı",
                "MDB bağlantısı yok.\nAna pencereden '💾 MDB Bağlan' butonuna basın.")
            return

        # Stok kodu 16 karakter mi?
        sc = self._ed_stock_code.text().strip()
        if len(sc) != 16:
            QMessageBox.warning(self, "Hata",
                f"Stok kodu tam 16 karakter olmalı.\nŞu an: {len(sc)} karakter")
            return

        # Tablodan geçerli satırları topla
        rows = self._collect_rows()
        if not rows:
            QMessageBox.warning(self, "Uyarı", "Hiçbir kesim boyu girilmemiş.")
            return

        # ── 3 seçenekli yazma sorusu ─────────────────────────
        existing_count = 0
        try:
            existing_count = len(self._db.get_all_records())
        except Exception:
            pass

        mb = QMessageBox(self)
        mb.setWindowTitle("MDB'ye Nasıl Yazılsın?")
        mb.setIcon(QMessageBox.Question)
        mb.setText(
            f"MDB'de şu an <b>{existing_count}</b> kayıt var.\n"
            f"Girilecek kayıt sayısı: <b>{len(rows)}</b>\n\n"
            "Nasıl devam edilsin?"
        )

        btn_overwrite = mb.addButton(
            "🔄  Üstüne Yaz  (1'den başlat, çakışanları güncelle)",
            QMessageBox.AcceptRole)
        btn_clear = mb.addButton(
            "🗑  Temizle ve Yaz  (tümünü sil, yeniden başla)",
            QMessageBox.DestructiveRole)
        btn_append = mb.addButton(
            f"➕  İlave Et  ({existing_count + 1}'den devam et)",
            QMessageBox.YesRole)
        btn_cancel = mb.addButton("İptal", QMessageBox.RejectRole)
        mb.setDefaultButton(btn_append)
        mb.exec()

        clicked = mb.clickedButton()
        if clicked == btn_cancel:
            return

        if clicked == btn_clear:
            ok, msg = self._db.clear_all_records()
            if not ok:
                QMessageBox.critical(self, "Hata", msg)
                return
            start_no = 1

        elif clicked == btn_overwrite:
            # Mevcut kayıtları 1'den itibaren sil, sonra yenile
            start_no = 1
            end_no   = start_no + len(rows) - 1
            try:
                self._db.cursor.execute(
                    f'DELETE FROM "{self._db.table_name}" '
                    f'WHERE "PROGRAM_NO" >= ? AND "PROGRAM_NO" <= ?',
                    (start_no, end_no)
                )
                self._db.conn.commit()
            except Exception as e:
                QMessageBox.warning(self, "Uyarı", f"Eski kayıtlar silinemedi: {e}")

        else:  # İlave Et
            start_no = self._db.get_next_program_no()

        # Barlara böl ve kaydet
        records = self._build_records(rows, start_no)
        count = 0
        for rec in records:
            ok, msg = self._db.insert_record(rec)
            if ok:
                count += 1
            else:
                QMessageBox.warning(self, "Kayıt Hatası", msg)

        n_bars = max((r['BAR_NO'] for r in records), default=0)
        QMessageBox.information(self, "✅ Optimizasyon Tamamlandı",
            f"{count} parça MDB'ye yazıldı.\n"
            f"Bar sayısı: {n_bars}  (FFD optimizasyonu)\n"
            f"Program No: {start_no} – {start_no + count - 1}")
        self._refresh_records()   # Sağ tabloyu güncelle
        self.records_ready.emit(records)
        self.accept()

    # ─────────────────────────────────────────────────────
    # Veri işleme
    # ─────────────────────────────────────────────────────

    def _collect_rows(self):
        """Tablodan dolu satırları okur (0=BarNo,1=Boy,2=Sol,3=Sağ,4=Taraf,5=Acl1,6=Acl2)."""
        rows = []
        for r in range(self._table.rowCount()):
            len_item = self._table.item(r, 1)   # Kesim Boyu sütunu
            if not len_item or not len_item.text().strip():
                continue
            try:
                length_mm = float(len_item.text().strip())
            except ValueError:
                continue
            if length_mm <= 0:
                continue

            # Bar No (col 0)
            bar_sp = self._table.cellWidget(r, 0)
            bar_no = bar_sp.value() if bar_sp else 1

            la_item = self._table.item(r, 2)
            ra_item = self._table.item(r, 3)
            try:   left_angle  = float(la_item.text()) if la_item else 45.0
            except: left_angle = 45.0
            try:   right_angle  = float(ra_item.text()) if ra_item else 45.0
            except: right_angle = 45.0

            side_cb = self._table.cellWidget(r, 4)
            side = side_cb.currentData() if side_cb else "1"

            expl1_item = self._table.item(r, 5)
            expl2_item = self._table.item(r, 6)
            expl1 = expl1_item.text().strip() if expl1_item else ""
            expl2 = expl2_item.text().strip() if expl2_item else ""

            rows.append({
                "bar_no":      bar_no,
                "length_mm":   length_mm,
                "left_angle":  left_angle,
                "right_angle": right_angle,
                "side":        side,
                "expl1":       expl1,
                "expl2":       expl2,
            })
        return rows

    def _build_records(self, rows, start_no):
        """
        Satırları FFD (First Fit Decreasing) optimizasyonuyla barlara dağıtır.
        Akıllı Üretim'deki algoritmanın aynısı: ayarlardan blade/head/tail okunur,
        parçalar uzundan kısaya sıralanır, ilk sığan bara yerleştirilir.
        BAR_NO, PICE_NO ve REMAINING_LENGTH otomatik hesaplanır.
        """
        import settings as st

        bar_len_mm  = self._sp_bar.value()
        bar_len_x10 = int(bar_len_mm * 10)

        stock_code  = self._ed_stock_code.text().strip()
        stock_name  = self._ed_stock_name.text().strip()
        cust_code   = self._ed_cust_code.text().strip()
        cust_name   = self._ed_cust_name.text().strip()
        order_no    = self._ed_order.text().strip()
        type_val    = self._cb_type.currentData()
        color_code  = self._cb_color.currentData()
        height_x10  = int(self._sp_height.value() * 10)
        width_x10   = int(self._sp_width.value() * 10)

        # ── Optimizasyon ayarları ──────────────────────────────────────────
        cfg       = st.load_settings()
        blade     = cfg.get('blade_mm',       4)
        head      = cfg.get('head_waste_mm', 20)
        tail      = cfg.get('tail_waste_mm', 20)
        gap       = cfg.get('gap_mm',         0)
        n_trol    = cfg.get('trolley_count',       5)
        n_shelf   = cfg.get('shelves_per_trolley', 6)

        piece_gap = blade + gap
        usable    = max(0, bar_len_mm - head - tail)   # mm

        # ── FFD: uzundan kısaya sırala, orijinal sırayı sakla ─────────────
        indexed = list(enumerate(rows))   # (orijinal_idx, row)
        sorted_idx = sorted(indexed, key=lambda x: x[1]['length_mm'], reverse=True)

        # bar_no → kalan alan (mm)
        bar_remaining: dict = {}
        # bar_no → parça sayısı
        bar_count: dict     = {}
        # bar_no → toplam kesilen (mm)
        bar_used_mm: dict   = {}
        # orijinal idx → atanan bar_no / pice_no
        assigned_bar: dict  = {}

        cur_bar = 1

        for orig_idx, row in sorted_idx:
            length = row['length_mm']
            placed = False

            # Mevcut barlarda yer var mı?
            for bn in sorted(bar_remaining.keys()):
                n_in = bar_count.get(bn, 0)
                needed = length + (piece_gap if n_in > 0 else 0)
                if bar_remaining[bn] >= needed:
                    bar_remaining[bn] -= needed
                    bar_count[bn]      = n_in + 1
                    bar_used_mm[bn]    = bar_used_mm.get(bn, 0) + length
                    assigned_bar[orig_idx] = bn
                    placed = True
                    break

            if not placed:
                # Yeni bar aç
                bn = cur_bar; cur_bar += 1
                needed = length   # ilk parça: gap yok
                bar_remaining[bn] = usable - needed
                bar_count[bn]     = 1
                bar_used_mm[bn]   = length
                assigned_bar[orig_idx] = bn

        # ── PICE_NO: her bar içinde parça sıra numarası ───────────────────
        pice_counters: dict = {}
        # Bar+orijinal sıra ile listele (bar'a göre sırala, aynı bar içinde orijinal sıra)
        bar_order = sorted(range(len(rows)), key=lambda i: (assigned_bar[i], i))

        assigned_pice: dict = {}
        for i in bar_order:
            bn = assigned_bar[i]
            pice_counters.setdefault(bn, 0)
            pice_counters[bn] += 1
            assigned_pice[i] = pice_counters[bn]

        # ── Trolley/Unit: bar sırasına göre basit atama ───────────────────
        # Her bar bir slot alır
        bar_to_slot = {bn: idx for idx, bn in enumerate(sorted(bar_remaining.keys()))}
        def bar_trolley(bn):
            slot = bar_to_slot.get(bn, 0)
            return slot // n_shelf + 1
        def bar_unit(bn):
            slot = bar_to_slot.get(bn, 0)
            return slot % n_shelf + 1

        # ── Kayıtları oluştur (bar→pice sırasıyla) ───────────────────────
        records = []
        prog_no  = start_no

        for orig_idx in bar_order:
            row      = rows[orig_idx]
            bn       = assigned_bar[orig_idx]
            pice_no  = assigned_pice[orig_idx]
            piece_x10 = int(row['length_mm'] * 10)
            rem_mm   = bar_remaining.get(bn, 0)

            rec = {
                "PROGRAM_NO":       prog_no,
                "CUSTOMER_CODE":    cust_code,
                "CUSTOMER_NAME":    cust_name,
                "STOCK_CODE":       stock_code,
                "STOCK_NAME":       stock_name,
                "ORDER_NO":         order_no,
                "EXPLANATION1":     row["expl1"],
                "EXPLANATION2":     row["expl2"],
                "LENGTH":           str(piece_x10),
                "INCH_MM":          "0",
                "FRAME_X":          "",
                "FRAME_Y":          "",
                "POSE_NO":          0,
                "TROLLEY":          bar_trolley(bn),
                "UNIT":             bar_unit(bn),
                "LEFT_ANGLE":       int(row["left_angle"] * 10),
                "RIGHT_ANGLE":      int(row["right_angle"] * 10),
                "SIDE":             int(row["side"]),
                "CUTTED":           0,
                "HEIGHT":           height_x10,
                "SELLER":           "",
                "IMAGE":            "",
                "PAIR":             0,
                "BAR_NO":           bn,
                "TOTAL_SIZE":       str(bar_len_x10),
                "PICE_NO":          pice_no,
                "GRUP":             "",
                "WIDTH":            width_x10,
                "TYPE":             type_val,
                "COLOR_CODE":       color_code,
                "STIL_LENGTH":      "",
                "FRAME_NO":         0,
                "REMAINING_LENGTH": str(max(0, int(rem_mm * 10))),
                "CODE":             "",
                "ROBOT_Y":          int(round(self._robot_y_mm * 10)) or 400,
                "ROBOT_Z":          int(round(self._robot_z_mm * 10)) or 400,
                "ROBOT_VERTICAL":   int(self._cb_robot_vert.currentData()),
            }
            records.append(rec)
            prog_no += 1

        return records

    # ─────────────────────────────────────────────────────
    # Stok kodu üretici
    # ─────────────────────────────────────────────────────

    @staticmethod
    def _gen_stock_code() -> str:
        """Tarih/saate göre 16 karakterlik stok kodu üretir."""
        now = datetime.now()
        code = now.strftime("%Y%m%d%H%M%S")   # 14 karakter
        return code.ljust(16, "0")[:16]        # 16'ya tamamla
