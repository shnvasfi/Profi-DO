"""
dialog_ayarlar.py
ProfiDO (KSB_ProfilKesim) – Şifreli İki Kademeli Ayarlar Dialogu.

Kullanım akışı:
  1. AyarlarDialog(parent) oluştur ve exec() çağır.
  2. Önce PasswordDialog açılır.
     • Kullanıcı şifresi → Kullanıcı Ayarları sekmesi
     • Master şifre    → Kullanıcı + Master sekmeleri
  3. Kaydet → settings.json güncellenir.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QGroupBox, QLabel, QSpinBox, QPushButton, QLineEdit,
    QFrame, QTabWidget, QWidget, QCheckBox, QScrollArea,
    QMessageBox, QRadioButton, QButtonGroup,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

import settings as st
from ui.kiosk import apply_kiosk
from ui.dialog_profil_kutuphanesi import ProfilKutuphanesiDialog

# ─────────────────────────────────────────────────────────────────────────────
# Ortak stil
# ─────────────────────────────────────────────────────────────────────────────
_STYLE = """
    QDialog        { background:#1a1a2e; color:#ccc; }
    QTabWidget::pane { border:1px solid #334; border-radius:4px; }
    QTabBar::tab   { background:#252540; color:#aaa; padding:6px 18px;
                     border:1px solid #334; border-bottom:none; border-radius:4px 4px 0 0;
                     font-size:12px; font-weight:bold; }
    QTabBar::tab:selected { background:#1a1a2e; color:#cdd6f4; }
    QTabBar::tab:hover    { background:#2e2e4e; }
    QGroupBox      { color:#89b4fa; font-weight:bold; font-size:12px;
                     border:1px solid #334; border-radius:6px;
                     margin-top:10px; padding-top:10px; }
    QGroupBox::title { subcontrol-origin:margin; left:10px; padding:0 4px; }
    QLabel         { color:#bbb; font-size:12px; }
    QLabel#note    { color:#667; font-size:11px; }
    QLabel#header  { color:#cdd6f4; font-size:11px; font-style:italic; }
    QSpinBox, QLineEdit {
        background:#2e2e42; color:#ddd; border:1px solid #556;
        border-radius:4px; padding:3px 6px; font-size:13px; }
    QSpinBox:focus, QLineEdit:focus { border:1px solid #7a9fd4; }
    QCheckBox      { color:#ccc; font-size:12px; spacing:8px; }
    QCheckBox::indicator { width:16px; height:16px; }
    QCheckBox::indicator:checked   { background:#2a6a2a; border:2px solid #4aaa4a;
                                     border-radius:3px; }
    QCheckBox::indicator:unchecked { background:#2e2e42; border:2px solid #556;
                                     border-radius:3px; }
    QPushButton    { background:#2e2e42; color:#ccc; border:1px solid #444;
                     border-radius:4px; padding:5px 14px; font-size:12px; }
    QPushButton:hover   { background:#3a3a55; }
    QPushButton#save    { background:#2a5a2a; color:#b8f0b8;
                          border:1px solid #4a8a4a; font-weight:bold; }
    QPushButton#save:hover  { background:#3a6a3a; }
    QPushButton#reset   { background:#5a2a00; color:#f4a261; border:1px solid #8a4a00; }
    QPushButton#reset:hover { background:#6a3a00; }
    QFrame#sep { background:#334; }
"""


# ─────────────────────────────────────────────────────────────────────────────
# Şifre Dialog
# ─────────────────────────────────────────────────────────────────────────────

class _PasswordDialog(QDialog):
    """Şifre girişi — 'user' veya 'master' role döndürür; iptal None döner."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('🔒  Ayarlar — Giriş')
        self.setFixedSize(360, 200)
        self.setModal(True)
        self.role = None   # 'user' | 'master'
        self._build()
        self.setStyleSheet(_STYLE)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        lbl = QLabel('Ayarlar sayfasına erişmek için şifrenizi girin:')
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl)

        self._ed = QLineEdit()
        self._ed.setEchoMode(QLineEdit.Password)
        self._ed.setPlaceholderText('Şifre…')
        self._ed.setFixedHeight(36)
        self._ed.setAlignment(Qt.AlignCenter)
        self._ed.returnPressed.connect(self._check)
        lay.addWidget(self._ed)

        self._lbl_err = QLabel('')
        self._lbl_err.setAlignment(Qt.AlignCenter)
        self._lbl_err.setStyleSheet('color:#ff7777; font-size:11px;')
        lay.addWidget(self._lbl_err)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton('İptal')
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton('Giriş  ➜')
        btn_ok.setObjectName('save')
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._check)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)

    def _check(self):
        s = st.load_settings()
        pwd = self._ed.text()
        if pwd == s.get('master_password', '12345678'):
            self.role = 'master'
            self.accept()
        elif pwd == s.get('user_password', '1234'):
            self.role = 'user'
            self.accept()
        else:
            self._lbl_err.setText('❌  Yanlış şifre, tekrar deneyin.')
            self._ed.clear()
            self._ed.setFocus()


# ─────────────────────────────────────────────────────────────────────────────
# Ana Ayarlar Dialog
# ─────────────────────────────────────────────────────────────────────────────

class AyarlarDialog(QDialog):
    """
    Şifreli iki kademeli ayarlar.
    • exec() çağrıldığında önce şifre sorulur.
    • Giriş başarısızsa dialog açılmaz.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('⚙  Ayarlar')
        self.setMinimumWidth(520)
        apply_kiosk(self)   # tam ekran, çerçevesiz kiosk modu
        self.setModal(True)
        self._role = None
        self._settings = st.load_settings()

    # ── exec() override: önce şifre sor ───────────────────────────────

    def exec(self):
        pwd_dlg = _PasswordDialog(self.parent())
        if pwd_dlg.exec() != QDialog.Accepted:
            return QDialog.Rejected
        self._role = pwd_dlg.role
        self._settings = st.load_settings()
        self._build_ui()
        self._load_to_ui()
        self.setStyleSheet(_STYLE)
        return super().exec()

    # ─────────────────────────────────────────────────────────────────
    # UI inşa
    # ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 16, 16, 16)

        # Rol etiketi
        role_lbl = QLabel(
            '🔑  Master Ayarları  (tam yetki)' if self._role == 'master'
            else '👤  Kullanıcı Ayarları'
        )
        role_lbl.setStyleSheet(
            'color:#f8c12f; font-size:13px; font-weight:bold;'
            if self._role == 'master'
            else 'color:#89b4fa; font-size:13px; font-weight:bold;'
        )
        root.addWidget(role_lbl)

        sep = QFrame(); sep.setObjectName('sep')
        sep.setFrameShape(QFrame.HLine); sep.setFixedHeight(1)
        root.addWidget(sep)

        # ── Sekmeler ──────────────────────────────────────────────
        self._tabs = QTabWidget()
        root.addWidget(self._tabs)

        # Kullanıcı sekmesi (her iki rol de görür)
        self._tabs.addTab(self._build_user_tab(), '⚙  Kullanıcı Ayarları')

        # Master sekmesi (sadece master görür)
        if self._role == 'master':
            self._tabs.addTab(self._build_master_tab(), '🔧  Master Ayarlar')

        # ── Alt butonlar ──────────────────────────────────────────
        sep2 = QFrame(); sep2.setObjectName('sep')
        sep2.setFrameShape(QFrame.HLine); sep2.setFixedHeight(1)
        root.addWidget(sep2)

        btn_row = QHBoxLayout()
        btn_reset = QPushButton('↺  Varsayılana Dön')
        btn_reset.setObjectName('reset')
        btn_reset.clicked.connect(self._reset_to_defaults)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()

        btn_cancel = QPushButton('İptal')
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton('✔  Kaydet')
        btn_save.setObjectName('save')
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save_and_close)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

    # ── Kullanıcı Ayarları Sekmesi ────────────────────────────────

    def _build_user_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(10, 10, 10, 10)

        def spinrow(grid, r, label, note, sp):
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(lbl, r, 0)
            grid.addWidget(sp, r, 1)
            if note:
                n = QLabel(note); n.setObjectName('note')
                grid.addWidget(n, r, 2)

        # Kesim optimizasyonu
        grp_cut = QGroupBox('✂  Kesim Optimizasyonu')
        g = QGridLayout(grp_cut); g.setSpacing(10)

        self._sp_blade = QSpinBox()
        self._sp_blade.setRange(0, 50); self._sp_blade.setSuffix(' mm')
        spinrow(g, 0, 'Testere Kalınlığı:', 'Her kesimde kaybedilen malzeme', self._sp_blade)

        self._sp_head = QSpinBox()
        self._sp_head.setRange(0, 200); self._sp_head.setSuffix(' mm')
        spinrow(g, 1, 'Baş Temizlik Payı:', 'Barın başında yapılan temizlik kesiği', self._sp_head)

        self._sp_tail = QSpinBox()
        self._sp_tail.setRange(0, 200); self._sp_tail.setSuffix(' mm')
        spinrow(g, 2, 'Son Temizlik ve Tutma Payı:', 'Barın sonunda kalan tutma+temizlik payı', self._sp_tail)

        self._sp_gap = QSpinBox()
        self._sp_gap.setRange(0, 100); self._sp_gap.setSuffix(' mm')
        spinrow(g, 3, 'Parçalar Arası Pay:', 'İki parça arası ek boşluk', self._sp_gap)

        self._lbl_summary = QLabel()
        self._lbl_summary.setStyleSheet('color:#56cfe1; font-size:11px; padding:4px 0;')
        self._lbl_summary.setWordWrap(True)
        g.addWidget(self._lbl_summary, 4, 0, 1, 3)

        lay.addWidget(grp_cut)

        # Trolley / Unit
        grp_tr = QGroupBox('🚚  Taşıyıcı ve Kapasite')
        t = QGridLayout(grp_tr); t.setSpacing(10)

        self._sp_trolleys = QSpinBox()
        self._sp_trolleys.setRange(1, 99); self._sp_trolleys.setSuffix(' adet')
        spinrow(t, 0, 'Trolley Sayısı:', 'Mevcut taşıyıcı araba adedi', self._sp_trolleys)

        self._sp_unit = QSpinBox()
        self._sp_unit.setRange(1, 99); self._sp_unit.setSuffix(' adet')
        spinrow(t, 1, 'Unit Sayısı:', 'Her trolleydeki birim (göz) sayısı', self._sp_unit)

        self._lbl_capacity = QLabel()
        self._lbl_capacity.setStyleSheet('color:#a6e3a1; font-size:11px; padding:4px 0;')
        t.addWidget(self._lbl_capacity, 2, 0, 1, 3)

        lay.addWidget(grp_tr)
        lay.addStretch()

        # Canlı güncelleme
        for sp in (self._sp_blade, self._sp_head, self._sp_tail, self._sp_gap):
            sp.valueChanged.connect(self._update_summary)
        for sp in (self._sp_trolleys, self._sp_unit):
            sp.valueChanged.connect(self._update_capacity)

        return w

    # ── Master Ayarları Sekmesi ───────────────────────────────────

    def _build_master_tab(self) -> QWidget:
        """Master ayarları — 4 alt sekme: Makine Listesi, Makine Program
        Seçimi, Profil Tanımlama, Şifre Yönetimi."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 6, 0, 0)
        lay.setSpacing(0)

        sub_tabs = QTabWidget()
        sub_tabs.addTab(self._build_machine_list_tab(),    '🏭  Makine Listesi')
        sub_tabs.addTab(self._build_machine_program_tab(), '💻  Makine Program Seçimi')
        sub_tabs.addTab(self._build_profil_tanimlama_tab(),'📚  Profil Tanımlama')
        sub_tabs.addTab(self._build_password_tab(),        '🔐  Şifre Yönetimi')
        lay.addWidget(sub_tabs)

        return w

    # ── Master alt sekme 1: Makine Listesi ─────────────────────────

    def _build_machine_list_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(10, 10, 10, 10)

        grp_mach = QGroupBox('🏭  Veri Gönderilecek Makine Listesi  (kullanılan makineleri işaretle)')
        mv = QVBoxLayout(grp_mach)
        mv.setSpacing(8)

        info = QLabel('Seçili makineler üretim listesi ve P-kod şablonlarında kullanılır.')
        info.setObjectName('note')
        info.setWordWrap(True)
        mv.addWidget(info)

        self._machine_checks: dict[str, QCheckBox] = {}
        for machine in st.ALL_MACHINES:
            cb = QCheckBox(machine)
            cb.setFont(QFont('Arial', 12))
            self._machine_checks[machine] = cb
            mv.addWidget(cb)

        lay.addWidget(grp_mach)
        lay.addStretch()
        return w

    # ── Master alt sekme 2: Makine Program Seçimi ──────────────────

    def _build_machine_program_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(10, 10, 10, 10)

        grp = QGroupBox('💻  Makine Program Seçimi')
        gv = QVBoxLayout(grp)
        gv.setSpacing(8)

        info = QLabel('Üretimde kullanılacak makine programını seçin.')
        info.setObjectName('note')
        info.setWordWrap(True)
        gv.addWidget(info)

        self._rb_program_group = QButtonGroup(w)

        self._rb_pim_dc = QRadioButton('PIM ve DC')
        self._rb_pim_dc.setFont(QFont('Arial', 12))
        self._rb_program_group.addButton(self._rb_pim_dc)
        gv.addWidget(self._rb_pim_dc)
        lbl_pim_dc = QLabel('Seçiliyse program şu anki gibi çalışmaya devam eder.')
        lbl_pim_dc.setObjectName('note')
        lbl_pim_dc.setWordWrap(True)
        gv.addWidget(lbl_pim_dc)

        self._rb_ncr = QRadioButton('NCR')
        self._rb_ncr.setFont(QFont('Arial', 12))
        self._rb_program_group.addButton(self._rb_ncr)
        gv.addWidget(self._rb_ncr)
        lbl_ncr = QLabel('Seçiliyse ilave çalışma gerekir — bu özellik henüz aktif değil (sonraki adım).')
        lbl_ncr.setObjectName('note')
        lbl_ncr.setWordWrap(True)
        gv.addWidget(lbl_ncr)

        lay.addWidget(grp)
        lay.addStretch()
        return w

    # ── Master alt sekme 3: Profil Tanımlama ───────────────────────

    def _build_profil_tanimlama_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(10, 10, 10, 10)

        grp = QGroupBox('📚  Profil Tanımlama')
        gv = QVBoxLayout(grp)
        gv.setSpacing(8)

        info = QLabel(
            'Profil kütüphanesine tam erişim: yeni profil ekleme, kopyalama, '
            'silme ve toplu Excel yükleme burada yapılır.'
        )
        info.setObjectName('note')
        info.setWordWrap(True)
        gv.addWidget(info)

        btn_open = QPushButton('📚  Profil Kütüphanesini Aç')
        btn_open.setObjectName('save')
        btn_open.setFixedHeight(36)
        btn_open.clicked.connect(self._open_profil_kutuphanesi)
        gv.addWidget(btn_open)

        lay.addWidget(grp)
        lay.addStretch()
        return w

    def _open_profil_kutuphanesi(self):
        dlg = ProfilKutuphanesiDialog(self, restricted=False)
        dlg.exec()

    # ── Master alt sekme 4: Şifre Yönetimi ─────────────────────────

    def _build_password_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(10, 10, 10, 10)

        grp_pwd = QGroupBox('🔐  Şifre Yönetimi')
        pg = QGridLayout(grp_pwd); pg.setSpacing(10)

        pg.addWidget(QLabel('Master Şifresi:'), 0, 0)
        self._ed_master_pwd = QLineEdit()
        self._ed_master_pwd.setEchoMode(QLineEdit.Password)
        self._ed_master_pwd.setPlaceholderText('Yeni master şifresi (boş bırakırsan değişmez)')
        pg.addWidget(self._ed_master_pwd, 0, 1)

        pg.addWidget(QLabel('Kullanıcı Şifresi:'), 1, 0)
        self._ed_user_pwd = QLineEdit()
        self._ed_user_pwd.setEchoMode(QLineEdit.Password)
        self._ed_user_pwd.setPlaceholderText('Yeni kullanıcı şifresi (boş bırakırsan değişmez)')
        pg.addWidget(self._ed_user_pwd, 1, 1)

        pwd_note = QLabel('Şifre alanları boş bırakılırsa mevcut şifreler korunur.')
        pwd_note.setObjectName('note')
        pg.addWidget(pwd_note, 2, 0, 1, 2)

        lay.addWidget(grp_pwd)
        lay.addStretch()
        return w

    # ─────────────────────────────────────────────────────────────
    # Veri yükleme / kaydetme
    # ─────────────────────────────────────────────────────────────

    def _load_to_ui(self):
        s = self._settings
        self._sp_blade.setValue(s.get('blade_mm', 4))
        self._sp_head.setValue(s.get('head_waste_mm', 20))
        self._sp_tail.setValue(s.get('tail_waste_mm', 20))
        self._sp_gap.setValue(s.get('gap_mm', 0))
        self._sp_trolleys.setValue(s.get('trolley_count', 5))
        self._sp_unit.setValue(s.get('unit_count', s.get('shelves_per_trolley', 6)))
        self._update_summary()
        self._update_capacity()

        if self._role == 'master':
            selected = s.get('selected_machines', [])
            for machine, cb in self._machine_checks.items():
                cb.setChecked(machine in selected)
            # Makine program seçimi
            if s.get('machine_program', 'PIM_DC') == 'NCR':
                self._rb_ncr.setChecked(True)
            else:
                self._rb_pim_dc.setChecked(True)
            # Şifre alanları boş (gösterme)
            self._ed_master_pwd.clear()
            self._ed_user_pwd.clear()

    def _save_and_close(self):
        data = {
            'blade_mm':            self._sp_blade.value(),
            'head_waste_mm':       self._sp_head.value(),
            'tail_waste_mm':       self._sp_tail.value(),
            'gap_mm':              self._sp_gap.value(),
            'trolley_count':       self._sp_trolleys.value(),
            'unit_count':          self._sp_unit.value(),
            'shelves_per_trolley': self._sp_unit.value(),   # geriye uyumluluk
        }

        if self._role == 'master':
            # Makine seçimleri
            data['selected_machines'] = [
                m for m, cb in self._machine_checks.items() if cb.isChecked()
            ]
            # Makine program seçimi
            data['machine_program'] = 'NCR' if self._rb_ncr.isChecked() else 'PIM_DC'
            # Şifreler — sadece dolu ise güncelle
            s = st.load_settings()
            new_mpwd = self._ed_master_pwd.text().strip()
            new_upwd = self._ed_user_pwd.text().strip()
            if new_mpwd:
                data['master_password'] = new_mpwd
            else:
                data['master_password'] = s.get('master_password', '12345678')
            if new_upwd:
                data['user_password'] = new_upwd
            else:
                data['user_password'] = s.get('user_password', '1234')

        st.save_settings(data)
        self.accept()

    def _reset_to_defaults(self):
        self._sp_blade.setValue(st.DEFAULTS['blade_mm'])
        self._sp_head.setValue(st.DEFAULTS['head_waste_mm'])
        self._sp_tail.setValue(st.DEFAULTS['tail_waste_mm'])
        self._sp_gap.setValue(st.DEFAULTS['gap_mm'])
        self._sp_trolleys.setValue(st.DEFAULTS['trolley_count'])
        self._sp_unit.setValue(st.DEFAULTS['unit_count'])

    # ─────────────────────────────────────────────────────────────
    # Canlı özet etiketleri
    # ─────────────────────────────────────────────────────────────

    def _update_summary(self):
        blade = self._sp_blade.value()
        head  = self._sp_head.value()
        tail  = self._sp_tail.value()
        gap   = self._sp_gap.value()
        usable = 6000 - head - tail
        self._lbl_summary.setText(
            f'Örnek (6000mm bar): Kullanılabilir = {usable}mm  |  '
            f'Parça arası = {blade+gap}mm  (testere {blade} + ek {gap})'
        )

    def _update_capacity(self):
        t = self._sp_trolleys.value()
        u = self._sp_unit.value()
        self._lbl_capacity.setText(
            f'Toplam {t} trolley × {u} unit = {t*u} kapasite'
        )

    # ─────────────────────────────────────────────────────────────
    # Dışarıdan çağrılabilir
    # ─────────────────────────────────────────────────────────────

    def get_settings(self) -> dict:
        s = st.load_settings()
        return s
