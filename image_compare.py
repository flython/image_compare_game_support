import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QLabel, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QTimer, QRect, QPoint, QEvent
from PyQt5.QtGui import QImage, QPixmap, QMouseEvent
import numpy as np
import cv2
import mss


class CompareWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 初始化变量
        self.display_mode = 'rgb'  # 设置默认模式为rgb
        self.mode_names = {
            'left': '左图',
            'right': '右图',
            'rgb': 'RGB对比',
            'gray': '灰度对比',
            'hsv': 'HSV对比',
            'edge': '边缘对比'
        }

        self.setWindowTitle("图片对比辅助")
        
        # 获取屏幕尺寸并设置窗口位置在屏幕中央
        screen = QApplication.primaryScreen().geometry()
        self.window_width = 387
        self.window_height = 292
        window_x = (screen.width() - self.window_width * 2 - 70) // 2  # 考虑两个窗口的宽度和间距
        window_y = (screen.height() - self.window_height) // 2
        self.setGeometry(window_x, window_y, self.window_width * 2 + 70, self.window_height + 40)  # +40为标题栏高度

        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)  # 无边框和置顶
        self.setAttribute(Qt.WA_TranslucentBackground)  # 设置窗口背景透明

        # 初始化其他变量
        self.resizing = False
        self.resize_start_pos = None
        self.start_geometry = None

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
        title_label.setFixedWidth(150)
        title_layout.addWidget(title_label)

        # 模式文本
        self.mode_label = QLabel(self.mode_names[self.display_mode])
        self.mode_label.setStyleSheet("color: white;")
        self.mode_label.setFixedWidth(100)
        title_layout.addWidget(self.mode_label, alignment=Qt.AlignRight)

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
        content_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-left: 2px solid #2b2b2b;
                border-right: 2px solid #2b2b2b;
                border-bottom: 2px solid #2b2b2b;
                border-bottom-left-radius: 5px;
                border-bottom-right-radius: 5px;
            }
        """)
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(70)  # 设置左右区域间距为70

        # 创建主副窗口的截图区域
        self.main_area = QLabel()
        self.main_area.setStyleSheet("""
            QLabel {
                border: 2px solid #FF0000;
                border-radius: 3px;
            }
        """)
        self.main_area.setFixedSize(self.window_width, self.window_height)

        self.sub_area = QLabel()
        self.sub_area.setStyleSheet("""
            QLabel {
                border: 2px solid #0000FF;
                border-radius: 3px;
            }
        """)
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
        self.diff_window.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.diff_window.setWindowTitle(f"差异显示 - {self.mode_names[self.display_mode]}")
        # 重写diff_window的closeEvent，关闭差异窗口时，关闭主窗口
        self.diff_window.closeEvent = lambda event: self.close_application()

        # 获取屏幕尺寸，设置差异窗口位置在屏幕中央
        screen = QApplication.primaryScreen().geometry()
        diff_width = 400
        diff_height = 400
        diff_x = (screen.width() - diff_width) // 2
        diff_y = (screen.height() - diff_height) // 2
        self.diff_window.setGeometry(diff_x, diff_y, diff_width, diff_height)

        # 创建中央部件和布局
        diff_central = QWidget()
        diff_layout = QVBoxLayout(diff_central)

        # 创建按钮布局（两行）
        button_layout_top = QHBoxLayout()
        button_layout_bottom = QHBoxLayout()

        # 创建按钮
        self.left_button = QPushButton("左图")
        self.right_button = QPushButton("右图")
        self.rgb_button = QPushButton("RGB对比")
        self.gray_button = QPushButton("灰度对比")
        self.hsv_button = QPushButton("HSV对比")
        self.edge_button = QPushButton("边缘对比")
        self.close_button = QPushButton("关闭")

        # 设置按钮样式
        button_style = """
            QPushButton {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
            QPushButton:pressed {
                background-color: #202020;
            }
        """
        
        # 应用样式到所有按钮
        for button in [self.left_button, self.right_button, self.rgb_button,
                      self.gray_button, self.hsv_button, self.edge_button,
                      self.close_button]:
            button.setStyleSheet(button_style)
        
        # 连接按钮信号
        self.left_button.clicked.connect(lambda: self.set_display_mode('left'))
        self.right_button.clicked.connect(lambda: self.set_display_mode('right'))
        self.rgb_button.clicked.connect(lambda: self.set_display_mode('rgb'))
        self.gray_button.clicked.connect(lambda: self.set_display_mode('gray'))
        self.hsv_button.clicked.connect(lambda: self.set_display_mode('hsv'))
        self.edge_button.clicked.connect(lambda: self.set_display_mode('edge'))
        self.close_button.clicked.connect(self.close)

        # 第一行按钮
        button_layout_top.addWidget(self.left_button)
        button_layout_top.addWidget(self.right_button)
        button_layout_top.addWidget(self.rgb_button)

        # 第二行按钮
        button_layout_bottom.addWidget(self.gray_button)
        button_layout_bottom.addWidget(self.hsv_button)
        button_layout_bottom.addWidget(self.edge_button)
        button_layout_bottom.addWidget(self.close_button)

        # 添加按钮布局到主布局
        diff_layout.addLayout(button_layout_top)
        diff_layout.addLayout(button_layout_bottom)

        # 创建显示标签
        self.diff_label = QLabel()
        self.diff_label.setAlignment(Qt.AlignCenter)
        

        # 添加组件到主布局
        diff_layout.addWidget(self.diff_label)

        # 设置中央部件
        self.diff_window.setCentralWidget(diff_central)

        # 初始化截图工具
        self.sct = mss.mss()

        # 设置定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.capture_and_compare)
        self.timer.start(100)

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
        # 更新差异窗口标题，显示当前模式
        self.diff_window.setWindowTitle(f"差异显示 - {self.mode_names.get(mode, 'RGB对比')}")
        self.mode_label.setText(self.mode_names.get(mode, 'RGB对比'))  # 更新标题栏模式文本
        # 立即更新显示
        self.capture_and_compare()


    def capture_and_compare(self):
        try:
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
            else:
                # 转换为RGB格式进行处理
                main_rgb = cv2.cvtColor(main_screenshot, cv2.COLOR_BGR2RGB)
                sub_rgb = cv2.cvtColor(sub_screenshot, cv2.COLOR_BGR2RGB)
                
                if self.display_mode == 'rgb':
                    # RGB对比：分别对比每个通道，加权合并
                    diff_r = cv2.absdiff(main_rgb[:,:,0], sub_rgb[:,:,0])
                    diff_g = cv2.absdiff(main_rgb[:,:,1], sub_rgb[:,:,1])
                    diff_b = cv2.absdiff(main_rgb[:,:,2], sub_rgb[:,:,2])
                    diff = diff_r + diff_g + diff_b
                    threshold = 60
                    
                elif self.display_mode == 'gray':
                    # 灰度对比：转换为灰度后对比
                    main_gray = cv2.cvtColor(main_screenshot, cv2.COLOR_BGR2GRAY)
                    sub_gray = cv2.cvtColor(sub_screenshot, cv2.COLOR_BGR2GRAY)
                    diff = cv2.absdiff(main_gray, sub_gray)
                    threshold = 70
                    
                elif self.display_mode == 'hsv':
                    # HSV对比：在HSV空间进行对比，加权H通道
                    main_hsv = cv2.cvtColor(main_screenshot, cv2.COLOR_BGR2HSV)
                    sub_hsv = cv2.cvtColor(sub_screenshot, cv2.COLOR_BGR2HSV)
                    # H通道权重更大，因为它代表颜色变化
                    diff_h = cv2.absdiff(main_hsv[:,:,0], sub_hsv[:,:,0]) * 2
                    diff_s = cv2.absdiff(main_hsv[:,:,1], sub_hsv[:,:,1]) * 0.8
                    diff_v = cv2.absdiff(main_hsv[:,:,2], sub_hsv[:,:,2]) * 0.2
                    diff = diff_h + diff_s + diff_v
                    threshold = 50
                    
                elif self.display_mode == 'edge':
                    # 边缘对比：使用Sobel算子检测边缘
                    main_gray = cv2.cvtColor(main_screenshot, cv2.COLOR_BGR2GRAY)
                    sub_gray = cv2.cvtColor(sub_screenshot, cv2.COLOR_BGR2GRAY)
                    
                    # 计算x和y方向的边缘
                    main_sobelx = cv2.Sobel(main_gray, cv2.CV_64F, 1, 0, ksize=3)
                    main_sobely = cv2.Sobel(main_gray, cv2.CV_64F, 0, 1, ksize=3)
                    sub_sobelx = cv2.Sobel(sub_gray, cv2.CV_64F, 1, 0, ksize=3)
                    sub_sobely = cv2.Sobel(sub_gray, cv2.CV_64F, 0, 1, ksize=3)
                    
                    # 计算边缘强度
                    main_edges = np.sqrt(main_sobelx**2 + main_sobely**2)
                    sub_edges = np.sqrt(sub_sobelx**2 + sub_sobely**2)
                    
                    # 对比边缘差异
                    diff = cv2.absdiff(main_edges, sub_edges)
                    # 归一化到0-255范围
                    diff = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
                    threshold = 60

                # 应用高斯模糊减少噪点
                diff = cv2.GaussianBlur(diff, (3, 3), 0)
                _, diff_thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)

                # 进行形态学操作，去除小的噪点
                # kernel = np.ones((3,3), np.uint8)
                # diff_thresh = cv2.morphologyEx(diff_thresh, cv2.MORPH_OPEN, kernel)

                # 在左侧显示原图，并在差异处用黄色标记
                display_img = main_rgb.copy()
                display_img[diff_thresh > 0] = [255, 255, 0]  # 黄色标记差异

            # 显示图像
            height, width = display_img.shape[:2]
            bytes_per_line = 3 * width
            q_img = QImage(display_img.data, width, height, bytes_per_line, QImage.Format_RGB888)
            self.diff_label.setPixmap(QPixmap.fromImage(q_img))
            
        except Exception as e:
            print(f"Error in capture_and_compare: {str(e)}")

    def mousePressEvent(self, event):
        if event.pos().y() <= self.title_bar.height():
            self.dragging = True
            self.drag_start_pos = event.globalPos()
            self.drag_start_geometry = self.geometry()
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'dragging') and self.dragging:
            delta = event.globalPos() - self.drag_start_pos
            new_pos = self.drag_start_geometry.topLeft() + delta
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if hasattr(self, 'dragging'):
            self.dragging = False
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.pos().y() <= self.title_bar.height():
            # 双击标题栏最大化/还原窗口
            if self.isMaximized():
                self.showNormal()
            else:
                self.showMaximized()

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
