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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
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
        self.title_bar.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # 标题栏不穿透
        
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
        content_widget.setAttribute(Qt.WA_TransparentForMouseEvents)  # 整个内容区域鼠标穿透
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 0, 10, 10)
        content_layout.setSpacing(70)  # 设置左右区域间距为70
        
        # 创建主副窗口的截图区域
        self.main_area = QLabel()
        self.main_area.setStyleSheet("background-color: rgba(255, 0, 0, 50);")
        self.main_area.setFixedSize(self.window_width, self.window_height)
        self.main_area.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 添加鼠标穿透
        
        self.sub_area = QLabel()
        self.sub_area.setStyleSheet("background-color: rgba(0, 0, 255, 50);")
        self.sub_area.setFixedSize(self.window_width, self.window_height)
        self.sub_area.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 添加鼠标穿透
        
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
        central_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(60, 60, 60, 128);
                border: 1px solid #555555;
                border-radius: 5px;
            }
        """)
        central_widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 中央部件穿透
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # 创建差异显示窗口
        self.diff_window = QMainWindow()
        self.diff_window.setWindowTitle("差异显示")
        self.diff_window.setGeometry(800, 100, 400, 400)  # 增加高度以容纳按钮
        
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
        if event.button() == Qt.LeftButton:
            # 只在标题栏区域响应事件
            if event.pos().y() <= self.title_bar.height():
                # 检查是否在窗口边缘
                edge_size = 10
                pos = event.pos()
                rect = self.rect()
                if (pos.x() >= rect.right() - edge_size or 
                    pos.y() >= rect.bottom() - edge_size):
                    self.resizing = True
                    self.resize_start_pos = event.globalPos()
                    self.start_geometry = self.geometry()
                else:
                    self.resizing = False
                    self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
            else:
                event.ignore()  # 忽略标题栏外的点击事件
        
    def mouseMoveEvent(self, event):
        # 只在标题栏区域响应事件
        if event.pos().y() <= self.title_bar.height():
            # 检查是否在窗口边缘
            edge_size = 10
            pos = event.pos()
            rect = self.rect()
            
            # 设置鼠标样式
            if pos.x() >= rect.right() - edge_size:
                self.setCursor(Qt.SizeHorCursor)
            elif pos.y() >= rect.bottom() - edge_size:
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

            # 处理窗口移动和大小调整
            if self.resizing and event.buttons() == Qt.LeftButton:
                diff = event.globalPos() - self.resize_start_pos
                new_geometry = self.start_geometry
                min_width = 400  # 最小宽度
                min_height = 200  # 最小高度
                
                # 处理宽度调整
                if pos.x() >= rect.right() - edge_size:
                    new_width = max(min_width, self.start_geometry.width() + diff.x())
                    self.window_width = new_width // 2
                    new_geometry.setWidth(new_width)
                
                # 处理高度调整
                if pos.y() >= rect.bottom() - edge_size:
                    new_height = max(min_height, self.start_geometry.height() + diff.y())
                    self.window_height = new_height
                    new_geometry.setHeight(new_height)
                
                self.setGeometry(new_geometry)
                self.main_area.setFixedSize(self.window_width, self.window_height)
                self.sub_area.setFixedSize(self.window_width, self.window_height)
                
            elif not self.resizing and event.buttons() == Qt.LeftButton:
                # 移动窗口
                self.move(event.globalPos() - self.drag_position)
                self.capture_and_compare()
            event.accept()
        else:
            event.ignore()  # 忽略标题栏外的移动事件

    def mouseReleaseEvent(self, event):
        # 只在标题栏区域响应事件
        if event.pos().y() <= self.title_bar.height():
            self.resizing = False
            self.resize_start_pos = None
            self.start_geometry = None
            event.accept()
        else:
            event.ignore()  # 忽略标题栏外的释放事件

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
