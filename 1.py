import sys
import os
import time
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox, QFileDialog, QVBoxLayout,
    QFormLayout, QSpacerItem, QSizePolicy, QHBoxLayout, QGridLayout, QMessageBox, QPlainTextEdit
)
from PyQt5.QtGui import QFont, QPixmap, QIcon, QPalette, QColor, QTextCursor, QTextCharFormat
from PyQt5.QtCore import Qt
import datetime
import pyautogui
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from pynput.keyboard import Controller, Key, KeyCode
import keyboard
import json
import psutil
import pygetwindow
from PyQt5.QtCore import QSettings

BUTTON_WIDTH = 150
BUTTON_HEIGHT = 35

SETTINGS_FILE = "settings.json"

def resource_path(relative_path):
    """Lấy đúng đường dẫn khi chạy từ exe hoặc script."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class AutoRB(QWidget):
    log_signal = pyqtSignal(str, str)  # text, level
    def save_setting(self, key, value):
        settings = {}
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
        settings[key] = value
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def load_settings(self):
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                # Khôi phục background và icon nếu có
                bg = settings.get("background")
                icon = settings.get("icon")
                if bg and os.path.exists(bg):
                   self.bg.setPixmap(QPixmap(resource_path("default_bg.png")).scaled(360, 600))
                if icon and os.path.exists(icon):
                   self.setWindowIcon(QIcon(icon))
                # Khôi phục combo box
                insert_key = settings.get("insert_key")
                hotkey = settings.get("hotkey")
                if insert_key in self.keylist:
                    self.combo_insert.setCurrentText(insert_key)
                else:
                    self.combo_insert.setCurrentText('Insert')
                if hotkey in self.keylist:
                    self.combo_hotkey.setCurrentText(hotkey)
                else:
                    self.combo_hotkey.setCurrentText('F1')
        else:
            self.combo_insert.setCurrentText('Insert')
            self.combo_hotkey.setCurrentText('F1')

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto RB Ranmelle")
        self.setFixedSize(360, 600)
        self.setWindowIcon(QIcon(resource_path("default_icon.png")))
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        self.keyboard = Controller()
        self.bot_active = False
        self.image_path = "image1.png"   # Đường dẫn ảnh lv 300
        self.image2_path = "image2.png"  # Đường dẫn ảnh dùng để dừng bot
        self.insert_key = Key.insert
        self.hotkey_toggle = "F1"
        self.running = True

        self.bg = QLabel(self)
        self.bg.setPixmap(QPixmap(resource_path("default_bg.png")).scaled(360, 600, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        self.bg.setGeometry(0, 0, 360, 600)

        self.status = QLabel('🔴 Bot đang tắt', self)
        self.status.setFont(QFont('Segoe UI Semibold', 11))
        self.status.setStyleSheet("color: #FF4C4C; background-color: rgba(0,0,0,030); padding: 3px; border-radius: 4px;")
        self.status.move(10, 10)
        self.status.resize(200, 25)
        
        self.command_count = 0
        self.bot_start_time = None
        

        self.container = QWidget(self)
        self.container.setGeometry(10, 40, 340, 540)
        self.container.setAutoFillBackground(True)
        p = self.container.palette()
        p.setColor(QPalette.Window, QColor(0, 0, 0, 180))
        self.container.setPalette(p)

        self.vbox = QVBoxLayout(self.container)
        self.vbox.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # ✅ Khai báo keylist TRƯỚC
        self.keylist = [f'F{i}' for i in range(1, 13)] + [str(i) for i in range(10)] + list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + ['Insert', 'Delete', 'Space', 'Tab', 'Ctrl', 'Alt', 'Shift', 'Home', 'End', 'Page Up', 'Page Down']
        self.combo_insert = QComboBox()
        self.combo_hotkey = QComboBox()
        self.combo_insert.addItems(self.keylist)
        self.combo_hotkey.addItems(self.keylist)
        # Gọi load settings SAU khi đã có keylist
        self.load_settings()
        self.combo_insert.currentTextChanged.connect(lambda val: self.save_setting("insert_key", val))
        self.combo_hotkey.currentTextChanged.connect(lambda val: self.save_setting("hotkey", val))
        self.set_combo_style(self.combo_insert)
        self.set_combo_style(self.combo_hotkey)

        self.combo_insert.setFixedWidth(130)       # hoặc 180
        self.combo_insert.setFixedHeight(28)       # cao hơn mặc định

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)

        label_insert = QLabel('Skill Dawn:')
        label_insert.setFont(QFont('Segoe UI Semibold', 11))
        label_insert.setStyleSheet('color: #f6c96b;')

        insert_input = QWidget()
        insert_layout = QHBoxLayout(insert_input)
        insert_layout.setContentsMargins(0, 0, 0, 0)
        insert_layout.addWidget(self.combo_insert)
        insert_layout.addStretch()

        self.btn_update_dawn = self.make_button("Update", self.update_insert_key)
        self.btn_update_dawn.setFixedHeight(BUTTON_HEIGHT)
        self.btn_update_dawn.setFixedWidth(self.combo_insert.sizeHint().width())
        insert_layout.addWidget(self.btn_update_dawn)

        form_layout.addRow(label_insert, insert_input)

        label_hotkey = QLabel('Hotkey Bot:')
        label_hotkey.setFont(QFont('Segoe UI Semibold', 11))
        label_hotkey.setStyleSheet('color: #f6c96b;')

        hotkey_input = QWidget()
        hotkey_layout = QHBoxLayout(hotkey_input)
        hotkey_layout.setContentsMargins(0, 0, 0, 0)
        hotkey_layout.addWidget(self.combo_hotkey)
        hotkey_layout.addStretch()

        self.update_btn = self.make_button('Update', self.apply_keys)
        self.update_btn.setFixedHeight(BUTTON_HEIGHT)
        self.update_btn.setFixedWidth(self.combo_hotkey.sizeHint().width())
        hotkey_layout.addWidget(self.update_btn)

        form_layout.addRow(label_hotkey, hotkey_input)
        self.vbox.addLayout(form_layout)

        grid = QGridLayout()
        # Nút: Chọn ảnh lv300
        btn_img1 = self.make_button("Chọn ảnh Lv 300", self.choose_image)
        btn_img1.setFixedWidth(150)
        grid.addWidget(btn_img1, 0, 0)

        # Nút: Chọn ảnh bot check (ảnh 2)

        btn_img2 = self.make_button("Chọn ảnh bot check", self.choose_image2)
        btn_img2.setFixedWidth(150)
        grid.addWidget(btn_img2, 0, 1)

        # Nút: Chọn ảnh nền
        btn_bg = self.make_button("Chọn ảnh nền", self.choose_background)
        btn_bg.setFixedWidth(150)
        grid.addWidget(btn_bg, 1, 0)

        # Nút: Bật Bot / Tắt bot
        self.bot_button = self.make_button("Bật Bot", self.toggle_bot, green=True)
        self.bot_button.setFixedWidth(150)
        grid.addWidget(self.bot_button, 1, 1)

        # Thêm vào bố cục chính
        self.vbox.addLayout(grid)

        # Nút: Thoát bot
        self.exit_button = self.make_button("Thoát", self.close, red=True)
        self.exit_button.setFixedWidth(320)
        
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            background-color: rgba(0,0,0,100);
            color: #00ff00;
            font-family: Consolas;
            font-size: 8pt;
            border: 1px solid #555;
        """)                                                                                                                                  
        self.log_output.setFixedHeight(120)
        clear_layout = QHBoxLayout()
        clear_layout.setContentsMargins(0, 0, 0, 0)
        clear_layout.setSpacing(10)

        # Nút: Chọn Icon
        self.icon_btn = self.make_button("Chọn Icon", self.choose_icon)
        clear_layout.addWidget(self.icon_btn)

        # Nút: Xoá log
        self.clear_log_btn = self.make_button("🧹 Xóa log", self.clear_log)
        clear_layout.addWidget(self.clear_log_btn)

        self.vbox.addLayout(clear_layout)
        self.vbox.addWidget(self.log_output)

        self.vbox.addWidget(self.exit_button, alignment=Qt.AlignHCenter)

        try:
            keyboard.add_hotkey(self.hotkey_toggle, self.toggle_bot)
        except Exception as e:
            print("Lỗi thiết lập hotkey:", e)

        self.log_signal.connect(self.append_log)

        threading.Thread(target=self.insert_task, daemon=True).start()
        threading.Thread(target=self.image_task, daemon=True).start()

    def make_button(self, text, func, green=False, red=False):
        btn = QPushButton(text)
        btn.setFont(QFont("Segoe UI Semibold", 11))
        btn.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        color = "#f6c96b"
        bg = "rgba(0,0,0,100)"
        if green: bg = "#166534"
        elif red: bg = "#8B0000"
        btn.setStyleSheet(f"""
            QPushButton {{ color: {color}; background-color: {bg}; border: 1px solid {color}; border-radius: 6px; }}
            QPushButton:hover {{ background-color: rgba(0,0,0,120); }}
        """)
        btn.clicked.connect(func)
        return btn

    def set_combo_style(self, combo):
        combo.setFont(QFont("Segoe UI Semibold", 10))
        combo.setStyleSheet(
            "color: #f6c96b; background-color: {bg}; border: 1px solid #f6c96b; padding: 4px; border-radius: 4px;"
        )

    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh để tìm", "", "Images (*.png *.jpg *.bmp)")
        if path: self.image_path = path

    def choose_image2(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh để dừng bot", "", "Images (*.png *.jpg *.bmp)")
        if path:
            self.image2_path = path
            self.log(f"Đã chọn ảnh 2 để dừng bot:\n{path}", level="info")

    def choose_background(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh nền", "", "Images (*.png *.jpg *.bmp)")
        if path: self.bg.setPixmap(QPixmap(path).scaled(360, 600, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        self.save_setting("background", path)

    def choose_icon(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn biểu tượng", "", "Images (*.ico *.png *.jpg)")
        if path: self.setWindowIcon(QIcon(path))
        self.save_setting("icon", path)

    def apply_keys(self):
        try:
            self.insert_key = getattr(Key, self.combo_insert.currentText().lower(), KeyCode.from_char(self.combo_insert.currentText().lower()))
            keyboard.remove_hotkey(self.hotkey_toggle)
            self.hotkey_toggle = self.combo_hotkey.currentText()
            keyboard.add_hotkey(self.hotkey_toggle, self.toggle_bot)
        except Exception as e: print("Lỗi:", e)
        # ✅ Thông báo sau khi cập nhật
        QMessageBox.information(
            self,
            "Thông báo",
            f"<span style='color:#f6c96b; font-weight:bold; font-size:13pt;'>Hotkey đã được cập nhật: {self.hotkey_toggle}</span>"
        )

    def toggle_bot(self):
        self.bot_active = not self.bot_active
        if self.bot_active:
            self.bot_start_time = time.time()
            self.command_count = 0
        if self.bot_active:
            self.status.setText("🟢 Bot đang chạy")
            self.status.setStyleSheet("color: #00ff00;")
            self.bot_button.setText("Tắt Bot")
            self.bot_button.setStyleSheet("background-color: #8B0000; color: #f6c96b; "
                                          "border: 1px solid #f6c96b; padding: 4px; border-radius: 4px;")  # 🔴 đỏ
            self.log("🚀 Bot bắt đầu chạy", level="success")
        else:
            self.status.setText("🔴 Bot đang tắt")
            self.status.setStyleSheet("color: red;")
            self.bot_button.setText("Bật Bot")
            self.bot_button.setStyleSheet("background-color: #166534; color: #f6c96b; "
                                          "border: 1px solid #f6c96b; padding: 4px; border-radius: 4px;")  # 🟢 xanh lại
            self.log("⛔ Bot đã dừng lại", level="error")

    def insert_task(self):
        last_sent = 0
        while self.running:
            if self.bot_active and (time.time() - last_sent > 100):
               self.keyboard.press(self.insert_key)
               self.log("⌨ Đã gửi phím Dawn")
               self.keyboard.release(self.insert_key)
               last_sent = time.time()
            time.sleep(0.5)

    def image_task(self):      
            # ✅ Kiểm tra game 1 lần duy nhất lúc bắt đầu
            self.log("🕵️ Đang kiểm tra Maple có chạy không...", level="debug")
            if not self.is_game_running():
                self.log("⚠️ Maple chưa mở! Bot sẽ không chạy.", level="error")
                self.running = False
                self.bot_active = False
                return
            else:
                self.log("✅ Maple đã mở — có thể chạy bot", level="success")

            # 🔁 Bắt đầu vòng lặp bot nếu game hợp lệ
            consecutive_found = 0
            while self.running:
                # Kiểm tra ảnh bot check
                if self.image2_path and os.path.exists(self.image2_path):
                    try:
                        stop_location = pyautogui.locateOnScreen(self.image2_path, confidence=0.8)
                        if stop_location:
                            self.running = False
                            self.bot_active = False
                            self.log("🛑 Phát hiện ảnh bot check — bot đã dừng", level="error")
                            break
                    except Exception:
                        pass  # Không log nếu lỗi nhỏ khi không tìm thấy ảnh
            
                # 🔄 Tìm ảnh lv300 để thực hiện lệnh
                if self.bot_active and os.path.exists(self.image_path):
                    try:
                        location = pyautogui.locateOnScreen(self.image_path, confidence=0.8)
                        if location:
                            consecutive_found += 1
                            if consecutive_found >= 2:
                                self.log("✅ Tìm thấy ảnh lv300 — thực hiện lệnh", level="info")
                                self.type_commands()
                                consecutive_found = 0
                        else:
                            consecutive_found = 0
                                                      
                    except Exception:
                        pass  # Không log nếu lỗi nhỏ khi không tìm thấy ảnh

                time.sleep(2)

    def type_commands(self):
        self.command_count += 1
        pyautogui.press('enter')
        pyautogui.write('@rb', interval=0.08)
        pyautogui.press('enter')
        pyautogui.press('enter')
        time.sleep(5)
        pyautogui.press('enter')
        pyautogui.write('@luk 2000', interval=0.08)
        pyautogui.press('enter')
        pyautogui.press('enter')


    

    def log(self, text, level="default"):
        self.log_signal.emit(text, level)
    def append_log(self, text, level="default", max_lines=50):
        timestamp = time.strftime("%H:%M:%S")
        color_map = {
            "default": "#00ff00",    # Xanh lá
            "info": "#ffffff",       # Trắng
            "error": "#ff5555",      # Đỏ
            "success": "#00ff88",    # Xanh lá nhạt
        }
        color = color_map.get(level.lower(), "#00ff00")
        html = f'<span style="color:{color}">{timestamp} - {text}</span>'
        self.log_output.appendHtml(html)

        # ✅ Tự giới hạn số dòng
        if self.log_output.blockCount() > max_lines:
            # Di chuyển đến đầu và xóa dòng đầu tiên
            cursor = self.log_output.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # xóa ký tự xuống dòng

    
    def clear_log(self):
        self.log_output.clear()

    def update_insert_key(self):
    
        try:
            self.insert_key = getattr(
                Key,
                self.combo_insert.currentText().lower(),
                KeyCode.from_char(self.combo_insert.currentText().lower())
            )
            QMessageBox.information(
                self,
                "Thông báo",
                f"<span style='color:#f6c96b; font-weight:bold; font-size:13pt;'>Phím skill Dawn đã được cập nhật: {self.combo_insert.currentText()}</span>"
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi cập nhật phím Dawn: {e}")

    def is_game_running(self):
        # ✅ Kiểm tra tiến trình MapleStory.exe có đang chạy
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and "MapleStory.exe" in proc.info['name']:
                return True
            
        # ✅ Kiểm tra xem có cửa sổ chứa "Ranmelle" đang mở không
        for w in pygetwindow.getAllTitles():
            if "Ranmelle" in w:
                return True
            
        return False

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = AutoRB()
    win.show()
    sys.exit(app.exec_())
