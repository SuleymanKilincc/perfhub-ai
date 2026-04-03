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
            data = ai_assistant.analyze_hardware(self._hw_name, self._is_cpu)
            self.finished.emit(data)
        except Exception as e:
            self.finished.emit({"error": f"Hata: {str(e)}"})

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
        self.setWindowTitle("TUF GAMING - PERFORMANCE HUB [V2 PRO]")
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
        self.init_ui()
        self.run_scanner()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        root_layout = QHBoxLayout(main_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ============================================================
        # LEFT SIDEBAR
        # ============================================================
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("background-color: #0d0d18; border-right: 1px solid #1e2a38;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # App logo
        logo_frame = QFrame()
        logo_frame.setStyleSheet("background-color: #090912; border-bottom: 1px solid #1e2a38; padding: 0px;")
        logo_frame.setFixedHeight(80)
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(15, 0, 15, 0)
        logo_lbl = QLabel("\u26a1 PerfHub AI")
        logo_lbl.setStyleSheet("color: #66FCF1; font-size: 18px; font-weight: 900; letter-spacing: 1px;")
        logo_layout.addWidget(logo_lbl)
        subtitle = QLabel("Benchmark & AI Asistan")
        subtitle.setStyleSheet("color: #45A29E; font-size: 11px;")
        logo_layout.addWidget(subtitle)
        sidebar_layout.addWidget(logo_frame)
        sidebar_layout.addSpacing(10)

        # Nav buttons
        NAV_ITEMS = [
            ("\U0001f5a5\ufe0f",  "Dashboard",          "Sistem özeti ve skor"),
            ("\u26a0\ufe0f",      "Darboğaz",               "CPU/GPU dengesiz mi?"),
            ("\U0001f3ae",       "Mevcut PC FPS",       "Mevcut sistem ile FPS"),
            ("\U0001f6e0\ufe0f", "PC Builder",          "Hayalindeki sistemi kur"),
            ("\U0001f680",       "Builder FPS",         "Hayalindeki sistem FPS"),
            ("\U0001f52c",       "Donanım Analizi",     "Seçili GPU/CPU analizi"),
            ("\U0001f916",       "AI Asistan",          "PerfHub AI ile sohbet et"),
        ]
        self.nav_buttons = []
        NAV_STYLE_NORMAL = """
            QPushButton {
                background-color: transparent;
                color: #8896a8;
                font-size: 14px;
                font-weight: bold;
                text-align: left;
                padding: 14px 18px;
                border: none;
                border-left: 3px solid transparent;
            }
            QPushButton:hover {
                background-color: rgba(69, 162, 158, 0.08);
                color: #C5C6C7;
                border-left: 3px solid #45A29E;
            }
        """
        NAV_STYLE_ACTIVE = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(102,252,241,0.12), stop:1 transparent);
                color: #66FCF1;
                font-size: 14px;
                font-weight: bold;
                text-align: left;
                padding: 14px 18px;
                border: none;
                border-left: 3px solid #66FCF1;
            }
        """
        self._nav_style_normal = NAV_STYLE_NORMAL
        self._nav_style_active = NAV_STYLE_ACTIVE

        for i, (icon, name, hint) in enumerate(NAV_ITEMS):
            btn = QPushButton(f"{icon}  {name}")
            btn.setToolTip(hint)
            btn.setStyleSheet(NAV_STYLE_NORMAL)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self.switch_page(idx))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append((btn, NAV_STYLE_NORMAL, NAV_STYLE_ACTIVE))

        sidebar_layout.addStretch()

        # Version footer
        ver = QLabel("v2.0 PRO")
        ver.setStyleSheet("color: #2C3E50; font-size: 10px; padding: 10px 18px;")
        sidebar_layout.addWidget(ver)
        
        # Language selector at bottom
        lang_frame = QFrame()
        lang_frame.setStyleSheet("background-color: #090912; border-top: 1px solid #1e2a38; padding: 10px;")
        lang_layout = QVBoxLayout(lang_frame)
        lang_layout.setContentsMargins(10, 10, 10, 10)
        
        lang_lbl = QLabel("🌐 Language / Dil")
        lang_lbl.setStyleSheet("color: #45A29E; font-size: 11px; font-weight: bold;")
        lang_layout.addWidget(lang_lbl)
        
        self.global_lang_combo = QComboBox()
        self.global_lang_combo.addItems(["🇹🇷 Türkçe", "🇬🇧 English"])
        self.global_lang_combo.setStyleSheet("background-color:#1F2833;color:white;padding:6px;border:1px solid #45A29E;border-radius:4px;font-size:11px;")
        lang_layout.addWidget(self.global_lang_combo)
        
        sidebar_layout.addWidget(lang_frame)

        root_layout.addWidget(sidebar)

        # ============================================================
        # MAIN CONTENT AREA  (QStackedWidget)
        # ============================================================
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #0B0C10;")

        self.page_dash      = QWidget(); self.page_dash.setObjectName("ScrollContent")
        self.page_bn        = QWidget(); self.page_bn.setObjectName("ScrollContent")
        self.page_fps       = QWidget(); self.page_fps.setObjectName("ScrollContent")
        self.page_builder   = QWidget(); self.page_builder.setObjectName("ScrollContent")
        self.page_b_fps     = QWidget(); self.page_b_fps.setObjectName("ScrollContent")
        self.page_hw_analyze = QWidget(); self.page_hw_analyze.setObjectName("ScrollContent")
        self.page_ai        = QWidget(); self.page_ai.setObjectName("ScrollContent")

        for page in [self.page_dash, self.page_bn, self.page_fps, self.page_builder,
                     self.page_b_fps, self.page_hw_analyze, self.page_ai]:
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

        # Default: show Dashboard
        self.switch_page(0)

    def switch_page(self, index):
        """Switch the stacked widget page and update sidebar button styling."""
        self.stack.setCurrentIndex(index)
        for i, (btn, normal_style, active_style) in enumerate(self.nav_buttons):
            btn.setStyleSheet(active_style if i == index else normal_style)

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

        title = QLabel("SYSTEM DASHBOARD")
        title.setProperty("class", "Title")
        layout.addWidget(title)

        # Hardware Info Grid (CPU, GPU, RAM, RAM Details, Storage)
        hw_grid = QGridLayout()
        hw_grid.setSpacing(15)
        
        self.lbl_cpu = self.create_hw_card("PROCESSOR", hw_grid, 0, 0)
        self.lbl_gpu = self.create_hw_card("GRAPHICS CARD", hw_grid, 0, 1)
        self.lbl_ram = self.create_hw_card("MEMORY (RAM)", hw_grid, 0, 2)
        self.lbl_ram_detail = self.create_hw_card("RAM TİPİ & HIZ", hw_grid, 1, 0)
        self.lbl_storage = self.create_hw_card("DEPOLAMA", hw_grid, 1, 1)
        
        layout.addLayout(hw_grid)

        # Score Area (Glowing Box)
        score_frame = QFrame()
        score_frame.setProperty("class", "Card")
        score_layout = QVBoxLayout(score_frame)
        score_layout.setContentsMargins(30,30,30,30)
        score_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        slbl = QLabel("GLOBAL PERFORMANCE SCORE")
        slbl.setStyleSheet("color: #C5C6C7; font-size: 14px; font-weight: bold; letter-spacing: 2px;")
        slbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_layout.addWidget(slbl)

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
        sep = QLabel("▼  DETAYLI DONANIM ANALİZİ")
        sep.setStyleSheet("color:#45A29E;font-size:13px;font-weight:bold;letter-spacing:2px;margin-top:10px;")
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sep)

        self.dash_detail_container = QWidget()
        self.dash_detail_layout = QVBoxLayout(self.dash_detail_container)
        self.dash_detail_layout.setContentsMargins(0, 0, 0, 0)
        self.dash_detail_layout.setSpacing(14)
        waiting_lbl = QLabel("Sistem taranıyor, lütfen bekleyin...")
        waiting_lbl.setStyleSheet("color:#45A29E;font-size:14px;")
        waiting_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dash_detail_layout.addWidget(waiting_lbl)
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

        title = QLabel("DARBOĞAZ ANALİZİ")
        title.setProperty("class", "Title")
        layout.addWidget(title)

        self.bn_frame = QFrame()
        self.bn_frame.setProperty("class", "Card")
        bn_layout = QVBoxLayout(self.bn_frame)
        bn_layout.setContentsMargins(40, 30, 40, 30)
        bn_layout.setSpacing(15)

        self.lbl_bn_title = QLabel("Taranıyor...")
        self.lbl_bn_title.setStyleSheet("color: #F59E0B; font-size: 22px; font-weight: bold;")
        self.lbl_bn_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_bn_desc = QLabel("Bileşenler analiz ediliyor...")
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
        
        title = QLabel("CURRENT PC: GAME FPS ESTIMATOR")
        title.setProperty("class", "Title")
        layout.addWidget(title)

        # Filters
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Resolution: ", styleSheet="color: #45A29E; font-weight: bold;"))
        self.cmb_res = QComboBox()
        self.cmb_res.addItems(["1080p", "1440p", "4k"])
        self.cmb_res.currentTextChanged.connect(self.populate_games)
        filter_layout.addWidget(self.cmb_res)

        filter_layout.addWidget(QLabel("  Select Game: ", styleSheet="color: #45A29E; font-weight: bold;"))
        self.cmb_game = QComboBox()
        self.cmb_game.setMinimumWidth(250)
        all_g = db_manager.get_all_games()
        for g in all_g:
            self.cmb_game.addItem(g["name"], g)
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
        self.cmb_upscale.addItems(["Native", "DLAA / Native AA", "Quality", "Balanced", "Performance", "Ultra Performance"])
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
        layout.addSpacing(12)

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
        
        title = QLabel("CUSTOM PC BUILDER")
        title.setProperty("class", "Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
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

        title = QLabel("\U0001f680 HAYALINDEKİ SİSTEM - SONUÇLAR")
        title.setProperty("class", "Title")
        layout.addWidget(title)

        # Score + bottleneck row
        score_card = QFrame(); score_card.setProperty("class", "Card")
        sc_layout = QVBoxLayout(score_card)
        sc_layout.setContentsMargins(30, 25, 30, 25)
        sc_layout.setSpacing(10)
        sc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sc_lbl = QLabel("TEÖRİK PERFORMANS SKORU")
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

        fps_head = QLabel("TAHMİNİ FPS (HAYALİ SİSTEM)")
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
        self.b_cmb_game.setMinimumWidth(250)
        for g in db_manager.get_all_games():
            self.b_cmb_game.addItem(g["name"], g)
        self.b_cmb_game.currentIndexChanged.connect(self.calculate_custom_build)
        b_filter_layout.addWidget(self.b_cmb_game)
        b_filter_layout.addStretch()
        fps_layout.addLayout(b_filter_layout)

        b_ai_layout = QHBoxLayout()
        b_ai_lbl = QLabel("\u26a1 AI Assist:"); b_ai_lbl.setStyleSheet("color: #9D00FF; font-weight: bold; font-size: 13px;")
        b_ai_layout.addWidget(b_ai_lbl)
        b_ai_layout.addWidget(QLabel("Upscaling:", styleSheet="color: #C5C6C7; font-size: 13px;"))
        self.b_cmb_upscale = QComboBox()
        self.b_cmb_upscale.addItems(["Native", "DLAA / Native AA", "Quality", "Balanced", "Performance", "Ultra Performance"])
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

        title = QLabel("\U0001f52c DONANIM ANALİZİ")
        title.setProperty("class", "Title")
        layout.addWidget(title)

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

        h_lbl = QLabel(f"{'🖥️ İŞLEMCİ' if is_cpu else '🎮 EKRAN KARTI'}  —  {name}")
        h_lbl.setStyleSheet("color:white;font-size:17px;font-weight:900;"); h_lbl.setWordWrap(True)
        self.hw_result_layout.addWidget(h_lbl)

        # ── AI Analysis Button ──
        self.ai_analyze_btn = QPushButton("🤖 AI ile Analiz Et (Kıdemli)")
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
        c1, l1 = self._hw_card("📊  KULLANIM PUANLARI")
        l1.addLayout(self._score_bar("Gaming",      gaming_s, "#9D00FF"))
        l1.addLayout(self._score_bar("Render / 3D", render_s, "#3B82F6"))
        l1.addLayout(self._score_bar("Günlük Ofis", daily_s,  "#10B981"))
        l1.addLayout(self._score_bar("Performans",  min(10, ps / 13.0), "#F59E0B"))
        self.hw_result_layout.addWidget(c1)

        # 2. Tech specs
        c2, l2 = self._hw_card("⚙️  TEKNİK ÖZELLİKLER")
        if is_cpu:
            specs = {"Çekirdek / Thread": f"{hw.get('cores','?')} / {hw.get('threads','?')}", "Taban / Boost GHz": f"{hw.get('base_clock','?')} / {hw.get('boost_clock','?')} GHz", "Mimari": arch, "TDP (tahmini)": self._est_tdp(name, ps, True), "Çıkış Yılı": str(self._est_year(arch, name, True)), "Güç Skoru": str(ps)}
        else:
            specs = {"VRAM": f"{hw.get('vram','?')} GB", "Çekirdek Saati": f"{hw.get('core_clock',0)} MHz", "Bellek Saati": f"{hw.get('memory_clock',0) or '?'} MHz", "Mimari": arch, "TDP (tahmini)": self._est_tdp(name, ps, False), "Çıkış Yılı": str(self._est_year(arch, name, False)), "Güç Skoru": str(ps)}
        for k, v in specs.items():
            row = QHBoxLayout(); kl = QLabel(f"{k}:"); kl.setFixedWidth(180)
            kl.setStyleSheet("color:#45A29E;font-size:13px;font-weight:bold;")
            vl = QLabel(str(v)); vl.setStyleSheet("color:white;font-size:13px;"); vl.setWordWrap(True)
            row.addWidget(kl); row.addWidget(vl, 1); l2.addLayout(row)
        self.hw_result_layout.addWidget(c2)

        # 3. Market & price
        c3, l3 = self._hw_card("💵  PAZAR KONUMU & FİYAT")
        seg, usd = self._market_info(ps, is_cpu); try_price = int(usd * 38.5)
        mrows = {"Segment": seg, "Tahmini Fiyat": f"~${usd} USD  /  ~{try_price:,} TRY", "Fiyat/Performans": self._fp_verdict(ps, usd)}
        for k, v in mrows.items():
            row = QHBoxLayout(); kl = QLabel(f"{k}:"); kl.setFixedWidth(180)
            kl.setStyleSheet("color:#45A29E;font-size:13px;font-weight:bold;")
            vl = QLabel(str(v)); vl.setStyleSheet("color:white;font-size:13px;"); vl.setWordWrap(True)
            row.addWidget(kl); row.addWidget(vl, 1); l3.addLayout(row)
        self.hw_result_layout.addWidget(c3)

        # 4. Gaming performance
        c4, l4 = self._hw_card("🎮  OYUN PERFORMANS TAHMİNİ")
        lines = self._gpu_perf_text(ps, hw.get("vram",8) or 8) if not is_cpu else self._cpu_perf_text(name, ps)
        for line in lines:
            lb = QLabel(line); lb.setStyleSheet("color:#C5C6C7;font-size:12px;"); lb.setWordWrap(True); l4.addWidget(lb)
        self.hw_result_layout.addWidget(c4)

        # 5. Kritik yorum + rakip
        c5, l5 = self._hw_card("📝  KRİTİK YORUM & RAKİP")
        pros, cons = self._pros_cons(name, ps, is_cpu, gaming_s, render_s)
        rival = self._find_rival(name, ps, is_cpu)
        for line in [f"✅ Artı:  {pros}", f"❌ Eksi:  {cons}", f"⚔️  Rakip: {rival}"]:
            lb = QLabel(line); lb.setWordWrap(True); lb.setStyleSheet("color:#C5C6C7;font-size:13px;"); l5.addWidget(lb)
        self.hw_result_layout.addWidget(c5)

        # 6. PSU / Bottleneck
        c6, l6 = self._hw_card("🔌  PSU ÖNERİSİ" if not is_cpu else "⚠️  DARBOĞAZ EŞLEŞMESİ")
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
        # Prevent multiple clicks
        self.ai_analyze_btn.setEnabled(False)
        self.ai_analyze_btn.setText("⏳ AI analiz ediyor, lütfen bekleyin...")
        
        # Clear previous AI content
        while self.ai_result_layout.count():
            child = self.ai_result_layout.takeAt(0)
            w = child.widget()
            if w:
                try: w.setParent(None); w.deleteLater()
                except RuntimeError: pass
        
        # Run in background thread (prevents UI freeze / crash)
        self._analyze_worker = AnalyzeWorkerThread(hw_name, is_cpu)
        self._analyze_worker.finished.connect(self._on_ai_analyze_result)
        self._analyze_worker.start()
    
    def _on_ai_analyze_result(self, data):
        self.ai_analyze_btn.setText("🤖 Yeniden Analiz Et")
        self.ai_analyze_btn.setEnabled(True)
        
        if "error" in data:
            err = QLabel(data["error"])
            err.setStyleSheet("color:#FF4655;font-weight:bold;margin-top:10px;")
            self.ai_result_layout.addWidget(err)
            return
            
        ai_card = QFrame(); ai_card.setProperty("class", "Card")
        ai_card.setStyleSheet("background-color:#1e2a38; border: 1px solid #F59E0B; border-radius: 6px;")
        al = QVBoxLayout(ai_card); al.setContentsMargins(15,15,15,15); al.setSpacing(10)
        
        header = QLabel("🔥 AI ANALİST YORUMU")
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

                amz_html = f"<a href='https://www.amazon.com.tr/s?k={search_term}&tag=perfhub-21' style='color:#FF9900;text-decoration:none;'>🛒 <b>Amazon'da Fiyatlara Bak</b></a>"
                tr_html = f"<a href='https://www.trendyol.com/sr?q={search_term}&pi=2' style='color:#F27A1A;text-decoration:none;'>🛒 <b>Trendyol İndirimleri</b></a>"
                
                amz_link = QLabel(amz_html); amz_link.setOpenExternalLinks(True)
                tr_link = QLabel(tr_html); tr_link.setOpenExternalLinks(True)
                
                link_lay.addWidget(amz_link)
                link_lay.addWidget(QLabel(" | "))
                link_lay.addWidget(tr_link)
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
            if ps >= 85:   t = "RTX 4090 Laptop GPU / RTX 4080 Laptop GPU dahil verimli"
            elif ps >= 70: t = "RTX 4070 Laptop / RTX 3080 Ti Laptop — üstü aşırı ısınır"
            elif ps >= 55: t = "RTX 4060 Laptop / RTX 3070 Laptop seviyesi ideal"
            else:          t = "RTX 3050 Laptop ve altı — daha fazlası darboğaz yapar"
            return [f"Bu laptop CPU için ideal GPU aralığı: {t}.",
                    "Laptop CPU'lar sürekli yükte termal olarak kısıtlanır; bu GPU sınırı pratikte geçerliliğini yitirir."]
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

        title = QLabel("🤖  PerfHub AI Asistan")
        title.setProperty("class", "Title")
        layout.addWidget(title)

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
        
        # Get selected language from global selector
        lang_text = self.global_lang_combo.currentText() if hasattr(self, 'global_lang_combo') else "🇹🇷 Türkçe"
        language = "EN" if "English" in lang_text else "TR"
        
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
                segment = "Tepe Model (Enthusiast)" if language == "TR" else "Top-Tier (Enthusiast)"
            elif raw_score >= 70:
                segment = "Üst Düzey (High-End)" if language == "TR" else "High-End"
            elif raw_score >= 40:
                segment = "Orta-Üst Seviye" if language == "TR" else "Mid-High Level"
            else:
                segment = "Giriş Seviyesi" if language == "TR" else "Entry Level"
            ctx = (
                f"CPU: {hd.get('cpu','Bilinmiyor' if language == 'TR' else 'Unknown')}\n"
                f"GPU: {hd.get('gpu','Bilinmiyor' if language == 'TR' else 'Unknown')}\n"
                f"RAM: {hd.get('ram','Bilinmiyor' if language == 'TR' else 'Unknown')}GB\n"
                f"PerfHub AI {'Skor' if language == 'TR' else 'Score'}: {raw_score}/100 — {segment}"
            )

        # Run in background thread (prevents crash on click during wait)
        self.chat_send_btn.setEnabled(False)
        self._chat_worker = ChatWorkerThread(text, ctx, language)
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
            # To avoid timer errors if it was previously running
            if hasattr(self, 'score_timer'): getattr(self, 'score_timer').stop()
        else:
            self.lbl_score_num.setStyleSheet("")  # reset
            self.current_score = 0
            self.score_timer = QTimer()
            self.score_timer.timeout.connect(self.animate_score)
            self.score_timer.start(20) # 20ms intervals

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

        # Dashboard affiliate links
        if not is_apple:
            import urllib.parse
            from core import db_manager
            cpu_upgrades = db_manager.get_recommended_upgrades(cpu_ps + 5, is_cpu=True, current_hardware_name=hw.get('cpu', ''), count=1)
            rec = cpu_upgrades[0] if cpu_upgrades else ""
            search_kw = urllib.parse.quote(rec) if rec else "islemci"
            btn_text = rec if rec else "İşlemcilere"
            
            d_links = QHBoxLayout()
            html = f"""
            <div style='margin-top:5px; margin-bottom:5px;'>
               <a href='https://www.hepsiburada.com/ara?q={search_kw}' style='background-color:#FF6000; color:white; padding:4px 10px; text-decoration:none; font-weight:bold; border-radius:4px; font-size:11px; margin-right:5px;'>HB'da {btn_text}</a>
               <a href='https://www.trendyol.com/sr?q={search_kw}&pi=2' style='background-color:#F27A1A; color:white; padding:4px 10px; text-decoration:none; font-weight:bold; border-radius:4px; font-size:11px; margin-right:5px;'>Trendyol'da {btn_text}</a>
               <a href='https://www.amazon.com.tr/s?k={search_kw}&tag=perfhub-21' style='background-color:#232F3E; color:#FF9900; padding:4px 10px; text-decoration:none; font-weight:bold; border-radius:4px; font-size:11px;'>Amazon'da {btn_text}</a>
            </div>
            """
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
        
        # Update RT/PT checkboxes based on game support
        self.chk_rt.setEnabled(supports_rt == 1)
        self.chk_pt.setEnabled(supports_pt == 1)
        
        if supports_rt == 0:
            self.chk_rt.setChecked(False)
        if supports_pt == 0:
            self.chk_pt.setChecked(False)
        
        # Update support label
        if supports_pt == 1:
            self.lbl_rt_support.setText("✅ Bu oyun RT + PT destekliyor")
        elif supports_rt == 1:
            self.lbl_rt_support.setText("✅ Bu oyun RT destekliyor")
        else:
            self.lbl_rt_support.setText("❌ Bu oyun RT/PT desteklemiyor")
        
        cpu_data = self.system_data['cpu_data']
        gpu_data = self.system_data['gpu_data']
        ram_gb = self.system_data['hw']['ram']
        upscaling = self.cmb_upscale.currentText()
        frame_gen_mode = self.cmb_framegen.currentText()
        
        # RT/PT performance penalty
        rt_enabled = self.chk_rt.isChecked() and supports_rt == 1
        pt_enabled = self.chk_pt.isChecked() and supports_pt == 1
        
        for preset, bar in self.fps_bars.items():
            fps = scoring_engine.estimate_fps(cpu_data, gpu_data, game_data, res, preset, upscaling, frame_gen_mode, ram_gb)
            
            # Apply RT/PT penalty
            if pt_enabled:
                fps = int(fps * 0.35)  # Path Tracing: ~65% FPS loss
            elif rt_enabled:
                fps = int(fps * 0.60)  # Ray Tracing: ~40% FPS loss
            
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
            for preset, bar in self.b_fps_bars.items():
                fps = scoring_engine.estimate_fps(cpu_data, gpu_data, b_game, b_res, preset, b_upscaling, b_frame_gen_mode, b_ram_gb)
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BenchmarkApp()
    window.show()
    sys.exit(app.exec())
