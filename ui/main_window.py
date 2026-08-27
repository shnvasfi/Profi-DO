"""
ui/main_window.py

Ana pencere.

Düzen:
┌─────────────────────────────────────────────────────────┐
│  ARAÇ ÇUBUĞU  (DXF Aç | Ekstrüzyon | Ayna/Döndür | MDB)│
├───────────┬──────────────────────────────┬──────────────┤
│  TAKIMLAR │        VIEWPORT (2D/3D)       │  İŞLEMLER   │
│  T10…T71  │                               │  P1…P7      │
│           │                               │  + Params   │
├───────────┴──────────────────────────────┴──────────────┤
│  DURUM ÇUBUĞU: takım | işlem | koordinat | dosya adı   │
├──────────────────────────────────────────────────────────┤
│  KOD GEÇMİŞİ (üretilen P kodları + MDB'ye ekle butonu) │
└─────────────────────────────────────────────────────────┘
"""

import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QToolBar, QLabel, QDoubleSpinBox, QPushButton,
    QFileDialog, QMessageBox, QStatusBar, QTextEdit,
    QSplitter, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QFont, QIcon

from dxf_loader import load_dxf, apply_transform, get_bounds
from database import Database
from ui.viewport_widget import ViewportWidget
from ui.panel_tools import ToolsPanel
from ui.panel_operations import OperationsPanel
from ui.dialog_record import RecordDialog
from ui.dialog_batch import BatchEntryDialog
from ui.dialog_frame_designer import FrameDesignerDialog
from ui.dialog_profil_kutuphanesi import ProfilKutuphanesiDialog
from ui.dialog_akilli_uretim import AkilliUretimDialog
from ui.dialog_ayarlar import AyarlarDialog


