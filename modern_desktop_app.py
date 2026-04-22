import sys
import json
import time

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QProgressBar, QFrame, QScrollArea, QListWidget,
                             QListWidgetItem, QLineEdit, QCheckBox, QStackedWidget, QGridLayout, 
                             QPushButton, QTextEdit, QTabWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QColor, QFont, QPalette, QIcon

from core import db_manager
from core import hardware_detector
from core import scoring_engine
from core import ai_assistant
import psutil
import subprocess
import os
import random

# --- QSS Styling ---
# This gives the "flashy", glowing gamer look to the desktop app!
STYLESHEET = """
QMainWindow {
    background-color: #0B0C10; 
}
QFrame#Sidebar {
    background-color: #1F2833;
    border-right: 2px solid #2C3E50;
}
QPushButton.NavBtn {
    background-color: transparent;
    color: #C5C6C7;
    font-size: 16px;
    font-weight: bold;
    text-align: left;
    padding: 15px 20px;
    border: none;
    border-radius: 8px;
}
QPushButton.NavBtn:hover {
    background-color: rgba(69, 162, 158, 0.2);
    color: #66FCF1;
}
QPushButton.NavBtnActive {
    background-color: rgba(102, 252, 241, 0.15);
    color: #66FCF1;
    border-left: 4px solid #66FCF1;
}
QLabel.Title {
    color: #66FCF1;
    font-size: 28px;
    font-weight: 900;
}
QLabel.CardTitle {
    color: #45A29E;
    font-size: 14px;
    font-weight: bold;
}
QFrame.Card {
    background-color: #1a1a24;
    border: 1px solid #2C3E50;
    border-radius: 12px;
}
QFrame.Card:hover {
    border: 1px solid #66FCF1;
    background-color: #1e1e2d;
}
QProgressBar {
    background-color: #1F2833;
    border-radius: 8px;
    text-align: center;
    color: white;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #45A29E, stop:1 #66FCF1);
    border-radius: 8px;
}
QComboBox {
    background-color: #1F2833;
    color: white;
    padding: 8px 15px;
    border: 1px solid #2C3E50;
    border-radius: 5px;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QWidget#ScrollContent {
    background-color: transparent;
}
"""

class ScannerThread(QThread):
    finished_scan = pyqtSignal(dict)

    def run(self):
        # 1. Hardware Detection
        raw_hw = hardware_detector.get_system_info()
        
        # 2. Database Lookup
        cpu = db_manager.find_cpu(raw_hw["cpu"])
        gpu = db_manager.find_gpu(raw_hw["gpu"])
        
        if not cpu: cpu = {"name": raw_hw["cpu"], "power_score": 50.0}
        
        gpu_unrecognized = False
        if not gpu: 
            gpu_unrecognized = True
            gpu = {"name": raw_hw["gpu"], "power_score": 0.0}
            
        sys_score = scoring_engine.calculate_system_score(cpu["power_score"], gpu["power_score"], raw_hw["ram"])
        if gpu_unrecognized:
            sys_score = 0

        bn_data = scoring_engine.analyze_bottleneck(cpu["power_score"], gpu["power_score"])
        
        results = {
            "hw": raw_hw,
            "cpu_data": cpu,
            "gpu_data": gpu,
            "score": sys_score,
            "bn": bn_data
        }
        self.finished_scan.emit(results)


class ChatWorkerThread(QThread):
    """Runs AI chat in background so UI stays responsive."""
    finished = pyqtSignal(str)
    
    def __init__(self, message, context, language="TR", parent=None):
        super().__init__(parent)
        self._msg = message
        self._ctx = context
        self._lang = language
    
    def run(self):
        try:
            resp = ai_assistant.general_chat(self._msg, self._ctx, self._lang)
            self.finished.emit(resp)
        except Exception as e:
            self.finished.emit(f"Hata: {str(e)}")


class AnalyzeWorkerThread(QThread):
    """Runs AI hardware analysis in background."""
    finished = pyqtSignal(dict)
    
    def __init__(self, hw_name, is_cpu, parent=None):
        super().__init__(parent)
        self._hw_name = hw_name
        self._is_cpu = is_cpu
    
    def run(self):
        try:
            data = ai_assistant.analyze_hardware(self._hw_name, self._is_cpu, "TR")
            self.finished.emit(data)
        except Exception as e:
            self.finished.emit({"error": f"Hata: {str(e)}"})

# ─────────────────────────────────────────────────────────────────────────────
#  LOCALIZATION STRINGS
# ─────────────────────────────────────────────────────────────────────────────
STRINGS = {
    "TR": {
        # Sidebar sections
        "sec_ana":"ANA", "sec_perf":"PERFORMANS", "sec_tools":"ARAÇLAR",
        # Nav items
        "nav_dashboard":"Dashboard", "nav_bottleneck":"Darboğaz",
        "nav_fps":"Mev. PC FPS", "nav_builder":"PC Builder", "nav_bfps":"Builder FPS",
        "nav_ai":"AI Asistan", "nav_compare":"Karşılaştır", "nav_hw":"Donanım Analizi", "nav_settings":"Ayarlar",
        # Score widget
        "score_header":"Genel Skor",
        # Page titles
        "title_dashboard":"SİSTEM KONTROL MERKEZİ",
        "title_bottleneck":"DARBOĞAZ ANALİZİ",
        "title_fps":"MEVCUT PC: OYUN FPS TAHMİNİ",
        "title_builder":"PC BUILDER — HAYALİNDEKİ SİSTEM",
        "title_bfps":"🚀 HAYALİNDEKİ SİSTEM — SONUÇLAR",
        "title_hw":"🔬 DONANIM ANALİZİ",
        "title_ai":"🤖  PerfHub AI Asistan",
        "title_compare":"⚖️  DONANIM KARŞILAŞTIRICI",
        "title_settings":"⚙️  AYARLAR",
        # Dashboard hw card titles
        "card_cpu":"İŞLEMCİ",
        "card_gpu":"EKRAN KARTI",
        "card_ram":"BELLEK (RAM)",
        "card_ram_type":"RAM TİPİ & HIZ",
        "card_storage":"DEPOLAMA",
        "score_title":"GENEL PERFORMANS SKORU",
        "detail_section":"▼  DETAYLI DONANIM ANALİZİ",
        "scanning":"Sistem taranıyor, lütfen bekleyin...",
        # HW Analysis dynamic labels
        "lbl_gaming":"Gaming",
        "lbl_render":"Render/3D",
        "lbl_daily":"Günlük Ofis",
        "lbl_cores":"Çekirdek/Thread",
        "lbl_clocks":"Taban / Boost",
        "lbl_arch":"Mimari",
        "lbl_tdp":"TDP (tahmini)",
        "lbl_year":"Çıkış Yılı",
        "lbl_vram":"VRAM",
        "lbl_core_mhz":"Çekirdek MHz",
        "lbl_mem_mhz":"Bellek MHz",
        # Settings page
        "settings_lang_head":"🌍  Dil / Language",
        "settings_lang_desc":"Uygulama arayüzü ve AI Asistan'ın kullandığı dili seçin.",
        "settings_lang_active":"Aktif Dil: 🇹🇷 Türkçe",
        "settings_aff_head":"🛒  Satış Ortaklığı Linkleri",
        "settings_aff_desc":"Darboğaz tespiti yapıldığında gösterilecek mağaza linklerini seç.",
        "settings_about_head":"ℹ️  PerfHub AI Hakkında",
    },
    "EN": {
        # Sidebar sections
        "sec_ana":"MAIN", "sec_perf":"PERFORMANCE", "sec_tools":"TOOLS",
        # Nav items
        "nav_dashboard":"Dashboard", "nav_bottleneck":"Bottleneck",
        "nav_fps":"Cur. PC FPS", "nav_builder":"PC Builder", "nav_bfps":"Builder FPS",
        "nav_ai":"AI Assistant", "nav_compare":"Compare", "nav_hw":"HW Analysis", "nav_settings":"Settings",
        # Score widget
        "score_header":"Overall Score",
        # Page titles
        "title_dashboard":"SYSTEM CONTROL CENTER",
        "title_bottleneck":"BOTTLENECK ANALYSIS",
        "title_fps":"CURRENT PC: GAME FPS ESTIMATOR",
        "title_builder":"PC BUILDER — DREAM SYSTEM",
        "title_bfps":"🚀 DREAM SYSTEM — RESULTS",
        "title_hw":"🔬 HARDWARE ANALYSIS",
        "title_ai":"🤖  PerfHub AI Assistant",
        "title_compare":"⚖️  HARDWARE COMPARATOR",
        "title_settings":"⚙️  SETTINGS",
        # Dashboard hw card titles
        "card_cpu":"PROCESSOR",
        "card_gpu":"GRAPHICS CARD",
        "card_ram":"MEMORY (RAM)",
        "card_ram_type":"RAM TYPE & SPEED",
        "card_storage":"STORAGE",
        "score_title":"GLOBAL PERFORMANCE SCORE",
        "detail_section":"▼  DETAILED HARDWARE ANALYSIS",
        "scanning":"Scanning system, please wait...",
        # HW Analysis dynamic labels
        "lbl_gaming":"Gaming",
        "lbl_render":"Render/3D",
        "lbl_daily":"Daily / Office",
        "lbl_cores":"Cores/Threads",
        "lbl_clocks":"Base / Boost",
        "lbl_arch":"Architecture",
        "lbl_tdp":"TDP (est.)",
        "lbl_year":"Release Year",
        "lbl_vram":"VRAM",
        "lbl_core_mhz":"Core MHz",
        "lbl_mem_mhz":"Memory MHz",
        # Settings page
        "settings_lang_head":"🌍  Language / Dil",
        "settings_lang_desc":"Select the language for the app interface and AI Assistant.",
        "settings_lang_active":"Active Language: 🇬🇧 English",
        "settings_aff_head":"🛒  Affiliate Links",
        "settings_aff_desc":"Choose which stores to show when a bottleneck is detected.",
        "settings_about_head":"ℹ️  About PerfHub AI",
    }
}


# ─────────────────────────────────────────────────────────────────────────────
#  CUSTOM NAV BUTTON  (proper hover + active colors, no QLabel color-inherit bug)
# ─────────────────────────────────────────────────────────────────────────────
class NavButton(QFrame):
    clicked_signal = pyqtSignal()

    _TXT_NORMAL = "color: #B0BEC5; font-size: 14px; font-weight: bold; background: transparent; border: none;"
    _TXT_HOVER  = "color: #E0E0E0; font-size: 14px; font-weight: bold; background: transparent; border: none;"
    _TXT_ACTIVE = "color: #66FCF1; font-size: 14px; font-weight: bold; background: transparent; border: none;"

    def __init__(self, icon, name, badge_text="", badge_color="#10B981", parent=None):
        super().__init__(parent)
        self._is_active = False
        self.setFixedHeight(46)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFrameShadow(QFrame.Shadow.Plain)
        # objectName-specific selector prevents CSS from leaking into child QFrames
        self.setObjectName("NavBtnOuter")
        self.setStyleSheet("#NavBtnOuter { background: transparent; border: none; }")

        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 12, 0)
        h.setSpacing(0)

        # ── Left indicator strip (3 px wide) — the single colored line ──────────
        self._indicator = QFrame()
        self._indicator.setObjectName("NavIndicator")
        self._indicator.setFixedWidth(3)
        self._indicator.setFrameShape(QFrame.Shape.NoFrame)
        self._indicator.setStyleSheet("#NavIndicator { background: transparent; border: none; }")
        h.addWidget(self._indicator)
        h.addSpacing(13)

        self.name_lbl = QLabel(f"{icon}  {name}")
        self.name_lbl.setStyleSheet(self._TXT_NORMAL)
        h.addWidget(self.name_lbl, 1)

        self.badge_lbl = None
        if badge_text:
            self.badge_lbl = QLabel(badge_text)
            self.badge_lbl.setStyleSheet(
                f"background-color:{badge_color}; color:#0B0C10; font-size:9px;"
                f" font-weight:900; padding:2px 7px; border-radius:8px; border: none;"
            )
            self.badge_lbl.setFixedHeight(17)
            h.addWidget(self.badge_lbl)

    def set_text(self, icon, name):
        self.name_lbl.setText(f"{icon}  {name}")

    def _apply_state(self, bg: str, ind_color: str, txt: str):
        self.setStyleSheet(f"#NavBtnOuter {{ background: {bg}; border: none; }}")
        self._indicator.setStyleSheet(f"#NavIndicator {{ background: {ind_color}; border: none; }}")
        self.name_lbl.setStyleSheet(txt)

    def set_active(self, active):
        self._is_active = active
        if active:
            self._apply_state("rgba(102,252,241,0.10)", "#66FCF1", self._TXT_ACTIVE)
        else:
            self._apply_state("transparent", "transparent", self._TXT_NORMAL)

    def enterEvent(self, event):
        if not self._is_active:
            self._apply_state("rgba(69,162,158,0.10)", "#45A29E", self._TXT_HOVER)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._is_active:
            self._apply_state("transparent", "transparent", self._TXT_NORMAL)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked_signal.emit()
        super().mousePressEvent(event)



class SearchableList(QWidget):
    def __init__(self, placeholder="Search...", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(placeholder)
        self.search_box.setStyleSheet("background-color: #1a1a24; color: white; padding: 8px; border: 1px solid #45A29E; border-radius: 4px;")
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("background-color: #0B0C10; color: #C5C6C7; border: 1px solid #2C3E50; padding: 5px; font-size: 13px;")
        
        layout.addWidget(self.search_box)
        layout.addWidget(self.list_widget)
        
        self.search_box.textChanged.connect(self.filter_list)
        
    def add_item(self, text, data_obj):
        from PyQt6.QtCore import QSize
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, data_obj)
        item.setSizeHint(QSize(0, 46))  # Tall enough for 2 lines
        self.list_widget.addItem(item)
        
    def filter_list(self, text):
        search_text = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(search_text not in item.text().lower())

    def get_selected_data(self):
        selected = self.list_widget.selectedItems()
        if selected:
            return selected[0].data(Qt.ItemDataRole.UserRole)
        return None


class BenchmarkApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PerfHub AI v5.0 PRO — PC Performance Intelligence")
        self.resize(1000, 750)
        
        # Set window icon if exists
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))
        
        self.setStyleSheet(STYLESHEET)
        
        db_manager.initialize_db()
        self.system_data = None
        self._last_builder_gpu_name = ""
        self._last_cur_gpu_name = ""
        self._b_current_score = 0
        self._b_target_score = 0
        self.lang = "TR"  # Default language: Turkish
        
        # Show permission dialog on first run
        self.show_permission_dialog()
        
        self.init_ui()
        self.run_scanner()
    
    def show_permission_dialog(self):
        """Show permission dialog for hardware data collection."""
        from PyQt6.QtWidgets import QMessageBox
        
        msg = QMessageBox(self)
        msg.setWindowTitle("PerfHub AI - İzin Gerekli / Permission Required")
        msg.setIcon(QMessageBox.Icon.Question)
        
        # Bilingual message
        text = """
🇹🇷 TÜRKÇE:
PerfHub AI, sistem performansınızı analiz etmek için donanım bilgilerinizi (CPU, GPU, RAM) okumak istiyor.

✅ Verileriniz sadece yerel olarak işlenir
✅ İnternet üzerinden hiçbir veri gönderilmez
✅ Gizliliğiniz korunur

Devam etmek istiyor musunuz?

---

🇬🇧 ENGLISH:
PerfHub AI wants to read your hardware information (CPU, GPU, RAM) to analyze your system performance.

✅ Your data is processed locally only
✅ No data is sent over the internet
✅ Your privacy is protected

Do you want to continue?
        """
        
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        # Custom button text
        yes_btn = msg.button(QMessageBox.StandardButton.Yes)
        no_btn = msg.button(QMessageBox.StandardButton.No)
        yes_btn.setText("✅ İzin Ver / Allow")
        no_btn.setText("❌ İptal / Cancel")
        
        result = msg.exec()
        
        if result == QMessageBox.StandardButton.No:
            # User declined, show info and exit
            info = QMessageBox(self)
            info.setWindowTitle("PerfHub AI")
            info.setIcon(QMessageBox.Icon.Information)
            info.setText("🇹🇷 Uygulama kapatılıyor.\n🇬🇧 Application closing.")
            info.exec()
            sys.exit(0)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        root_layout = QHBoxLayout(main_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ============================================================
        # LEFT SIDEBAR (V3 — grouped, full-height, proper colors)
        # ============================================================
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setObjectName("SidebarFrame")
        sidebar.setStyleSheet(
            "#SidebarFrame { background-color: #111827; border-right: 1px solid #1F2D3D; }"
        )
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # ── Logo area ──────────────────────────────────────────────
        logo_frame = QFrame()
        logo_frame.setFixedHeight(72)
        logo_frame.setStyleSheet("background-color: #0D1117; border-bottom: 1px solid #1F2D3D;")
        logo_lay = QVBoxLayout(logo_frame)
        logo_lay.setContentsMargins(18, 10, 18, 10)
        logo_lay.setSpacing(2)
        logo_lbl = QLabel("⚡ PerfHub AI")
        logo_lbl.setStyleSheet("color: #66FCF1; font-size: 19px; font-weight: 900; letter-spacing: 1px;")
        logo_lay.addWidget(logo_lbl)
        sub_lbl = QLabel("v5.0 PRO")
        sub_lbl.setStyleSheet("color: #45A29E; font-size: 11px; font-weight: 700;")
        logo_lay.addWidget(sub_lbl)
        sidebar_layout.addWidget(logo_frame)

        # ── Nav button registry (for active state toggling) ────────
        self.nav_btns = []   # list of NavButton
        self._nav_page_map = {}  # page_idx -> NavButton

        def _section(key):
            lbl = QLabel(STRINGS["TR"][key])
            lbl.setStyleSheet(
                "color: #4A6280; font-size: 10px; font-weight: 900;"
                " letter-spacing: 2px; padding: 16px 18px 5px 18px;"
            )
            lbl.setObjectName(f"sec_{key}")
            sidebar_layout.addWidget(lbl)
            return lbl

        def _nav(page_idx, icon, str_key, badge_text="", badge_color="#10B981"):
            btn = NavButton(icon, STRINGS["TR"][str_key], badge_text, badge_color)
            btn.setObjectName(f"nav_{str_key}")
            btn.clicked_signal.connect(lambda: self.switch_page(page_idx))
            sidebar_layout.addWidget(btn)
            self.nav_btns.append(btn)
            self._nav_page_map[page_idx] = btn
            return btn

        # Store section labels for language updates
        self._sec_ana  = _section("sec_ana")
        self._nb_dash  = _nav(0, "🖥️",  "nav_dashboard")
        self._nb_bn    = _nav(1, "⚠️",   "nav_bottleneck")

        self._sec_perf = _section("sec_perf")
        self._nb_fps   = _nav(2, "🎮",   "nav_fps")
        self._nb_bld   = _nav(3, "🛠️",   "nav_builder")
        self._nb_bfps  = _nav(4, "🚀",   "nav_bfps")

        self._sec_tools = _section("sec_tools")
        self._nb_ai    = _nav(6, "🤖",   "nav_ai")
        self._nb_cmp   = _nav(7, "⚖️",   "nav_compare", "YENİ",  "#66FCF1")
        self._nb_hw    = _nav(5, "🔬",   "nav_hw")
        self._nb_set   = _nav(8, "⚙️",   "nav_settings")

        sidebar_layout.addStretch(1)

        # ── Score widget (bottom) ──────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1F2D3D;")
        sidebar_layout.addWidget(sep)

        score_w = QWidget()
        score_w.setStyleSheet("background-color: #0D1117;")
        sw_lay = QVBoxLayout(score_w)
        sw_lay.setContentsMargins(16, 12, 16, 16)
        sw_lay.setSpacing(4)

        self._lbl_score_header = QLabel(STRINGS["TR"]["score_header"])
        self._lbl_score_header.setStyleSheet(
            "color: #4A90B8; font-size: 11px; font-weight: 700; letter-spacing: 1px;"
        )
        sw_lay.addWidget(self._lbl_score_header)

        self.sidebar_score_lbl = QLabel("— / 100")
        self.sidebar_score_lbl.setStyleSheet(
            "color: #66FCF1; font-size: 22px; font-weight: 900;"
        )
        sw_lay.addWidget(self.sidebar_score_lbl)

        self.sidebar_score_bar = QProgressBar()
        self.sidebar_score_bar.setRange(0, 100)
        self.sidebar_score_bar.setValue(0)
        self.sidebar_score_bar.setFixedHeight(7)
        self.sidebar_score_bar.setTextVisible(False)
        self.sidebar_score_bar.setStyleSheet(
            "QProgressBar { background-color: #1F2D3D; border-radius: 3px; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #45A29E, stop:1 #66FCF1); border-radius: 3px; }"
        )
        sw_lay.addWidget(self.sidebar_score_bar)
        sidebar_layout.addWidget(score_w)

        root_layout.addWidget(sidebar)

        # ============================================================
        # MAIN CONTENT AREA  (QStackedWidget)
        # ============================================================
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #0B0C10;")

        self.page_dash       = QWidget(); self.page_dash.setObjectName("ScrollContent")
        self.page_bn         = QWidget(); self.page_bn.setObjectName("ScrollContent")
        self.page_fps        = QWidget(); self.page_fps.setObjectName("ScrollContent")
        self.page_builder    = QWidget(); self.page_builder.setObjectName("ScrollContent")
        self.page_b_fps      = QWidget(); self.page_b_fps.setObjectName("ScrollContent")
        self.page_hw_analyze = QWidget(); self.page_hw_analyze.setObjectName("ScrollContent")
        self.page_ai         = QWidget(); self.page_ai.setObjectName("ScrollContent")
        self.page_compare    = QWidget(); self.page_compare.setObjectName("ScrollContent")
        self.page_settings   = QWidget(); self.page_settings.setObjectName("ScrollContent")

        for page in [self.page_dash, self.page_bn, self.page_fps, self.page_builder,
                     self.page_b_fps, self.page_hw_analyze, self.page_ai,
                     self.page_compare, self.page_settings]:
            self.stack.addWidget(page)

        root_layout.addWidget(self.stack)

        # Setup page content
        self.setup_dash()
        self.setup_bottleneck()
        self.setup_games()
        self.setup_builder()
        self.setup_builder_fps()
        self.setup_hw_analyze()
        self.setup_ai()
        self.setup_compare()
        self.setup_settings()

        # Default: show Dashboard
        self.switch_page(0)

    def switch_page(self, index):
        """Switch the stacked widget page and update nav button active states."""
        self.stack.setCurrentIndex(index)
        for btn in self.nav_btns:
            btn.set_active(False)
        if index in self._nav_page_map:
            self._nav_page_map[index].set_active(True)

    # ---- SCROLLABLE WRAPPER for tall pages ----
    def _scrollable(self, inner_widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        scroll.setWidget(inner_widget)
        return scroll

    # ---------------- SECTION SETUPS ----------------

    def setup_dash(self):
        inner = QWidget(); inner.setObjectName("ScrollContent")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        self._page_title_dash = QLabel(STRINGS[self.lang]["title_dashboard"])
        self._page_title_dash.setProperty("class", "Title")
        layout.addWidget(self._page_title_dash)

        # Hardware Info Grid (CPU, GPU, RAM, RAM Details, Storage)
        hw_grid = QGridLayout()
        hw_grid.setSpacing(15)
        
        self._hw_card_title_cpu   = self.create_hw_card(STRINGS[self.lang]["card_cpu"],      hw_grid, 0, 0)
        self.lbl_cpu              = self._hw_card_title_cpu
        self._hw_card_title_gpu   = self.create_hw_card(STRINGS[self.lang]["card_gpu"],      hw_grid, 0, 1)
        self.lbl_gpu              = self._hw_card_title_gpu
        self._hw_card_title_ram   = self.create_hw_card(STRINGS[self.lang]["card_ram"],      hw_grid, 0, 2)
        self.lbl_ram              = self._hw_card_title_ram
        self._hw_card_title_ramt  = self.create_hw_card(STRINGS[self.lang]["card_ram_type"], hw_grid, 1, 0)
        self.lbl_ram_detail       = self._hw_card_title_ramt
        self._hw_card_title_stor  = self.create_hw_card(STRINGS[self.lang]["card_storage"],  hw_grid, 1, 1)
        self.lbl_storage          = self._hw_card_title_stor
        
        layout.addLayout(hw_grid)

        # Score Area (Glowing Box)
        score_frame = QFrame()
        score_frame.setProperty("class", "Card")
        score_layout = QVBoxLayout(score_frame)
        score_layout.setContentsMargins(30,30,30,30)
        score_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._lbl_score_title = QLabel(STRINGS[self.lang]["score_title"])
        self._lbl_score_title.setStyleSheet("color: #C5C6C7; font-size: 14px; font-weight: bold; letter-spacing: 2px;")
        self._lbl_score_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_layout.addWidget(self._lbl_score_title)

        self.lbl_score_num = QLabel("...")
        self.lbl_score_num.setStyleSheet("color: white; font-size: 72px; font-weight: 900;")
        self.lbl_score_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_layout.addWidget(self.lbl_score_num)

        self.score_bar = QProgressBar()
        self.score_bar.setFixedHeight(20)
        self.score_bar.setRange(0, 100)
        self.score_bar.setValue(0)
        score_layout.addWidget(self.score_bar)
        
        layout.addWidget(score_frame)

        # ── Detailed hardware analysis section (populated after scan) ──
        self._lbl_detail_section = QLabel(STRINGS[self.lang]["detail_section"])
        self._lbl_detail_section.setStyleSheet("color:#45A29E;font-size:13px;font-weight:bold;letter-spacing:2px;margin-top:10px;")
        self._lbl_detail_section.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_detail_section)

        self.dash_detail_container = QWidget()
        self.dash_detail_layout = QVBoxLayout(self.dash_detail_container)
        self.dash_detail_layout.setContentsMargins(0, 0, 0, 0)
        self.dash_detail_layout.setSpacing(14)
        self._lbl_scanning = QLabel(STRINGS[self.lang]["scanning"])
        self._lbl_scanning.setStyleSheet("color:#45A29E;font-size:14px;")
        self._lbl_scanning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dash_detail_layout.addWidget(self._lbl_scanning)
        layout.addWidget(self.dash_detail_container)

        layout.addStretch()
        page_layout = QVBoxLayout(self.page_dash)
        page_layout.setContentsMargins(0,0,0,0)
        page_layout.addWidget(self._scrollable(inner))

    def setup_bottleneck(self):
        inner = QWidget(); inner.setObjectName("ScrollContent")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        self._page_title_bn = QLabel(STRINGS[self.lang]["title_bottleneck"])
        self._page_title_bn.setProperty("class", "Title")
        layout.addWidget(self._page_title_bn)

        self.bn_frame = QFrame()
        self.bn_frame.setProperty("class", "Card")
        bn_layout = QVBoxLayout(self.bn_frame)
        bn_layout.setContentsMargins(40, 30, 40, 30)
        bn_layout.setSpacing(15)

        self.lbl_bn_title = QLabel(("Taranıyor..." if self.lang=="TR" else "Scanning..."))
        self.lbl_bn_title.setStyleSheet("color: #F59E0B; font-size: 22px; font-weight: bold;")
        self.lbl_bn_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_bn_desc = QLabel(("Bileşenler analiz ediliyor..." if self.lang=="TR" else "Analyzing components..."))
        self.lbl_bn_desc.setStyleSheet("color: #C5C6C7; font-size: 15px; line-height: 1.6;")
        self.lbl_bn_desc.setWordWrap(True)
        self.lbl_bn_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        bn_layout.addWidget(self.lbl_bn_title)
        bn_layout.addWidget(self.lbl_bn_desc)
        layout.addWidget(self.bn_frame)
        layout.addStretch()

        page_layout = QVBoxLayout(self.page_bn)
        page_layout.setContentsMargins(0,0,0,0)
        page_layout.addWidget(self._scrollable(inner))

    def create_hw_card(self, title, grid, row, col):
        card = QFrame()
        card.setProperty("class", "Card")
        l = QVBoxLayout(card)
        l.setContentsMargins(20,20,20,20)
        
        t = QLabel(title)
        t.setProperty("class", "CardTitle")
        val = QLabel("Scanning...")
        val.setStyleSheet("color: white; font-size: 16px; font-weight: bold; margin-top: 10px;")
        val.setWordWrap(True)
        
        l.addWidget(t)
        l.addWidget(val)
        grid.addWidget(card, row, col)
        return val

    def setup_games(self):
        inner = QWidget(); inner.setObjectName("ScrollContent")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)
        
        self._page_title_fps = QLabel(STRINGS[self.lang]["title_fps"])
        self._page_title_fps.setProperty("class", "Title")
        layout.addWidget(self._page_title_fps)


        # Filters
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Resolution: ", styleSheet="color: #45A29E; font-weight: bold;"))
        self.cmb_res = QComboBox()
        self.cmb_res.addItems(["1080p", "1440p", "4k"])
        self.cmb_res.currentTextChanged.connect(self.populate_games)
        filter_layout.addWidget(self.cmb_res)

        filter_layout.addWidget(QLabel("  Select Game: ", styleSheet="color: #45A29E; font-weight: bold;"))
        self.cmb_game = QComboBox()
        self.cmb_game.setEditable(True)
        self.cmb_game.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_game.setMinimumWidth(260)
        all_g = db_manager.get_all_games()
        for g in all_g:
            self.cmb_game.addItem(g["name"], g)
        # Enable MatchContains search while typing
        from PyQt6.QtWidgets import QCompleter
        from PyQt6.QtCore import Qt as _Qt
        _comp = self.cmb_game.completer()
        if _comp:
            _comp.setFilterMode(_Qt.MatchFlag.MatchContains)
            _comp.setCaseSensitivity(_Qt.CaseSensitivity.CaseInsensitive)
        self.cmb_game.currentIndexChanged.connect(self.populate_games)
        filter_layout.addWidget(self.cmb_game)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        layout.addSpacing(8)
        
        # --- AI Assist Row ---
        ai_layout = QHBoxLayout()
        ai_lbl = QLabel("\u26a1 AI Assist:")
        ai_lbl.setStyleSheet("color: #9D00FF; font-weight: bold; font-size: 13px;")
        ai_layout.addWidget(ai_lbl)
        
        ai_layout.addWidget(QLabel("Upscaling:", styleSheet="color: #C5C6C7; font-size: 13px;"))
        self.cmb_upscale = QComboBox()
        self.cmb_upscale.addItems([
            "Native",
            "DLAA / Native AA",
            "DLSS Quality", "DLSS Balanced", "DLSS Performance", "DLSS Ultra Performance",
            "FSR Quality",  "FSR Balanced",  "FSR Performance",  "FSR Ultra Performance",
            "XeSS Quality", "XeSS Balanced", "XeSS Performance",
        ])
        self.cmb_upscale.currentTextChanged.connect(self.populate_games)
        ai_layout.addWidget(self.cmb_upscale)
        
        ai_layout.addSpacing(20)
        ai_layout.addWidget(QLabel("Frame Gen:", styleSheet="color: #C5C6C7; font-size: 13px;"))
        self.cmb_framegen = QComboBox()
        self.cmb_framegen.addItems(["Kapalı"])
        self.cmb_framegen.setMinimumWidth(90)
        self.cmb_framegen.setStyleSheet("color: #F59E0B; font-weight: bold;")
        self.cmb_framegen.currentTextChanged.connect(self.populate_games)
        ai_layout.addWidget(self.cmb_framegen)
        ai_layout.addStretch()
        layout.addLayout(ai_layout)
        
        # RT/PT Row
        rt_layout = QHBoxLayout()
        rt_lbl = QLabel("🌟 Ray/Path Tracing:")
        rt_lbl.setStyleSheet("color: #9D00FF; font-weight: bold; font-size: 13px;")
        rt_layout.addWidget(rt_lbl)
        
        self.chk_rt = QCheckBox("Ray Tracing")
        self.chk_rt.setStyleSheet("color: #C5C6C7; font-size: 13px;")
        self.chk_rt.stateChanged.connect(self.populate_games)
        rt_layout.addWidget(self.chk_rt)
        
        self.chk_pt = QCheckBox("Path Tracing")
        self.chk_pt.setStyleSheet("color: #C5C6C7; font-size: 13px;")
        self.chk_pt.stateChanged.connect(self.populate_games)
        rt_layout.addWidget(self.chk_pt)
        
        self.lbl_rt_support = QLabel("")
        self.lbl_rt_support.setStyleSheet("color: #45A29E; font-size: 13px; font-weight: bold;")
        rt_layout.addWidget(self.lbl_rt_support)
        
        rt_layout.addStretch()
        layout.addLayout(rt_layout)

        # Upscaling support info label
        self.lbl_upscale_support = QLabel("")
        self.lbl_upscale_support.setStyleSheet("color: #C5C6C7; font-size: 12px; font-style: italic;")
        self.lbl_upscale_support.setWordWrap(True)
        layout.addWidget(self.lbl_upscale_support)
        layout.addSpacing(8)


        # FPS Progress Bars Container
        bars_container = QWidget()
        bars_layout = QVBoxLayout(bars_container)
        bars_layout.setContentsMargins(10, 10, 10, 10)
        bars_layout.setSpacing(15)
        
        self.fps_bars = {}
        for preset in ["Low", "Medium", "High", "Ultra"]:
            h_lay = QHBoxLayout()
            lbl = QLabel(f"{preset}:")
            lbl.setFixedWidth(70)
            lbl.setStyleSheet("color: #C5C6C7; font-size: 14px; font-weight: bold;")
            
            bar = QProgressBar()
            bar.setTextVisible(True)
            bar.setFormat("%v FPS")
            bar.setRange(0, 360) # Max 360 FPS scale
            bar.setFixedHeight(28)
            bar.setStyleSheet("QProgressBar { border: 1px solid #45A29E; background-color: #1a1a24; color: white; border-radius: 5px; text-align: center; font-weight: 900; } QProgressBar::chunk { background-color: #10B981; border-radius: 4px; }")
            
            h_lay.addWidget(lbl)
            h_lay.addWidget(bar)
            bars_layout.addLayout(h_lay)
            self.fps_bars[preset] = bar
            
        layout.addWidget(bars_container)
        layout.addStretch()
        page_layout = QVBoxLayout(self.page_fps)
        page_layout.setContentsMargins(0,0,0,0)
        page_layout.addWidget(self._scrollable(inner))

    def setup_builder(self):
        inner = QWidget(); inner.setObjectName("ScrollContent")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(15)
        
        self._page_title_builder = QLabel(STRINGS[self.lang]["title_builder"])
        self._page_title_builder.setProperty("class", "Title")
        self._page_title_builder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._page_title_builder)
        
        desc = QLabel("Select hardware to simulate a theoretical benchmark score.")
        desc.setStyleSheet("color: #C5C6C7; font-size: 16px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        layout.addSpacing(20)
        
        # Selectors Split
        sel_layout = QHBoxLayout()
        
        # --- CPU Block ---
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("SELECT CPU BRAND:", styleSheet="color: #45A29E; font-weight: bold; font-size: 14px;"))
        self.cpu_tabs = QTabWidget()
        self.cpu_tabs.setStyleSheet("QTabBar::tab { background: #1F2833; color: white; padding: 8px 20px; font-weight:bold;} QTabBar::tab:selected { background: #45A29E; }")
        
        self.cpu_list_intel = SearchableList("Search Intel CPUs...")
        self.cpu_list_amd = SearchableList("Search AMD CPUs...")
        self.cpu_list_apple = SearchableList("Search Apple M-Series CPUs...")
        
        self.cpu_tabs.addTab(self.cpu_list_intel, "Intel")
        self.cpu_tabs.addTab(self.cpu_list_amd, "AMD")
        self.cpu_tabs.addTab(self.cpu_list_apple, "Apple")
        
        # Connect tab change to disable GPU if Apple is selected
        self.cpu_tabs.currentChanged.connect(self.check_apple_selection)
        
        v1.addWidget(self.cpu_tabs)
        sel_layout.addLayout(v1)
        
        sel_layout.addSpacing(20)
        
        # --- GPU Block (Wrapped in widget for disabling) ---
        self.gpu_block_widget = QWidget()
        v2 = QVBoxLayout(self.gpu_block_widget)
        v2.setContentsMargins(0,0,0,0)
        self.gpu_lbl_title = QLabel("SELECT GPU BRAND:", styleSheet="color: #45A29E; font-weight: bold; font-size: 14px;")
        v2.addWidget(self.gpu_lbl_title)
        
        self.gpu_tabs = QTabWidget()
        self.gpu_tabs.setStyleSheet("QTabBar::tab { background: #1F2833; color: white; padding: 8px 20px; font-weight:bold;} QTabBar::tab:selected { background: #45A29E; }")
        
        self.gpu_list_nvidia = SearchableList("Search NVIDIA GPUs...")
        self.gpu_list_amd = SearchableList("Search AMD GPUs...")
        self.gpu_list_intel = SearchableList("Search Intel ARC GPUs...")
        
        self.gpu_tabs.addTab(self.gpu_list_nvidia, "NVIDIA")
        self.gpu_tabs.addTab(self.gpu_list_amd, "AMD")
        self.gpu_tabs.addTab(self.gpu_list_intel, "Intel")
        v2.addWidget(self.gpu_tabs)
        sel_layout.addWidget(self.gpu_block_widget)
        
        layout.addLayout(sel_layout)
        
        # Populate combinations from DB
        all_cpus = db_manager.get_all_cpus()
        for c in all_cpus:
            name = c['name'].upper()
            cores = c.get('cores', '?')
            boost = c.get('boost_clock', '?')
            arch = c.get('architecture', '')
            display = f"{c['name']}\n  {cores} Çekirdek  |  Max {boost} GHz  |  {arch}"
            if "INTEL" in name: self.cpu_list_intel.add_item(display, c)
            elif "AMD" in name or "RYZEN" in name: self.cpu_list_amd.add_item(display, c)
            else: self.cpu_list_apple.add_item(display, c)

        all_gpus = db_manager.get_all_gpus()
        for g in all_gpus:
            name = g['name'].upper()
            vram_val = g.get('vram', 0)
            clk = g.get('core_clock', 0)
            arch = g.get('architecture', '')
            # Strip any existing (xGB) from the name to avoid duplication
            base_name = g['name'].split('(')[0].strip()
            if vram_val and vram_val > 0:
                display = f"{base_name}\n  {vram_val} GB VRAM  |  {clk} MHz  |  {arch}"
            else:
                display = f"{base_name}\n  {arch} (Paylaşımlı)"
            if "NVIDIA" in name or "GEFORCE" in name or "RTX" in name or "GTX" in name:
                self.gpu_list_nvidia.add_item(display, g)
            elif "AMD" in name or "RADEON" in name or "RX " in name:
                self.gpu_list_amd.add_item(display, g)
            else:
                self.gpu_list_intel.add_item(display, g)
             
        # Button + RAM Selector
        layout.addSpacing(20)
        
        # RAM Selector
        ram_layout = QHBoxLayout()
        ram_lbl = QLabel("💾 RAM Miktarı:")
        ram_lbl.setStyleSheet("color: #45A29E; font-size: 16px; font-weight: bold;")
        ram_layout.addWidget(ram_lbl)
        
        self.b_cmb_ram = QComboBox()
        self.b_cmb_ram.addItems(["4 GB", "8 GB", "16 GB", "32 GB", "64 GB", "128 GB"])
        self.b_cmb_ram.setCurrentText("16 GB")  # Default
        self.b_cmb_ram.setMinimumWidth(120)
        self.b_cmb_ram.setStyleSheet("background-color: #1F2833; color: white; padding: 8px 15px; border: 1px solid #45A29E; border-radius: 5px; font-size: 14px; font-weight: bold;")
        ram_layout.addWidget(self.b_cmb_ram)
        ram_layout.addStretch()
        layout.addLayout(ram_layout)
        
        layout.addSpacing(10)
        
        btn_calc = QPushButton("⚙️ CALCULATE THEORETICAL SCORE")
        btn_calc.setFixedSize(400, 50)
        btn_calc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_calc.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #66FCF1; font-size: 18px; font-weight: 900; 
                border-radius: 8px; border: 2px solid #66FCF1;
            }
            QPushButton:hover { background-color: rgba(102, 252, 241, 0.2); }
        """)
        btn_calc.clicked.connect(self.calculate_custom_build)
        layout.addWidget(btn_calc, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        page_layout = QVBoxLayout(self.page_builder)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(self._scrollable(inner))

    def setup_builder_fps(self):
        """Page 4 - Builder FPS results, displayed after Calculate is clicked."""
        inner = QWidget(); inner.setObjectName("ScrollContent")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        self._page_title_bfps = QLabel(STRINGS[self.lang]["title_bfps"])
        self._page_title_bfps.setProperty("class", "Title")
        layout.addWidget(self._page_title_bfps)


        # Score + bottleneck row
        score_card = QFrame(); score_card.setProperty("class", "Card")
        sc_layout = QVBoxLayout(score_card)
        sc_layout.setContentsMargins(30, 25, 30, 25)
        sc_layout.setSpacing(10)
        sc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sc_lbl = QLabel("TEÖRİK PERFORMANS SKORU" if self.lang=="TR" else "THEORETICAL PERFORMANCE SCORE")
        sc_lbl.setStyleSheet("color: #C5C6C7; font-size: 13px; font-weight: bold; letter-spacing: 2px;")
        sc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sc_layout.addWidget(sc_lbl)

        self.lbl_b_score_num = QLabel("--")
        self.lbl_b_score_num.setStyleSheet("color: #66FCF1; font-size: 72px; font-weight: 900;")
        self.lbl_b_score_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sc_layout.addWidget(self.lbl_b_score_num)

        self.b_score_bar = QProgressBar()
        self.b_score_bar.setFixedHeight(18)
        self.b_score_bar.setRange(0, 100)
        self.b_score_bar.setValue(0)
        self.b_score_bar.setStyleSheet("QProgressBar { background-color: #1F2833; border-radius: 8px; text-align: center; color: white; font-weight: bold; } QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #45A29E, stop:1 #66FCF1); border-radius: 8px; }")
        sc_layout.addWidget(self.b_score_bar)

        self.lbl_b_bn = QLabel("Hesaplanıyor...")
        self.lbl_b_bn.setStyleSheet("color: #F59E0B; font-size: 15px;")
        self.lbl_b_bn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sc_layout.addWidget(self.lbl_b_bn)

        self.b_affiliate_lbl = QLabel("")
        self.b_affiliate_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.b_affiliate_lbl.setOpenExternalLinks(True)
        self.b_affiliate_lbl.hide()
        sc_layout.addWidget(self.b_affiliate_lbl)
        layout.addWidget(score_card)

        # FPS Estimator controls
        fps_card = QFrame(); fps_card.setProperty("class", "Card")
        fps_layout = QVBoxLayout(fps_card)
        fps_layout.setContentsMargins(30, 20, 30, 20)
        fps_layout.setSpacing(14)

        fps_head = QLabel("TAHMİNİ FPS (HAYALİ SİSTEM)" if self.lang=="TR" else "ESTIMATED FPS (DREAM SYSTEM)")
        fps_head.setStyleSheet("color: #66FCF1; font-size: 16px; font-weight: bold;")
        fps_head.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fps_layout.addWidget(fps_head)

        b_filter_layout = QHBoxLayout()
        b_filter_layout.addWidget(QLabel("Çözünürlük: ", styleSheet="color: #45A29E; font-weight: bold;"))
        self.b_cmb_res = QComboBox()
        self.b_cmb_res.addItems(["1080p", "1440p", "4k"])
        self.b_cmb_res.currentTextChanged.connect(self.calculate_custom_build)
        b_filter_layout.addWidget(self.b_cmb_res)
        
        b_filter_layout.addWidget(QLabel("  RAM: ", styleSheet="color: #45A29E; font-weight: bold;"))
        self.b_cmb_ram_fps = QComboBox()
        self.b_cmb_ram_fps.addItems(["4 GB", "8 GB", "16 GB", "32 GB", "64 GB", "128 GB"])
        self.b_cmb_ram_fps.setCurrentText("16 GB")
        self.b_cmb_ram_fps.currentTextChanged.connect(self.calculate_custom_build)
        b_filter_layout.addWidget(self.b_cmb_ram_fps)
        
        b_filter_layout.addWidget(QLabel("  Oyun: ", styleSheet="color: #45A29E; font-weight: bold;"))
        self.b_cmb_game = QComboBox()
        self.b_cmb_game.setEditable(True)
        self.b_cmb_game.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.b_cmb_game.setMinimumWidth(260)
        for g in db_manager.get_all_games():
            self.b_cmb_game.addItem(g["name"], g)
        from PyQt6.QtWidgets import QCompleter as _QC
        from PyQt6.QtCore import Qt as _Qt2
        _comp2 = self.b_cmb_game.completer()
        if _comp2:
            _comp2.setFilterMode(_Qt2.MatchFlag.MatchContains)
            _comp2.setCaseSensitivity(_Qt2.CaseSensitivity.CaseInsensitive)
        self.b_cmb_game.currentIndexChanged.connect(self.calculate_custom_build)
        b_filter_layout.addWidget(self.b_cmb_game)
        b_filter_layout.addStretch()
        fps_layout.addLayout(b_filter_layout)

        b_ai_layout = QHBoxLayout()
        b_ai_lbl = QLabel("\u26a1 AI Assist:"); b_ai_lbl.setStyleSheet("color: #9D00FF; font-weight: bold; font-size: 13px;")
        b_ai_layout.addWidget(b_ai_lbl)
        b_ai_layout.addWidget(QLabel("Upscaling:", styleSheet="color: #C5C6C7; font-size: 13px;"))
        self.b_cmb_upscale = QComboBox()
        self.b_cmb_upscale.addItems([
            "Native",
            "DLAA / Native AA",
            "DLSS Quality", "DLSS Balanced", "DLSS Performance", "DLSS Ultra Performance",
            "FSR Quality",  "FSR Balanced",  "FSR Performance",  "FSR Ultra Performance",
            "XeSS Quality", "XeSS Balanced", "XeSS Performance",
        ])
        self.b_cmb_upscale.currentTextChanged.connect(self.calculate_custom_build)
        b_ai_layout.addWidget(self.b_cmb_upscale)
        b_ai_layout.addSpacing(20)
        b_ai_layout.addWidget(QLabel("Frame Gen:", styleSheet="color: #C5C6C7; font-size: 13px;"))
        self.b_cmb_framegen = QComboBox()
        self.b_cmb_framegen.addItems(["Kapalı"])
        self.b_cmb_framegen.setMinimumWidth(90)
        self.b_cmb_framegen.setStyleSheet("color: #F59E0B; font-weight: bold;")
        self.b_cmb_framegen.currentTextChanged.connect(self.calculate_custom_build)
        b_ai_layout.addWidget(self.b_cmb_framegen)
        b_ai_layout.addStretch()
        fps_layout.addLayout(b_ai_layout)
        
        # RT/PT Row for Builder
        b_rt_layout = QHBoxLayout()
        b_rt_lbl = QLabel("🌟 Ray/Path Tracing:")
        b_rt_lbl.setStyleSheet("color: #9D00FF; font-weight: bold; font-size: 13px;")
        b_rt_layout.addWidget(b_rt_lbl)
        
        self.b_chk_rt = QCheckBox("Ray Tracing")
        self.b_chk_rt.setStyleSheet("color: #C5C6C7; font-size: 13px;")
        self.b_chk_rt.stateChanged.connect(self.calculate_custom_build)
        b_rt_layout.addWidget(self.b_chk_rt)
        
        self.b_chk_pt = QCheckBox("Path Tracing")
        self.b_chk_pt.setStyleSheet("color: #C5C6C7; font-size: 13px;")
        self.b_chk_pt.stateChanged.connect(self.calculate_custom_build)
        b_rt_layout.addWidget(self.b_chk_pt)
        
        self.b_lbl_rt_support = QLabel("")
        self.b_lbl_rt_support.setStyleSheet("color: #45A29E; font-size: 13px; font-weight: bold;")
        b_rt_layout.addWidget(self.b_lbl_rt_support)
        
        b_rt_layout.addStretch()
        fps_layout.addLayout(b_rt_layout)
        
        # Upscaling support info label for Builder
        self.b_lbl_upscale_support = QLabel("")
        self.b_lbl_upscale_support.setStyleSheet("color: #C5C6C7; font-size: 12px; font-style: italic;")
        self.b_lbl_upscale_support.setWordWrap(True)
        fps_layout.addWidget(self.b_lbl_upscale_support)
        fps_layout.addSpacing(8)


        self.b_fps_bars = {}
        for preset in ["Low", "Medium", "High", "Ultra"]:
            h_lay = QHBoxLayout()
            lbl = QLabel(f"{preset}:"); lbl.setFixedWidth(70)
            lbl.setStyleSheet("color: #C5C6C7; font-size: 14px; font-weight: bold;")
            bar = QProgressBar()
            bar.setTextVisible(True); bar.setFormat("%v FPS")
            bar.setRange(0, 360); bar.setFixedHeight(30)
            bar.setStyleSheet("QProgressBar { border:1px solid #45A29E; background-color:#1a1a24; color:white; border-radius:5px; text-align:center; font-weight:900; font-size:15px; } QProgressBar::chunk { background-color:#10B981; border-radius:4px; }")
            h_lay.addWidget(lbl); h_lay.addWidget(bar)
            fps_layout.addLayout(h_lay)
            self.b_fps_bars[preset] = bar

        layout.addWidget(fps_card)
        layout.addStretch()

        page_layout = QVBoxLayout(self.page_b_fps)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(self._scrollable(inner))

    # ---------------- HARDWARE ANALYZER PAGE ----------------

    def setup_hw_analyze(self):
        """Page 5 - Detailed hardware analysis."""
        inner = QWidget(); inner.setObjectName("ScrollContent")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        self._page_title_hw = QLabel(STRINGS[self.lang]["title_hw"])
        self._page_title_hw.setProperty("class", "Title")
        layout.addWidget(self._page_title_hw)

        # Selector row
        sel_card = QFrame(); sel_card.setProperty("class", "Card")
        sel_layout = QHBoxLayout(sel_card)
        sel_layout.setContentsMargins(20, 14, 20, 14)
        sel_layout.addWidget(QLabel("Kategori:", styleSheet="color:#45A29E;font-weight:bold;"))
        self.hw_type_combo = QComboBox()
        self.hw_type_combo.addItems(["İşlemci (CPU)", "Ekran Kartı (GPU)"])
        self.hw_type_combo.setMinimumWidth(170)
        self.hw_type_combo.currentIndexChanged.connect(self._reload_hw_list)
        sel_layout.addWidget(self.hw_type_combo)
        sel_layout.addSpacing(20)
        sel_layout.addWidget(QLabel("Ara:", styleSheet="color:#45A29E;font-weight:bold;"))
        self.hw_search = QLineEdit()
        self.hw_search.setPlaceholderText("Donanım adı yazın...")
        self.hw_search.setMinimumWidth(280)
        self.hw_search.setStyleSheet("background-color:#1F2833;color:white;border:1px solid #45A29E;border-radius:6px;padding:6px 10px;")
        self.hw_search.textChanged.connect(self._filter_hw_list)
        sel_layout.addWidget(self.hw_search)
        sel_layout.addStretch()
        layout.addWidget(sel_card)

        # List + result split
        split = QHBoxLayout(); split.setSpacing(16)
        list_panel = QFrame(); list_panel.setProperty("class", "Card"); list_panel.setFixedWidth(300)
        lp_lay = QVBoxLayout(list_panel); lp_lay.setContentsMargins(8, 8, 8, 8)
        self.hw_list = QListWidget()
        self.hw_list.setStyleSheet(
            "QListWidget{background-color:#0d0d18;color:white;border:none;font-size:12px;}"
            "QListWidget::item{padding:8px 6px;border-bottom:1px solid #1e2a38;}"
            "QListWidget::item:selected{background-color:#45A29E;color:#0d0d18;font-weight:bold;}"
            "QListWidget::item:hover{background-color:#1e2a38;}")
        self.hw_list.currentRowChanged.connect(self._on_hw_selected)
        lp_lay.addWidget(self.hw_list)
        split.addWidget(list_panel)

        self.hw_result_panel = QWidget(); self.hw_result_panel.setObjectName("ScrollContent")
        self.hw_result_layout = QVBoxLayout(self.hw_result_panel)
        self.hw_result_layout.setContentsMargins(0, 0, 0, 0); self.hw_result_layout.setSpacing(14)
        placeholder = QLabel("\u2190 Listeden bir donanım seçin")
        placeholder.setStyleSheet("color:#45A29E;font-size:18px;font-weight:bold;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hw_result_layout.addWidget(placeholder)
        result_scroll = QScrollArea(); result_scroll.setWidgetResizable(True)
        result_scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        result_scroll.setWidget(self.hw_result_panel)
        split.addWidget(result_scroll, 1)
        layout.addLayout(split)

        page_layout = QVBoxLayout(self.page_hw_analyze)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(self._scrollable(inner))
        self._hw_all_items = []
        self._reload_hw_list()

    def _reload_hw_list(self):
        is_cpu = self.hw_type_combo.currentIndex() == 0
        rows = db_manager.get_all_cpus() if is_cpu else db_manager.get_all_gpus()
        self._hw_all_items = [{"type": "cpu" if is_cpu else "gpu", **r} for r in rows]
        self.hw_search.clear()
        self._filter_hw_list()

    def _filter_hw_list(self):
        query = self.hw_search.text().lower()
        self.hw_list.blockSignals(True); self.hw_list.clear()
        for item in self._hw_all_items:
            if query in item["name"].lower():
                lw = QListWidgetItem(item["name"])
                lw.setData(Qt.ItemDataRole.UserRole, item)
                self.hw_list.addItem(lw)
        self.hw_list.blockSignals(False)

    def _on_hw_selected(self, row):
        if row < 0: return
        item = self.hw_list.item(row)
        if item: self._build_analysis(item.data(Qt.ItemDataRole.UserRole))

    def _score_bar(self, label, score_10, color):
        row = QHBoxLayout()
        lbl = QLabel(f"{label}:"); lbl.setFixedWidth(100)
        lbl.setStyleSheet("color:#C5C6C7;font-size:13px;font-weight:bold;")
        bar = QProgressBar(); bar.setRange(0, 10); bar.setValue(int(score_10))
        bar.setFixedHeight(22); bar.setTextVisible(True); bar.setFormat(f"  {score_10:.0f} / 10")
        bar.setStyleSheet(f"QProgressBar{{border:1px solid #1e2a38;background:#1F2833;color:white;border-radius:5px;text-align:left;font-weight:bold;font-size:12px;}} QProgressBar::chunk{{background-color:{color};border-radius:4px;}}")
        row.addWidget(lbl); row.addWidget(bar)
        return row

    def _hw_card(self, title_text):
        card = QFrame(); card.setProperty("class", "Card")
        lay = QVBoxLayout(card); lay.setContentsMargins(22, 18, 22, 18); lay.setSpacing(10)
        t = QLabel(title_text)
        t.setStyleSheet("color:#66FCF1;font-size:14px;font-weight:900;letter-spacing:1px;border-bottom:1px solid #1e2a38;padding-bottom:6px;")
        lay.addWidget(t)
        return card, lay

    def _build_analysis(self, hw):
        while self.hw_result_layout.count():
            child = self.hw_result_layout.takeAt(0)
            w = child.widget()
            if w:
                try: w.setParent(None); w.deleteLater()
                except RuntimeError: pass
        is_cpu = hw["type"] == "cpu"
        ps = hw.get("power_score", 50.0); arch = hw.get("architecture", "N/A"); name = hw["name"]

        if is_cpu:
            cores = hw.get("cores", 0)
            n_up   = name.upper()
            is_apple_a  = "APPLE" in n_up or any(f"M{i}" in n_up for i in range(1,6))
            is_u_a      = " U" in n_up or n_up.endswith("U)") or "ULTRA-LOW" in n_up
            is_laptop_a = not is_apple_a and ("HX" in n_up or "HS" in n_up or "HK" in n_up
                          or n_up.endswith(" H") or " H " in n_up or n_up.endswith("-H")
                          or " U " in n_up or "MOBILE" in n_up)
            # Gaming: desktop > laptop H > laptop HS > U-series, X3D bonus
            if is_apple_a:
                gaming_s = min(6.0, ps / 22.0 + 1.0)  # macOS game library is very limited
            elif "X3D" in n_up:
                gaming_s = min(10, ps / 10.0 + 2.0)
            elif is_u_a:
                gaming_s = min(6.5, ps / 14.0)
            elif is_laptop_a:
                gaming_s = min(8.5, ps / 11.0 + 0.5)
            else:
                gaming_s = min(10, ps / 10.5)
            # Render: Apple unified memory excels, laptop throttles under sustained load
            if is_apple_a:
                render_s = min(10, ps / 9.0)
            else:
                render_s = min(10, (cores / 3.2) * 0.6 + ps / 28.0)
                if is_laptop_a and not is_u_a: render_s *= 0.82
                elif is_u_a: render_s *= 0.65
            # Office: monotonically increasing — powerful CPUs handle office perfectly
            if ps >= 50:   daily_s = min(10, 8.5 + (ps - 50) / 80.0)
            elif ps >= 30: daily_s = 7.0 + (ps - 30) / 20.0
            else:          daily_s = max(4.0, ps / 7.5)
        else:
            vram = hw.get("vram", 8) or 8
            gaming_s = min(10, ps / 13.0 + vram / 14.0)
            render_s = min(10, vram / 2.8 + ps / 25.0)
            # GPU office: mid-range cards are fine for office, flagship is overkill but still fine
            daily_s  = 8.5 if ps >= 40 else max(5.0, ps / 6.0)
        gaming_s = round(gaming_s, 1); render_s = round(render_s, 1); daily_s = round(min(10, daily_s), 1)

        _cpu_lbl = STRINGS[self.lang]["card_cpu"] if is_cpu else STRINGS[self.lang]["card_gpu"]
        h_lbl = QLabel(f"{'🖥️ ' if is_cpu else '🎮 '}{_cpu_lbl}  —  {name}")
        h_lbl.setStyleSheet("color:white;font-size:17px;font-weight:900;"); h_lbl.setWordWrap(True)
        self.hw_result_layout.addWidget(h_lbl)

        # ── AI Analysis Button ──
        self.ai_analyze_btn = QPushButton(STRINGS[self.lang].get("btn_ai_analyze","🤖 AI ile Analiz Et") if self.lang=="TR" else "🤖 Analyze with AI (Expert)")
        self.ai_analyze_btn.setStyleSheet("background-color:#F59E0B;color:#0B0C10;font-weight:900;padding:8px;border-radius:4px;font-size:13px;")
        self.ai_analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ai_analyze_btn.clicked.connect(lambda: self._on_ai_analyze_clicked(name, is_cpu))
        self.hw_result_layout.addWidget(self.ai_analyze_btn)

        # Container for the AI result
        self.ai_result_container = QWidget()
        self.ai_result_layout = QVBoxLayout(self.ai_result_container)
        self.ai_result_layout.setContentsMargins(0,0,0,0)
        self.hw_result_layout.addWidget(self.ai_result_container)

        # 1. Use-case score bars
        c1, l1 = self._hw_card(STRINGS[self.lang].get("card_title_scores","📊  KULLANIM PUANLARI") if self.lang=="TR" else "📊  USE-CASE SCORES")
        S = STRINGS[self.lang]
        l1.addLayout(self._score_bar(S["lbl_gaming"],         gaming_s, "#9D00FF"))
        l1.addLayout(self._score_bar(S["lbl_render"],         render_s, "#3B82F6"))
        l1.addLayout(self._score_bar(S["lbl_daily"],          daily_s,  "#10B981"))
        l1.addLayout(self._score_bar("Performans",  min(10, ps / 13.0), "#F59E0B"))
        self.hw_result_layout.addWidget(c1)

        # 2. Tech specs
        c2, l2 = self._hw_card(STRINGS[self.lang].get("card_title_specs","⚙️  TEKNİK ÖZELLİKLER") if self.lang=="TR" else "⚙️  SPECIFICATIONS")
        if is_cpu:
            _S = STRINGS[self.lang]
            specs = {
                _S["lbl_cores"]: f"{hw.get('cores','?')} / {hw.get('threads','?')}",
                _S["lbl_clocks"]: f"{hw.get('base_clock','?')} / {hw.get('boost_clock','?')} GHz",
                _S["lbl_arch"]: arch,
                _S["lbl_tdp"]: self._est_tdp(name, ps, True),
                _S["lbl_year"]: str(self._est_year(arch, name, True)),
                ("Güç Skoru" if self.lang=="TR" else "Power Score"): str(ps),
            }
        else:
            _S = STRINGS[self.lang]
            specs = {
                _S["lbl_vram"]: f"{hw.get('vram','?')} GB",
                _S["lbl_core_mhz"]: f"{hw.get('core_clock',0)} MHz",
                _S["lbl_mem_mhz"]: f"{hw.get('memory_clock',0) or '?'} MHz",
                _S["lbl_arch"]: arch,
                _S["lbl_tdp"]: self._est_tdp(name, ps, False),
                _S["lbl_year"]: str(self._est_year(arch, name, False)),
                ("Güç Skoru" if self.lang=="TR" else "Power Score"): str(ps),
            }
        for k, v in specs.items():
            row = QHBoxLayout(); kl = QLabel(f"{k}:"); kl.setFixedWidth(180)
            kl.setStyleSheet("color:#45A29E;font-size:13px;font-weight:bold;")
            vl = QLabel(str(v)); vl.setStyleSheet("color:white;font-size:13px;"); vl.setWordWrap(True)
            row.addWidget(kl); row.addWidget(vl, 1); l2.addLayout(row)
        self.hw_result_layout.addWidget(c2)

        # 3. Market & price
        c3, l3 = self._hw_card(STRINGS[self.lang].get("card_title_market","💵  PAZAR KONUMU & FİYAT") if self.lang=="TR" else "💵  MARKET POSITION & PRICE")
        seg, usd = self._market_info(ps, is_cpu); try_price = int(usd * 38.5)
        mrows = {"Segment": seg, "Tahmini Fiyat": f"~${usd} USD  /  ~{try_price:,} TRY", "Fiyat/Performans": self._fp_verdict(ps, usd)}
        for k, v in mrows.items():
            row = QHBoxLayout(); kl = QLabel(f"{k}:"); kl.setFixedWidth(180)
            kl.setStyleSheet("color:#45A29E;font-size:13px;font-weight:bold;")
            vl = QLabel(str(v)); vl.setStyleSheet("color:white;font-size:13px;"); vl.setWordWrap(True)
            row.addWidget(kl); row.addWidget(vl, 1); l3.addLayout(row)
        self.hw_result_layout.addWidget(c3)

        # 4. Gaming performance
        c4, l4 = self._hw_card(STRINGS[self.lang].get("card_title_fps","🎮  OYUN PERFORMANS TAHMİNİ") if self.lang=="TR" else "🎮  GAMING PERFORMANCE EST.")
        lines = self._gpu_perf_text(ps, hw.get("vram",8) or 8) if not is_cpu else self._cpu_perf_text(name, ps)
        for line in lines:
            lb = QLabel(line); lb.setStyleSheet("color:#C5C6C7;font-size:12px;"); lb.setWordWrap(True); l4.addWidget(lb)
        self.hw_result_layout.addWidget(c4)

        # 5. Kritik yorum + rakip
        c5, l5 = self._hw_card(STRINGS[self.lang].get("card_title_review","📝  KRİTİK YORUM & RAKİP") if self.lang=="TR" else "📝  REVIEW & RIVAL")
        pros, cons = self._pros_cons(name, ps, is_cpu, gaming_s, render_s)
        rival = self._find_rival(name, ps, is_cpu)
        for line in [f"✅ Artı:  {pros}", f"❌ Eksi:  {cons}", f"⚔️  Rakip: {rival}"]:
            lb = QLabel(line); lb.setWordWrap(True); lb.setStyleSheet("color:#C5C6C7;font-size:13px;"); l5.addWidget(lb)
        self.hw_result_layout.addWidget(c5)

        # 6. PSU / Bottleneck
        c6, l6 = self._hw_card(("🔌  PSU ÖNERİSİ" if self.lang=="TR" else "🔌  PSU RECOMMENDATION") if not is_cpu else ("⚠️  DARBOĞAZ EŞLEŞMESİ" if self.lang=="TR" else "⚠️  BOTTLENECK MATCH"))
        extras = self._psu_advice(name, ps) if not is_cpu else self._bottleneck_pairs(ps)
        for line in extras:
            lb = QLabel(line); lb.setWordWrap(True); lb.setStyleSheet("color:#C5C6C7;font-size:13px;"); l6.addWidget(lb)
        self.hw_result_layout.addWidget(c6)
        self.hw_result_layout.addStretch()

    def _est_tdp(self, name, ps, is_cpu):
        n = name.upper()
        is_apple = "APPLE" in n or any(f"M{i}" in n for i in range(1,6))
        if is_cpu:
            if is_apple:
                if "ULTRA" in n: return "~60-130 W"
                if "MAX" in n: return "~35-78 W"
                if "PRO" in n: return "~27-45 W"
                return "~15-20 W"
            if "HX" in n or "KS" in n: return "~125-253 W"
            if n.endswith("K") or n.endswith("KF"): return "~125-253 W"
            if "HS" in n or "H)" in n or n.endswith(" H") or " H " in n or "-H" in n: return "~35-54 W"
            if " U " in n or n.endswith(" U") or n.endswith("U)") or "ULTRA-LOW" in n: return "~15-28 W"
            if ps > 85: return "~105-170 W"
            return "~65-90 W"
        if ps > 120: return "~450-600 W"
        if ps > 100: return "~285-320 W"
        if ps > 80:  return "~200-250 W"
        if ps > 60:  return "~130-160 W"
        return "~75-115 W"

    def _est_year(self, arch, name, is_cpu):
        n = name.upper()
        if "APPLE" in n or any(f"M{i}" in n for i in range(1,6)):
            if "M5" in n: return 2025
            if "M4" in n: return 2024
            if "M3" in n: return 2023
            if "M2" in n: return 2022
            return 2020
        m = {"blackwell":2025,"ada lovelace":2022,"ampere":2020,"turing":2018,"pascal":2016,
             "rdna 4":2024,"rdna 3":2023,"rdna 3.5":2024,"rdna 2":2020,"rdna":2019,
             "zen 5":2024,"zen 4":2022,"zen 3+":2022,"zen 3":2020,"zen 2":2019,"zen+":2018,"zen":2017,
             "arrow lake":2024,"raptor lake refresh":2023,"raptor lake":2022,"alder lake":2021,
             "rocket lake":2021,"comet lake":2020,"coffee lake refresh":2018,"coffee lake":2017,
             "apple silicon":2020,"battlemage":2024,"alchemist":2022,"polaris":2016,"vega":2017}
        return m.get(arch.lower(), "?")

    def _market_info(self, ps, is_cpu):
        if is_cpu:
            if ps>=100: return "Flagship",650
            if ps>=85:  return "Üst Segment",320
            if ps>=70:  return "Orta-Üst",190
            if ps>=50:  return "Orta",110
            return "Bütçe",65
        if ps>=130: return "Ultra Flagship",2500
        if ps>=110: return "Flagship",1000
        if ps>=90:  return "Üst Segment",650
        if ps>=70:  return "Orta-Üst",380
        if ps>=55:  return "Orta",270
        if ps>=40:  return "Bütçe-Orta",180
        return "Bütçe",100

    def _fp_verdict(self, ps, usd):
        r = ps / max(usd, 1) * 100
        if r>28: return "⭐⭐⭐⭐⭐  Mükemmel fiyat/performans"
        if r>18: return "⭐⭐⭐⭐    Çok iyi"
        if r>10: return "⭐⭐⭐      Orta"
        if r>5:  return "⭐⭐        Zayıf — alternatif değerlendirin"
        return       "⭐          Aşırı pahalı segmentinde"

    def _gpu_perf_text(self, ps, vram):
        results = []
        for res, gw, cw, vmin in [("1080p",1.9,0.75,4),("1440p",2.2,0.55,8),("4K",2.5,0.35,12)]:
            raw = ps*gw + 75*cw
            fh = int(raw/1.3); fu = int(raw/1.7)
            note = ""
            if vram < vmin: fh=int(fh*0.55); fu=int(fu*0.45); note=" ⚠️ VRAM yetersiz"
            tag = "60+ FPS ✅" if fh>=60 else ("30-60 FPS ⚠️" if fh>=30 else "<30 FPS ❌")
            results.append(f"  {res:5s}  High: ~{fh} FPS   Ultra: ~{fu} FPS{note}  [{tag}]")
        return results

    def _cpu_perf_text(self, name, ps):
        n = name.upper()
        is_apple = "APPLE" in n or any(f"M{i}" in n for i in range(1,6))
        if is_apple:
            if ps>=100: return ["✅ Mükemmel: Video kurgu, render ve profesyonel iş yükü canavarı.", "⚠️ Oyun Puanı yüksek görünse de, macOS oyun kütüphanesi çok sınırlıdır.", "Dahili GPU ile çalışır, harici ekran kartı takılamaz."]
            if ps>=70: return ["✅ Yüksek verimlilik: Yazılım Geliştirme, Logic Pro ve video düzenleme için ideal.", "⚠️ Sınırlı AAA oyun desteği (çoğunlukla çevrilmiş veya Rosetta 2)."]
            return ["✅ Günlük kullanım, pil ömrü ve ofis işleri için kusursuz.", "❌ Modern büyük prodüksiyonlu oyunlar için uygun değildir."]

        if ps>=90: return ["✅ Darboğazsız: RTX 5090 dahil tüm GPU'larla mükemmel."]
        if ps>=75: return ["✅ RTX 4090'a kadar darboğaz yapmaz."]
        if ps>=60: return ["⚠️  RTX 4070 SUPER seviyesine kadar ideal. Üstü için upgrade önerilir."]
        if ps>=45: return ["⚠️  RTX 4060 Ti ve altı GPU'larla eşleşmeli."]
        return ["❌ Düşük CPU. Modern üst-orta GPU'larla darboğaz yapar."]

    def _pros_cons(self, name, ps, is_cpu, gs, rs):
        n = name.upper()
        if is_cpu:
            pros = "3D V-Cache ile efsanevi oyun performansı" if "X3D" in n else ("Güçlü çok çekirdekli performans" if rs>gs else "Mükemmel oyun hızı")
            cons = "Yüksek güç tüketimi ve ısı" if ps>95 else ("Entegre grafik yok" if n.endswith("F)") or n.endswith("F ") else "Orta düzey render iş yükü")
        else:
            if "RTX 50" in n:   pros = "DLSS 4 Multi Frame Gen — neslin en hızlısı"
            elif "RTX 40" in n: pros = "Ray tracing + DLSS 3 Frame Gen mükemmeli"
            elif "RX 7" in n:   pros = "Bol VRAM, yüksek 1440p/4K rasterizasyon"
            else:               pros = "İyi fiyat/performans dengesi"
            vram_val = 0
            for it in self._hw_all_items:
                if it["name"]==name: vram_val=it.get("vram",0) or 0; break
            cons = "Yüksek TDP ve fiyat" if ps>110 else ("Az VRAM (4K/AI için kısıtlayıcı)" if vram_val<8 else "Yakın rakip segment rekabeti yüksek")
        return pros, cons

    def _find_rival(self, name, ps, is_cpu):
        src = db_manager.get_all_cpus() if is_cpu else db_manager.get_all_gpus()
        n_up = name.upper()
        cross = []
        for r in src:
            if r["name"]==name: continue
            diff = abs(r["power_score"]-ps)
            if diff<=7:
                ru = r["name"].upper()
                orig_nv = "NVIDIA" in n_up or "RTX" in n_up or "GTX" in n_up
                riv_nv  = "NVIDIA" in ru  or "RTX" in ru  or "GTX" in ru
                orig_int = "INTEL" in n_up or "CORE" in n_up
                riv_int  = "INTEL" in ru  or "CORE" in ru
                if (not is_cpu and orig_nv != riv_nv) or (is_cpu and orig_int != riv_int):
                    cross.append((diff, r["name"]))
        if cross: cross.sort(); return cross[0][1]
        same = sorted([(abs(r["power_score"]-ps), r["name"]) for r in src if r["name"]!=name])
        return same[0][1] if same else "—"

    def _psu_advice(self, name, ps):
        watt = 450 if ps<40 else (500 if ps<60 else (550 if ps<80 else (650 if ps<100 else (750 if ps<110 else (850 if ps<130 else 1000)))))
        return [f"Bu GPU için minimum {watt} W PSU önerilir.", f"Tam sistem (CPU + diğer): {watt+100} W 80+ Gold veya üstü önerilir." + (" ⚡ Yüksek güçlü PSU seçin (EVGA, Seasonic)." if ps>100 else "")]

    def _on_ai_analyze_clicked(self, hw_name, is_cpu):
        """Navigate to AI Asistan page and auto-send a detailed analysis prompt."""
        hw_type = "İşlemci (CPU)" if is_cpu else "Ekran Kartı (GPU)"
        prompt = (
            f"Lütfen bu donanımı detaylıca analiz et: {hw_name} ({hw_type}). "
            f"Oyun performansı, render kapasitesi, darboğaz riski, piyasa değeri, "
            f"güçlü ve zayıf yönleri, rakip alternatifler ve bu donanıma en uygun PSU/eşleşme önerisini de ver."
        )
        # Switch to AI Asistan page first
        self.switch_page(6)
        # Inject the prompt and fire send
        self.chat_input.setText(prompt)
        self.on_ai_chat_send()

    
    def _on_ai_analyze_result(self, data):
        self.ai_analyze_btn.setText("🤖 Yeniden Analiz Et" if self.lang=="TR" else "🤖 Re-analyze")
        self.ai_analyze_btn.setEnabled(True)
        
        if "error" in data:
            err = QLabel(data["error"])
            err.setStyleSheet("color:#FF4655;font-weight:bold;margin-top:10px;")
            self.ai_result_layout.addWidget(err)
            return
            
        ai_card = QFrame(); ai_card.setProperty("class", "Card")
        ai_card.setStyleSheet("background-color:#1e2a38; border: 1px solid #F59E0B; border-radius: 6px;")
        al = QVBoxLayout(ai_card); al.setContentsMargins(15,15,15,15); al.setSpacing(10)
        
        header = QLabel("🔥 AI ANALİST YORUMU" if self.lang=="TR" else "🔥 AI ANALYST REVIEW")
        header.setStyleSheet("color:#F59E0B;font-size:13px;font-weight:900;")
        al.addWidget(header)
        
        def _add_ai_row(title, val, color="#C5C6C7"):
            if not val: return
            r = QHBoxLayout()
            t = QLabel(f"{title}:"); t.setFixedWidth(140)
            t.setStyleSheet("color:#45A29E;font-size:12px;font-weight:bold;")
            v = QLabel(str(val)); v.setStyleSheet(f"color:{color};font-size:12px;"); v.setWordWrap(True)
            r.addWidget(t); r.addWidget(v, 1)
            al.addLayout(r)
            
            # --- AFFILIATE / MONETIZATION INJECTION ---
            if title == "Gerçekçi Darboğaz":
                link_lay = QHBoxLayout()
                link_lay.setContentsMargins(140, 0, 0, 5)
                # Parse HW name roughly to figure out if we search for CPU or GPU upgrades
                search_term = "bilgisayar+bilesenleri"
                if "CPU" in str(val) or "İşlemci" in str(val):
                    search_term = "islemci"
                elif "GPU" in str(val) or "Ekran Kartı" in str(val) or "RTX" in str(val) or "RX" in str(val):
                    search_term = "ekran+karti"

                # Respect affiliate store preferences
                show_amz = getattr(self, 'chk_amazon', None) and self.chk_amazon.isChecked()
                show_tr  = getattr(self, 'chk_trendyol', None) and self.chk_trendyol.isChecked()
                show_hb  = getattr(self, 'chk_hepsiburada', None) and self.chk_hepsiburada.isChecked()

                if show_amz:
                    amz_html = f"<a href='https://www.amazon.com.tr/s?k={search_term}&tag=perfhub-21' style='color:#FF9900;text-decoration:none;'>🛒 <b>Amazon</b></a>"
                    amz_link = QLabel(amz_html); amz_link.setOpenExternalLinks(True)
                    link_lay.addWidget(amz_link)
                if show_tr:
                    if show_amz: link_lay.addWidget(QLabel(" | "))
                    tr_html = f"<a href='https://www.trendyol.com/sr?q={search_term}&pi=2' style='color:#F27A1A;text-decoration:none;'>🛒 <b>Trendyol</b></a>"
                    tr_link = QLabel(tr_html); tr_link.setOpenExternalLinks(True)
                    link_lay.addWidget(tr_link)
                if show_hb:
                    if show_amz or show_tr: link_lay.addWidget(QLabel(" | "))
                    hb_html = f"<a href='https://www.hepsiburada.com/ara?q={search_term}' style='color:#FF6000;text-decoration:none;'>🛒 <b>Hepsiburada</b></a>"
                    hb_link = QLabel(hb_html); hb_link.setOpenExternalLinks(True)
                    link_lay.addWidget(hb_link)

                link_lay.addStretch()
                al.addLayout(link_lay)
            # ------------------------------------------

        _add_ai_row("Gerçek Künye", data.get("gercek_kunye", ""), "#66FCF1")
        _add_ai_row("Oyun", f"{data.get('oyun_puani','')} — {data.get('oyun_aciklama','')}")
        _add_ai_row("Render / İş", f"{data.get('render_puani','')} — {data.get('render_aciklama','')}")
        _add_ai_row("Fiyat / Performans", f"{data.get('fiyat_perf_puani','')} — {data.get('fiyat_perf_aciklama','')}")
        _add_ai_row("Gerçekçi Darboğaz", data.get("darbogaz_siniri",""), "#FF4655")
        _add_ai_row("En Büyük Defo", data.get("en_buyuk_defo",""), "#FF4655")
        
        self.ai_result_layout.addWidget(ai_card)

    def _bottleneck_pairs(self, ps):
        # Detect laptop context from the list selection
        hw_item = self.hw_list.currentItem()
        is_laptop_b = False; is_apple_b = False
        if hw_item:
            hw = hw_item.data(Qt.ItemDataRole.UserRole)
            n_up = hw.get("name","").upper()
            is_apple_b  = "APPLE" in n_up or any(f"M{i}" in n_up for i in range(1,6))
            is_laptop_b = not is_apple_b and (
                "HX" in n_up or "HS" in n_up or "HK" in n_up or " U " in n_up
                or n_up.endswith(" H") or n_up.endswith("-H") or "MOBILE" in n_up)
        if is_apple_b:
            return ["🍎 Apple Silicon: Dahili GPU — harici GPU yuvası bulunmaz.",
                    "CPU ve GPU aynı çipte birleşik (Unified Memory). Ayrıca kart takılamaz."]
        if is_laptop_b:
            if ps >= 88:   t = "RTX 5080/5090 Laptop GPU veya RTX 4090 Laptop GPU — en üst segment"
            elif ps >= 78: t = "RTX 4070 Ti / RTX 4080 Laptop GPU — ideal eşleşme"
            elif ps >= 68: t = "RTX 4060 / RTX 4070 Laptop GPU seviyesi ideal"
            elif ps >= 55: t = "RTX 3060 / RTX 3070 Laptop GPU seviyesi"
            elif ps >= 40: t = "RTX 3050 / RTX 3050 Ti Laptop GPU"
            else:          t = "GTX 1650 / GTX 1660 Ti Laptop GPU ve altı"
            note = ("⚡ Yüksek TGP (100W+) laptop GPU'lar masaüstüne yakın performans verebilir." if ps >= 65
                    else "⚠️ Düşük TGP (<80W) sistemlerde GPU tam potansiyelini kullanamayabilir.")
            return [f"Bu laptop CPU için ideal GPU aralığı: {t}.", note]

        # Desktop
        if ps >= 95:   t = "RTX 5090 / RX 9070 XT dahil darboğaz yapmaz"
        elif ps >= 80: t = "RTX 5080 / RX 9070 XT'ye kadar verimli"
        elif ps >= 65: t = "RTX 4070 SUPER / RX 7800 XT seviyesi ideal"
        elif ps >= 50: t = "RTX 4060 Ti / RX 7700 XT eşleşmesi önerilir"
        elif ps >= 35: t = "RTX 3060 / RX 6600 XT — üstü CPU darboğazı"
        else:          t = "RTX 3050 ve altı GPU seviyesi"
        return [f"Önerilen GPU aralığı: {t}.",
                "1440p/4K'da darboğaz etkisi azalır; 1080p'de CPU daha kritik rol oynar."]

    def setup_ai(self):
        inner = QWidget(); inner.setObjectName("ScrollContent")
        layout = QVBoxLayout(inner); layout.setContentsMargins(40,40,40,40); layout.setSpacing(20)

        self._page_title_ai = QLabel(STRINGS[self.lang]["title_ai"])
        self._page_title_ai.setProperty("class", "Title")
        layout.addWidget(self._page_title_ai)

        # ── Welcome Banner ──
        key_frame = QFrame(); key_frame.setProperty("class", "Card")
        klay = QVBoxLayout(key_frame); klay.setContentsMargins(20,20,20,20); klay.setSpacing(8)
        
        welcome_title = QLabel("🤖  PerfHub AI'ya Hoş Geldiniz!")
        welcome_title.setStyleSheet("color:#66FCF1;font-size:15px;font-weight:900;")
        klay.addWidget(welcome_title)
        
        welcome_desc = QLabel(
            "Sisteminizdeki her donanım hakkında soru sorabilirsiniz. "
            "Analist sisteminizin TUF Benchmark sonucunu ve donanım bilgilerini otomatik olarak görücek, "
            "size kişisel ve gerçekçi bir analiz sunacak.\n\n"
            "Örneğin: \"Sistemim 4K oyunculuk yapar mı?\" veya \"i7 vs Ryzen 7 hangisi?\""
        )
        welcome_desc.setStyleSheet("color:#C5C6C7;font-size:12px;")
        welcome_desc.setWordWrap(True)
        klay.addWidget(welcome_desc)
        layout.addWidget(key_frame)

        # ── Chat Area ──
        chat_frame = QFrame(); chat_frame.setProperty("class", "Card")
        chat_lay = QVBoxLayout(chat_frame); chat_lay.setContentsMargins(20,20,20,20); chat_lay.setSpacing(15)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("background-color:#0d0d18;color:white;border:1px solid #1e2a38;padding:10px;font-size:14px;")
        self.chat_history.append("<b style='color:#66FCF1;'>💬 Analist:</b> Selam! Ben PerfHub AI'nın Kıdemli Donanım Analistiyim. PerfHub AI Benchmark skorunuzu ve donanım verilerinizi otomatik görüyorum. Darboğaz, FPS veya herhangi bir donanım hakkında hiç çekinmeden sorabilirsiniz!")
        chat_lay.addWidget(self.chat_history, 1) # expanding

        input_lay = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Örn: i3 ile RTX 4070 kullanırsam ne olur?")
        self.chat_input.setStyleSheet("background-color:#1e2a38;color:white;border:1px solid #45A29E;padding:12px;border-radius:4px;font-size:14px;")
        self.chat_input.returnPressed.connect(self.on_ai_chat_send)
        
        self.chat_send_btn = QPushButton("GÖNDER")
        self.chat_send_btn.setStyleSheet("background-color:#66FCF1;color:#0B0C10;font-weight:900;padding:12px 20px;border-radius:4px;")
        self.chat_send_btn.clicked.connect(self.on_ai_chat_send)
        
        input_lay.addWidget(self.chat_input, 1); input_lay.addWidget(self.chat_send_btn)
        chat_lay.addLayout(input_lay)
        layout.addWidget(chat_frame, 1)

        page_layout = QVBoxLayout(self.page_ai)
        page_layout.setContentsMargins(0,0,0,0)
        page_layout.addWidget(self._scrollable(inner))

    def on_ai_chat_send(self):
        text = self.chat_input.text().strip()
        if not text: return
        self.chat_input.clear()
        
        self.chat_history.append(f"<br><b style='color:#66FCF1;'>🧑 Sen:</b> {text}")
        QApplication.processEvents() # UI update
        self.chat_history.append("<i style='color:#45A29E;'>⏳ AI düşünüyor...</i>")
        QApplication.processEvents()
        
        # Build context — inject score WITH segment label so the AI never questions it
        ctx = ""
        if hasattr(self, 'system_data') and self.system_data:
            hd = self.system_data.get('hw', {})
            raw_score = self.system_data.get('score', 0)
            if raw_score >= 90:
                segment = "Tepe Model (Enthusiast)"
            elif raw_score >= 70:
                segment = "Üst Düzey (High-End)"
            elif raw_score >= 40:
                segment = "Orta-Üst Seviye"
            else:
                segment = "Giriş Seviyesi"
            ctx = (
                f"CPU: {hd.get('cpu','Bilinmiyor')}\n"
                f"GPU: {hd.get('gpu','Bilinmiyor')}\n"
                f"RAM: {hd.get('ram','Bilinmiyor')}GB\n"
                f"PerfHub AI Skor: {raw_score}/100 — {segment}"
            )

        # Run in background thread (prevents crash on click during wait)
        self.chat_send_btn.setEnabled(False)
        self._chat_worker = ChatWorkerThread(text, ctx, language=self.lang)
        self._chat_worker.finished.connect(self._on_chat_response)
        self._chat_worker.start()

    def _on_chat_response(self, resp):
        self.chat_send_btn.setEnabled(True)
        import re
        html_resp = resp.replace("\n", "<br>")
        html_resp = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html_resp)
        html_resp = re.sub(r'\*(.*?)\*', r'<i>\1</i>', html_resp)
        
        self.chat_history.append(f"<br><b style='color:#F59E0B;'>🤖 Asistan:</b> {html_resp}")
        sb = self.chat_history.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ---------------- LOGIC ----------------

    def check_apple_selection(self, index):
        # Index 2 is the Apple tab
        if index == 2:
            self.gpu_block_widget.setEnabled(False)
            self.gpu_lbl_title.setText("GPU DISABLED (APPLE UNIFIED MEMORY)")
            self.gpu_lbl_title.setStyleSheet("color: #7A7A7A; font-weight: bold; font-size: 14px;")
            self.gpu_tabs.setStyleSheet("QTabBar::tab { background: #1a1a24; color: #7A7A7A; padding: 8px 20px;} QTabBar::tab:selected { background: #2C3E50; }")
            # Apple uses MetalFX
            self.update_upscale_options("Apple", self.b_cmb_upscale)
        else:
            self.gpu_block_widget.setEnabled(True)
            self.gpu_lbl_title.setText("SELECT GPU BRAND:")
            self.gpu_lbl_title.setStyleSheet("color: #45A29E; font-weight: bold; font-size: 14px;")
            self.gpu_tabs.setStyleSheet("QTabBar::tab { background: #1F2833; color: white; padding: 8px 20px; font-weight:bold;} QTabBar::tab:selected { background: #45A29E; }")

    def update_upscale_options(self, gpu_name, cmb, fg_cmb=None):
        """Dynamically populate upscaling and frame-gen dropdowns based on GPU vendor."""
        cmb.blockSignals(True)
        cmb.clear()
        gn = gpu_name.upper()
        if "NVIDIA" in gn or "RTX" in gn or "GTX" in gn:
            cmb.addItems(["Native", "DLAA / Native AA", "Quality (DLSS)", "Balanced (DLSS)", "Performance (DLSS)", "Ultra Performance (DLSS)"])
        elif "AMD" in gn or "RADEON" in gn or "RX" in gn:
            cmb.addItems(["Native", "Native AA (FSR)", "Quality (FSR)", "Balanced (FSR)", "Performance (FSR)", "Ultra Performance (FSR)"])
        elif "APPLE" in gn or "UNIFIED" in gn:
            cmb.addItems(["Native", "Native AA (MetalFX)", "Quality (MetalFX)", "Balanced (MetalFX)", "Performance (MetalFX)", "Ultra Performance (MetalFX)"])
        elif "INTEL" in gn or "ARC" in gn or "IRIS" in gn:
            cmb.addItems(["Native", "Native AA (XeSS)", "Quality (XeSS)", "Balanced (XeSS)", "Performance (XeSS)", "Ultra Performance (XeSS)"])
        else:
            cmb.addItems(["Native", "Native AA", "Quality", "Balanced", "Performance", "Ultra Performance"])
        cmb.blockSignals(False)

        # Update Frame Gen dropdown if provided
        if fg_cmb is not None:
            fg_cmb.blockSignals(True)
            fg_cmb.clear()
            fg_cmb.addItems(scoring_engine.get_fg_options(gpu_name))
            fg_cmb.blockSignals(False)

    def run_scanner(self):
        self.scanner = ScannerThread()
        self.scanner.finished_scan.connect(self.on_scan_complete)
        self.scanner.start()

    def on_scan_complete(self, data):
        self.system_data = data
        
        # Dashboard Update — Show rich specs
        cpu_d = data['cpu_data']
        gpu_d = data['gpu_data']
        
        cpu_spec = f"{data['hw']['cpu']}"
        if cpu_d.get('cores'):
            cpu_spec += f"\n{cpu_d['cores']} Çekirdek  |  Max {cpu_d.get('boost_clock', '?')} GHz"
        cpu_spec += f"\n{cpu_d.get('architecture', '')}  |  Puan: {cpu_d['power_score']}"
        self.lbl_cpu.setText(cpu_spec)
        
        gpu_spec = f"{data['hw']['gpu']}"
        vram_gb = gpu_d.get('vram', 0)
        cc = gpu_d.get('core_clock', 0)
        if vram_gb and vram_gb > 0:
            gpu_spec += f"\n{vram_gb} GB VRAM  |  {cc} MHz"
        gpu_spec += f"\n{gpu_d.get('architecture', '')}  |  Puan: {gpu_d['power_score']}"
        self.lbl_gpu.setText(gpu_spec)
        self.lbl_ram.setText(f"{data['hw']['ram']} GB")

        # RAM Details
        ram_label = data['hw'].get('ram_label', '')
        ram_details = data['hw'].get('ram_details', [])
        if ram_details:
            sticks = len(ram_details)
            mfr = ram_details[0].get('manufacturer', '')
            part = ram_details[0].get('part_number', '')
            ram_det_txt = f"{ram_label}\n{sticks} Modül  |  {mfr}"
            if part: ram_det_txt += f"\n{part[:20]}"
        else:
            ram_det_txt = ram_label or f"{data['hw']['ram']} GB RAM"
        self.lbl_ram_detail.setText(ram_det_txt)

        # Storage
        storage = data['hw'].get('storage', [])
        if storage:
            lines = []
            for d in storage:
                bus = d.get('bus_type', '')
                tag = d.get('media_type', 'Disk')
                sz = d.get('size_gb', 0)
                name_short = d.get('name', '')[:30]
                lines.append(f"{tag} ({bus}) {sz}GB\n{name_short}")
            self.lbl_storage.setText("\n".join(lines))
        else:
            self.lbl_storage.setText("Tespit edilemedi")
        
        # Animating the Score
        self.target_score = int(data['score'])
        if self.target_score <= 0:
            self.lbl_score_num.setText("N/A")
            self.score_bar.setValue(0)
            self.lbl_score_num.setStyleSheet("color:#FF4655;font-weight:900;")
            self.sidebar_score_lbl.setText("— / 100")
            self.sidebar_score_bar.setValue(0)
            if hasattr(self, 'score_timer'): getattr(self, 'score_timer').stop()
        else:
            self.lbl_score_num.setStyleSheet("")  # reset
            self.current_score = 0
            self.score_timer = QTimer()
            self.score_timer.timeout.connect(self.animate_score)
            self.score_timer.start(20) # 20ms intervals
            # Update sidebar score widget immediately
            self.sidebar_score_lbl.setText(f"{self.target_score} / 100")
            self.sidebar_score_bar.setValue(self.target_score)

        # Bottleneck Update
        bn = data['bn']
        self.lbl_bn_title.setText(bn['status'])
        # If green/balanced, make border green
        if "PERFECT" in bn['status']:
            self.lbl_bn_title.setStyleSheet("color: #10B981; font-size: 18px; font-weight: bold;")
            self.bn_frame.setStyleSheet("border: 2px solid rgba(16, 185, 129, 0.4); background-color: #1a1a24; border-radius: 12px;")
        else:
             self.bn_frame.setStyleSheet("border: 2px solid rgba(245, 158, 11, 0.4); background-color: #1a1a24; border-radius: 12px;")
        
        self.lbl_bn_desc.setText(bn['msg'])

        # Only update upscaling & frame gen dropdowns when detected GPU changes
        detected_gpu_name = data['gpu_data'].get('name', '')
        if detected_gpu_name != self._last_cur_gpu_name:
            self._last_cur_gpu_name = detected_gpu_name
            self.update_upscale_options(detected_gpu_name, self.cmb_upscale, self.cmb_framegen)
        self.populate_games()
        # Build the detailed analysis section on the dashboard
        self.populate_dash_detail(data)

    def animate_score(self):
        self.current_score += 1
        self.score_bar.setValue(self.current_score)
        self.lbl_score_num.setText(str(self.current_score))
        if self.current_score >= self.target_score:
            self.score_timer.stop()

    def animate_builder_score(self):
        """Animates the builder score bar like the system dashboard."""
        self._b_current_score += 1
        self.b_score_bar.setValue(self._b_current_score)
        self.lbl_b_score_num.setText(str(self._b_current_score))
        if self._b_current_score >= self._b_target_score:
            self._b_score_timer.stop()

    def populate_dash_detail(self, data):
        """Build detailed hardware cards in the dashboard below the score bar."""
        # Clear previous content
        while self.dash_detail_layout.count():
            child = self.dash_detail_layout.takeAt(0)
            w = child.widget()
            if w:
                try: w.setParent(None); w.deleteLater()
                except RuntimeError: pass

        cpu_d  = data.get('cpu_data', {})
        gpu_d  = data.get('gpu_data', {})
        hw     = data.get('hw', {})
        ram_details = hw.get('ram_details', [])
        storage     = hw.get('storage', [])

        # ── 2-column grid for CPU + GPU ──────────────────────────────────
        top_row = QHBoxLayout(); top_row.setSpacing(14)

        # ── CPU CARD ────────────────────────────────────────────────────
        cpu_card, cpu_lay = self._hw_card("🖥️  İŞLEMCİ  (CPU)")
        cpu_ps    = cpu_d.get('power_score', 50.0)
        cpu_cores = cpu_d.get('cores', 0)
        cpu_name  = hw.get('cpu', '')
        cpu_arch  = cpu_d.get('architecture', 'N/A')
        cpu_boost = cpu_d.get('boost_clock', '?')
        cpu_base  = cpu_d.get('base_clock', '?')

        cpu_n_up  = cpu_name.upper()
        is_apple  = "APPLE" in cpu_n_up or "M1" in cpu_n_up or "M2" in cpu_n_up or "M3" in cpu_n_up or "M4" in cpu_n_up
        is_laptop = not is_apple and ("HX" in cpu_n_up or "HS" in cpu_n_up or "HK" in cpu_n_up
                    or cpu_n_up.endswith(" H") or " H " in cpu_n_up or "-H " in cpu_n_up
                    or cpu_n_up.endswith("-H") or "HX)" in cpu_n_up
                    or " U " in cpu_n_up or cpu_n_up.endswith(" U") or "U)" in cpu_n_up
                    or "MOBILE" in cpu_n_up)
        is_u_series = " U" in cpu_n_up or cpu_n_up.endswith("U)") or "ULTRA-LOW" in cpu_n_up

        # ── Corrected scoring ──────────────────────────────────────────
        # Gaming: Apple chips have decent but limited gaming vs desktop
        if is_apple:
            gaming_s = round(min(6.0, cpu_ps / 22.0 + 1.0), 1)  # macOS game library limited
        elif "X3D" in cpu_n_up:
            gaming_s = round(min(10, cpu_ps / 10.0 + 2.0), 1)
        elif is_u_series:
            gaming_s = round(min(6.5, cpu_ps / 14.0), 1)
        elif is_laptop:
            gaming_s = round(min(8.5, cpu_ps / 11.0 + 0.5), 1)
        else:
            gaming_s = round(min(10, cpu_ps / 10.5), 1)

        # Render: Apple unified memory excels; laptop throttles under sustained load
        if is_apple:
            render_s = round(min(10, cpu_ps / 9.0), 1)
        else:
            render_s = round(min(10, (cpu_cores / 3.2) * 0.6 + cpu_ps / 28.0), 1)
            if is_laptop and not is_u_series: render_s = round(render_s * 0.82, 1)
            elif is_u_series: render_s = round(render_s * 0.65, 1)

        # Office: ANY CPU above budget handles office tasks perfectly — never penalize high-end
        if cpu_ps >= 50:   daily_s = round(min(10, 8.5 + (cpu_ps - 50) / 80.0), 1)
        elif cpu_ps >= 30: daily_s = round(7.0 + (cpu_ps - 30) / 20.0, 1)
        else:              daily_s = round(max(4.0, cpu_ps / 7.5), 1)
        daily_s = round(min(10, daily_s), 1)


        cpu_lay.addLayout(self._score_bar("Gaming",      gaming_s, "#9D00FF"))
        cpu_lay.addLayout(self._score_bar("Render/3D",   render_s, "#3B82F6"))
        cpu_lay.addLayout(self._score_bar("Günlük Ofis", daily_s,  "#10B981"))

        for k, v in {
            "Çekirdek / Thread": f"{cpu_d.get('cores','?')} / {cpu_d.get('threads','?')}",
            "Taban / Boost":     f"{cpu_base} / {cpu_boost} GHz",
            "Mimari":            cpu_arch,
            "TDP (tahmini)":     self._est_tdp(cpu_name, cpu_ps, True),
            "Çıkış Yılı":        str(self._est_year(cpu_arch, cpu_name, True)),
            "Güç Skoru":         str(cpu_ps),
        }.items():
            r = QHBoxLayout(); kl = QLabel(f"{k}:"); kl.setFixedWidth(155)
            kl.setStyleSheet("color:#45A29E;font-size:12px;font-weight:bold;")
            vl = QLabel(str(v)); vl.setStyleSheet("color:white;font-size:12px;"); vl.setWordWrap(True)
            r.addWidget(kl); r.addWidget(vl, 1); cpu_lay.addLayout(r)

        # ── GPU pairing tip — laptop-aware, Apple-aware ───────────────
        if is_apple:
            pair_lbl  = "🍎 Apple Silicon: Dahili GPU (Unified Memory) — harici GPU yok"
            pair_color = "#45A29E"
        elif is_u_series:
            # Ultra-low power — paired with integrated or very light GPUs
            pair_lbl  = "⚠️  Ultra-low power CPU — harici GPU için uygun değil; entegre grafik kullanılır"
            pair_color = "#FF4655"
        elif is_laptop:
            # Laptop CPUs are thermally limited; realistic perf ceiling
            if "HX" in cpu_n_up and cpu_ps >= 80:
                pair_lbl = "✅ Laptop HX sınıfı — RTX 4090/5080 Laptop'a kadar verimliliği korur"
            elif ("HS" in cpu_n_up or " H" in cpu_n_up or "-H" in cpu_n_up) and cpu_ps >= 70:
                pair_lbl = "⚠️  Laptop H/HS — RTX 4070 Laptop / RTX 4060 Ti Laptop seviyesi ideal; üstü darboğaz yapabilir"
            elif cpu_ps >= 55:
                pair_lbl = "⚠️  Orta laptop CPU — RTX 4060 Laptop / RTX 3060 Laptop üstü darboğaz yapar"
            else:
                pair_lbl = "🔴 Düşük güçlü laptop CPU — RTX 3050 Laptop seviyesi; üstü önerilmez"
            pair_color = "#F59E0B"
        else:
            # Desktop — realistic ceiling
            if cpu_ps >= 95:
                pair_lbl = "✅ Üst sınıf masaüstü CPU — RTX 5090 / RX 9070 XTX'e kadar darboğaz yapmaz"
            elif cpu_ps >= 80:
                pair_lbl = "✅ Güçlü masaüstü CPU — RTX 4080 SUPER / RX 7900 XTX'e kadar verimli"
            elif cpu_ps >= 65:
                pair_lbl = "⚠️  Orta-üst masaüstü CPU — RTX 4070 SUPER / RTX 5070 seviyesi ideal"
            elif cpu_ps >= 50:
                pair_lbl = "⚠️  Orta masaüstü CPU — RTX 4060 Ti / RTX 5060 üstü darboğaz riski"
            else:
                pair_lbl = "🔴 Bütçe CPU — RTX 3060 ve altı GPU ile eşleştirin"
            pair_color = "#F59E0B" if cpu_ps < 80 else "#10B981"

        tip = QLabel(pair_lbl); tip.setWordWrap(True)
        tip.setStyleSheet(f"color:{pair_color};font-size:12px;font-style:italic;")
        cpu_lay.addWidget(tip)

        # Dashboard CPU affiliate links — respect store checkbox preferences
        if not is_apple:
            import urllib.parse
            from core import db_manager
            cpu_upgrades = db_manager.get_recommended_upgrades(cpu_ps + 5, is_cpu=True, current_hardware_name=hw.get('cpu', ''), count=1)
            rec = cpu_upgrades[0] if cpu_upgrades else ""
            search_kw = urllib.parse.quote(rec) if rec else "islemci"
            btn_text = rec if rec else "İşlemcilere"

            show_amz = getattr(self, 'chk_amazon', None) and self.chk_amazon.isChecked()
            show_tr  = getattr(self, 'chk_trendyol', None) and self.chk_trendyol.isChecked()
            show_hb  = getattr(self, 'chk_hepsiburada', None) and self.chk_hepsiburada.isChecked()

            parts = []
            if show_hb:
                parts.append(f"<a href='https://www.hepsiburada.com/ara?q={search_kw}' style='background-color:#FF6000; color:white; padding:4px 10px; text-decoration:none; font-weight:bold; border-radius:4px; font-size:11px; margin-right:5px;'>HB'da {btn_text}</a>")
            if show_tr:
                parts.append(f"<a href='https://www.trendyol.com/sr?q={search_kw}&pi=2' style='background-color:#F27A1A; color:white; padding:4px 10px; text-decoration:none; font-weight:bold; border-radius:4px; font-size:11px; margin-right:5px;'>Trendyol'da {btn_text}</a>")
            if show_amz:
                parts.append(f"<a href='https://www.amazon.com.tr/s?k={search_kw}&tag=perfhub-21' style='background-color:#232F3E; color:#FF9900; padding:4px 10px; text-decoration:none; font-weight:bold; border-radius:4px; font-size:11px;'>Amazon'da {btn_text}</a>")

            if parts:
                html = f"<div style='margin-top:5px; margin-bottom:5px;'>{''.join(parts)}</div>"
                d_links = QHBoxLayout()
                lbl_links = QLabel(html); lbl_links.setOpenExternalLinks(True)
                d_links.addWidget(lbl_links); d_links.addStretch()
                cpu_lay.addLayout(d_links)

        top_row.addWidget(cpu_card)

        # ── GPU CARD ────────────────────────────────────────────────────
        gpu_card, gpu_lay = self._hw_card("🎮  EKRAN KARTI  (GPU)")
        gpu_ps   = gpu_d.get('power_score', 50.0)
        gpu_vram = gpu_d.get('vram', 8) or 8
        gpu_name = hw.get('gpu', '')
        gpu_arch = gpu_d.get('architecture', 'N/A')
        gpu_clk  = gpu_d.get('core_clock', 0)
        gpu_mclk = gpu_d.get('memory_clock', 0)

        g_gaming = round(min(10, gpu_ps / 13.0 + gpu_vram / 14.0), 1)
        g_render = round(min(10, gpu_vram / 2.8 + gpu_ps / 25.0), 1)
        g_daily  = round(max(2, 9 - gpu_ps / 15.0), 1)
        gpu_lay.addLayout(self._score_bar("Gaming",      g_gaming, "#9D00FF"))
        gpu_lay.addLayout(self._score_bar("Render/AI",   g_render, "#3B82F6"))
        gpu_lay.addLayout(self._score_bar("Günlük Ofis", g_daily,  "#10B981"))

        for k, v in {
            "VRAM":            f"{gpu_vram} GB",
            "Çekirdek Saati":  f"{gpu_clk} MHz",
            "Bellek Saati":    f"{gpu_mclk or '?'} MHz",
            "Mimari":          gpu_arch,
            "TDP (tahmini)":   self._est_tdp(gpu_name, gpu_ps, False),
            "Çıkış Yılı":      str(self._est_year(gpu_arch, gpu_name, False)),
            "Güç Skoru":       str(gpu_ps),
        }.items():
            r = QHBoxLayout(); kl = QLabel(f"{k}:"); kl.setFixedWidth(155)
            kl.setStyleSheet("color:#45A29E;font-size:12px;font-weight:bold;")
            vl = QLabel(str(v)); vl.setStyleSheet("color:white;font-size:12px;"); vl.setWordWrap(True)
            r.addWidget(kl); r.addWidget(vl, 1); gpu_lay.addLayout(r)

        # PSU recommendation
        psu_w = 450 if gpu_ps<40 else (550 if gpu_ps<60 else (650 if gpu_ps<80 else (750 if gpu_ps<100 else (850 if gpu_ps<120 else 1000))))
        psu_lbl = QLabel(f"🔌 Önerilen PSU: minimum {psu_w} W 80+ Gold")
        psu_lbl.setStyleSheet("color:#F59E0B;font-size:12px;font-style:italic;")
        gpu_lay.addWidget(psu_lbl)
        
        # GPU affiliate links
        if not is_apple:
            import urllib.parse
            from core import db_manager
            # GPU target upgrade depends on cpu_ps to avoid bottleneck
            gpu_upgrades = db_manager.get_recommended_upgrades(cpu_ps, is_cpu=False, current_hardware_name=hw.get('gpu', ''), count=1)
            rec = gpu_upgrades[0] if gpu_upgrades else ""
            search_kw = urllib.parse.quote(rec) if rec else "ekran+karti"
            btn_text = rec if rec else "Ekran Kartlarına"
            
            g_links = QHBoxLayout()
            html = f"""
            <div style='margin-top:5px; margin-bottom:5px;'>
               <a href='https://www.hepsiburada.com/ara?q={search_kw}' style='background-color:#FF6000; color:white; padding:4px 10px; text-decoration:none; font-weight:bold; border-radius:4px; font-size:11px; margin-right:5px;'>HB'da {btn_text}</a>
               <a href='https://www.trendyol.com/sr?q={search_kw}&pi=2' style='background-color:#F27A1A; color:white; padding:4px 10px; text-decoration:none; font-weight:bold; border-radius:4px; font-size:11px; margin-right:5px;'>Trendyol'da {btn_text}</a>
               <a href='https://www.amazon.com.tr/s?k={search_kw}&tag=perfhub-21' style='background-color:#232F3E; color:#FF9900; padding:4px 10px; text-decoration:none; font-weight:bold; border-radius:4px; font-size:11px;'>Amazon'da {btn_text}</a>
            </div>
            """
            lbl_links = QLabel(html); lbl_links.setOpenExternalLinks(True)
            g_links.addWidget(lbl_links); g_links.addStretch()
            gpu_lay.addLayout(g_links)

        top_row.addWidget(gpu_card)
        self.dash_detail_layout.addLayout(top_row)

        # ── RAM CARD ─────────────────────────────────────────────────────
        ram_card, ram_lay = self._hw_card("💾  RAM BELLEK")
        ram_row = QHBoxLayout(); ram_row.setSpacing(14)
        total_gb = hw.get('ram', 0)

        if ram_details:
            s0 = ram_details[0]
            mem_type    = s0.get('mem_type', 'RAM')
            configured  = s0.get('configured_mhz', 0) or s0.get('speed_mhz', 0)
            mfr         = s0.get('manufacturer', '—')
            part        = s0.get('part_number', '—')[:22]
            stick_count = len(ram_details)
            total_cap   = sum(s.get('capacity_gb', 0) for s in ram_details)

            # Performance score for RAM
            is_ddr5 = "DDR5" in mem_type.upper() or "LPDDR5" in mem_type.upper()
            ram_perf = round(min(10, (configured / 600.0) * 0.6 + (total_cap / 4.0) * 0.4), 1)
            ram_lay.addLayout(self._score_bar("Oyun Performansı", ram_perf, "#9D00FF"))
            ram_lay.addLayout(self._score_bar("Çok Görev",        min(10, total_cap / 3.2), "#3B82F6"))

            for k, v in {
                "Kapasite":      f"{total_cap} GB ({stick_count} modül)",
                "Bellek Tipi":   mem_type,
                "Çalışma Hızı":  f"{configured} MHz",
                "OC Potansiyel": f"{s0.get('speed_mhz', configured)} MHz (rated)",
                "Üretici":       mfr,
                "Part No":       part,
                "DDR5 Avantajı": "✅ Evet — yüksek bant genişliği" if is_ddr5 else "❌ Hayır — DDR4",
            }.items():
                r = QHBoxLayout(); kl = QLabel(f"{k}:"); kl.setFixedWidth(155)
                kl.setStyleSheet("color:#45A29E;font-size:12px;font-weight:bold;")
                vl = QLabel(str(v)); vl.setStyleSheet("color:white;font-size:12px;"); vl.setWordWrap(True)
                r.addWidget(kl); r.addWidget(vl, 1); ram_lay.addLayout(r)

            if total_gb < 16:
                ram_warn = QLabel("⚠️  16 GB altı RAM modern AAA oyunlarda yetersiz kalabilir!")
                ram_warn.setStyleSheet("color:#FF4655;font-size:12px;font-weight:bold;")
                ram_lay.addWidget(ram_warn)
        else:
            ram_lay.addWidget(QLabel(f"Toplam: {total_gb} GB (detay alınamadı)"))

        self.dash_detail_layout.addWidget(ram_card)

        # ── STORAGE CARD ─────────────────────────────────────────────────
        if storage:
            ssd_card, ssd_lay = self._hw_card("💿  DEPOLAMA BİRİMLERİ")
            for d in storage:
                drv_name  = d.get('name', 'Bilinmiyor')
                drv_size  = d.get('size_gb', 0)
                drv_type  = d.get('media_type', '?')
                drv_bus   = d.get('bus_type', '?')

                is_nvme = "NVME" in drv_bus.upper() or drv_bus in ("NVMe", "17", "9")
                is_ssd  = drv_type == "SSD" or is_nvme

                speed_tag = "NVMe (3000-7000 MB/s)" if is_nvme else ("SATA SSD (~550 MB/s)" if is_ssd else "HDD (~150 MB/s) ⚠️")
                icon      = "⚡" if is_nvme else ("✅" if is_ssd else "🔴")
                perf_s    = round(9.5 if is_nvme else (6.5 if is_ssd else 2.0), 1)

                ssd_lay.addLayout(self._score_bar(f"{icon} {drv_type}", perf_s, "#66FCF1" if is_nvme else ("#10B981" if is_ssd else "#FF4655")))

                for k, v in {
                    "Model":    drv_name[:35],
                    "Kapasite": f"{drv_size} GB",
                    "Arayüz":   drv_bus,
                    "Hız Sınıfı": speed_tag,
                }.items():
                    r = QHBoxLayout(); kl = QLabel(f"{k}:"); kl.setFixedWidth(155)
                    kl.setStyleSheet("color:#45A29E;font-size:12px;font-weight:bold;")
                    vl = QLabel(str(v)); vl.setStyleSheet("color:white;font-size:12px;"); vl.setWordWrap(True)
                    r.addWidget(kl); r.addWidget(vl, 1); ssd_lay.addLayout(r)

                if not is_ssd:
                    warn = QLabel("🔴 HDD tespit edildi — SSD'ye geçiş sistem hızını ciddi oranda artırır!")
                    warn.setStyleSheet("color:#FF4655;font-size:12px;font-weight:bold;"); warn.setWordWrap(True)
                    ssd_lay.addWidget(warn)

            self.dash_detail_layout.addWidget(ssd_card)


    def populate_games(self):
        if not self.system_data: return
        
        res = self.cmb_res.currentText()
        game_data = self.cmb_game.currentData()
        if not game_data: return
        
        # Check RT/PT support
        supports_rt = game_data.get("supports_rt", 0)
        supports_pt = game_data.get("supports_pt", 0)
        
        # Check if GPU supports RT/PT (NVIDIA RTX 20+ or AMD RX 6000+)
        gpu_name = self.system_data['gpu_data'].get('name', '').upper()
        gpu_supports_rt = (
            'RTX' in gpu_name or  # NVIDIA RTX series
            'RX 6' in gpu_name or 'RX 7' in gpu_name or  # AMD RDNA 2/3
            'ARC' in gpu_name  # Intel ARC
        )
        
        # Enable RT/PT only if BOTH game AND GPU support it
        self.chk_rt.setEnabled(supports_rt == 1 and gpu_supports_rt)
        self.chk_pt.setEnabled(supports_pt == 1 and gpu_supports_rt)
        
        if supports_rt == 0 or not gpu_supports_rt:
            self.chk_rt.setChecked(False)
        if supports_pt == 0 or not gpu_supports_rt:
            self.chk_pt.setChecked(False)
        
        # RT support label
        if not gpu_supports_rt:
            self.lbl_rt_support.setText("❌ GPU'nuz RT/PT desteklemiyor")
        elif supports_pt == 1:
            self.lbl_rt_support.setText("✅ Bu oyun RT + PT destekliyor")
        elif supports_rt == 1:
            self.lbl_rt_support.setText("✅ Bu oyun RT destekliyor")
        else:
            self.lbl_rt_support.setText("❌ Bu oyun RT/PT desteklemiyor")

        # ── Upscaling support label ─────────────────────────────────────────
        g_dlss = game_data.get("supports_dlss", 1)
        g_fsr  = game_data.get("supports_fsr",  1)
        g_xess = game_data.get("supports_xess", 0)
        tech_parts = []
        if g_dlss: tech_parts.append("DLSS")
        if g_fsr:  tech_parts.append("FSR")
        if g_xess: tech_parts.append("XeSS")
        tech_str = " · ".join(tech_parts) if tech_parts else "Yok (Native TAA)"
        upscaling_sel = self.cmb_upscale.currentText().lower()
        warn = ""
        if "dlss" in upscaling_sel and not g_dlss:
            warn = "  ⚠️ Bu oyun DLSS desteklemiyor — Native olarak hesaplanacak"
        elif "fsr" in upscaling_sel and not g_fsr:
            warn = "  ⚠️ Bu oyun FSR desteklemiyor — Native olarak hesaplanacak"
        elif "xess" in upscaling_sel and not g_xess:
            warn = "  ⚠️ Bu oyun XeSS desteklemiyor — Native olarak hesaplanacak"
        lbl_txt = f"🎮 Upscaling Desteği: {tech_str}{warn}"
        if hasattr(self, 'lbl_upscale_support'):
            color = "#FF9900" if warn else "#45A29E"
            self.lbl_upscale_support.setStyleSheet(f"color:{color}; font-size:12px; font-style:italic;")
            self.lbl_upscale_support.setText(lbl_txt)

        cpu_data = self.system_data['cpu_data']
        gpu_data = self.system_data['gpu_data']
        ram_gb = self.system_data['hw']['ram']
        upscaling = self.cmb_upscale.currentText()
        frame_gen_mode = self.cmb_framegen.currentText()

        
        # RT/PT performance penalty
        rt_enabled = self.chk_rt.isChecked() and supports_rt == 1 and gpu_supports_rt
        pt_enabled = self.chk_pt.isChecked() and supports_pt == 1 and gpu_supports_rt
        
        for preset, bar in self.fps_bars.items():
            fps = scoring_engine.estimate_fps(cpu_data, gpu_data, game_data, res, preset, upscaling, frame_gen_mode, ram_gb)
            
            # Apply RT/PT penalty (calibrated against Digital Foundry / HardwareUnboxed 2024)
            # RT in demanding games (Cyberpunk, AW2) typically cuts FPS by 40-50%.
            # Lighter RT implementations (GTA V RT reflections) cut by ~15-25%.
            # We use the game's supports_rt level as a proxy for RT intensity.
            if pt_enabled:
                # Path Tracing (Cyberpunk full PT): ~55% FPS loss
                fps = int(fps * 0.45)
            elif rt_enabled:
                # Ray Tracing: ~40% FPS loss for heavy RT games (Cyberpunk, AW2, MFR)
                fps = int(fps * 0.60)

            
            bar.setRange(0, max(fps * 2, 360))
            bar.setValue(fps)
            
            if fps >= 120: color = "#9D00FF" # Purple
            elif fps >= 90: color = "#3B82F6" # Blue
            elif fps >= 60: color = "#10B981" # Green
            elif fps >= 30: color = "#F59E0B" # Orange
            else: color = "#FF4655" # Red
                
            bar.setStyleSheet(f"QProgressBar {{ border: 1px solid #45A29E; background-color: #1a1a24; color: white; border-radius: 5px; text-align: center; font-weight: 900; font-size: 16px; }} QProgressBar::chunk {{ background-color: {color}; border-radius: 4px; }}")
            
    def calculate_custom_build(self):
        # Retrieve data from active tabs
        active_cpu_list = self.cpu_tabs.currentWidget()
        cpu_data = active_cpu_list.get_selected_data() if active_cpu_list else None
        
        # If Apple is selected, mock the GPU score
        is_apple = self.cpu_tabs.currentIndex() == 2
        
        if is_apple and cpu_data:
            # Apple Silicon essentially uses its CPU power score / 1.1 as its GPU equivalent for unified estimation
            gpu_data = {"power_score": cpu_data["power_score"], "name": "Apple Unified GPU"}
        else:
            active_gpu_list = self.gpu_tabs.currentWidget()
            gpu_data = active_gpu_list.get_selected_data() if active_gpu_list else None
        
        if not cpu_data or not gpu_data:
            self.lbl_b_bn.setText("LÜTFEN LİSTEDEN DONANIM SEÇİN!")
            self.lbl_b_bn.setStyleSheet("color: #FF4655; font-size: 16px; font-weight: bold;")
            self.switch_page(4)
            return

        # ── Laptop / Desktop mixing prevention ──
        cpu_name_up = cpu_data.get('name', '').upper()
        gpu_name_up = gpu_data.get('name', '').upper()
        
        cpu_is_laptop = any(s in cpu_name_up for s in ['HX', 'HS', 'HK'])
        cpu_is_laptop = cpu_is_laptop or cpu_name_up.endswith(' H') or cpu_name_up.endswith('-H')
        cpu_is_laptop = cpu_is_laptop or ' H ' in cpu_name_up or ' H)' in cpu_name_up
        cpu_is_laptop = cpu_is_laptop or any(s in cpu_name_up for s in [' U ', 'MOBILE'])
        cpu_is_laptop = cpu_is_laptop or cpu_name_up.endswith(' U') or cpu_name_up.endswith('U)')
        
        gpu_is_laptop = 'LAPTOP' in gpu_name_up or 'MOBILE' in gpu_name_up
        gpu_is_desktop = not gpu_is_laptop and ('RTX' in gpu_name_up or 'RX ' in gpu_name_up or 'GTX' in gpu_name_up or 'ARC' in gpu_name_up)
        
        if cpu_is_laptop and gpu_is_desktop:
            self.lbl_b_bn.setText("⚠️ UYUMSUZ: Laptop CPU ile Masaüstü GPU eşleştirilemez!\nLaptop CPU seçtiniz, lütfen Laptop GPU seçin veya masaüstü CPU'ya geçin.")
            self.lbl_b_bn.setStyleSheet("color: #FF4655; font-size: 14px; font-weight: bold;")
            self.switch_page(4)
            return
        
        if not cpu_is_laptop and gpu_is_laptop:
            self.lbl_b_bn.setText("⚠️ UYUMSUZ: Masaüstü CPU ile Laptop GPU eşleştirilemez!\nMasaüstü GPU seçin veya laptop CPU'ya geçin.")
            self.lbl_b_bn.setStyleSheet("color: #FF4655; font-size: 14px; font-weight: bold;")
            self.switch_page(4)
            return

        # Only update upscaling & frame gen labels if the GPU vendor actually changed
        new_gpu_name = gpu_data.get('name', '')
        if new_gpu_name != self._last_builder_gpu_name:
            self._last_builder_gpu_name = new_gpu_name
            self.update_upscale_options(new_gpu_name, self.b_cmb_upscale, self.b_cmb_framegen)
        
        # Get selected RAM from builder
        ram_text = self.b_cmb_ram.currentText() if hasattr(self, 'b_cmb_ram') else "16 GB"
        builder_ram_gb = int(ram_text.split()[0])  # Extract number from "16 GB"
        
        # Assume standard RAM for system score calculation
        sys_score = scoring_engine.calculate_system_score(cpu_data["power_score"], gpu_data["power_score"], builder_ram_gb)
        bn_data = scoring_engine.analyze_bottleneck(cpu_data["power_score"], gpu_data["power_score"])
        
        # Animate the score bar
        self._b_target_score = min(int(sys_score), 100)
        self._b_current_score = 0
        self.lbl_b_score_num.setText("0")
        self.b_score_bar.setValue(0)
        if hasattr(self, '_b_score_timer') and self._b_score_timer.isActive():
            self._b_score_timer.stop()
        self._b_score_timer = QTimer()
        self._b_score_timer.timeout.connect(self.animate_builder_score)
        self._b_score_timer.start(15)
        
        self.lbl_b_bn.setText(f"{bn_data['status']} — {bn_data['msg']}")
        # Color coding the bottleneck & Affiliate Links
        search_kw = "bilgisayar+parcalari"
        btn_text = "Önerilen Parçalara"
        show_links = False
        
        if "PERFECT" in bn_data['status']:
            self.lbl_b_bn.setStyleSheet("color: #10B981; font-size: 16px; font-weight: bold; text-align: center;")
            self.b_affiliate_lbl.hide()
        else:
            show_links = True
            if "CRITICAL" in bn_data['status']:
                self.lbl_b_bn.setStyleSheet("color: #FF4655; font-size: 16px; font-weight: bold; text-align: center;")
            else:
                self.lbl_b_bn.setStyleSheet("color: #F59E0B; font-size: 16px; font-weight: bold; text-align: center;")
                
            import urllib.parse
            from core import db_manager
            
            msg_up = bn_data['msg'].upper()
            stat_up = bn_data['status'].upper()
            
            target_model = ""
            if "CPU DARBOĞAZI" in stat_up or "İŞLEMCİ" in msg_up or "CPU" in msg_up:
                cpu_upgrades = db_manager.get_recommended_upgrades(gpu_data['power_score'], is_cpu=True, current_hardware_name=cpu_data.get('name', ''), count=1)
                target_model = cpu_upgrades[0] if cpu_upgrades else ""
                search_kw = urllib.parse.quote(target_model) if target_model else "kutu+islemci"
                btn_text = target_model if target_model else "İşlemcilere"
            elif "GPU DARBOĞAZI" in stat_up or "EKRAN KARTI" in msg_up or "GPU" in msg_up:
                gpu_upgrades = db_manager.get_recommended_upgrades(cpu_data['power_score'], is_cpu=False, current_hardware_name=gpu_data.get('name', ''), count=1)
                target_model = gpu_upgrades[0] if gpu_upgrades else ""
                search_kw = urllib.parse.quote(target_model) if target_model else "oyuncu+ekran+karti"
                btn_text = target_model if target_model else "Ekran Kartlarına"
                
        if show_links:
            # Color Palettes (Amazon: Dark Blue/Black, Trendyol: Orange, HB: Red/Orange)
            html = f"""
            <div style='margin-top:15px; margin-bottom:5px; text-align:center;'>
               <a href='https://www.hepsiburada.com/ara?q={search_kw}' style='background-color:#FF6000; color:white; padding:8px 18px; text-decoration:none; font-weight:bold; border-radius:6px; font-size:13px; margin-right:12px;'>🛒 HB'da {btn_text}</a>
               <a href='https://www.trendyol.com/sr?q={search_kw}&pi=2' style='background-color:#F27A1A; color:white; padding:8px 18px; text-decoration:none; font-weight:bold; border-radius:6px; font-size:13px; margin-right:12px;'>🛒 Trendyol'da {btn_text}</a>
               <a href='https://www.amazon.com.tr/s?k={search_kw}&tag=perfhub-21' style='background-color:#232F3E; color:#FF9900; padding:8px 18px; text-decoration:none; font-weight:bold; border-radius:6px; font-size:13px;'>🛒 Amazon'da {btn_text}</a>
            </div>
            """
            self.b_affiliate_lbl.setText(html)
            self.b_affiliate_lbl.show()
            
        # --- FPS CALCULATIONS FOR BUILDER ---
        b_res = self.b_cmb_res.currentText()
        b_game = self.b_cmb_game.currentData()
        b_upscaling = self.b_cmb_upscale.currentText()
        b_frame_gen_mode = self.b_cmb_framegen.currentText()
        
        # Get RAM from FPS page selector (synced with builder)
        b_ram_text = self.b_cmb_ram_fps.currentText() if hasattr(self, 'b_cmb_ram_fps') else "16 GB"
        b_ram_gb = int(b_ram_text.split()[0])
        
        if b_game:
            # Check RT/PT support for builder
            supports_rt = b_game.get("supports_rt", 0)
            supports_pt = b_game.get("supports_pt", 0)
            
            # Check if selected GPU supports RT/PT
            gpu_name_builder = gpu_data.get('name', '').upper()
            gpu_supports_rt_builder = (
                'RTX' in gpu_name_builder or
                'RX 6' in gpu_name_builder or 'RX 7' in gpu_name_builder or
                'ARC' in gpu_name_builder
            )
            
            # Enable RT/PT only if BOTH game AND GPU support it
            self.b_chk_rt.setEnabled(supports_rt == 1 and gpu_supports_rt_builder)
            self.b_chk_pt.setEnabled(supports_pt == 1 and gpu_supports_rt_builder)
            
            if supports_rt == 0 or not gpu_supports_rt_builder:
                self.b_chk_rt.setChecked(False)
            if supports_pt == 0 or not gpu_supports_rt_builder:
                self.b_chk_pt.setChecked(False)
            
            # Update support label
            if not gpu_supports_rt_builder:
                self.b_lbl_rt_support.setText("❌ Seçili GPU RT/PT desteklemiyor")
            elif supports_pt == 1:
                self.b_lbl_rt_support.setText("✅ Bu oyun RT + PT destekliyor")
            elif supports_rt == 1:
                self.b_lbl_rt_support.setText("✅ Bu oyun RT destekliyor")
            else:
                self.b_lbl_rt_support.setText("❌ Bu oyun RT/PT desteklemiyor")

            # ── Upscaling support label (Builder) ───────────────────────────
            b_dlss = b_game.get("supports_dlss", 1)
            b_fsr  = b_game.get("supports_fsr",  1)
            b_xess = b_game.get("supports_xess", 0)
            tech_parts = []
            if b_dlss: tech_parts.append("DLSS")
            if b_fsr:  tech_parts.append("FSR")
            if b_xess: tech_parts.append("XeSS")
            tech_str = " · ".join(tech_parts) if tech_parts else "Yok (Native TAA)"
            
            b_warn = ""
            up_sel = b_upscaling.lower()
            if "dlss" in up_sel and not b_dlss:
                b_warn = "  ⚠️ Bu oyun DLSS desteklemiyor — Native olarak hesaplanacak"
            elif "fsr" in up_sel and not b_fsr:
                b_warn = "  ⚠️ Bu oyun FSR desteklemiyor — Native olarak hesaplanacak"
            elif "xess" in up_sel and not b_xess:
                b_warn = "  ⚠️ Bu oyun XeSS desteklemiyor — Native olarak hesaplanacak"
                
            b_lbl_txt = f"🎮 Upscaling Desteği: {tech_str}{b_warn}"
            if hasattr(self, 'b_lbl_upscale_support'):
                b_color = "#FF9900" if b_warn else "#45A29E"
                self.b_lbl_upscale_support.setStyleSheet(f"color:{b_color}; font-size:12px; font-style:italic;")
                self.b_lbl_upscale_support.setText(b_lbl_txt)

            
            # RT/PT performance penalty
            b_rt_enabled = self.b_chk_rt.isChecked() and supports_rt == 1 and gpu_supports_rt_builder
            b_pt_enabled = self.b_chk_pt.isChecked() and supports_pt == 1 and gpu_supports_rt_builder
            
            for preset, bar in self.b_fps_bars.items():
                fps = scoring_engine.estimate_fps(cpu_data, gpu_data, b_game, b_res, preset, b_upscaling, b_frame_gen_mode, b_ram_gb)
                
                # Apply RT/PT penalty (calibrated against Digital Foundry / HardwareUnboxed 2024)
                if b_pt_enabled:
                    # Path Tracing (Cyberpunk full PT): ~55% FPS loss
                    fps = int(fps * 0.45)
                elif b_rt_enabled:
                    # Ray Tracing: ~40% FPS loss for heavy RT games
                    fps = int(fps * 0.60)
                
                bar.setRange(0, max(fps * 2, 360))
                bar.setValue(fps)
                if fps >= 120: color = "#9D00FF"
                elif fps >= 90: color = "#3B82F6"
                elif fps >= 60: color = "#10B981"
                elif fps >= 30: color = "#F59E0B"
                else: color = "#FF4655"
                    
                bar.setStyleSheet(f"QProgressBar {{ border: 1px solid #45A29E; background-color: #1a1a24; color: white; border-radius: 5px; text-align: center; font-weight: 900; font-size: 16px; }} QProgressBar::chunk {{ background-color: {color}; border-radius: 4px; }}")

        # Auto-navigate to the Builder FPS page to show results
        self.switch_page(4)

    # ─────────────────────────────────────────────────────────────
    #  KARŞILAŞTIR SAYFASI  (page index 7)
    # ─────────────────────────────────────────────────────────────
    def setup_compare(self):
        inner = QWidget(); inner.setObjectName("ScrollContent")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        self._page_title_compare = QLabel(STRINGS[self.lang]["title_compare"])
        self._page_title_compare.setProperty("class", "Title")
        layout.addWidget(self._page_title_compare)

        desc = QLabel("İki CPU veya iki GPU'yu yan yana karşılaştır, hangisi daha güçlü hemen gör.")
        desc.setStyleSheet("color:#C5C6C7; font-size:14px;")
        layout.addWidget(desc)

        # Tabs: CPU vs CPU | GPU vs GPU
        self.cmp_tabs = QTabWidget()
        self.cmp_tabs.setStyleSheet(
            "QTabBar::tab { background:#1F2833; color:white; padding:10px 28px; font-weight:bold; border-radius:6px 6px 0 0; }"
            "QTabBar::tab:selected { background:#45A29E; color:#0B0C10; }"
            "QTabWidget::pane { border: 1px solid #2C3E50; border-radius:0 6px 6px 6px; }"
        )

        # ── CPU vs CPU Tab ──────────────────────────────────────
        cpu_tab = QWidget()
        cpu_tab_lay = QVBoxLayout(cpu_tab)
        cpu_tab_lay.setContentsMargins(20, 20, 20, 20)
        cpu_tab_lay.setSpacing(14)

        cpu_sel_row = QHBoxLayout()
        cpu_sel_row.setSpacing(20)

        # CPU 1
        v1 = QVBoxLayout()
        lbl1 = QLabel("🔵 CPU 1")
        lbl1.setStyleSheet("color:#66FCF1; font-weight:bold; font-size:14px;")
        v1.addWidget(lbl1)
        self.cmp_cpu1_list = SearchableList("CPU 1 ara...")
        v1.addWidget(self.cmp_cpu1_list)
        cpu_sel_row.addLayout(v1)

        # VS
        vs_lbl = QLabel("VS")
        vs_lbl.setStyleSheet("color:#F59E0B; font-size:28px; font-weight:900;")
        vs_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cpu_sel_row.addWidget(vs_lbl)

        # CPU 2
        v2 = QVBoxLayout()
        lbl2 = QLabel("🔴 CPU 2")
        lbl2.setStyleSheet("color:#FF4655; font-weight:bold; font-size:14px;")
        v2.addWidget(lbl2)
        self.cmp_cpu2_list = SearchableList("CPU 2 ara...")
        v2.addWidget(self.cmp_cpu2_list)
        cpu_sel_row.addLayout(v2)
        cpu_tab_lay.addLayout(cpu_sel_row)

        btn_cmp_cpu = QPushButton("⚖️  KARŞILAŞTIR")
        btn_cmp_cpu.setFixedHeight(44)
        btn_cmp_cpu.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cmp_cpu.setStyleSheet(
            "QPushButton{background-color:transparent;color:#66FCF1;font-size:16px;font-weight:900;"
            "border:2px solid #66FCF1;border-radius:8px;}"
            "QPushButton:hover{background-color:rgba(102,252,241,0.15);}"
        )
        btn_cmp_cpu.clicked.connect(self._do_compare_cpu)
        cpu_tab_lay.addWidget(btn_cmp_cpu)

        self.cmp_cpu_result = QWidget()
        self.cmp_cpu_result_lay = QVBoxLayout(self.cmp_cpu_result)
        self.cmp_cpu_result_lay.setContentsMargins(0,0,0,0)
        cpu_tab_lay.addWidget(self.cmp_cpu_result)
        cpu_tab_lay.addStretch()

        # ── GPU vs GPU Tab ──────────────────────────────────────
        gpu_tab = QWidget()
        gpu_tab_lay = QVBoxLayout(gpu_tab)
        gpu_tab_lay.setContentsMargins(20, 20, 20, 20)
        gpu_tab_lay.setSpacing(14)

        gpu_sel_row = QHBoxLayout()
        gpu_sel_row.setSpacing(20)

        # GPU 1
        g1 = QVBoxLayout()
        glbl1 = QLabel("🔵 GPU 1")
        glbl1.setStyleSheet("color:#66FCF1; font-weight:bold; font-size:14px;")
        g1.addWidget(glbl1)
        self.cmp_gpu1_list = SearchableList("GPU 1 ara...")
        g1.addWidget(self.cmp_gpu1_list)
        gpu_sel_row.addLayout(g1)

        vs_lbl2 = QLabel("VS")
        vs_lbl2.setStyleSheet("color:#F59E0B; font-size:28px; font-weight:900;")
        vs_lbl2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gpu_sel_row.addWidget(vs_lbl2)

        # GPU 2
        g2 = QVBoxLayout()
        glbl2 = QLabel("🔴 GPU 2")
        glbl2.setStyleSheet("color:#FF4655; font-weight:bold; font-size:14px;")
        g2.addWidget(glbl2)
        self.cmp_gpu2_list = SearchableList("GPU 2 ara...")
        g2.addWidget(self.cmp_gpu2_list)
        gpu_sel_row.addLayout(g2)
        gpu_tab_lay.addLayout(gpu_sel_row)

        btn_cmp_gpu = QPushButton("⚖️  KARŞILAŞTIR")
        btn_cmp_gpu.setFixedHeight(44)
        btn_cmp_gpu.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cmp_gpu.setStyleSheet(
            "QPushButton{background-color:transparent;color:#66FCF1;font-size:16px;font-weight:900;"
            "border:2px solid #66FCF1;border-radius:8px;}"
            "QPushButton:hover{background-color:rgba(102,252,241,0.15);}"
        )
        btn_cmp_gpu.clicked.connect(self._do_compare_gpu)
        gpu_tab_lay.addWidget(btn_cmp_gpu)

        self.cmp_gpu_result = QWidget()
        self.cmp_gpu_result_lay = QVBoxLayout(self.cmp_gpu_result)
        self.cmp_gpu_result_lay.setContentsMargins(0,0,0,0)
        gpu_tab_lay.addWidget(self.cmp_gpu_result)
        gpu_tab_lay.addStretch()

        # Populate lists from DB
        all_cpus = db_manager.get_all_cpus()
        for c in all_cpus:
            display = f"{c['name']}  |  Puan: {c['power_score']}  |  {c.get('architecture','')}"
            self.cmp_cpu1_list.add_item(display, c)
            self.cmp_cpu2_list.add_item(display, c)

        all_gpus = db_manager.get_all_gpus()
        for g in all_gpus:
            vram = g.get('vram', 0)
            display = f"{g['name']}  |  Puan: {g['power_score']}  |  {vram}GB VRAM"
            self.cmp_gpu1_list.add_item(display, g)
            self.cmp_gpu2_list.add_item(display, g)

        self.cmp_tabs.addTab(cpu_tab, "🖥️  CPU vs CPU")
        self.cmp_tabs.addTab(gpu_tab, "🎮  GPU vs GPU")
        layout.addWidget(self.cmp_tabs)

        page_layout = QVBoxLayout(self.page_compare)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(self._scrollable(inner))

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            w = child.widget()
            if w:
                try: w.setParent(None); w.deleteLater()
                except: pass

    def _compare_cards(self, result_layout, hw1, hw2, is_cpu):
        """Build side-by-side comparison cards."""
        self._clear_layout(result_layout)

        if not hw1 or not hw2:
            result_layout.addWidget(QLabel("⚠️ İki donanım da seçilmeli!"))
            return

        ps1 = hw1.get('power_score', 0)
        ps2 = hw2.get('power_score', 0)
        winner_idx = 0 if ps1 >= ps2 else 1

        row = QHBoxLayout(); row.setSpacing(16)

        for idx, (hw, color, tag) in enumerate([(hw1, "#66FCF1", "🔵"), (hw2, "#FF4655", "🔴")]):
            ps = hw.get('power_score', 0)
            name = hw.get('name', 'N/A')
            arch = hw.get('architecture', 'N/A')
            is_winner = (idx == winner_idx)

            card = QFrame()
            card.setProperty("class", "Card")
            if is_winner:
                card.setStyleSheet("background-color:#1a1a24; border:2px solid #66FCF1; border-radius:12px;")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(18, 16, 18, 16)
            cl.setSpacing(10)

            # Name + winner badge
            name_row = QHBoxLayout()
            name_lbl = QLabel(f"{tag}  {name}")
            name_lbl.setStyleSheet(f"color:{color}; font-size:14px; font-weight:900;")
            name_lbl.setWordWrap(True)
            name_row.addWidget(name_lbl, 1)
            if is_winner:
                w_badge = QLabel("🏆 ÜSTÜN")
                w_badge.setStyleSheet("background-color:#66FCF1; color:#0B0C10; font-size:10px; font-weight:900; padding:3px 8px; border-radius:8px;")
                name_row.addWidget(w_badge)
            cl.addLayout(name_row)

            # Score bar
            score_pct = min(int(ps), 100)
            bar = QProgressBar()
            bar.setRange(0, 150); bar.setValue(int(ps))
            bar.setFixedHeight(20); bar.setTextVisible(True)
            bar.setFormat(f"  Puan: {ps}")
            bar.setStyleSheet(f"QProgressBar{{background:#1F2833;border-radius:6px;color:white;font-weight:bold;}}"
                              f"QProgressBar::chunk{{background-color:{color};border-radius:6px;}}")
            cl.addWidget(bar)

            # Specs
            if is_cpu:
                specs = [
                    ("Çekirdek/Thread", f"{hw.get('cores','?')} / {hw.get('threads','?')}"),
                    ("Taban / Boost",   f"{hw.get('base_clock','?')} / {hw.get('boost_clock','?')} GHz"),
                    ("Mimari",          arch),
                    ("TDP (tahmini)",   self._est_tdp(name, ps, True)),
                    ("Çıkış Yılı",      str(self._est_year(arch, name, True))),
                ]
                gaming_s  = round(min(10, ps / 10.5), 1)
                render_s  = round(min(10, hw.get('cores', 8) / 3.2 * 0.6 + ps / 28.0), 1)
            else:
                vram = hw.get('vram', 8) or 8
                specs = [
                    ("VRAM",          f"{vram} GB"),
                    ("Çekirdek MHz",  f"{hw.get('core_clock',0)} MHz"),
                    ("Bellek MHz",    f"{hw.get('memory_clock',0) or '?'} MHz"),
                    ("Mimari",        arch),
                    ("TDP (tahmini)", self._est_tdp(name, ps, False)),
                ]
                gaming_s = round(min(10, ps / 13.0 + vram / 14.0), 1)
                render_s = round(min(10, vram / 2.8 + ps / 25.0), 1)

            cl.addLayout(self._score_bar("Gaming",    gaming_s, "#9D00FF"))
            cl.addLayout(self._score_bar("Render/3D", render_s, "#3B82F6"))

            for k, v in specs:
                sr = QHBoxLayout()
                kl = QLabel(f"{k}:"); kl.setFixedWidth(130)
                kl.setStyleSheet("color:#45A29E; font-size:12px; font-weight:bold;")
                vl = QLabel(str(v)); vl.setStyleSheet("color:white; font-size:12px;"); vl.setWordWrap(True)
                sr.addWidget(kl); sr.addWidget(vl, 1); cl.addLayout(sr)

            row.addWidget(card, 1)

        result_layout.addLayout(row)

        # Verdict
        diff = abs(ps1 - ps2)
        if diff < 5:
            verdict = "⚖️  Bu iki donanım birbirine çok yakın — fark pratikte hissedilmez."
            vcolor = "#10B981"
        else:
            winner_name = hw1['name'] if winner_idx == 0 else hw2['name']
            verdict = f"🏆  {winner_name} yaklaşık {diff:.0f} puan ({int(diff/max(min(ps1,ps2),1)*100)}%) daha güçlü."
            vcolor = "#66FCF1"
        vl = QLabel(verdict)
        vl.setStyleSheet(f"color:{vcolor}; font-size:14px; font-weight:bold; margin-top:8px;")
        vl.setWordWrap(True)
        result_layout.addWidget(vl)

        # AI Deeper Analysis button
        hw_names = f"{hw1['name']} vs {hw2['name']}"
        hw_type_str = "CPU" if is_cpu else "GPU"
        ai_btn = QPushButton(f"🤖 AI'ya Derin Karşılaştırma Yaptır: {hw_names[:45]}")
        ai_btn.setStyleSheet("background-color:#F59E0B;color:#0B0C10;font-weight:900;padding:10px;border-radius:6px;font-size:13px;")
        ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ai_btn.clicked.connect(lambda: self._compare_ai_chat(hw1['name'], hw2['name'], hw_type_str))
        result_layout.addWidget(ai_btn)

    def _compare_ai_chat(self, name1, name2, hw_type):
        prompt = (
            f"{name1} ile {name2} arasında kapsamlı bir {hw_type} karşılaştırması yap. "
            f"Oyun performansı, güç tüketimi, fiyat/performans, termal davranış ve "
            f"'hangisini almalıyım?' sorusuna net bir tavsiye ver."
        )
        self.switch_page(6)
        self.chat_input.setText(prompt)
        self.on_ai_chat_send()

    def _do_compare_cpu(self):
        hw1 = self.cmp_cpu1_list.get_selected_data()
        hw2 = self.cmp_cpu2_list.get_selected_data()
        self._compare_cards(self.cmp_cpu_result_lay, hw1, hw2, is_cpu=True)

    def _do_compare_gpu(self):
        hw1 = self.cmp_gpu1_list.get_selected_data()
        hw2 = self.cmp_gpu2_list.get_selected_data()
        self._compare_cards(self.cmp_gpu_result_lay, hw1, hw2, is_cpu=False)

    # ─────────────────────────────────────────────────────────────
    #  AYARLAR SAYFASI  (page index 8)
    # ─────────────────────────────────────────────────────────────
    def setup_settings(self):
        inner = QWidget(); inner.setObjectName("ScrollContent")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        self._page_title_settings = QLabel(STRINGS[self.lang]["title_settings"])
        self._page_title_settings.setProperty("class", "Title")
        layout.addWidget(self._page_title_settings)

        # ── Dil / Language ───────────────────────────────────────
        lang_card = QFrame(); lang_card.setProperty("class", "Card")
        lc_lay = QVBoxLayout(lang_card); lc_lay.setContentsMargins(24, 20, 24, 20); lc_lay.setSpacing(12)
        self._lbl_settings_lang_head = QLabel(STRINGS[self.lang]["settings_lang_head"])
        self._lbl_settings_lang_head.setStyleSheet("color:#66FCF1; font-size:15px; font-weight:900;")
        lc_lay.addWidget(self._lbl_settings_lang_head)
        self._lbl_settings_lang_desc = QLabel(STRINGS[self.lang]["settings_lang_desc"])
        self._lbl_settings_lang_desc.setStyleSheet("color:#C5C6C7; font-size:12px;")
        lc_lay.addWidget(self._lbl_settings_lang_desc)

        lang_row = QHBoxLayout()
        self.btn_lang_tr = QPushButton("🇹🇷  Türkçe")
        self.btn_lang_en = QPushButton("🇬🇧  English")
        for btn in [self.btn_lang_tr, self.btn_lang_en]:
            btn.setFixedHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton{background-color:#1F2833;color:#C5C6C7;font-size:14px;"
                "font-weight:bold;border:1px solid #2C3E50;border-radius:6px;padding:0 20px;}"
                "QPushButton:hover{border-color:#45A29E;color:#66FCF1;}"
            )
        self.btn_lang_tr.clicked.connect(lambda: self._set_language("TR"))
        self.btn_lang_en.clicked.connect(lambda: self._set_language("EN"))
        lang_row.addWidget(self.btn_lang_tr)
        lang_row.addWidget(self.btn_lang_en)
        lang_row.addStretch()
        lc_lay.addLayout(lang_row)
        self.settings_lang_status = QLabel("Aktif Dil: 🇹🇷 Türkçe")
        self.settings_lang_status.setStyleSheet("color:#10B981; font-size:13px; font-weight:bold;")
        lc_lay.addWidget(self.settings_lang_status)
        layout.addWidget(lang_card)

        # ── Satış Ortaklığı Linkleri ─────────────────────────────
        aff_card = QFrame(); aff_card.setProperty("class", "Card")
        ac_lay = QVBoxLayout(aff_card); ac_lay.setContentsMargins(24, 20, 24, 20); ac_lay.setSpacing(10)
        self._lbl_settings_aff_head = QLabel("🛒  Satış Ortaklığı Linkleri")
        self._lbl_settings_aff_head.setStyleSheet("color:#66FCF1; font-size:15px; font-weight:900;")
        ac_lay.addWidget(self._lbl_settings_aff_head)
        self._lbl_settings_aff_desc = QLabel("Darboğaz tespiti yapıldığında gösterilecek mağaza linklerini seç.")
        self._lbl_settings_aff_desc.setStyleSheet("color:#C5C6C7; font-size:12px;")
        ac_lay.addWidget(self._lbl_settings_aff_desc)

        from PyQt6.QtWidgets import QCheckBox
        self.chk_amazon = QCheckBox("🛒 Amazon")
        self.chk_trendyol = QCheckBox("🛒 Trendyol")
        self.chk_hepsiburada = QCheckBox("🛒 Hepsiburada")
        for chk in [self.chk_amazon, self.chk_trendyol, self.chk_hepsiburada]:
            chk.setChecked(True)
            chk.setStyleSheet("color:#C5C6C7; font-size:14px;")
            ac_lay.addWidget(chk)
        layout.addWidget(aff_card)

        # ── Hakkında / About ─────────────────────────────────────
        about_card = QFrame(); about_card.setProperty("class", "Card")
        ab_lay = QVBoxLayout(about_card); ab_lay.setContentsMargins(24, 20, 24, 20); ab_lay.setSpacing(8)
        self._lbl_settings_about_head = QLabel("ℹ️  PerfHub AI Hakkında")
        self._lbl_settings_about_head.setStyleSheet("color:#66FCF1; font-size:15px; font-weight:900;")
        ab_lay.addWidget(self._lbl_settings_about_head)
        for line in [
            "📌 Versiyon: 5.0 PRO",
            "🔒 Veri gizliliği: Tüm veriler yerel olarak işlenir.",
            "🤖 AI Motor: xAI Grok (grok-3-mini-fast — hızlı ve akıllı)",
            "💻 Geliştirici: Süleyman Kılınç",
            "© 2026 PerfHub AI. Tüm hakları saklıdır.",
        ]:
            lb = QLabel(line)
            lb.setStyleSheet("color:#C5C6C7; font-size:13px;")
            ab_lay.addWidget(lb)
        layout.addWidget(about_card)

        layout.addStretch()
        page_layout = QVBoxLayout(self.page_settings)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(self._scrollable(inner))

    def _safe_set_text(self, widget_attr, text):
        """Safely set text on a widget, ignoring deleted C++ object errors."""
        try:
            widget = getattr(self, widget_attr, None)
            if widget is not None:
                widget.setText(text)
        except RuntimeError:
            pass  # Widget was deleted (C++ object destroyed)

    def _set_language(self, lang):
        self.lang = lang
        self._apply_language()

    def _apply_language(self):
        """Update ALL visible UI strings to match self.lang (TR or EN)."""
        lang = self.lang
        S = STRINGS[lang]

        # ── Sidebar section labels ────────────────────────────────
        try:
            self._sec_ana.setText(S["sec_ana"])
            self._sec_perf.setText(S["sec_perf"])
            self._sec_tools.setText(S["sec_tools"])
        except RuntimeError:
            pass

        # ── Nav button labels ─────────────────────────────────────
        try:
            self._nb_dash.set_text("🖥️",  S["nav_dashboard"])
            self._nb_bn.set_text(  "⚠️",  S["nav_bottleneck"])
            self._nb_fps.set_text( "🎮",  S["nav_fps"])
            self._nb_bld.set_text( "🛠️",  S["nav_builder"])
            self._nb_bfps.set_text("🚀",  S["nav_bfps"])
            self._nb_ai.set_text(  "🤖",  S["nav_ai"])
            self._nb_cmp.set_text( "⚖️",  S["nav_compare"])
            self._nb_hw.set_text(  "🔬",  S["nav_hw"])
            self._nb_set.set_text( "⚙️",  S["nav_settings"])
        except RuntimeError:
            pass

        # ── Score widget header ───────────────────────────────────
        try:
            self._lbl_score_header.setText(S["score_header"])
        except RuntimeError:
            pass

        # ── Page titles ───────────────────────────────────────────
        for attr, key in [
            ("_page_title_dash",     "title_dashboard"),
            ("_page_title_bn",       "title_bottleneck"),
            ("_page_title_fps",      "title_fps"),
            ("_page_title_builder",  "title_builder"),
            ("_page_title_bfps",     "title_bfps"),
            ("_page_title_hw",       "title_hw"),
            ("_page_title_ai",       "title_ai"),
            ("_page_title_compare",  "title_compare"),
            ("_page_title_settings", "title_settings"),
        ]:
            self._safe_set_text(attr, S[key])

        # ── Settings page labels ──────────────────────────────────
        for attr, key in [
            ("settings_lang_status",      "settings_lang_active"),
            ("_lbl_settings_lang_head",   "settings_lang_head"),
            ("_lbl_settings_lang_desc",   "settings_lang_desc"),
            ("_lbl_settings_aff_head",    "settings_aff_head"),
            ("_lbl_settings_aff_desc",    "settings_aff_desc"),
            ("_lbl_settings_about_head",  "settings_about_head"),
        ]:
            self._safe_set_text(attr, S[key])

        # ── Highlight active lang button ──────────────────────────
        active_style = (
            "QPushButton{background-color:#45A29E;color:#0B0C10;font-size:14px;"
            "font-weight:900;border:1px solid #45A29E;border-radius:6px;padding:0 20px;}"
        )
        inactive_style = (
            "QPushButton{background-color:#1F2833;color:#C5C6C7;font-size:14px;"
            "font-weight:bold;border:1px solid #2C3E50;border-radius:6px;padding:0 20px;}"
            "QPushButton:hover{border-color:#45A29E;color:#66FCF1;}"
        )
        try:
            if hasattr(self, "btn_lang_tr"):
                self.btn_lang_tr.setStyleSheet(active_style if lang == "TR" else inactive_style)
                self.btn_lang_en.setStyleSheet(active_style if lang == "EN" else inactive_style)
        except RuntimeError:
            pass

        # ── Dashboard static labels ───────────────────────────────
        # NOTE: _hw_card_title_* references may point to deleted C++ objects
        # after populate_dash_detail() rebuilds the layout — always guard!
        for attr, key in [
            ("_lbl_score_title",   "score_title"),
            ("_lbl_detail_section","detail_section"),
            ("_lbl_scanning",      "scanning"),
        ]:
            self._safe_set_text(attr, S[key])

        # ── Repopulate games if scan is already done ──────────────
        try:
            if self.system_data is not None:
                self.populate_games()
        except Exception:
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BenchmarkApp()
    window.show()
    sys.exit(app.exec())

