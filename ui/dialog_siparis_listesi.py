"""
ui/dialog_siparis_listesi.py – Sipariş Listesi Ekranı
ProfiDO (KSB_ProfilKesim) Programı

Akıllı Üretim ekranında kaydedilen siparişleri (her biri bir veya daha
fazla çizim/çerçeve içerebilir) listeler; buradan:
  - Yeni bir sipariş başlatılabilir (boş bir Akıllı Üretim ekranı açılır),
  - Mevcut bir sipariş açılıp düzenlenebilir (tüm çizimleriyle birlikte
    Akıllı Üretim ekranına geri yüklenir; orada çizim ekleme/düzenleme/
    silme yapılıp tekrar "💾 Siparişi Kaydet" ile güncellenebilir),
  - Bir sipariş tamamen silinebilir.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFrame,
)
from PySide6.QtCore import Qt

import order_store as ordst
from ui.dialog_akilli_uretim import _STYLE
from ui.kiosk import apply_kiosk

COLS = ['Sipariş No', 'Müşteri Adı', 'Müşteri Kodu', 'Çizim Sayısı', 'Toplam Parça', 'Son Güncelleme']


class SiparisListesiDialog(QDialog):
    """Kayıtlı siparişlerin listesi + yeni/aç-düzenle/sil işlemleri."""

    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.setWindowTitle('📁 Siparişler')
        self.resize(820, 520)
        apply_kiosk(self)   # tam ekran, çerçevesiz kiosk modu
        self.setStyleSheet(_STYLE)
        self._db = db
        self._orders = []          # order_store.list_orders() sonucu (özet)
        self._akilli_dlg = None    # açık tutulan AkilliUretimDialog referansı (GC engellemek için)

        self._build_ui()
        self._reload()

    # ─────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        title = QLabel('📁 Siparişler')
        title.setObjectName('lbl_head')
        root.addWidget(title)

        # Arama çubuğu
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel('Ara:'))
        self._ed_search = QLineEdit()
        self._ed_search.setPlaceholderText('Sipariş no, müşteri adı veya kodu...')
        self._ed_search.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._ed_search, 1)
        root.addLayout(search_row)

        # Tablo
        self._tbl = QTableWidget(0, len(COLS))
        self._tbl.setHorizontalHeaderLabels(COLS)
        self._tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tbl.verticalHeader().setVisible(False)
        hh = self._tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self._tbl.doubleClicked.connect(self._open_selected)
        root.addWidget(self._tbl, 1)

        self._lbl_status = QLabel('')
        self._lbl_status.setObjectName('lbl_sub')
        root.addWidget(self._lbl_status)

        # Alt buton çubuğu
        bar = QFrame()
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(0, 0, 0, 0)
        bar_lay.setSpacing(8)

        btn_new = QPushButton('🆕  Yeni Sipariş')
        btn_new.setObjectName('btn_calc')
        btn_new.setFixedHeight(36)
        btn_new.clicked.connect(self._new_order)
        bar_lay.addWidget(btn_new)

        btn_open = QPushButton('✏️  Aç / Düzenle')
        btn_open.setObjectName('btn_gen')
        btn_open.setFixedHeight(36)
        btn_open.clicked.connect(self._open_selected)
        bar_lay.addWidget(btn_open)

        btn_delete = QPushButton('🗑  Siparişi Sil')
        btn_delete.setFixedHeight(36)
        btn_delete.setStyleSheet(
            'QPushButton{background:#5a1a1a;color:#ffaaaa;border:1px solid #7a2a2a;'
            'border-radius:4px;padding:4px 10px;font-size:12px;}'
            'QPushButton:hover{background:#7a2a2a;}')
        btn_delete.clicked.connect(self._delete_selected)
        bar_lay.addWidget(btn_delete)

        bar_lay.addStretch()

        btn_refresh = QPushButton('🔄  Yenile')
        btn_refresh.setFixedHeight(36)
        btn_refresh.clicked.connect(self._reload)
        bar_lay.addWidget(btn_refresh)

        btn_close = QPushButton('Kapat')
        btn_close.setFixedHeight(36)
        btn_close.clicked.connect(self.close)
        bar_lay.addWidget(btn_close)

        root.addWidget(bar)

    # ─────────────────────────────────────────────────────────
    def _reload(self):
        try:
            self._orders = ordst.list_orders()
        except Exception as e:
            self._orders = []
            QMessageBox.warning(self, 'Sipariş Listesi Hatası', str(e))
        self._apply_filter()

    def _apply_filter(self):
        term = self._ed_search.text().strip().lower()
        rows = self._orders
        if term:
            rows = [
                o for o in rows
                if term in (o.get('order_no', '') or '').lower()
                or term in (o.get('customer_name', '') or '').lower()
                or term in (o.get('customer_code', '') or '').lower()
            ]
        self._filtered = rows
        self._tbl.setRowCount(len(rows))
        for r, o in enumerate(rows):
            vals = [
                o.get('order_no', '') or '(boş)',
                o.get('customer_name', '') or '(boş)',
                o.get('customer_code', '') or '',
                str(o.get('frame_count', 0)),
                str(o.get('piece_count', 0)),
                (o.get('updated_at', '') or '').replace('T', '  '),
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setData(Qt.UserRole, o.get('order_id'))
                if c in (3, 4):
                    item.setTextAlignment(Qt.AlignCenter)
                self._tbl.setItem(r, c, item)
        self._lbl_status.setText(f'{len(rows)} sipariş bulundu (toplam {len(self._orders)}).')

    def _selected_order_id(self):
        row = self._tbl.currentRow()
        if row < 0 or row >= len(self._filtered):
            return None
        return self._filtered[row].get('order_id')

    # ─────────────────────────────────────────────────────────
    def _new_order(self):
        """Boş bir Akıllı Üretim ekranı açar; kullanıcı çizim(ler)i tamamlayıp
        "💾 Siparişi Kaydet" dediğinde yeni bir sipariş olarak diske yazılır."""
        from ui.dialog_akilli_uretim import AkilliUretimDialog
        try:
            dlg = AkilliUretimDialog(self, db=self._db, order_data=None)
        except Exception as e:
            import traceback
            QMessageBox.critical(self, 'Akıllı Üretim Hatası',
                f'{e}\n\n{traceback.format_exc()[:600]}')
            return
        self._akilli_dlg = dlg
        dlg.finished.connect(lambda _=None: self._reload())
        dlg.show()

    def _open_selected(self, *_args):
        order_id = self._selected_order_id()
        if not order_id:
            QMessageBox.information(self, 'Uyarı', 'Lütfen açmak için bir sipariş seçin.')
            return
        try:
            order_data = ordst.load_order(order_id)
        except Exception as e:
            QMessageBox.critical(self, 'Sipariş Yüklenemedi', str(e))
            return
        if not order_data:
            QMessageBox.warning(self, 'Uyarı', 'Sipariş bulunamadı (silinmiş olabilir).')
            self._reload()
            return

        from ui.dialog_akilli_uretim import AkilliUretimDialog
        try:
            dlg = AkilliUretimDialog(self, db=self._db, order_data=order_data)
        except Exception as e:
            import traceback
            QMessageBox.critical(self, 'Akıllı Üretim Hatası',
                f'{e}\n\n{traceback.format_exc()[:600]}')
            return
        self._akilli_dlg = dlg
        dlg.finished.connect(lambda _=None: self._reload())
        dlg.show()

    def _delete_selected(self):
        order_id = self._selected_order_id()
        if not order_id:
            QMessageBox.information(self, 'Uyarı', 'Lütfen silmek için bir sipariş seçin.')
            return
        row = self._tbl.currentRow()
        o = self._filtered[row] if 0 <= row < len(self._filtered) else {}
        label = o.get('order_no') or o.get('customer_name') or order_id
        reply = QMessageBox.question(
            self, 'Siparişi Sil',
            f'"{label}" siparişini ve tüm çizimlerini kalıcı olarak silmek istediğinize emin misiniz?\n'
            f'Bu işlem geri alınamaz.',
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            ordst.delete_order(order_id)
        except Exception as e:
            QMessageBox.critical(self, 'Silme Hatası', str(e))
            return
        self._reload()
