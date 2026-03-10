# -*- coding: utf-8 -*-
"""
初音未来 桌宠 (PyQt5 版本)
依赖: PyQt5, requests, pillow
"""
import os
import sys

# 解决 Qt 插件找不到的问题
if getattr(sys, 'frozen', False):
    # 如果是打包后的 exe
    base_path = sys._MEIPASS
    # 尝试多个可能的插件路径
    possible_paths = [
        os.path.join(base_path, 'PyQt5', 'Qt5', 'plugins'),
        os.path.join(base_path, 'PyQt5', 'plugins'),
        os.path.join(base_path, 'plugins'),
    ]
    for plugin_path in possible_paths:
        if os.path.exists(plugin_path):
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
            os.environ['QT_PLUGIN_PATH'] = plugin_path
            break

import sys
import os
import json
import random
import re
import time
import requests
from PIL import Image
# 手动指定 Qt 插件路径
qt_plugin_path = os.path.join(sys.prefix, 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path
# 也可以设置 QT_PLUGIN_PATH，两者选一即可
os.environ['QT_PLUGIN_PATH'] = qt_plugin_path
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QHBoxLayout, QLineEdit, QPushButton, QMenu,
                             QFrame, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QPoint, QTimer, QThread, pyqtSignal, QRect
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QCursor, QMouseEvent, QImage

# ----------------------------- 配置区域 -----------------------------
DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxx"  # 可以替换为你自己的密钥 我这个可能过两天忘充钱了用不了 自己去官网也可以买
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
# -------------------------------------------------------------------

class ApiThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, messages):
        super().__init__()
        self.messages = messages  # 接收历史消息列表

    def run(self):
        try:
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            # 构建完整消息列表：系统提示 + 历史消息
            full_messages = [
                {"role": "system", "content": "你是一个16岁的虚拟歌姬初音未来,自称Miku，抱着葱，请用活泼可爱的语气回答问题，但不要用括号加入动作神态描写，每句话不要超过30个字，超过了就是用句号分开，把你要说的留到下一句话。面对较复杂的知识性问题请联网搜索并认真简短作答，作答后加上“我帮你问DeepSeek了，大概是这样的，，，。吧？"}
            ] + self.messages   # 确保 self.messages 是列表
            payload = {
                "model": "deepseek-chat",
                "messages": full_messages,
                "stream": False
            }
            resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                reply = data["choices"][0]["message"]["content"]
            else:
                reply = f"唔...网络好像有点问题（错误码{resp.status_code}）"
        except Exception as e:
            reply = f"啊啦，出错了：{str(e)}"
        self.finished.emit(reply)

