"""
ui/dialog_record.py

MDB kayıt formu dialog penceresi.
Tüm 37 alan sekme sekme düzenlenmiştir.
P kodu (CODE) alanı ana pencereden otomatik doldurulabilir.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit,
    QPushButton, QLabel, QMessageBox, QScrollArea, QSizePolicy,
    QDialogButtonBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models import COLUMN_INFO, COLUMNS, NUMERIC_COLS


class RecordDialog(QDialog):
    """
    Yeni kayıt ekle / mevcut kaydı düzenle.
    record_saved sinyali kaydedilen veriyi dict olarak yayınlar.
    """
    record_saved = Signal(dict)

    def __init__(self, parent=None, record: dict = None, next_program_no: int = 1):
        super().__init__(parent)
        self.setWindowTitle('MDB Kayıt Formu')
        self.setMinimumSize(620, 560)
        self.resize(700, 600)

        self._record = record or {}
        self._widgets: dict = {}   # {col: widget}
        self._setup_ui(next_program_no)
        if record:
            self._fill_form(record)

    # ─────────────────────────────────────────────────────
    # Dışarıdan çağrılan API
    # ─────────────────────────────────────────────────────

    def append_code(self, code_str: str):
        """Ana pencereden üretilen P kodunu CODE alanına ekler."""
        if 'CODE' in self._widgets:
            w = self._widgets['CODE']
            cur = w.toPlainText().strip()
            w.setPlainText((cur + code_str) if cur else code_str)

    def set_code(self, code_str: str):
        """CODE alanını tamamen değiştirir."""
        if 'CODE' in self._widgets:
            self._widgets['CODE'].setPlainText(code_str)

    # ─────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────

    def _setup_ui(self, next_pno: int):
        main = QVBoxLayout(self)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        # Başlık
        h = QLabel(f'  Yeni Kayıt  —  Program No: {next_pno}')
        h.setStyleSheet('background:#2e2e42; color:#f8c12f; font-size:12px;'
                        ' font-weight:bold; padding:6px 10px; border-radius:4px;')
        main.addWidget(h)

        # Sekmeler
        tabs = QTabWidget()
        tabs.setStyleSheet(
            'QTabWidget::pane { border:1px solid #444; border-radius:4px; }'
            'QTabBar::tab { background:#2e2e42; color:#aaa; padding:6px 14px; }'
            'QTabBar::tab:selected { background:#5a3ea0; color:white; }'
        )
        main.addWidget(tabs, 1)

        # Grupları bul
        groups = {}
        for col in COLUMNS:
            info = COLUMN_INFO.get(col, {})
            grp = info.get('grp', 'Diğer')
            groups.setdefault(grp, []).append(col)

        for grp_name, cols in groups.items():
            tab = self._make_tab(cols, grp_name, next_pno)
            tabs.addTab(tab, grp_name)

        # Butonlar
        btn_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        btn_box.button(QDialogButtonBox.Save).setText('💾 Kaydet')
        btn_box.button(QDialogButtonBox.Cancel).setText('İptal')
        btn_box.accepted.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        btn_box.setStyleSheet(
            'QPushButton { background:#2e2e42; color:#ddd; border:1px solid #555;'
            ' border-radius:4px; padding:5px 16px; }'
            'QPushButton:hover { background:#3a3a55; }'
        )
        main.addWidget(btn_box)

        self.setStyleSheet('QDialog { background:#1e1e2e; }')

    def _make_tab(self, cols, grp_name, next_pno) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('QScrollArea { border:none; background:#1e1e2e; }')

        inner = QWidget()
        inner.setStyleSheet('background:#1e1e2e;')
        form = QFormLayout(inner)
        form.setContentsMargins(12, 8, 12, 8)
        form.setSpacing(6)
        form.setLabelAlignment(Qt.AlignRight)

        for col in cols:
            info = COLUMN_INFO.get(col, {'label': col, 'type': 'str'})
            label = info['label']
            t = info['type']
            note = info.get('note', '')
            default = info.get('def', None)
            req = info.get('req', False)

            lbl_text = f'{"* " if req else ""}{label}'
            if note:
                lbl_text += f'\n({note})'
            lbl = QLabel(lbl_text)
            lbl.setStyleSheet('color:#ccc; font-size:9px;')
            lbl.setWordWrap(True)
            lbl.setMinimumWidth(110)
            lbl.setMaximumWidth(130)

            if t == 'choice':
                w = QComboBox()
                for val, disp in info.get('choices', []):
                    w.addItem(disp, val)
                w.setStyleSheet(self._combo_style())
                if default is not None:
                    idx = w.findData(str(default))
                    if idx >= 0:
                        w.setCurrentIndex(idx)

            elif t == 'text':
                w = QTextEdit()
                w.setFixedHeight(80)
                w.setStyleSheet(
                    'background:#0d1117; color:#56cfe1; border:1px solid #444;'
                    ' font-family:Courier New; font-size:9px; border-radius:3px;'
                )

            elif t in ('float', 'int'):
                w = QDoubleSpinBox()
                w.setRange(0, 9999999)
                w.setDecimals(0 if t == 'int' else 1)
                w.setStyleSheet(self._spin_style())
                if default is not None:
                    w.setValue(float(default))
                if col == 'PROGRAM_NO':
                    w.setValue(next_pno)

            else:  # str
                max_len = info.get('max', 50)
                w = QLineEdit()
                w.setMaxLength(max_len)
                w.setPlaceholderText(f'maks {max_len} karakter')
                w.setStyleSheet(self._line_style())

            self._widgets[col] = w
            form.addRow(lbl, w)

        scroll.setWidget(inner)
        return scroll

    # ─────────────────────────────────────────────────────
    # Okuma / yazma
    # ─────────────────────────────────────────────────────

    def _fill_form(self, record: dict):
        for col, w in self._widgets.items():
            val = record.get(col)
            if val is None:
                continue
            t = COLUMN_INFO.get(col, {}).get('type', 'str')
            if t == 'choice':
                idx = w.findData(str(val))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            elif t == 'text':
                w.setPlainText(str(val))
            elif t in ('float', 'int'):
                try:
                    w.setValue(float(val))
                except (ValueError, TypeError):
                    pass
            else:
                w.setText(str(val))

    def _collect(self) -> dict:
        record = {}
        for col, w in self._widgets.items():
            t = COLUMN_INFO.get(col, {}).get('type', 'str')
            if t == 'choice':
                record[col] = w.currentData()
            elif t == 'text':
                record[col] = w.toPlainText()
            elif t in ('float', 'int'):
                record[col] = w.value()
            else:
                record[col] = w.text().strip()
        return record

    def _on_save(self):
        record = self._collect()
        # Basit doğrulama
        errors = []
        for col in COLUMNS:
            info = COLUMN_INFO.get(col, {})
            if not info.get('req', False):
                continue
            val = record.get(col)
            if val is None or str(val).strip() == '':
                errors.append(f'• {info["label"]} boş bırakılamaz')
        # STOCK_CODE tam 16 karakter mi?
        sc = str(record.get('STOCK_CODE', '')).strip()
        if sc and len(sc) != 16:
            errors.append(f'• Stok Kodu tam 16 karakter olmalı (şu an: {len(sc)})')

        if errors:
            QMessageBox.warning(self, 'Eksik Bilgi',
                                'Lütfen aşağıdaki alanları düzeltin:\n\n' + '\n'.join(errors))
            return

        self.record_saved.emit(record)
        self.accept()

    # ─────────────────────────────────────────────────────
    # Stiller
    # ─────────────────────────────────────────────────────

    @staticmethod
    def _combo_style():
        return ('QComboBox { background:#2e2e42; color:#ddd; border:1px solid #555;'
                ' border-radius:3px; padding:3px; font-size:9px; }'
                'QComboBox QAbstractItemView { background:#2e2e42; color:#ddd; }')

    @staticmethod
    def _spin_style():
        return ('QDoubleSpinBox { background:#2e2e42; color:#ddd; border:1px solid #555;'
                ' border-radius:3px; padding:2px; font-size:9px; }')

    @staticmethod
    def _line_style():
        return ('QLineEdit { background:#2e2e42; color:#ddd; border:1px solid #555;'
                ' border-radius:3px; padding:3px; font-size:10px; }')