class MainWindow(QMainWindow):
    def __init__(self, go_home_callback=None):
        super().__init__()
        self._go_home_cb   = go_home_callback   # Ana Menüye Dön callback
        self._quit_blocked = False              # closeEvent kapanmayı engeller mi?
        self.setWindowTitle('ProfiDO')
        self.setMinimumSize(900, 600)
        self.showMaximized()   # Tam ekran başlat

        # Durum
        self._raw_segs     = []   # Orijinal DXF segmentleri
        self._cur_segs     = []   # Dönüşüm uygulanmış
        self._mirror_y     = False
        self._mirror_z     = False
        self._rotate_deg   = 0.0
        self._dxf_file     = ''
        self._selected_tool = ''
        self._selected_op   = ''
        self._code_buffer   = ''   # Birikmiş P kodları

        self._db = Database()
        self._record_dialog: RecordDialog = None

        self._setup_style()
        self._setup_ui()
        self._setup_statusbar()
        # MDB sorusu kaldırıldı — kullanıcı "MDB Aç" butonuyla bağlanabilir

    # ─────────────────────────────────────────────────────
    # UI Kurulum
    # ─────────────────────────────────────────────────────

    def _setup_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background:#1e1e2e; color:#ccc; }
            QToolBar { background:#252535; border-bottom:1px solid #333; spacing:4px; padding:3px; }
            QToolBar QLabel { color:#aaa; font-size:9px; }
            QSplitter::handle { background:#333; width:2px; height:2px; }
            QStatusBar { background:#252535; color:#888; font-size:9px; border-top:1px solid #333; }
            QTextEdit { background:#0d1117; color:#56cfe1; font-family:'Courier New';
                        font-size:14px; border:1px solid #333; border-radius:3px; }
            QPushButton { background:#2e2e42; color:#ccc; border:1px solid #444;
                          border-radius:4px; padding:4px 10px; font-size:12px; }
            QPushButton:hover { background:#3a3a55; }
            QDoubleSpinBox { background:#2e2e42; color:#ddd; border:1px solid #555;
                             border-radius:3px; padding:2px; font-size:12px; }
            QLabel { color:#ccc; font-size:12px; }
        """)

    def _setup_ui(self):
        # ── Araç çubuğu ──────────────────────────────────
        tb = QToolBar('Araçlar')
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        # DXF Aç
        btn_dxf = QPushButton('📂 DXF Aç')
        btn_dxf.clicked.connect(self._open_dxf)
        tb.addWidget(btn_dxf)
        tb.addSeparator()

        # Ekstrüzyon
        tb.addWidget(QLabel(' Ekstrüzyon: '))
        self._sp_extrude = QDoubleSpinBox()
        self._sp_extrude.setRange(0, 99999)
        self._sp_extrude.setSuffix(' mm')
        self._sp_extrude.setDecimals(1)
        self._sp_extrude.setFixedWidth(110)
        self._sp_extrude.setToolTip('Profil uzunluğunu girin → 3D moda geçer')
        self._sp_extrude.valueChanged.connect(self._on_extrude_changed)
        tb.addWidget(self._sp_extrude)

        btn_2d = QPushButton('2D')
        btn_2d.setToolTip('2D Kesit görünümüne dön')
        btn_2d.clicked.connect(self._go_2d)
        tb.addWidget(btn_2d)
        tb.addSeparator()

        # Ayna
        tb.addWidget(QLabel(' Ayna: '))
        btn_my = QPushButton('↔ Y Ekseninde')
        btn_my.setToolTip('Yatay (Y ekseninde) ayna')
        btn_my.clicked.connect(self._mirror_y_toggle)
        tb.addWidget(btn_my)

        btn_mz = QPushButton('↕ Z Ekseninde')
        btn_mz.setToolTip('Dikey (Z ekseninde) ayna')
        btn_mz.clicked.connect(self._mirror_z_toggle)
        tb.addWidget(btn_mz)
        tb.addSeparator()

        # Döndür
        tb.addWidget(QLabel(' Döndür: '))
        btn_ccw = QPushButton('↺ 90° Sol')
        btn_ccw.clicked.connect(lambda: self._rotate(-90))
        tb.addWidget(btn_ccw)

        btn_cw = QPushButton('↻ 90° Sağ')
        btn_cw.clicked.connect(lambda: self._rotate(90))
        tb.addWidget(btn_cw)
        tb.addSeparator()

        # MDB
        btn_mdb = QPushButton('💾 MDB Bağlan')
        btn_mdb.clicked.connect(self._open_mdb)
        tb.addWidget(btn_mdb)

        btn_frame = QPushButton('🏗 Çerçeve Tasarımcısı')
        btn_frame.setStyleSheet(
            'QPushButton{background:#1a5c5c;color:white;border-radius:4px;'
            'font-size:12px;font-weight:bold;padding:4px 12px;}'
            'QPushButton:hover{background:#237575;}'
        )
        btn_frame.setToolTip('W×H girerek 4 profil parçasını otomatik hesapla')
        btn_frame.clicked.connect(self._open_frame_designer)
        tb.addWidget(btn_frame)

        btn_batch = QPushButton('📋 Toplu Kesim Girişi')
        btn_batch.setStyleSheet(
            'QPushButton{background:#5a3ea0;color:white;border-radius:4px;'
            'font-size:12px;font-weight:bold;padding:4px 12px;}'
            'QPushButton:hover{background:#6e50b8;}'
        )
        btn_batch.clicked.connect(self._open_batch)
        tb.addWidget(btn_batch)

        # ── İkinci araç çubuğu: Akıllı Üretim ──────────
        self.addToolBarBreak()   # ← yeni satıra geç
        tb2 = QToolBar('Akıllı Üretim')
        tb2.setMovable(False)
        tb2.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(tb2)

        lbl_tb2 = QLabel('  🤖 Akıllı Sistem: ')
        lbl_tb2.setStyleSheet('color:#56cfe1; font-size:12px; font-weight:bold;')
        tb2.addWidget(lbl_tb2)

        btn_library = QPushButton('📚 Profil Kütüphanesi')
        btn_library.setStyleSheet(
            'QPushButton{background:#3a2060;color:white;border-radius:4px;'
            'font-size:13px;font-weight:bold;padding:5px 16px;}'
            'QPushButton:hover{background:#4e2e80;}'
        )
        btn_library.setToolTip('Stok kodu bazlı profil ve işlem makrolarını yönet')
        btn_library.clicked.connect(self._open_profil_kutuphanesi)
        tb2.addWidget(btn_library)

        btn_akilli = QPushButton('⚡ Akıllı Üretim')
        btn_akilli.setStyleSheet(
            'QPushButton{background:#7a5a00;color:white;border-radius:4px;'
            'font-size:13px;font-weight:bold;padding:5px 16px;}'
            'QPushButton:hover{background:#a07800;}'
        )
        btn_akilli.setToolTip('Profil kütüphanesini kullanarak çerçeve oluştur ve P-kodları otomatik üret')
        btn_akilli.clicked.connect(self._open_akilli_uretim)
        tb2.addWidget(btn_akilli)

        btn_siparisler = QPushButton('📁 Siparişler')
        btn_siparisler.setStyleSheet(
            'QPushButton{background:#1a4a5a;color:white;border-radius:4px;'
            'font-size:13px;font-weight:bold;padding:5px 16px;}'
            'QPushButton:hover{background:#206278;}'
        )
        btn_siparisler.setToolTip('Kaydedilmiş siparişleri listele; aç, düzenle veya sil')
        btn_siparisler.clicked.connect(self._open_siparisler)
        tb2.addWidget(btn_siparisler)

        tb2.addSeparator()

        btn_ayarlar = QPushButton('⚙  Ayarlar')
        btn_ayarlar.setStyleSheet(
            'QPushButton{background:#2a3a4a;color:#89b4fa;border-radius:4px;'
            'font-size:12px;padding:5px 14px;border:1px solid #4a6a8a;}'
            'QPushButton:hover{background:#3a4a5a;}'
        )
        btn_ayarlar.setToolTip('Kesim optimizasyonu ve trolley parametrelerini ayarla')
        btn_ayarlar.clicked.connect(self._open_ayarlar)
        tb2.addWidget(btn_ayarlar)

        # ── Ana Menüye Dön (sağda) ───────────────────────
        tb2.addSeparator()
        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb2.addWidget(spacer)

        btn_home = QPushButton('🏠  Ana Menü')
        btn_home.setStyleSheet(
            'QPushButton{background:#3a1a1a;color:#ff9999;border-radius:4px;'
            'font-size:12px;font-weight:bold;padding:5px 16px;border:1px solid #884444;}'
            'QPushButton:hover{background:#5a2a2a;}'
        )
        btn_home.setToolTip('Açılış ekranına dön (programı oradan kapatabilirsiniz)')
        btn_home.clicked.connect(self._go_home)
        tb2.addWidget(btn_home)

        # ── Merkez widget ────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        main_lay = QVBoxLayout(central)
        main_lay.setContentsMargins(4, 4, 4, 4)
        main_lay.setSpacing(4)

        # Yatay bölücü: Takımlar | Viewport | İşlemler
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        self._tools_panel = ToolsPanel()
        self._tools_panel.tool_selected.connect(self._on_tool_selected)
        splitter.addWidget(self._tools_panel)

        self._viewport = ViewportWidget()
        self._viewport.point_selected.connect(self._on_point_selected)
        self._viewport.mouse_moved.connect(
            lambda y, z: self._lbl_coord.setText(f'Y: {y:.2f}  Z: {z:.2f}'))
        splitter.addWidget(self._viewport)

        self._ops_panel = OperationsPanel()
        self._ops_panel.operation_selected.connect(self._on_op_selected)
        self._ops_panel.pick_requested.connect(self._start_pick)
        self._ops_panel.code_ready.connect(self._on_code_ready)
        self._ops_panel.tool_change.connect(self._on_tool_selected)
        self._ops_panel.save_to_mdb.connect(self._save_code_to_record)
        self._ops_panel.program_no_changed.connect(self._on_program_no_changed)
        splitter.addWidget(self._ops_panel)

        splitter.setSizes([155, 900, 310])
        main_lay.addWidget(splitter, 1)

        # ── Kod geçmişi çubuğu ───────────────────────────
        code_frame = QFrame()
        code_frame.setFixedHeight(110)
        code_frame.setStyleSheet('background:#111122; border-top:1px solid #333;')
        code_lay = QHBoxLayout(code_frame)
        code_lay.setContentsMargins(6, 4, 6, 4)
        code_lay.setSpacing(6)

        code_lay.addWidget(QLabel('📋 Kod Tamponu:'))
        self._code_edit = QTextEdit()
        self._code_edit.setPlaceholderText(
            'Üretilen P kodları burada birikir. Yeni Kayıt açık iken "Kayda Ekle" ile CODE alanına aktarın.')
        code_lay.addWidget(self._code_edit, 1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)

        btn_add = QPushButton('➡ Kayda Ekle')
        btn_add.setToolTip('Tamponu açık MDB kayıt formuna ekler')
        btn_add.setFixedWidth(110)
        btn_add.clicked.connect(self._add_code_to_record)
        btn_col.addWidget(btn_add)

        btn_clear_code = QPushButton('🗑 Temizle')
        btn_clear_code.setFixedWidth(110)
        btn_clear_code.clicked.connect(self._code_edit.clear)
        btn_col.addWidget(btn_clear_code)

        btn_col.addStretch()
        code_lay.addLayout(btn_col)

        main_lay.addWidget(code_frame)

    def _setup_statusbar(self):
        sb = self.statusBar()
        self._lbl_tool_status = QLabel('Takım: –')
        self._lbl_op_status   = QLabel('İşlem: –')
        self._lbl_coord       = QLabel('Y: –  Z: –')
        self._lbl_dxf         = QLabel('DXF: yüklenmedi')
        self._lbl_db          = QLabel('MDB: bağlı değil')
        for lbl in (self._lbl_tool_status, self._lbl_op_status,
                    self._lbl_coord, self._lbl_dxf, self._lbl_db):
            sb.addWidget(lbl)
            sep = QFrame(); sep.setFrameShape(QFrame.VLine)
            sep.setStyleSheet('color:#444;')
            sb.addWidget(sep)

    # ─────────────────────────────────────────────────────
    # DXF işlemleri
    # ─────────────────────────────────────────────────────

    def _open_dxf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'DXF Dosyası Aç', '', 'DXF Dosyaları (*.dxf)')
        if not path:
            return
        try:
            segs = load_dxf(path)
        except Exception as e:
            QMessageBox.critical(self, 'DXF Hatası', str(e))
            return
        if not segs:
            QMessageBox.warning(self, 'Boş DXF', 'DXF dosyasında çizim varlığı bulunamadı.')
            return

        self._raw_segs   = segs
        self._cur_segs   = segs
        self._mirror_y   = False
        self._mirror_z   = False
        self._rotate_deg = 0.0
        self._dxf_file   = os.path.basename(path)
        self._sp_extrude.setValue(0)
        self._viewport.load_segments(segs)
        self._lbl_dxf.setText(f'DXF: {self._dxf_file}')

        min_y, max_y, min_z, max_z = get_bounds(segs)
        self.statusBar().showMessage(
            f'DXF yüklendi: {len(segs)} segment | '
            f'Y: {min_y:.1f}–{max_y:.1f}  Z: {min_z:.1f}–{max_z:.1f}', 4000)

    def _apply_transform(self):
        if not self._raw_segs:
            return
        self._cur_segs = apply_transform(
            self._raw_segs,
            mirror_y=self._mirror_y,
            mirror_z=self._mirror_z,
            rotate_deg=self._rotate_deg,
        )
        self._viewport.set_segments(self._cur_segs)

    def _mirror_y_toggle(self):
        self._mirror_y = not self._mirror_y
        self._apply_transform()

    def _mirror_z_toggle(self):
        self._mirror_z = not self._mirror_z
        self._apply_transform()

    def _rotate(self, deg: float):
        self._rotate_deg = (self._rotate_deg + deg) % 360
        self._apply_transform()

    def _on_extrude_changed(self, val: float):
        self._viewport.set_extrude(val)

    def _go_2d(self):
        self._sp_extrude.setValue(0)

    # ─────────────────────────────────────────────────────
    # Takım / İşlem sinyalleri
    # ─────────────────────────────────────────────────────

    def _on_tool_selected(self, tool: str):
        self._selected_tool = tool
        self._ops_panel.set_tool(tool)
        self._lbl_tool_status.setText(f'Takım: {tool}')

    def _on_op_selected(self, op: str):
        self._selected_op = op
        self._lbl_op_status.setText(f'İşlem: {op}')

    def _start_pick(self):
        """İşlemler paneli "DXF'e Tıkla" butonuna bastı."""
        if not self._cur_segs:
            QMessageBox.information(self, 'Uyarı', 'Önce bir DXF dosyası yükleyin.')
            return
        if self._sp_extrude.value() > 0:
            QMessageBox.information(self, 'Uyarı',
                '3D modda tıklama devre dışı. 2D görünüme geçin.')
            return
        self._viewport.set_pick_mode(True)
        self.statusBar().showMessage('📍 DXF üzerine tıklayın — Y ve Z koordinatı alınacak')

    def _on_point_selected(self, y: float, z: float):
        self._ops_panel.set_yz_from_click(y, z)
        self._lbl_coord.setText(f'Y: {y:.2f}  Z: {z:.2f}')
        self.statusBar().showMessage(f'Seçilen nokta → Y={y:.2f}  Z={z:.2f}', 3000)

    def _on_code_ready(self, code: str):
        """İşlemler paneli kod üretti."""
        cur = self._code_edit.toPlainText().strip()
        self._code_edit.setPlainText((cur + code) if cur else code)
        self.statusBar().showMessage(f'Kod üretildi: {code}', 4000)

    # ─────────────────────────────────────────────────────
    # Kayda ekleme
    # ─────────────────────────────────────────────────────

    def _add_code_to_record(self):
        code = self._code_edit.toPlainText().strip()
        if not code:
            QMessageBox.information(self, 'Uyarı', 'Kod tamponu boş.')
            return
        if self._record_dialog and self._record_dialog.isVisible():
            self._record_dialog.append_code(code)
            self.statusBar().showMessage('Kod kayıt formuna eklendi.', 3000)
        else:
            QMessageBox.information(self, 'Uyarı',
                'Açık bir kayıt formu yok.\n"➕ Yeni Kayıt" butonuna basın.')

    # ─────────────────────────────────────────────────────
    # MDB işlemleri
    # ─────────────────────────────────────────────────────

    def _open_mdb(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'MDB Dosyası Seç', '', 'Access Veritabanı (*.mdb *.accdb)')
        if not path:
            return
        ok, msg = self._db.connect(path)
        if ok:
            self._lbl_db.setText(f'MDB: ✅ {os.path.basename(path)}')
            QMessageBox.information(self, 'Bağlandı', msg)
        else:
            self._lbl_db.setText('MDB: ❌ bağlantı hatası')
            QMessageBox.critical(self, 'Bağlantı Hatası', msg)

    def _new_record(self):
        next_no = 1
        if self._db.connected:
            try:
                next_no = self._db.get_next_program_no()
            except Exception:
                pass
        dlg = RecordDialog(self, next_program_no=next_no)
        dlg.record_saved.connect(self._save_record)
        self._record_dialog = dlg
        dlg.show()  # Modalsiz — ana pencereyle birlikte kullanılabilir

    def _save_record(self, record: dict):
        if not self._db.connected:
            QMessageBox.warning(self, 'Uyarı',
                'MDB bağlantısı yok. Önce "💾 MDB Bağlan" butonuna basın.')
            return
        ok, msg = self._db.insert_record(record)
        if ok:
            QMessageBox.information(self, 'Kaydedildi', msg)
        else:
            QMessageBox.critical(self, 'Kayıt Hatası', msg)

    # ─────────────────────────────────────────────────────
    # Kodu doğrudan MDB kaydına yaz
    # ─────────────────────────────────────────────────────

    def _on_program_no_changed(self, program_no: int):
        """Program No değişince MDB'den o kaydın LENGTH'ini çekip Profil Boyu'na yazar."""
        if not self._db.connected:
            return
        try:
            self._db.cursor.execute(
                f'SELECT "LENGTH" FROM "{self._db.table_name}" WHERE "PROGRAM_NO"=?',
                (program_no,)
            )
            row = self._db.cursor.fetchone()
            if row and row[0]:
                length_val = float(row[0])
                self._ops_panel.set_profile_length(length_val)
                self.statusBar().showMessage(
                    f'#{program_no} → Profil Boyu: {length_val:.0f} (×10 mm)', 3000)
            else:
                self.statusBar().showMessage(
                    f'#{program_no} bulunamadı veya boyu yok', 3000)
        except Exception:
            pass

    def _save_code_to_record(self, program_no: int, code_str: str):
        if not self._db.connected:
            QMessageBox.warning(self, 'MDB Bağlı Değil',
                'Önce "💾 MDB Bağlan" butonuna basarak bir MDB dosyası seçin.')
            return

        # Kayıt var mı kontrol et
        try:
            self._db.cursor.execute(
                f'SELECT COUNT(*) FROM "{self._db.table_name}" WHERE "PROGRAM_NO"=?',
                (program_no,))
            count = self._db.cursor.fetchone()[0]
        except Exception as e:
            QMessageBox.critical(self, 'Sorgu Hatası', str(e))
            return

        if count == 0:
            QMessageBox.warning(self, 'Kayıt Bulunamadı',
                f'Program No {program_no} veritabanında yok.\n\n'
                f'Önce "📋 Toplu Kesim Girişi" ile kesim listesini kaydedin,\n'
                f'ardından bu Program No\'ya kod ekleyebilirsiniz.')
            return

        # Mevcut kodu kontrol et
        existing_code = ''
        try:
            self._db.cursor.execute(
                f'SELECT "CODE" FROM "{self._db.table_name}" WHERE "PROGRAM_NO"=?',
                (program_no,))
            row = self._db.cursor.fetchone()
            existing_code = (row[0] or '').strip() if row else ''
        except Exception:
            pass

        if existing_code:
            preview = existing_code[:60] + ('…' if len(existing_code) > 60 else '')
            mb = QMessageBox(self)
            mb.setWindowTitle(f'#{program_no} — Mevcut Kod Var')
            mb.setIcon(QMessageBox.Question)
            mb.setText(
                f'<b>#{program_no}</b> kaydında zaten kod var:\n\n'
                f'{preview}\n\nNasıl devam edilsin?'
            )
            btn_append  = mb.addButton('➕  Mevcut Koda Ekle',    QMessageBox.AcceptRole)
            btn_replace = mb.addButton('🔄  Üzerine Yaz (Sil)',   QMessageBox.DestructiveRole)
            btn_cancel  = mb.addButton('İptal',                   QMessageBox.RejectRole)
            mb.setDefaultButton(btn_append)
            mb.exec()

            if mb.clickedButton() == btn_cancel:
                return
            if mb.clickedButton() == btn_replace:
                ok, msg = self._db.replace_code_in_record(program_no, code_str)
            else:
                ok, msg = self._db.append_code_to_record(program_no, code_str)
        else:
            ok, msg = self._db.append_code_to_record(program_no, code_str)

        if ok:
            QMessageBox.information(self, '✅ Kaydedildi',
                f'#{program_no} kaydına kod yazıldı.')
            self._lbl_db.setText(f'MDB: ✅ #{program_no} güncellendi')
        else:
            QMessageBox.critical(self, 'Kayıt Hatası', msg)

    # ─────────────────────────────────────────────────────
    # Toplu kesim girişi
    # ─────────────────────────────────────────────────────

    def _open_frame_designer(self):
        try:
            dlg = FrameDesignerDialog(self, db=self._db)
            dlg.show()
        except Exception as e:
            import traceback
            QMessageBox.critical(self, 'Hata', f'{e}\n\n{traceback.format_exc()}')

    def _open_batch(self):
        """Toplu Kesim Girişi — önce MDB seçimi, sonra mevcut liste yüklenir."""
        try:
            from database import Database as _DB

            # ── MDB Seçimi ────────────────────────────────
            # Mevcut bağlı MDB veya yeni seç
            choices = []
            if self._db.connected and self._db.path:
                choices.append(f'Mevcut: {os.path.basename(self._db.path)}')
            choices.append('Başka MDB seç…')
            choices.append('MDB olmadan devam et')

            from PySide6.QtWidgets import QInputDialog
            choice, ok = QInputDialog.getItem(
                self, 'Toplu Kesim — Veritabanı',
                'Hangi veritabanıyla çalışmak istiyorsunuz?',
                choices, 0, False
            )
            if not ok:
                return

            db_to_use = self._db
            if choice == 'Başka MDB seç…':
                path, _ = QFileDialog.getOpenFileName(
                    self, 'MDB Dosyası Seç', '', 'Access DB (*.mdb *.accdb)')
                if not path:
                    return
                db_to_use = _DB()
                db_to_use.connect(path)
                if not db_to_use.connected:
                    QMessageBox.warning(self, 'Hata', 'MDB dosyası açılamadı.')
                    return
            elif choice == 'MDB olmadan devam et':
                db_to_use = _DB()   # bağlı olmayan boş DB

            # ── Mevcut kayıtları oku ──────────────────────
            existing_records = []
            if db_to_use.connected:
                try:
                    existing_records = db_to_use.get_all_records()
                except Exception:
                    existing_records = []

            next_no = 1
            if db_to_use.connected:
                try:
                    next_no = db_to_use.get_next_program_no()
                except Exception:
                    pass

            dlg = BatchEntryDialog(
                self, db=db_to_use,
                next_program_no=next_no,
                existing_records=existing_records
            )
            dlg.show()

        except Exception as e:
            import traceback
            QMessageBox.critical(self, 'Toplu Giriş Hatası',
                f'{e}\n\n{traceback.format_exc()}')

    def _open_profil_kutuphanesi(self):
        try:
            dlg = ProfilKutuphanesiDialog(self)

            # DXF pick entegrasyonu ─────────────────────────────────────
            def _on_dxf_pick_requested():
                if not self._cur_segs:
                    from PySide6.QtWidgets import QMessageBox as _MB
                    _MB.information(self, 'Uyarı', 'Önce bir DXF dosyası yükleyin.')
                    return
                if self._sp_extrude.value() > 0:
                    from PySide6.QtWidgets import QMessageBox as _MB
                    _MB.information(self, 'Uyarı',
                        '3D modda tıklama devre dışı. 2D görünüme geçin.')
                    return
                self._viewport.set_pick_mode(True)
                self.statusBar().showMessage(
                    '📍 DXF üzerine tıklayın — Y ve Z değeri alınacak')

            def _on_point_for_lib(y: float, z: float):
                dlg.receive_dxf_point(y, z)
                self.statusBar().showMessage(
                    f'Profil kütüphanesi → Y={y:.2f}  Z={z:.2f}', 3000)

            dlg.request_dxf_pick.connect(_on_dxf_pick_requested)
            self._viewport.point_selected.connect(_on_point_for_lib)

            # Dialog kapanınca geçici bağlantıyı kopar
            dlg.finished.connect(
                lambda _: self._viewport.point_selected.disconnect(_on_point_for_lib))
            # ────────────────────────────────────────────────────────────

            dlg.show()
        except Exception as e:
            import traceback
            QMessageBox.critical(self, 'Profil Kütüphanesi Hatası',
                f'{e}\n\n{traceback.format_exc()}')

    def _open_akilli_uretim(self):
        try:
            dlg = AkilliUretimDialog(self, db=self._db)
            dlg.show()
        except Exception as e:
            import traceback
            QMessageBox.critical(self, 'Akıllı Üretim Hatası',
                f'{e}\n\n{traceback.format_exc()}')

    def _open_siparisler(self):
        try:
            from ui.dialog_siparis_listesi import SiparisListesiDialog
            dlg = SiparisListesiDialog(self, db=self._db)
            dlg.show()
        except Exception as e:
            import traceback
            QMessageBox.critical(self, 'Siparişler Hatası',
                f'{e}\n\n{traceback.format_exc()}')

    def _open_ayarlar(self):
        try:
            dlg = AyarlarDialog(self)
            dlg.exec()
        except Exception as e:
            import traceback
            QMessageBox.critical(self, 'Ayarlar Hatası',
                f'{e}\n\n{traceback.format_exc()}')

    # ─────────────────────────────────────────────────────
    # Başlangıçta MDB sor
    # ─────────────────────────────────────────────────────

    def _ask_mdb_on_start(self):
        reply = QMessageBox.question(
            self, 'MDB Dosyası',
            'Başlamadan önce bir MDB dosyası seçmek ister misiniz?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self._open_mdb()

    # ─────────────────────────────────────────────────────
    # Ana Menü / Kapanma yönetimi
    # ─────────────────────────────────────────────────────

    def set_app_quit_blocked(self, blocked: bool):
        """True: closeEvent kapanmayı engeller, Ana Menü'ye yönlendirir."""
        self._quit_blocked = blocked

    def _go_home(self):
        """Ana Menüye Dön butonuna basıldı."""
        if self._go_home_cb:
            self._go_home_cb()
        else:
            self.hide()

    def closeEvent(self, event):
        """Pencere X butonuna basıldığında Ana Menü'ye yönlendir."""
        if self._quit_blocked and self._go_home_cb:
            event.ignore()
            self._go_home_cb()
        else:
            event.accept()
