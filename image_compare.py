import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QLabel, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QTimer, QRect, QPoint
from PyQt5.QtGui import QImage, QPixmap
import numpy as np
import cv2
import mss

class CompareWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片对比辅助")
        self.setGeometry(100, 100, 800, 400)
        
        # 设置窗口属性
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)  # 无边框和置顶
        self.setAttribute(Qt.WA_TranslucentBackground)  # 设置窗口背景透明
        
        # 初始化变量
        self.resizing = False
        self.resize_start_pos = None
        self.start_geometry = None
        self.window_width = 387
        self.window_height = 292
        self.display_mode = 'diff'  # 'left', 'right', 'diff'
        
        # 创建标题栏
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(30)
        self.title_bar.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
        """)
        
        # 标题栏布局
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        
        # 标题文本
        title_label = QLabel("图片对比辅助")
        title_label.setStyleSheet("color: white;")
        title_layout.addWidget(title_label)
        
        # 关闭按钮
        close_button = QPushButton("×")
        close_button.setFixedSize(20, 20)
        close_button.setStyleSheet("""
            QPushButton {
                color: white;
                border: none;
                background: none;
            }
            QPushButton:hover {
                background-color: #c93437;
                border-radius: 10px;
            }
        """)
        close_button.clicked.connect(self.close_application)
        title_layout.addWidget(close_button, alignment=Qt.AlignRight)
        
        # 创建内容区域（透明背景）
        content_widget = QWidget()
        content_widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 内容区域穿透
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 0, 10, 10)
        content_layout.setSpacing(70)  # 设置左右区域间距为70

        
        # 创建主副窗口的截图区域
        self.main_area = QLabel()
        self.main_area.setStyleSheet("background-color: rgba(255, 0, 0, 50);")
        self.main_area.setFixedSize(self.window_width, self.window_height)
        
        self.sub_area = QLabel()
        self.sub_area.setStyleSheet("background-color: rgba(0, 0, 255, 50);")
        self.sub_area.setFixedSize(self.window_width, self.window_height)

        
        content_layout.addWidget(self.main_area)
        content_layout.addWidget(self.sub_area)
        
        # 主窗口整体布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(content_widget)
        
        # 设置主窗口边框样式
        central_widget = QWidget()
        central_widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # 中央部件不穿透
        central_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # 创建差异显示窗口
        self.diff_window = QMainWindow()
        self.diff_window.setWindowTitle("差异显示")
        
        # 获取屏幕尺寸，设置差异窗口位置在右下角
        screen = QApplication.primaryScreen().geometry()
        diff_width = 400
        diff_height = 400
        diff_x = screen.width() - diff_width - 20  # 右边距离20像素
        diff_y = screen.height() - diff_height - 40  # 下边距离40像素（考虑任务栏）
        self.diff_window.setGeometry(diff_x, diff_y, diff_width, diff_height)
        
        # 创建中央部件和布局
        diff_central = QWidget()
        diff_layout = QVBoxLayout(diff_central)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # 创建按钮
        self.left_button = QPushButton("显示左图")
        self.right_button = QPushButton("显示右图")
        self.diff_button = QPushButton("显示差异")
        
        # 设置按钮样式
        button_style = """
            QPushButton {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
            QPushButton:pressed {
                background-color: #202020;
            }
        """
        self.left_button.setStyleSheet(button_style)
        self.right_button.setStyleSheet(button_style)
        self.diff_button.setStyleSheet(button_style)
        
        # 连接按钮信号
        self.left_button.clicked.connect(lambda: self.set_display_mode('left'))
        self.right_button.clicked.connect(lambda: self.set_display_mode('right'))
        self.diff_button.clicked.connect(lambda: self.set_display_mode('diff'))
        
        # 添加按钮到布局
        button_layout.addWidget(self.left_button)
        button_layout.addWidget(self.right_button)
        button_layout.addWidget(self.diff_button)
        
        # 创建显示标签
        self.diff_label = QLabel()
        self.diff_label.setAlignment(Qt.AlignCenter)
        
        # 添加组件到主布局
        diff_layout.addLayout(button_layout)
        diff_layout.addWidget(self.diff_label)
        
        # 设置中央部件
        self.diff_window.setCentralWidget(diff_central)
        
        # 初始化截图工具
        self.sct = mss.mss()
        
        # 设置定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.capture_and_compare)
        self.timer.start(1000)
        
        self.show()
        self.diff_window.show()

    def close_application(self):
        self.diff_window.close()
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        self.close_application()
        event.accept()

    def set_display_mode(self, mode):
        self.display_mode = mode
        # 立即更新显示
        self.capture_and_compare()
        
    def capture_and_compare(self):
        # 获取主窗口和副窗口的位置
        main_pos = self.main_area.mapToGlobal(QPoint(0, 0))
        sub_pos = self.sub_area.mapToGlobal(QPoint(0, 0))

        # 截取主窗口和副窗口区域
        main_monitor = {"top": main_pos.y(), "left": main_pos.x(),
                       "width": self.window_width, "height": self.window_height}
        sub_monitor = {"top": sub_pos.y(), "left": sub_pos.x(),
                      "width": self.window_width, "height": self.window_height}
        
        main_screenshot = np.array(self.sct.grab(main_monitor))
        sub_screenshot = np.array(self.sct.grab(sub_monitor))
        
        # 根据显示模式选择要显示的图像
        if self.display_mode == 'left':
            display_img = cv2.cvtColor(main_screenshot, cv2.COLOR_BGR2RGB)
        elif self.display_mode == 'right':
            display_img = cv2.cvtColor(sub_screenshot, cv2.COLOR_BGR2RGB)
        else:  # diff mode
            # 转换为灰度图进行对比
            main_gray = cv2.cvtColor(main_screenshot, cv2.COLOR_BGR2GRAY)
            sub_gray = cv2.cvtColor(sub_screenshot, cv2.COLOR_BGR2GRAY)
            
            # 计算差异
            diff = cv2.absdiff(main_gray, sub_gray)
            _, diff_thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
            
            # 在差异图上标记差异区域
            display_img = cv2.cvtColor(diff_thresh, cv2.COLOR_GRAY2BGR)
            display_img[diff_thresh > 0] = [0, 0, 255]  # 红色标记差异
        
        # 显示图像
        height, width = display_img.shape[:2]
        bytes_per_line = 3 * width
        q_img = QImage(display_img.data, width, height, bytes_per_line, QImage.Format_RGB888)
        self.diff_label.setPixmap(QPixmap.fromImage(q_img))

    def mousePressEvent(self, event):
        if event.pos().y() <= self.title_bar.height():
            if event.button() == Qt.LeftButton:
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if event.pos().y() <= self.title_bar.height() and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            self.capture_and_compare()
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if event.pos().y() <= self.title_bar.height():
            event.accept()
        else:
            event.ignore()

    def enterEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        event.accept()

    def leaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CompareWindow()
    sys.exit(app.exec_())
