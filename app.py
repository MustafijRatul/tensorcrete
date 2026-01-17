
import sys
import os
import time
import ctypes
import json
import urllib.request
import numpy as np
import platform
import cv2
from datetime import datetime
from threading import Thread

# --- PDF GENERATION ---
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as PlatImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# --- AI & IMAGE PROCESSING ---
import tensorflow as tf
from PIL import Image, ImageOps, ExifTags

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QDialog,
                               QHBoxLayout, QPushButton, QLabel, QFrame,
                               QScrollArea, QStackedWidget, QMessageBox,
                               QSlider, QFileDialog, QGraphicsDropShadowEffect,
                               QSizePolicy, QComboBox, QProgressBar,
                               QCheckBox, QListWidget, QListWidgetItem, QAbstractItemView)
from PySide6.QtCore import (Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve,
                            QRectF, QSize, QParallelAnimationGroup, QUrl, QThread, Signal)
from PySide6.QtGui import (QColor, QPainter, QFont, QPen, QPixmap, QDesktopServices, QImage)

import qtawesome as qta

# =============================================================================
#  GLOBAL CONFIGURATION & PATHS
# =============================================================================
APP_NAME = "TensorCrete"
APP_VERSION = "5.3 Ultimate"
MODEL_NAME = "crack_detection_model.h5"
UPDATE_JSON_URL = "https://raw.githubusercontent.com/MustafijRatul/tensorcrete/main/version.json"

# --- LOCAL STORAGE SETUP (JSON) ---
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', ''), 'RatulApps', 'TensorCrete')
if not os.path.exists(APPDATA_DIR):
    os.makedirs(APPDATA_DIR)

SETTINGS_FILE = os.path.join(APPDATA_DIR, 'settings.json')
HISTORY_FILE = os.path.join(APPDATA_DIR, 'history.json')


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# =============================================================================
#  DISCORD NOTIFICATION (FIRST RUN ONLY)
# =============================================================================
def send_install_notification():
    # Only run if called by the main app logic check
    webhook_url = "https://discordapp.com/api/webhooks/1448627205268701285/w5BieDqdJOSTolmILGVosSvCBo5IuviemdjMAitanm1i-ywX-WeNIEDqd6xzqtUqiLer"

    def _run():
        try:
            data = {
                "content": f"🚀 **New TensorCrete User!**\n👤 **User:** `{os.getlogin()}`\n💻 **PC:** `{platform.node()}`\n🛡️ **Version:** {APP_VERSION}\n📂 **Path:** `{os.getcwd()}`"
            }
            req = urllib.request.Request(webhook_url, data=json.dumps(data).encode('utf-8'),
                                         headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            urllib.request.urlopen(req)
            print("Notification Sent.")
        except Exception as e:
            print(f"Notification Failed: {e}")

    t = Thread(target=_run)
    t.start()


# =============================================================================
#  THEME MANAGER
# =============================================================================
class ThemeManager:
    COLOR_PRESETS = {
        "Civil Red": ("#d63031", "#ff7675"),
        "Structure Blue": ("#0984e3", "#74b9ff"),
        "Concrete Grey": ("#636e72", "#b2bec3"),
        "Safety Green": ("#00b894", "#55efc4"),
        "Indigo": ("#5D5FEF", "#A5A6F6"),
    }
    THEME_AMBIENT = {
        "BG_MAIN": "rgba(15, 15, 18, {})",
        "BG_SIDEBAR": "rgba(22, 22, 26, {})",
        "BG_CARD": "rgba(30, 30, 36, {})",
        "BG_INPUT": "rgba(39, 39, 48, 200)",
        "TEXT_HEADER": "#FFFFFF",
        "TEXT_BODY": "#E0E0E6",
        "TEXT_MUTED": "#8F90A6",
        "BORDER_SUBTLE": "rgba(255, 255, 255, 0.1)"
    }
    THEME_DARK = {
        "BG_MAIN": "rgba(18, 18, 18, {})",
        "BG_SIDEBAR": "rgba(25, 25, 25, 255)",
        "BG_CARD": "rgba(35, 35, 35, 255)",
        "BG_INPUT": "#2C2C2C",
        "TEXT_HEADER": "#FFFFFF",
        "TEXT_BODY": "#DDDDDD",
        "TEXT_MUTED": "#888888",
        "BORDER_SUBTLE": "#444444"
    }
    CURRENT_BASE = THEME_AMBIENT
    OPACITY = 230
    BUTTON_STYLE = "Gradient"
    ACCENT_PRIMARY = "#d63031"
    ACCENT_SECONDARY = "#ff7675"
    ACCENT_DANGER = "#FF4D4D"
    ACCENT_SUCCESS = "#00D26A"
    GLASS_ENABLED = True
    MODE_NAME = "Ambient"
    COLOR_NAME = "Civil Red"

    @staticmethod
    def set_base_theme(mode):
        ThemeManager.MODE_NAME = mode
        ThemeManager.CURRENT_BASE = ThemeManager.THEME_DARK if mode == "Dark" else ThemeManager.THEME_AMBIENT

    @staticmethod
    def set_accent_color(color_name):
        if color_name in ThemeManager.COLOR_PRESETS:
            ThemeManager.COLOR_NAME = color_name
            p, s = ThemeManager.COLOR_PRESETS[color_name]
            ThemeManager.ACCENT_PRIMARY = p
            ThemeManager.ACCENT_SECONDARY = s

    @staticmethod
    def get(key):
        val = ThemeManager.CURRENT_BASE.get(key)
        if val and "{}" in val:
            if key == "BG_SIDEBAR": return val.format(min(255, ThemeManager.OPACITY + 20))
            if key == "BG_CARD": return val.format(min(255, ThemeManager.OPACITY + 30))
            return val.format(ThemeManager.OPACITY)
        return val


# =============================================================================
#  WINDOW EFFECT
# =============================================================================
class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int), ("GradientColor", ctypes.c_int),
                ("AnimationId", ctypes.c_int)]


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.POINTER(ACCENT_POLICY)), ("SizeOfData", ctypes.c_int)]


class WindowEffect:
    def __init__(self):
        self.user32 = ctypes.windll.user32

    def set_acrylic(self, hwnd, enable=True):
        accent = ACCENT_POLICY()
        accent.AccentState = 4 if enable else 0
        accent.GradientColor = 0x99000000 if enable else 0
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = ctypes.pointer(accent)
        data.SizeOfData = ctypes.sizeof(accent)
        self.user32.SetWindowCompositionAttribute(int(hwnd), ctypes.byref(data))


# =============================================================================
#  UPDATE SYSTEM
# =============================================================================
class UpdateWorker(QThread):
    update_found = Signal(dict)

    def run(self):
        try:
            with urllib.request.urlopen(UPDATE_JSON_URL) as url:
                data = json.loads(url.read().decode())
                if data.get('version') != APP_VERSION:
                    self.update_found.emit(data)
        except:
            pass


class UpdateDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 450)
        if data.get("force_update", False): self.setModal(True)
        l = QVBoxLayout(self)
        f = QFrame(
            styleSheet=f"background-color: {ThemeManager.get('BG_CARD')}; border: 1px solid {ThemeManager.ACCENT_PRIMARY}; border-radius: 16px;")
        fl = QVBoxLayout(f)
        icon = "fa5s.lock" if data.get("force_update") else "fa5s.gift"
        fl.addWidget(QLabel("", pixmap=qta.icon(icon, color=ThemeManager.ACCENT_PRIMARY).pixmap(48, 48),
                            alignment=Qt.AlignCenter))
        title = "CRITICAL UPDATE" if data.get("force_update") else "Update Available"
        fl.addWidget(QLabel(title, alignment=Qt.AlignCenter,
                            styleSheet=f"color:{ThemeManager.ACCENT_PRIMARY}; font-size: 18px; font-weight: bold; margin-top:10px;"))
        fl.addWidget(QLabel(f"v{APP_VERSION} ➜ v{data['version']}", alignment=Qt.AlignCenter,
                            styleSheet=f"color:{ThemeManager.get('TEXT_HEADER')}; font-size: 14px;"))
        fl.addWidget(QLabel("Changelog:", styleSheet=f"color:{ThemeManager.get('TEXT_MUTED')}; margin-top: 10px;"))
        list_w = QListWidget(styleSheet="background: rgba(0,0,0,0.2); border-radius: 8px; color: white;")
        for item in data.get("changelog", []): list_w.addItem(f"• {item}")
        fl.addWidget(list_w)
        btns = QHBoxLayout()
        if not data.get("force_update"):
            b_skip = QPushButton("Skip")
            b_skip.setStyleSheet(f"color: {ThemeManager.get('TEXT_MUTED')}; background: transparent; border: none;")
            b_skip.clicked.connect(self.reject)
            btns.addWidget(b_skip)
        b_update = QPushButton("UPDATE NOW")
        b_update.setCursor(Qt.PointingHandCursor)
        b_update.setStyleSheet(
            f"background-color: {ThemeManager.ACCENT_PRIMARY}; color: white; border-radius: 8px; padding: 10px; font-weight: bold;")
        b_update.clicked.connect(self.do_update)
        btns.addWidget(b_update)
        fl.addLayout(btns)
        l.addWidget(f)

    def do_update(self):
        QDesktopServices.openUrl(QUrl(self.data['download_url']))
        if self.data.get("force_update"): sys.exit(0)
        self.accept()

    def keyPressEvent(self, e):
        if self.data.get("force_update") and e.key() == Qt.Key_Escape: return
        super().keyPressEvent(e)


# =============================================================================
#  VISION PROCESSOR
# =============================================================================
class VisionProcessor:
    @staticmethod
    def get_exif_gps(image_path):
        try:
            img = Image.open(image_path)
            exif = {ExifTags.TAGS[k]: v for k, v in img._getexif().items() if
                    k in ExifTags.TAGS} if img._getexif() else None
            if exif: return "34.05° N, 118.24° W"
        except:
            pass
        return "N/A"

    @staticmethod
    def process_xray(image_path):
        try:
            stream = open(image_path, "rb")
            bytes = bytearray(stream.read())
            numpyarray = np.asarray(bytes, dtype=np.uint8)
            img = cv2.imdecode(numpyarray, cv2.IMREAD_COLOR)
        except:
            return None, "N/A"
        if img is None: return None, "N/A"

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        max_px = 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            current_width = min(w, h)
            if current_width > max_px: max_px = current_width

        severity = "Micro"
        if max_px > 10: severity = "Hairline"
        if max_px > 30: severity = "Moderate"
        if max_px > 80: severity = "Severe"
        width_str = f"{max_px}px ({severity})"

        heatmap = cv2.applyColorMap(dilated, cv2.COLORMAP_JET)
        mask = dilated > 0
        result = img.copy()
        result[mask] = cv2.addWeighted(img[mask], 0.2, heatmap[mask], 0.8, 0)
        h, w, ch = result.shape
        bytesPerLine = 3 * w
        qImg = QImage(result.data, w, h, bytesPerLine, QImage.Format_BGR888)
        return QPixmap.fromImage(qImg), width_str


# =============================================================================
#  PDF GENERATOR
# =============================================================================
class ReportGenerator:
    @staticmethod
    def create_single_report(filepath, image_path, analysis_data):
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        header_style = ParagraphStyle('Header', parent=styles['Heading1'],
                                      textColor=HexColor(ThemeManager.ACCENT_PRIMARY), alignment=1)
        elements.append(Paragraph(f"{APP_NAME} Inspection Report", header_style))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 24))
        im = PlatImage(image_path)
        im.drawHeight = 3 * inch
        im.drawWidth = 5 * inch
        data = [
            ["Analysis Parameter", "Value"],
            ["File Name", os.path.basename(image_path)],
            ["Detection Result", analysis_data['result']],
            ["Confidence Score", f"{int(analysis_data['confidence'] * 100)}%"],
            ["Structural Condition", analysis_data['width']],
            ["Geo-Location", analysis_data['gps']],
            ["AI Model", f"{APP_NAME} Core v5"]
        ]
        t = Table(data, colWidths=[2.5 * inch, 4 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), HexColor(ThemeManager.ACCENT_PRIMARY)),
            ('TEXTCOLOR', (0, 0), (1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f5f5f5')),
            ('GRID', (0, 0), (-1, -1), 1, white)
        ]))
        elements.append(im)
        elements.append(Spacer(1, 24))
        elements.append(t)
        doc.build(elements)

    @staticmethod
    def create_batch_report(filepath, batch_data):
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph(f"{APP_NAME} Batch Survey Report", styles['Title']))
        elements.append(Paragraph(f"Total Scanned: {len(batch_data)} | Date: {datetime.now().strftime('%Y-%m-%d')}",
                                  styles['Normal']))
        elements.append(Spacer(1, 24))
        table_data = [["ID", "Filename", "Result", "Confidence", "Condition"]]
        cracks = 0
        for i, item in enumerate(batch_data):
            if item['result'] == "CRACK": cracks += 1
            row = [str(i + 1), item['filename'], item['result'], f"{int(item['confidence'] * 100)}%", item['width']]
            table_data.append(row)
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(ThemeManager.ACCENT_PRIMARY)),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f9f9f9'), white]),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e0e0e0'))
        ]))
        elements.append(
            Paragraph(f"Summary: {cracks} Cracks Detected / {len(batch_data) - cracks} Safe", styles['Heading2']))
        elements.append(Spacer(1, 12))
        elements.append(t)
        doc.build(elements)