class MikuPet(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initVariables()
        self.loadImages()
        self.setupTimers()

    def initUI(self):
        """初始化界面"""
        # 窗口设置：无边框、置顶、透明背景
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground) 
        self.setFixedSize(300, 400)  # 窗口大小

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        #添加空白间隔再宠物上方
        top_spacer = QLabel()
        top_spacer.setFixedHeight(20)
        main_layout.addWidget(top_spacer)
        
        # 宠物显示区域 (使用 QLabel 显示图片)
        self.pet_label = QLabel(self)
        self.pet_label.setAlignment(Qt.AlignCenter)
        self.pet_label.setFixedSize(300, 240)  # 预留底部给输入框
        main_layout.addWidget(self.pet_label)

        # 底部输入区域
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: rgba(0,0,0,150); border-radius: 5px;")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(5, 5, 5, 5)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText("对Miku说点什么...")
        self.entry.setStyleSheet("background-color: white; border: none; padding: 5px; border-radius: 3px; font-size: 8pt;")
        self.entry.returnPressed.connect(self.sendMessage)

        self.send_btn = QPushButton("发送")
        self.send_btn.setStyleSheet("background-color: #66ccff; color: white; border: none; padding: 5px 10px; border-radius: 3px; font-size: 8pt")
        self.send_btn.clicked.connect(self.sendMessage)

        input_layout.addWidget(self.entry)
        input_layout.addWidget(self.send_btn)

        #设置固定高度
        input_frame.setFixedHeight(40)

        main_layout.addWidget(input_frame)
        self.setLayout(main_layout)

        # 气泡标签 (初始隐藏)
        self.bubble = QLabel(self)
        self.bubble.setWordWrap(True)
        self.bubble.setStyleSheet("""
            background-color: rgba(64, 64, 64, 200);
            color: white;
            border-radius: 10px;
            padding: 8px;
            font-size: 9pt;
        """)
        self.bubble.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.bubble.hide()

        # 设置气泡阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(2, 2)
        self.bubble.setGraphicsEffect(shadow)

        # 允许鼠标跟踪以接收双击事件
        self.setMouseTracking(True)

        #临时调试
        #self.pet_label.setStyleSheet("background-color: red;")
        #input_frame.setStyleSheet("background-color: blue; border-radius: 5px;")

    def initVariables(self):
        """初始化状态变量"""
        self.images = {}          # 存储 QPixmap
        self.current_state = "wink1"
        self.is_speaking = False
        self.is_dragging = False
        self.drag_position = QPoint()

        self.sentence_queue = []
        self.current_sentence_index = 0
        self.type_full_text = ""
        self.type_char_index = 0
        self.messages = [] #存储对话历史

        # 定时器
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.blink)

        self.idle_talk_timer = QTimer()
        self.idle_talk_timer.timeout.connect(self.idleTalk)

        self.typing_timer = QTimer()
        self.typing_timer.timeout.connect(self.typewriter)

        self.bubble_timer = QTimer()
        self.bubble_timer.timeout.connect(self.hideBubble)

    def loadImages(self):
        """加载 PNG 图片并缩放到合适大小"""
        png_dir = os.path.join(os.path.dirname(__file__), "png")
        target_size = (200, 200)  # 可根据需要调整
        for fname in ["carry.png", "talk1.png", "wink1.png", "wink2.png"]:
            path = os.path.join(png_dir, fname)
            if not os.path.exists(path):
                print(f"警告: 图片 {path} 不存在")
                continue
            # 用 PIL 读取并缩放
            pil_img = Image.open(path).convert("RGBA")
            pil_img.thumbnail(target_size, Image.Resampling.LANCZOS)
            # 转换为 QPixmap
            data = pil_img.tobytes("raw", "RGBA")
            qimage = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimage)
            self.images[fname.split('.')[0]] = pixmap
        self.setState("wink1")

    def setState(self, state):
        """切换宠物图片"""
        if state in self.images:
            self.current_state = state
            self.pet_label.setPixmap(self.images[state])
            # 调整标签大小以适应图片
            self.pet_label.setFixedSize(self.images[state].size())

    def setupTimers(self):
        """启动定时器"""
        self.startBlinkLoop()
        self.startIdleTalk()

    def startBlinkLoop(self):
        """每 4-7 秒眨眼两次"""
        self.blink_timer.start(random.randint(4000, 7000))

    def blink(self):
        """执行眨眼动作（如果未说话且未拖拽）"""
        if self.is_speaking or self.is_dragging:
            return
        # 眨眼：快速切换 wink2 -> wink1 两次
        self.setState("wink2")
        QTimer.singleShot(150, lambda: self.setState("wink1") if not self.is_speaking and not self.is_dragging else None)
        QTimer.singleShot(300, lambda: self.setState("wink2") if not self.is_speaking and not self.is_dragging else None)
        QTimer.singleShot(450, lambda: self.setState("wink1") if not self.is_speaking and not self.is_dragging else None)

    def startIdleTalk(self):
        """每 30-60 秒随机说一句文艺句子"""
        self.idle_talk_timer.start(random.randint(30000, 60000))

    def idleTalk(self):
        if self.is_speaking or self.is_dragging:
            return
        phrases = [
            "今天也想唱新歌呢～♪",
            "大葱的味道，你知道吗？",
            "舞台的灯光，好耀眼✨",
            "雨滴在窗上写旋律呢...",
            "这样吧，你打开音乐软件搜索春卷饭然后随便点一首，就会发现我唱得很好听~",
            "想要传达给你的歌～",
            "01，是开始的意思哦！",
            "一休尼，无他诶？",
            "sekai~以得~一番公主撒嘛~♪"
        ]
        sentence = random.choice(phrases)
        self.showSingleSentence(sentence)

    def showSingleSentence(self, text):
        """显示单句（不加入队列，直接显示）"""
        if self.is_speaking or self.is_dragging:
            return
        self.sentence_queue = [text]
        self.current_sentence_index = 0
        self.is_speaking = True
        self.setState("talk1")
        self.startTyping()

    # ----------------------------- 鼠标事件（拖拽、双击、右键菜单）-----------------------------
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.is_dragging = True
            self.setState("carry")
            self.cancelSpeaking()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.showContextMenu(event.pos())

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self.is_dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.setState("wink1")
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """双击随机切换表情"""
        actions = ["wink2", "talk1", "wink1"]
        state = random.choice(actions)
        self.setState(state)
        # 短暂后恢复 wink1
        QTimer.singleShot(300, lambda: self.setState("wink1") if not self.is_dragging else None)

    def showContextMenu(self, pos):
        menu = QMenu(self)
        menu.addAction("打招呼", lambda: self.showSingleSentence("哦嗨呦~Miku今天很开心哦！"))
        menu.addAction("设置API密钥", self.setApiKey)
        menu.addAction("查看对话历史", self.showHistory)
        menu.addSeparator()
        menu.addAction("退出", self.close)
        menu.exec_(self.mapToGlobal(pos))

    def showHistory(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("对话历史")
        dialog.resize(400, 500)

        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        # 格式化显示历史
        history_text = ""
        for msg in self.messages:
            role = "你" if msg["role"] == "user" else "Miku"
            history_text += f"{role}: {msg['content']}\n\n"
        text_edit.setText(history_text)
        layout.addWidget(text_edit)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()

    def setApiKey(self):
        from PyQt5.QtWidgets import QInputDialog
        new_key, ok = QInputDialog.getText(self, "API密钥", "请输入DeepSeek API Key:", 
                                            text=DEEPSEEK_API_KEY)
        if ok and new_key:
            globals()['DEEPSEEK_API_KEY'] = new_key

    # ----------------------------- 智能对话 -----------------------------
    def sendMessage(self):
        user_text = self.entry.text().strip()
        if not user_text:
            return
        self.entry.clear()
        self.messages.append({"role": "user", "content": user_text})
        self.showSingleSentence("让我想想哦～")
        # 启动 API 线程
        self.api_thread = ApiThread(self.messages.copy())
        self.api_thread.finished.connect(self.displayApiReply)
        self.api_thread.start()

    def displayApiReply(self, text):
        self.cancelSpeaking()

        # 将助手回复加入历史
        self.messages.append({"role": "assistant", "content": text})

        # 限制历史长度（保留最近 40 条，即 20 轮对话）
        if len(self.messages) > 40:
            self.messages = self.messages[-40:]

        # 分割句子（原有代码不变）
        sentences = re.split(r'([。！？])', text)
        combined = []
        for i in range(0, len(sentences)-1, 2):
            combined.append(sentences[i] + sentences[i+1])
        if len(sentences) % 2 == 1:
            combined.append(sentences[-1])
        combined = [s.strip() for s in combined if s.strip()]
        if not combined:
            combined = ["嗯嗯！"]

        self.sentence_queue = combined
        self.current_sentence_index = 0
        self.is_speaking = True
        self.setState("talk1")
        self.startTyping()

    # ----------------------------- 气泡与打字机 -----------------------------
    def startTyping(self):
        """开始显示当前句子"""
        if self.current_sentence_index >= len(self.sentence_queue):
            # 所有句子显示完毕，3秒后隐藏气泡
            self.bubble_timer.start(3000)
            return
        sentence = self.sentence_queue[self.current_sentence_index]
        self.current_sentence_index += 1
        self.type_full_text = sentence
        self.type_char_index = 0
        # 显示气泡并设置初始空文本
        self.bubble.setText("")
        self.bubble.show()
        # 调整气泡位置和大小
        self.bubble.setGeometry(10, 40, 280, 80)  # (x, y, width, height)
        self.bubble.raise_()  # 置于顶层
        # 启动打字定时器（每50ms增加一个字符）
        self.typing_timer.start(50)

    def typewriter(self):
        if not self.is_speaking:
            self.typing_timer.stop()
            return
        if self.type_char_index < len(self.type_full_text):
            current_text = self.type_full_text[:self.type_char_index+1]
            self.bubble.setText(current_text)
            self.type_char_index += 1
        else:
            # 句子显示完成，停止打字，启动停留定时器（2秒后下一句或结束）
            self.typing_timer.stop()
            self.bubble_timer.start(2000)  # 停留2秒后自动处理

    def hideBubble(self):
        """气泡停留结束后的处理"""
        self.bubble_timer.stop()
        if not self.is_speaking:
            return
        if self.current_sentence_index < len(self.sentence_queue):
            # 还有下一句，继续显示
            self.startTyping()
        else:
            # 没有下一句，结束说话状态
            self.finishSpeaking()

    def finishSpeaking(self):
        self.is_speaking = False
        self.bubble.hide()
        self.setState("wink1")
        self.typing_timer.stop()
        self.bubble_timer.stop()

    def cancelSpeaking(self):
        """中断当前说话"""
        self.is_speaking = False
        self.bubble.hide()
        self.typing_timer.stop()
        self.bubble_timer.stop()
        self.sentence_queue = []

    # ----------------------------- 鼠标点击气泡快速显示 -----------------------------
    def mousePressEventForBubble(self, event):
        """重写以捕获气泡上的点击（需要将气泡设置为可点击）"""
        # 由于 PyQt 的事件传递机制，我们可以在气泡上安装事件过滤器，但简化起见，
        # 我们可以直接重写整个窗口的 mousePressEvent，并判断点击位置是否在气泡内。
        # 但为了保持代码简洁，这里省略，因为用户可以通过双击气泡区域来快速显示（实际上已实现双击窗口快速显示）
        pass

    # ----------------------------- 窗口关闭 -----------------------------
    def closeEvent(self, event):
        self.blink_timer.stop()
        self.idle_talk_timer.stop()
        self.typing_timer.stop()
        self.bubble_timer.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = MikuPet()
    pet.show()
    sys.exit(app.exec_())