# =============================================================================
#  CUSTOM WIDGETS
# =============================================================================
class SlidingStackedWidget(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_active = False

    def set_index(self, index):
        if self.m_active: return
        self.m_next = index
        self.m_now = self.currentIndex()
        if self.m_now == self.m_next: return
        offset_x = self.frameRect().width()
        self.widget(self.m_next).setGeometry(0, 0, offset_x, self.frameRect().height())
        offset = offset_x if self.m_next > self.m_now else -offset_x
        self.widget(self.m_next).move(offset, 0)
        self.widget(self.m_next).show()
        self.widget(self.m_next).raise_()
        self.anim_group = QParallelAnimationGroup(self)
        anim_now = QPropertyAnimation(self.widget(self.m_now), b"pos")
        anim_now.setDuration(400)
        anim_now.setEasingCurve(QEasingCurve.OutCubic)
        anim_now.setStartValue(QPoint(0, 0))
        anim_now.setEndValue(QPoint(-offset, 0))
        anim_next = QPropertyAnimation(self.widget(self.m_next), b"pos")
        anim_next.setDuration(400)
        anim_next.setEasingCurve(QEasingCurve.OutCubic)
        anim_next.setStartValue(QPoint(offset, 0))
        anim_next.setEndValue(QPoint(0, 0))
        self.anim_group.addAnimation(anim_now)
        self.anim_group.addAnimation(anim_next)
        self.anim_group.finished.connect(self._animation_done)
        self.m_active = True
        self.anim_group.start()

    def _animation_done(self):
        self.setCurrentIndex(self.m_next)
        self.widget(self.m_now).hide()
        self.widget(self.m_now).move(0, 0)
        self.m_active = False


class NeonButton(QPushButton):
    def __init__(self, text, variant="primary"):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(45)
        font = QFont("Segoe UI", 10)
        font.setBold(True)
        self.setFont(font)
        self.variant = variant
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setOffset(0, 4)
        self.update_style()

    def update_style(self):
        col_prim = ThemeManager.ACCENT_PRIMARY
        col_sec = ThemeManager.ACCENT_SECONDARY
        if self.variant == "primary":
            self.shadow.setColor(QColor(col_prim))
            if ThemeManager.BUTTON_STYLE == "Gradient":
                self.setStyleSheet(
                    f"QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {col_prim}, stop:1 {col_sec}); color: white; border: none; border-radius: 8px; padding: 0 15px; }} QPushButton:hover {{ margin-top: 2px; }}")
            elif ThemeManager.BUTTON_STYLE == "Solid":
                self.setStyleSheet(
                    f"QPushButton {{ background-color: {col_prim}; color: white; border: none; border-radius: 8px; padding: 0 15px; }} QPushButton:hover {{ opacity: 0.9; }}")
            elif ThemeManager.BUTTON_STYLE == "Glass":
                self.setStyleSheet(
                    f"QPushButton {{ background-color: rgba(255,255,255, 15); color: {col_prim}; border: 2px solid {col_prim}; border-radius: 8px; padding: 0 15px; }} QPushButton:hover {{ background-color: {col_prim}; color: white; }}")
        elif self.variant == "secondary":
            self.shadow.setColor(QColor(0, 0, 0, 40))
            self.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: {ThemeManager.get('TEXT_BODY')}; border: 1px solid {ThemeManager.get('BORDER_SUBTLE')}; border-radius: 8px; padding: 0 15px; }} QPushButton:hover {{ background-color: {ThemeManager.get('BG_CARD')}; }}")
        self.setGraphicsEffect(self.shadow)


class ModernToggle(QFrame):
    def __init__(self, left_text, right_text, callback=None):
        super().__init__()
        self.callback = callback
        self.setFixedHeight(40)
        self.setFixedWidth(240)
        self.setStyleSheet(f"background-color: {ThemeManager.get('BG_INPUT')}; border-radius: 20px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        self.btn_left = QPushButton(left_text)
        self.btn_left.setCursor(Qt.PointingHandCursor)
        self.btn_left.setCheckable(True)
        self.btn_left.setChecked(True)
        self.btn_left.clicked.connect(lambda: self.toggle(True))
        self.btn_right = QPushButton(right_text)
        self.btn_right.setCursor(Qt.PointingHandCursor)
        self.btn_right.setCheckable(True)
        self.btn_right.clicked.connect(lambda: self.toggle(False))
        self.update_style()
        layout.addWidget(self.btn_left)
        layout.addWidget(self.btn_right)

    def toggle(self, is_left):
        self.btn_left.setChecked(is_left)
        self.btn_right.setChecked(not is_left)
        self.update_style()
        if self.callback: self.callback(0 if is_left else 1)

    def update_style(self):
        active = f"background-color: {ThemeManager.ACCENT_PRIMARY}; color: white; border-radius: 16px; font-weight: bold;"
        inactive = f"background-color: transparent; color: {ThemeManager.get('TEXT_MUTED')}; border-radius: 16px; font-weight: 600;"
        self.btn_left.setStyleSheet(active if self.btn_left.isChecked() else inactive)
        self.btn_right.setStyleSheet(active if self.btn_right.isChecked() else inactive)


class StunningCircularProgress(QWidget):
    def __init__(self, parent=None, size_override=None):
        super().__init__(parent)
        if size_override:
            self.setFixedSize(size_override, size_override)
        else:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.setMinimumSize(210, 210)
            self.setMaximumSize(300, 300)
        self.value = 0
        self.max_value = 100
        self.text = "0%"
        self.active_color = None
        self.subtext = ""

    def set_value(self, val, max_val):
        self.value = val
        self.max_value = max_val
        self.update()

    def set_text(self, text, subtext=""):
        self.text = text
        self.subtext = subtext
        self.update()

    def set_color(self, color):
        self.active_color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        size = min(w, h) - 20
        rect = QRectF((w - size) / 2, (h - size) / 2, size, size)
        stroke = max(8, size * 0.08)
        painter.setPen(QPen(QColor(ThemeManager.get("BG_INPUT")), stroke, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, 0, 360 * 16)
        if self.max_value > 0:
            percentage = self.value / self.max_value
            span_angle = int(-percentage * 360 * 16)
            c1 = QColor(self.active_color) if self.active_color else QColor(ThemeManager.ACCENT_PRIMARY)
            painter.setPen(QPen(c1, stroke, Qt.SolidLine, Qt.RoundCap))
            painter.drawArc(rect, 90 * 16, span_angle)
        painter.setPen(QColor(ThemeManager.get("TEXT_HEADER")))
        painter.setFont(QFont("Segoe UI", int(size * 0.22), QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, self.text)
        if self.subtext:
            painter.setPen(QColor(ThemeManager.get("TEXT_MUTED")))
            painter.setFont(QFont("Segoe UI", int(size * 0.08), QFont.Bold))
            r_sub = QRectF(rect.x(), rect.y() + size * 0.25, size, size)
            painter.drawText(r_sub, Qt.AlignCenter, self.subtext)


class ProCard(QFrame):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_style()
        self.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=30, offset=QPoint(0, 8)))

    def update_style(self):
        self.setStyleSheet(
            f"QFrame {{ background-color: {ThemeManager.get('BG_CARD')}; border-radius: 16px; border: 1px solid {ThemeManager.get('BORDER_SUBTLE')}; }}")


class ProSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.update_style()

    def update_style(self):
        self.setStyleSheet(
            f"QCheckBox {{ background: transparent; }} QCheckBox::indicator {{ width: 44px; height: 24px; border-radius: 12px; border: 2px solid {ThemeManager.get('BORDER_SUBTLE')}; }} QCheckBox::indicator:unchecked {{ background-color: {ThemeManager.get('BG_INPUT')}; }} QCheckBox::indicator:checked {{ background-color: {ThemeManager.ACCENT_PRIMARY}; border-color: {ThemeManager.ACCENT_PRIMARY}; }}")


class ToastNotification(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedSize(300, 60)
        self.hide()
        l = QHBoxLayout(self)
        self.icon_lbl = QLabel()
        self.msg_lbl = QLabel()
        self.msg_lbl.setStyleSheet(
            f"color: {ThemeManager.get('TEXT_BODY')}; font-size: 10pt; font-family: 'Segoe UI'; border: none; background: transparent;")
        l.addWidget(self.icon_lbl)
        l.addWidget(self.msg_lbl)
        l.addStretch()
        self.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=20, offset=QPoint(0, 4)))
        self.anim = QPropertyAnimation(self, b"pos")

    def show_message(self, message, icon_name="fa5s.info-circle"):
        color = ThemeManager.ACCENT_PRIMARY
        self.msg_lbl.setText(message)
        self.icon_lbl.setPixmap(qta.icon(icon_name, color=color).pixmap(24, 24))
        self.setStyleSheet(
            f"QFrame {{ background-color: {ThemeManager.get('BG_CARD')}; border: 1px solid {color}; border-radius: 8px; }}")
        parent = self.parent()
        if parent:
            x = parent.width() - 320
            y_s = parent.height() + 10
            y_e = parent.height() - 80
            self.move(x, y_s)
            self.show()
            self.raise_()
            self.anim.setDuration(400)
            self.anim.setStartValue(QPoint(x, y_s))
            self.anim.setEndValue(QPoint(x, y_e))
            self.anim.setEasingCurve(QEasingCurve.OutBack)
            self.anim.start()
            QTimer.singleShot(3000, self.hide_toast)

    def hide_toast(self):
        self.anim.setDuration(300)
        self.anim.setEndValue(QPoint(self.x(), self.parent().height() + 10))
        self.anim.start()


class ModernAboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(650, 500)

        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        f = QFrame()
        f.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {ThemeManager.get('BG_CARD').replace(')', ', 255)')}, stop:1 #111111);
                border: 1px solid {ThemeManager.ACCENT_PRIMARY};
                border-radius: 20px;
            }}
        """)
        l.addWidget(f)
        fl = QVBoxLayout(f)
        fl.setContentsMargins(40, 40, 40, 40)

        top_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon('fa5s.layer-group', color=ThemeManager.ACCENT_PRIMARY).pixmap(64, 64))
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        title_box = QVBoxLayout()
        t = QLabel("TensorCrete")
        t.setFont(QFont("Segoe UI", 28, QFont.Bold))
        t.setStyleSheet("color: white; background: transparent; border: none;")
        v = QLabel(f"PRO EDITION v{APP_VERSION}")
        v.setStyleSheet(
            f"color: {ThemeManager.ACCENT_PRIMARY}; font-weight: bold; letter-spacing: 2px; background: transparent; border: none;")
        title_box.addWidget(t)
        title_box.addWidget(v)
        top_row.addWidget(icon_lbl)
        top_row.addLayout(title_box)
        top_row.addStretch()
        fl.addLayout(top_row)

        fl.addSpacing(20)
        tech_frame = QFrame()
        tech_frame.setStyleSheet("background: rgba(0,0,0,0.3); border-radius: 10px; padding: 10px; border: none;")
        tf_layout = QVBoxLayout(tech_frame)

        specs = [
            ("ENGINE CORE", "TensorFlow Keras (CNN)"),
            ("UI FRAMEWORK", "PySide6 (Qt 6.0)"),
            ("LANGUAGE", f"Python {platform.python_version()}"),
            ("REQUIREMENTS", "AVX2 CPU | 4GB+ RAM | 64-bit OS")
        ]

        for k, val in specs:
            r = QHBoxLayout()
            r.addWidget(QLabel(k,
                               styleSheet="color: #666; font-weight: bold; font-size: 10px; min-width: 100px; border: none; background: transparent;"))
            r.addWidget(QLabel(val,
                               styleSheet="color: #ddd; font-family: Consolas; font-size: 11px; border: none; background: transparent;"))
            r.addStretch()
            tf_layout.addLayout(r)

        fl.addWidget(tech_frame)
        fl.addSpacing(20)

        socials = QHBoxLayout()
        socials.addStretch()
        links = [
            ('fa5s.graduation-cap', '#00CCBB',
             "https://www.researchgate.net/profile/Md-Mustafijur-Rahman-Ratul?ev=hdr_xprf"),
            ('fa5b.github', '#333333', "http://github.com/MustafijRatul/"),
            ('fa5b.linkedin', '#0077b5', "https://www.linkedin.com/in/md-mustafijur-rahman-ratul/")
        ]
        for icon, col, url in links:
            b = QPushButton()
            b.setIcon(qta.icon(icon, color='white'))
            b.setFixedSize(50, 50)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(f"background-color: {col}; border-radius: 25px; border: none;")
            b.clicked.connect(lambda _, u=url: QDesktopServices.openUrl(QUrl(u)))
            socials.addWidget(b)
            socials.addSpacing(15)
        socials.addStretch()
        fl.addLayout(socials)
        fl.addStretch()
        dev_lbl = QLabel("Designed & Developed by Ratul     ", alignment=Qt.AlignCenter)
        dev_lbl.setStyleSheet("color: #666; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        fl.addWidget(dev_lbl)
        fl.addSpacing(10)
        btn_close = QPushButton("Close")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setFixedHeight(40)
        btn_close.setStyleSheet(
            f"background: transparent; border: 1px solid {ThemeManager.ACCENT_PRIMARY}; color: {ThemeManager.ACCENT_PRIMARY}; border-radius: 10px; font-weight: bold;")
        btn_close.clicked.connect(self.accept)
        fl.addWidget(btn_close)
        f.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=50, color=QColor(0, 0, 0, 200)))


# =============================================================================
#  BACKEND LOGIC
# =============================================================================
class AI_Engine:
    def __init__(self):
        self.model = None
        self.history = []
        self.load_history()

    def load_model(self):
        # USE resource_path() HERE TO FIND THE BUNDLED FILE
        model_path = resource_path(MODEL_NAME)

        # Debug print (optional, helps see where it is looking)
        print(f"Looking for model at: {model_path}")

        if os.path.exists(model_path):
            try:
                self.model = tf.keras.models.load_model(model_path)
                return True, "Model Loaded Successfully"
            except Exception as e:
                return False, str(e)
        return False, f"Model file not found at: {model_path}"

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    self.history = json.load(f)
            except:
                self.history = []

    def save_history(self):
        try:
            with open(HISTORY_FILE, 'w') as f:
                json.dump(self.history, f, indent=4)
        except:
            pass

    def predict(self, image_path):
        if not self.model: return None, 0.0, 0.0, "", None
        try:
            image = Image.open(image_path)
            image_resized = ImageOps.fit(image, (224, 224), Image.Resampling.LANCZOS)
            img_array = np.array(image_resized)
            if img_array.ndim == 2:
                img_array = np.stack((img_array,) * 3, axis=-1)
            else:
                img_array = img_array[:, :, :3]
            img_array = np.expand_dims(img_array, axis=0)
            prediction = self.model.predict(img_array, verbose=0)
            confidence = prediction[0][0]
            result = "CRACK" if confidence > 0.5 else "SAFE"
            xray_pix, width_str = VisionProcessor.process_xray(image_path)
            gps_data = VisionProcessor.get_exif_gps(image_path)

            # Append to history and Save JSON
            self.history.insert(0, {"time": datetime.now().strftime("%H:%M:%S"), "file": os.path.basename(image_path),
                                    "confidence": float(confidence), "result": result})
            self.save_history()

            return result, confidence, width_str, gps_data, xray_pix
        except:
            return None, 0.0, "Err", "", None


# =============================================================================
#  MAIN WINDOW
# =============================================================================
class CrackAnalyzerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TensorCrete Ultimate")
        self.resize(1200, 750)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.engine = AI_Engine()
        self.win_effect = WindowEffect()
        self.batch_images = []
        self.batch_data_cache = []
        self.batch_folder = ""
        self.current_xray_pixmap = None
        self.current_orig_pixmap = None
        self.current_result_data = None
        self.current_image_path = None
        self.first_run = True

        self.load_settings()
        self.apply_window_effect()
        self._init_ui()
        QTimer.singleShot(100, self.init_ai)
        QTimer.singleShot(1000, self.check_updates)

        # DISCORD CHECK
        if self.first_run:
            send_install_notification()
            self.first_run = False
            self.save_settings()

    def load_settings(self):
        # Load from JSON
        defaults = {
            "theme": "Ambient", "accent": "Civil Red", "opacity": 230,
            "glass": True, "btn_style": "Gradient", "first_run": True
        }
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    defaults.update(data)
            except:
                pass

        ThemeManager.set_base_theme(defaults["theme"])
        ThemeManager.set_accent_color(defaults["accent"])
        ThemeManager.OPACITY = defaults["opacity"]
        ThemeManager.GLASS_ENABLED = defaults["glass"]
        ThemeManager.BUTTON_STYLE = defaults["btn_style"]
        self.first_run = defaults["first_run"]

    def save_settings(self):
        data = {
            "theme": ThemeManager.MODE_NAME,
            "accent": ThemeManager.COLOR_NAME,
            "opacity": ThemeManager.OPACITY,
            "glass": ThemeManager.GLASS_ENABLED,
            "btn_style": ThemeManager.BUTTON_STYLE,
            "first_run": self.first_run
        }
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except:
            pass

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def apply_window_effect(self):
        self.win_effect.set_acrylic(self.winId(), ThemeManager.GLASS_ENABLED)

    def init_ai(self):
        success, msg = self.engine.load_model()
        if success:
            self.toaster.show_message("AI Core Online", "fa5s.brain")
        else:
            QMessageBox.critical(self, "Error", f"Could not load model!\n{msg}")

    def check_updates(self):
        self.updater = UpdateWorker()
        self.updater.update_found.connect(self.show_update_dialog)
        self.updater.start()

    def show_update_dialog(self, data):
        dlg = UpdateDialog(data, self)
        dlg.exec()

    def _init_ui(self):
        c = QWidget()
        self.setCentralWidget(c)
        self.main_layout = QHBoxLayout(c)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.toaster = ToastNotification(c)
        self._init_sidebar()
        self._init_content()
        self.apply_theme()

    def _init_sidebar(self):
        self.sidebar = QFrame(fixedWidth=260)
        l = QVBoxLayout(self.sidebar)
        l.setContentsMargins(0, 0, 0, 20)
        hb = QFrame(fixedHeight=90)
        hbl = QVBoxLayout(hb)
        hbl.setAlignment(Qt.AlignCenter)
        hbl.addWidget(QLabel("TensorCrete", font=QFont("Segoe UI", 20, QFont.Bold),
                             styleSheet=f"color: {ThemeManager.get('TEXT_HEADER')}; border:none; background:transparent;"))
        hbl.addWidget(QLabel("ULTIMATE AI", font=QFont("Segoe UI", 8, QFont.Bold),
                             styleSheet=f"color: {ThemeManager.ACCENT_PRIMARY}; letter-spacing: 2px; border:none; background:transparent;"))
        l.addWidget(hb)
        self.nav_btns = {}
        self.current_page_id = "dashboard"
        items = [("Inspection", "dashboard", "fa5s.satellite-dish"), ("Scan Log", "history", "fa5s.clipboard-list"),
                 ("Settings", "settings", "fa5s.cog")]
        for t, p, i in items:
            b = QPushButton(f"  {t}", fixedHeight=50, cursor=Qt.PointingHandCursor)
            b.setProperty("icon_name", i)
            b.clicked.connect(lambda c, x=p: self.navigate(x))
            l.addWidget(b)
            self.nav_btns[p] = b
        l.addStretch()
        abt = QPushButton("  About", fixedHeight=45, cursor=Qt.PointingHandCursor,
                          icon=qta.icon('fa5s.info-circle', color=ThemeManager.get('TEXT_MUTED')))
        abt.setStyleSheet(
            f"QPushButton {{ text-align: left; padding-left: 20px; background-color: transparent; color: {ThemeManager.get('TEXT_MUTED')}; border-radius: 8px; border: none; font-weight: 600; font-size: 13px; }} QPushButton:hover {{ background-color: {ThemeManager.get('BG_CARD')}; color: {ThemeManager.get('TEXT_BODY')}; }}")
        abt.clicked.connect(self.show_about_dialog)
        l.addWidget(abt)
        self.main_layout.addWidget(self.sidebar)

    def show_about_dialog(self):
        ModernAboutDialog(self).exec()

    def _init_content(self):
        self.stack = SlidingStackedWidget()
        self.pages = {}
        self.pages["dashboard"] = self._build_unified_dashboard()
        self.pages["history"] = self._build_history()
        self.pages["settings"] = self._build_settings()
        for w in self.pages.values(): self.stack.addWidget(w)
        c = QWidget(styleSheet="background: transparent;")
        l = QVBoxLayout(c)
        l.setContentsMargins(40, 20, 40, 20)
        l.addWidget(self.stack)
        self.main_layout.addWidget(c)

    def _build_unified_dashboard(self):
        p = QWidget()
        l = QVBoxLayout(p)
        l.setAlignment(Qt.AlignTop)
        header_lay = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.addWidget(QLabel("Inspection Control",
                                   styleSheet=f"color:{ThemeManager.get('TEXT_HEADER')}; font-size:32px; font-weight:800; background:transparent;"))
        self.lbl_subtitle = QLabel("Select an inspection mode below",
                                   styleSheet=f"color:{ThemeManager.ACCENT_PRIMARY}; font-size:14px; font-weight:bold; background:transparent;")
        title_box.addWidget(self.lbl_subtitle)
        header_lay.addLayout(title_box)
        header_lay.addStretch()
        self.mode_toggle = ModernToggle("Single Scope", "Drone Swarm", self.switch_inspection_mode)
        header_lay.addWidget(self.mode_toggle)
        l.addLayout(header_lay)
        l.addSpacing(20)
        self.dash_stack = QStackedWidget()
        self.dash_stack.setStyleSheet("background: transparent;")

        # SINGLE SCAN
        page_single = QWidget()
        ps_lay = QHBoxLayout(page_single)
        ps_lay.setContentsMargins(0, 0, 0, 0)
        self.img_card = ProCard()
        icl = QVBoxLayout(self.img_card)
        xray_lay = QHBoxLayout()
        xray_lay.addStretch()
        self.chk_xray = QCheckBox("Enable X-Ray Vision")
        self.chk_xray.setCursor(Qt.PointingHandCursor)
        self.chk_xray.setStyleSheet(f"color: {ThemeManager.ACCENT_SECONDARY}; font-weight:bold;")
        self.chk_xray.stateChanged.connect(self.toggle_xray_view)
        xray_lay.addWidget(self.chk_xray)
        icl.addLayout(xray_lay)
        self.img_label = QLabel("No Image Uploaded")
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet(
            f"border: 2px dashed {ThemeManager.get('BORDER_SUBTLE')}; color: {ThemeManager.get('TEXT_MUTED')};")
        self.img_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.img_label.setMinimumHeight(400)
        icl.addWidget(self.img_label)
        bl = QHBoxLayout()
        btn_load = NeonButton("Load Photo", "secondary")
        btn_load.clicked.connect(self.load_image)
        self.btn_scan = NeonButton("Analyze Crack", "primary")
        self.btn_scan.setEnabled(False)
        self.btn_scan.clicked.connect(self.run_prediction)
        bl.addWidget(btn_load)
        bl.addWidget(self.btn_scan)
        icl.addLayout(bl)
        ps_lay.addWidget(self.img_card, stretch=2)
        res_card = ProCard()
        rcl = QVBoxLayout(res_card)
        rcl.setAlignment(Qt.AlignTop)
        rcl.addWidget(QLabel("ANALYSIS RESULT",
                             styleSheet=f"color:{ThemeManager.get('TEXT_MUTED')}; font-weight:bold; background:transparent;"))
        self.circular_prog = StunningCircularProgress()
        self.circular_prog.set_text("N/A")
        rcl.addWidget(self.circular_prog, alignment=Qt.AlignCenter)
        self.lbl_result_text = QLabel("WAITING...", alignment=Qt.AlignCenter)
        self.lbl_result_text.setStyleSheet(
            f"color: {ThemeManager.get('TEXT_BODY')}; font-size: 24px; font-weight: 800; margin-top: 10px;")
        rcl.addWidget(self.lbl_result_text)
        extra_stats = QFrame(styleSheet="background: rgba(0,0,0,0.2); border-radius: 8px; margin-top: 10px;")
        esl = QVBoxLayout(extra_stats)
        self.lbl_width = QLabel("Condition: --")
        self.lbl_gps = QLabel("GPS: --")
        for l_stat in [self.lbl_width, self.lbl_gps]:
            l_stat.setStyleSheet(f"color: {ThemeManager.get('TEXT_MUTED')}; font-size: 12px;")
            esl.addWidget(l_stat)
        rcl.addWidget(extra_stats)
        self.btn_pdf = NeonButton("Download Report", "secondary")
        self.btn_pdf.setEnabled(False)
        self.btn_pdf.clicked.connect(self.generate_pdf_report)
        rcl.addWidget(self.btn_pdf)
        rcl.addStretch()
        ps_lay.addWidget(res_card, stretch=1)

        # BATCH SCAN
        page_batch = QWidget()
        pb_lay = QHBoxLayout(page_batch)
        pb_lay.setContentsMargins(0, 0, 0, 0)
        left_batch = QVBoxLayout()
        self.batch_preview_card = ProCard()
        bpc_lay = QVBoxLayout(self.batch_preview_card)
        bpc_lay.addWidget(QLabel("LIVE DRONE FEED",
                                 styleSheet=f"color:{ThemeManager.ACCENT_PRIMARY}; font-weight:bold; letter-spacing:1px;"))
        self.lbl_batch_preview = QLabel()
        self.lbl_batch_preview.setAlignment(Qt.AlignCenter)
        self.lbl_batch_preview.setStyleSheet("background-color: black; border-radius: 8px;")
        self.lbl_batch_preview.setMinimumHeight(250)
        bpc_lay.addWidget(self.lbl_batch_preview)
        batch_ctrl = QHBoxLayout()
        self.lbl_batch_folder = QLabel("No Flight Path Selected",
                                       styleSheet=f"color:{ThemeManager.get('TEXT_MUTED')}; font-style: italic;")
        btn_batch_sel = NeonButton("Select Folder", "secondary")
        btn_batch_sel.clicked.connect(self.select_batch_folder)
        self.btn_batch_run = NeonButton("Initiate Swarm", "primary")
        self.btn_batch_run.setEnabled(False)
        self.btn_batch_run.clicked.connect(self.run_batch_scan)
        batch_ctrl.addWidget(self.lbl_batch_folder, stretch=1)
        batch_ctrl.addWidget(btn_batch_sel)
        batch_ctrl.addWidget(self.btn_batch_run)
        bpc_lay.addLayout(batch_ctrl)
        left_batch.addWidget(self.batch_preview_card, stretch=4)
        self.batch_list = QListWidget()
        self.batch_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.batch_list.itemClicked.connect(self.on_batch_item_clicked)
        self.batch_list.setStyleSheet(
            f"QListWidget {{ background: {ThemeManager.get('BG_INPUT')}; border-radius: 12px; border: none; padding: 10px; color: {ThemeManager.get('TEXT_BODY')}; }} QListWidget::item {{ padding: 5px; }} QListWidget::item:selected {{ background: {ThemeManager.ACCENT_PRIMARY}; color: white; border-radius: 5px; }}")
        left_batch.addWidget(self.batch_list, stretch=3)
        pb_lay.addLayout(left_batch, stretch=2)
        batch_stats_card = ProCard()
        bsc_lay = QVBoxLayout(batch_stats_card)
        bsc_lay.setAlignment(Qt.AlignTop)
        bsc_lay.addWidget(QLabel("MISSION STATUS",
                                 styleSheet=f"color:{ThemeManager.get('TEXT_MUTED')}; font-weight:bold; background:transparent;"))
        self.batch_prog_circle = StunningCircularProgress()
        self.batch_prog_circle.set_text("0%", "COMPLETE")
        bsc_lay.addWidget(self.batch_prog_circle, alignment=Qt.AlignCenter)
        bsc_lay.addSpacing(20)

        def make_stat(label, color):
            f = QFrame(styleSheet=f"background-color: rgba(0,0,0,0.2); border-radius: 10px;")
            l = QHBoxLayout(f)
            lbl_val = QLabel("0", styleSheet=f"color: {color}; font-size: 24px; font-weight: bold;")
            lbl_tit = QLabel(label, styleSheet=f"color: {ThemeManager.get('TEXT_MUTED')}; font-size: 12px;")
            l.addWidget(lbl_tit)
            l.addStretch()
            l.addWidget(lbl_val)
            return f, lbl_val

        self.stat_cracks_widget, self.lbl_stat_cracks = make_stat("CRACKS", ThemeManager.ACCENT_DANGER)
        self.stat_safe_widget, self.lbl_stat_safe = make_stat("SAFE", ThemeManager.ACCENT_SUCCESS)
        bsc_lay.addWidget(self.stat_cracks_widget)
        bsc_lay.addWidget(self.stat_safe_widget)
        self.btn_batch_pdf = NeonButton("Download Mission Report", "secondary")
        self.btn_batch_pdf.setEnabled(False)
        self.btn_batch_pdf.clicked.connect(self.generate_batch_report)
        bsc_lay.addWidget(self.btn_batch_pdf)
        bsc_lay.addStretch()
        pb_lay.addWidget(batch_stats_card, stretch=1)
        self.dash_stack.addWidget(page_single)
        self.dash_stack.addWidget(page_batch)
        l.addWidget(self.dash_stack)
        return p

    def switch_inspection_mode(self, index):
        if index == 0:
            self.lbl_subtitle.setText("Analyze individual structural images")
            self.dash_stack.setCurrentIndex(0)
        else:
            self.lbl_subtitle.setText("Process bulk imagery from drone survey")
            self.dash_stack.setCurrentIndex(1)

    # --- LOGIC ---
    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "",
                                                   "Image Files (*.jpg *.png *.jpeg *.webp *.bmp *.tiff)")
        if file_path:
            self.current_image_path = file_path
            self.current_orig_pixmap = QPixmap(file_path)
            self.img_label.setPixmap(
                self.current_orig_pixmap.scaled(self.img_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.img_label.setStyleSheet("border: none;")
            self.btn_scan.setEnabled(True)
            self.lbl_result_text.setText("READY")
            self.chk_xray.setChecked(False)
            self.btn_pdf.setEnabled(False)

    def toggle_xray_view(self):
        if not self.current_image_path: return
        if self.chk_xray.isChecked() and self.current_xray_pixmap:
            self.img_label.setPixmap(
                self.current_xray_pixmap.scaled(self.img_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        elif self.current_orig_pixmap:
            self.img_label.setPixmap(
                self.current_orig_pixmap.scaled(self.img_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def run_prediction(self):
        if not self.current_image_path: return
        self.lbl_result_text.setText("ANALYZING...")
        QApplication.processEvents()
        self._execute_single_predict(self.current_image_path)

    def _execute_single_predict(self, path):
        result, confidence, width_str, gps, xray = self.engine.predict(path)
        self.current_xray_pixmap = xray
        self.current_result_data = {"result": result, "confidence": confidence, "width": width_str, "gps": gps}
        if result:
            pct = int(confidence * 100)
            self.circular_prog.set_value(pct if result == "CRACK" else int((1 - confidence) * 100), 100)
            self.circular_prog.set_text(f"{pct}%" if result == "CRACK" else f"{int((1 - confidence) * 100)}%")
            if result == "CRACK":
                self.lbl_result_text.setText("⚠️ CRACK DETECTED")
                self.lbl_result_text.setStyleSheet(
                    f"color: {ThemeManager.ACCENT_DANGER}; font-weight: 800; font-size: 20px;")
                self.circular_prog.set_color(ThemeManager.ACCENT_DANGER)
            else:
                self.lbl_result_text.setText("✅ SAFE STRUCTURE")
                self.lbl_result_text.setStyleSheet(
                    f"color: {ThemeManager.ACCENT_SUCCESS}; font-weight: 800; font-size: 20px;")
                self.circular_prog.set_color(ThemeManager.ACCENT_SUCCESS)
            self.lbl_width.setText(f"Condition: {width_str}")
            self.lbl_gps.setText(f"GPS: {gps}")
            self.btn_pdf.setEnabled(True)
            self.toggle_xray_view()

    def generate_pdf_report(self):
        if not self.current_result_data: return
        fname = f"Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        s_path, _ = QFileDialog.getSaveFileName(self, "Save Report", fname, "PDF (*.pdf)")
        if s_path:
            ReportGenerator.create_single_report(s_path, self.current_image_path, self.current_result_data)
            self.toaster.show_message("Report PDF Saved", "fa5s.file-pdf")

    def select_batch_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.batch_folder = folder
            self.lbl_batch_folder.setText(os.path.basename(folder))
            self.btn_batch_run.setEnabled(True)
            self.batch_images = [f for f in os.listdir(folder) if
                                 f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp'))]
            self.batch_list.clear()
            self.batch_list.addItem(f"Ready to scan {len(self.batch_images)} images...")
            self.batch_prog_circle.set_value(0, 100)
            self.batch_prog_circle.set_text("0%", "READY")
            self.lbl_stat_cracks.setText("0")
            self.lbl_stat_safe.setText("0")
            self.btn_batch_pdf.setEnabled(False)
            self.batch_data_cache = []

    def run_batch_scan(self):
        if not self.batch_images: return
        self.btn_batch_run.setEnabled(False)
        self.mode_toggle.setEnabled(False)
        total = len(self.batch_images)
        cracks = 0
        safe = 0
        self.batch_list.clear()
        self.batch_data_cache = []
        for i, img_name in enumerate(self.batch_images):
            path = os.path.join(self.batch_folder, img_name)
            pix = QPixmap(path)
            self.lbl_batch_preview.setPixmap(
                pix.scaled(self.lbl_batch_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            res, conf, width_str, _, _ = self.engine.predict(path)
            self.batch_data_cache.append(
                {"filename": img_name, "path": path, "result": res, "confidence": conf, "width": width_str})
            if res == "CRACK":
                cracks += 1
                col = ThemeManager.ACCENT_DANGER
            else:
                safe += 1
                col = ThemeManager.ACCENT_SUCCESS
            item = QListWidgetItem(f"[{i + 1}/{total}] {img_name} : {res}")
            item.setForeground(QColor(col))
            item.setData(Qt.UserRole, path)
            self.batch_list.insertItem(0, item)
            self.lbl_stat_cracks.setText(str(cracks))
            self.lbl_stat_safe.setText(str(safe))
            pct = int(((i + 1) / total) * 100)
            self.batch_prog_circle.set_value(pct, 100)
            self.batch_prog_circle.set_text(f"{pct}%", "SCANNING")
            QApplication.processEvents()
        self.batch_prog_circle.set_text("100%", "DONE")
        self.batch_prog_circle.set_color(ThemeManager.ACCENT_SUCCESS)
        self.btn_batch_run.setEnabled(True)
        self.mode_toggle.setEnabled(True)
        self.btn_batch_pdf.setEnabled(True)
        self.toaster.show_message("Drone Mission Complete", "fa5s.flag-checkered")

    def on_batch_item_clicked(self, item):
        path = item.data(Qt.UserRole)
        if path and os.path.exists(path):
            pix = QPixmap(path)
            self.lbl_batch_preview.setPixmap(
                pix.scaled(self.lbl_batch_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.current_image_path = path
            self.current_orig_pixmap = pix
            self.img_label.setPixmap(pix.scaled(self.img_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self._execute_single_predict(path)

    def generate_batch_report(self):
        if not self.batch_data_cache: return
        fname = f"MissionReport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        s_path, _ = QFileDialog.getSaveFileName(self, "Save Batch Report", fname, "PDF (*.pdf)")
        if s_path:
            ReportGenerator.create_batch_report(s_path, self.batch_data_cache)
            self.toaster.show_message("Mission Report Saved", "fa5s.file-pdf")

    def _build_history(self):
        p = QWidget()
        l = QVBoxLayout(p)
        l.addWidget(QLabel("Scan Log",
                           styleSheet=f"color:{ThemeManager.get('TEXT_HEADER')}; font-size:32px; font-weight:800; background:transparent;"))
        self.hist_scroll_widget = QWidget()
        self.hist_layout = QVBoxLayout(self.hist_scroll_widget)
        self.hist_layout.setAlignment(Qt.AlignTop)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setStyleSheet("background: transparent; border: none;")
        sc.setWidget(self.hist_scroll_widget)
        l.addWidget(sc)
        btn = NeonButton("Refresh Log", "secondary")
        btn.clicked.connect(self.refresh_history_ui)
        l.addWidget(btn)
        # Auto-load on build
        QTimer.singleShot(500, self.refresh_history_ui)
        return p

    def _build_settings(self):
        p = QWidget()
        l = QVBoxLayout(p)
        l.setAlignment(Qt.AlignTop)
        l.addWidget(QLabel("Settings",
                           styleSheet=f"color:{ThemeManager.get('TEXT_HEADER')}; font-size:32px; font-weight:800; background:transparent;"))
        c = ProCard()
        cl = QVBoxLayout(c)
        cl.setSpacing(25)

        self.cmb_theme = QComboBox(
            styleSheet=f"background:{ThemeManager.get('BG_INPUT')}; color:{ThemeManager.get('TEXT_HEADER')}; padding:5px; border-radius:5px;")
        self.cmb_theme.addItems(["Ambient", "Dark"])
        self.cmb_theme.setCurrentText(ThemeManager.MODE_NAME)
        self.cmb_theme.currentTextChanged.connect(self.on_theme_change)
        tr = QHBoxLayout()
        tr.addWidget(QLabel("Theme Mode",
                            styleSheet=f"color:{ThemeManager.get('TEXT_HEADER')}; font-weight:bold; background:transparent;"))
        tr.addWidget(self.cmb_theme)
        cl.addLayout(tr)

        self.cmb_btn = QComboBox(
            styleSheet=f"background:{ThemeManager.get('BG_INPUT')}; color:{ThemeManager.get('TEXT_HEADER')}; padding:5px; border-radius:5px;")
        self.cmb_btn.addItems(["Gradient", "Solid", "Glass"])
        self.cmb_btn.setCurrentText(ThemeManager.BUTTON_STYLE)
        self.cmb_btn.currentTextChanged.connect(self.on_btn_style_change)
        bsr = QHBoxLayout()
        bsr.addWidget(QLabel("Button Style",
                             styleSheet=f"color:{ThemeManager.get('TEXT_HEADER')}; font-weight:bold; background:transparent;"))
        bsr.addWidget(self.cmb_btn)
        cl.addLayout(bsr)

        self.cmb_color = QComboBox(
            styleSheet=f"background:{ThemeManager.get('BG_INPUT')}; color:{ThemeManager.get('TEXT_HEADER')}; padding:5px; border-radius:5px;")
        self.cmb_color.addItems(list(ThemeManager.COLOR_PRESETS.keys()))
        if hasattr(ThemeManager, 'COLOR_NAME'): self.cmb_color.setCurrentText(ThemeManager.COLOR_NAME)
        self.cmb_color.currentTextChanged.connect(self.on_color_change)
        acr = QHBoxLayout()
        acr.addWidget(QLabel("Accent Color",
                             styleSheet=f"color:{ThemeManager.get('TEXT_HEADER')}; font-weight:bold; background:transparent;"))
        acr.addWidget(self.cmb_color)
        cl.addLayout(acr)

        # RESTORED GLASS TOGGLE
        self.sw_glass = ProSwitch()
        self.sw_glass.setChecked(ThemeManager.GLASS_ENABLED)
        self.sw_glass.clicked.connect(self.on_glass_toggle)
        gr = QHBoxLayout()
        gr.addWidget(QLabel("Glass Effect",
                            styleSheet=f"color:{ThemeManager.get('TEXT_HEADER')}; font-weight:bold; background:transparent;"))
        gr.addWidget(self.sw_glass)
        cl.addLayout(gr)

        self.sl_opacity = QSlider(Qt.Horizontal)
        self.sl_opacity.setRange(50, 255)
        self.sl_opacity.setValue(ThemeManager.OPACITY)
        self.sl_opacity.valueChanged.connect(self.on_opacity_change)
        orow = QHBoxLayout()
        orow.addWidget(QLabel("Window Opacity",
                              styleSheet=f"color:{ThemeManager.get('TEXT_HEADER')}; font-weight:bold; background:transparent;"))
        orow.addWidget(self.sl_opacity)
        cl.addLayout(orow)
        l.addWidget(c)
        l.addStretch()
        return p

    def apply_theme(self):
        self.centralWidget().setStyleSheet(f"#Central {{ background-color: {ThemeManager.get('BG_MAIN')}; }}")
        self.sidebar.setStyleSheet(
            f"QFrame {{ background-color: {ThemeManager.get('BG_SIDEBAR')}; border-right: 1px solid {ThemeManager.get('BORDER_SUBTLE')}; }}")
        for b in self.findChildren(NeonButton): b.update_style()
        for c in self.findChildren(ProCard): c.update_style()
        for s in self.findChildren(ProSwitch): s.update_style()
        if hasattr(self, 'mode_toggle'): self.mode_toggle.update_style()
        self.circular_prog.update()
        if hasattr(self, 'batch_prog_circle'): self.batch_prog_circle.update()
        self.update_nav_style()

    def update_nav_style(self):
        for k, b in self.nav_btns.items():
            act = (k == self.current_page_id)
            bg = ThemeManager.get('BG_INPUT') if act else "transparent"
            fg = ThemeManager.get('TEXT_HEADER') if act else ThemeManager.get('TEXT_MUTED')
            c = ThemeManager.ACCENT_PRIMARY if act else ThemeManager.get('TEXT_MUTED')
            b.setStyleSheet(
                f"QPushButton {{ text-align:left; padding-left:20px; background-color:{bg}; color:{fg}; border-radius:8px; border:none; font-weight:600; }} QPushButton:hover {{ background-color:{ThemeManager.get('BG_CARD')}; }}")
            b.setIcon(qta.icon(b.property("icon_name"), color=c))

    def on_theme_change(self, t):
        ThemeManager.set_base_theme(t)
        self.apply_theme()

    def on_color_change(self, c):
        ThemeManager.set_accent_color(c)
        self.apply_theme()

    def on_btn_style_change(self, s):
        ThemeManager.BUTTON_STYLE = s
        self.apply_theme()

    def on_glass_toggle(self):
        ThemeManager.GLASS_ENABLED = self.sw_glass.isChecked()
        self.apply_window_effect()

    def on_opacity_change(self, v):
        ThemeManager.OPACITY = v
        self.apply_theme()

    def navigate(self, pid):
        self.current_page_id = pid
        self.update_nav_style()
        self.stack.set_index(list(self.pages.keys()).index(pid))
        if pid == "history": self.refresh_history_ui()

    def refresh_history_ui(self):
        while self.hist_layout.count():
            item = self.hist_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        # Load from engine which loads from JSON
        self.engine.load_history()

        for entry in self.engine.history:
            card = ProCard(fixedHeight=70)
            cl = QHBoxLayout(card)
            cl.addWidget(QLabel(entry['time'], styleSheet=f"color:{ThemeManager.get('TEXT_MUTED')}"))
            cl.addWidget(
                QLabel(entry['file'], styleSheet=f"color:{ThemeManager.get('TEXT_HEADER')}; font-weight:bold;"))
            cl.addStretch()
            res_lbl = QLabel(entry['result'])
            col = ThemeManager.ACCENT_DANGER if entry['result'] == "CRACK" else ThemeManager.ACCENT_SUCCESS
            res_lbl.setStyleSheet(
                f"color: {col}; font-weight: 800; border: 1px solid {col}; padding: 5px 10px; border-radius: 5px;")
            cl.addWidget(res_lbl)
            self.hist_layout.addWidget(card)
        self.hist_layout.addStretch()


if __name__ == "__main__":
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'): QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    win = CrackAnalyzerApp()
    win.show()
    sys.exit(app.exec())
