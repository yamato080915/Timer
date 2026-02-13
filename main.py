import sys
import math
import winsound
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QStackedWidget
)
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QBrush, QPainterPath,
    QLinearGradient, QConicalGradient, QRadialGradient
)


class CircleTimerWidget(QWidget):
    """円形のタイマー表示ウィジェット"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self._progress = 1.0  # 1.0 = 全体、0.0 = 終了
        self._total_seconds = 0
        self._remaining_seconds = 0

    def set_progress(self, progress, remaining):
        self._progress = max(0.0, min(1.0, progress))
        self._remaining_seconds = remaining
        self.update()

    def set_total(self, total):
        self._total_seconds = total
        self._remaining_seconds = total
        self._progress = 1.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        side = min(self.width(), self.height())
        radius = side / 2 - 20
        center = QPointF(self.width() / 2, self.height() / 2)

        # 背景トラック（暗いリング）
        track_pen = QPen(QColor(255, 255, 255, 30), 8)
        track_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(track_pen)
        painter.setBrush(Qt.NoBrush)
        rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        painter.drawEllipse(rect)

        # プログレスアーク
        if self._progress > 0:
            gradient = QConicalGradient(center, 90)
            gradient.setColorAt(0.0, QColor(0, 220, 255, 220))
            gradient.setColorAt(0.5, QColor(0, 150, 255, 200))
            gradient.setColorAt(1.0, QColor(100, 80, 255, 180))

            arc_pen = QPen(QBrush(gradient), 10)
            arc_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(arc_pen)

            start_angle = 90 * 16  # 12時位置から
            span_angle = int(-self._progress * 360 * 16)
            painter.drawArc(rect, start_angle, span_angle)

            # アーク先端のグロー効果
            angle_rad = math.radians(90 - self._progress * 360)
            glow_x = center.x() + radius * math.cos(angle_rad)
            glow_y = center.y() - radius * math.sin(angle_rad)
            glow_gradient = QRadialGradient(QPointF(glow_x, glow_y), 14)
            glow_gradient.setColorAt(0.0, QColor(0, 220, 255, 120))
            glow_gradient.setColorAt(1.0, QColor(0, 220, 255, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow_gradient))
            painter.drawEllipse(QPointF(glow_x, glow_y), 14, 14)

        # 中央の時間テキスト
        hrs = self._remaining_seconds // 3600
        mins = (self._remaining_seconds % 3600) // 60
        secs = self._remaining_seconds % 60
        time_text = f"{hrs:02d}:{mins:02d}:{secs:02d}"

        font = QFont("Segoe UI", 32, QFont.Weight.Light)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 230))
        painter.drawText(self.rect(), Qt.AlignCenter, time_text)

        painter.end()


class TimerApp(QWidget):
    def __init__(self):
        super().__init__()

        # ウィンドウ設定：フレームレス＋完全透明
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(340, 420)

        # ドラッグ用
        self._drag_pos = None

        # タイマーのステート
        self._running = False
        self._paused = False
        self._total_seconds = 300  # デフォルト5分
        self._remaining_seconds = 300

        # タイマー
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(4)

        # 閉じるボタン（右上）+ ドラッグエリア
        top_bar_widget = QWidget()
        top_bar_widget.setFixedHeight(36)
        top_bar_widget.setCursor(Qt.SizeAllCursor)
        top_bar_widget.setStyleSheet("""
            QWidget {
                background: rgba(255,255,255,0.05);
                border-radius: 8px;
            }
            QWidget:hover {
                background: rgba(255,255,255,0.08);
            }
        """)
        
        top_bar_layout = QHBoxLayout(top_bar_widget)
        top_bar_layout.setContentsMargins(8, 0, 8, 0)
        top_bar_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255,255,255,0.5);
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                color: rgba(255,100,100,0.9);
            }
        """)
        close_btn.clicked.connect(self.close)
        top_bar_layout.addWidget(close_btn)
        
        main_layout.addWidget(top_bar_widget)

        # 円形タイマー
        self._circle = CircleTimerWidget()
        main_layout.addWidget(self._circle, 1)

        # 時間設定エリア（スタック切り替え）
        self._stack = QStackedWidget()

        # ページ0: 設定画面
        setting_page = QWidget()
        setting_layout = QVBoxLayout(setting_page)
        setting_layout.setContentsMargins(0, 0, 0, 0)
        setting_layout.setSpacing(6)

        spin_layout = QHBoxLayout()
        spin_layout.setSpacing(8)

        spin_style = """
            QSpinBox {
                background: rgba(255,255,255,0.08);
                color: rgba(255,255,255,0.9);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 16px;
                font-family: 'Segoe UI';
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                background: transparent;
                border: none;
            }
            QSpinBox::up-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-bottom: 6px solid rgba(255,255,255,0.6); }
            QSpinBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid rgba(255,255,255,0.6); }
        """

        lbl_style = "color: rgba(255,255,255,0.5); font-size: 12px; font-family: 'Segoe UI';"

        self._hr_spin = QSpinBox()
        self._hr_spin.setRange(0, 99)
        self._hr_spin.setValue(0)
        self._hr_spin.setSuffix(" 時")
        self._hr_spin.setFixedWidth(90)
        self._hr_spin.setStyleSheet(spin_style)
        self._hr_spin.valueChanged.connect(self._on_time_changed)

        self._min_spin = QSpinBox()
        self._min_spin.setRange(0, 59)
        self._min_spin.setValue(5)
        self._min_spin.setSuffix(" 分")
        self._min_spin.setFixedWidth(90)
        self._min_spin.setStyleSheet(spin_style)
        self._min_spin.valueChanged.connect(self._on_time_changed)

        self._sec_spin = QSpinBox()
        self._sec_spin.setRange(0, 59)
        self._sec_spin.setValue(0)
        self._sec_spin.setSuffix(" 秒")
        self._sec_spin.setFixedWidth(90)
        self._sec_spin.setStyleSheet(spin_style)
        self._sec_spin.valueChanged.connect(self._on_time_changed)

        spin_layout.addStretch()
        spin_layout.addWidget(self._hr_spin)
        spin_layout.addWidget(self._min_spin)
        spin_layout.addWidget(self._sec_spin)
        spin_layout.addStretch()
        setting_layout.addLayout(spin_layout)

        start_btn = QPushButton("START")
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.setFixedHeight(38)
        start_btn.setStyleSheet(self._action_btn_style("0, 200, 255"))
        start_btn.clicked.connect(self._start)
        setting_layout.addWidget(start_btn)

        self._stack.addWidget(setting_page)

        # ページ1: 実行中画面
        running_page = QWidget()
        running_layout = QHBoxLayout(running_page)
        running_layout.setContentsMargins(0, 0, 0, 0)
        running_layout.setSpacing(10)

        self._pause_btn = QPushButton("PAUSE")
        self._pause_btn.setCursor(Qt.PointingHandCursor)
        self._pause_btn.setFixedHeight(38)
        self._pause_btn.setStyleSheet(self._action_btn_style("255, 180, 0"))
        self._pause_btn.clicked.connect(self._toggle_pause)
        running_layout.addWidget(self._pause_btn)

        reset_btn = QPushButton("RESET")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setFixedHeight(38)
        reset_btn.setStyleSheet(self._action_btn_style("255, 80, 80"))
        reset_btn.clicked.connect(self._reset)
        running_layout.addWidget(reset_btn)

        self._stack.addWidget(running_page)

        main_layout.addWidget(self._stack)

        # 初期表示
        self._on_time_changed()

    def _action_btn_style(self, rgb):
        return f"""
            QPushButton {{
                background: rgba({rgb}, 0.15);
                color: rgba({rgb}, 0.95);
                border: 1px solid rgba({rgb}, 0.3);
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI';
                letter-spacing: 2px;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background: rgba({rgb}, 0.25);
                border: 1px solid rgba({rgb}, 0.5);
            }}
            QPushButton:pressed {{
                background: rgba({rgb}, 0.35);
            }}
        """

    def _on_time_changed(self):
        total = self._hr_spin.value() * 3600 + self._min_spin.value() * 60 + self._sec_spin.value()
        self._total_seconds = max(total, 1)
        self._remaining_seconds = self._total_seconds
        self._circle.set_total(self._total_seconds)

    def _start(self):
        if self._total_seconds <= 0:
            return
        self._remaining_seconds = self._total_seconds
        self._running = True
        self._paused = False
        self._pause_btn.setText("PAUSE")
        self._stack.setCurrentIndex(1)
        self._timer.start()

    def _toggle_pause(self):
        if self._paused:
            self._timer.start()
            self._paused = False
            self._pause_btn.setText("PAUSE")
            self._pause_btn.setStyleSheet(self._action_btn_style("255, 180, 0"))
        else:
            self._timer.stop()
            self._paused = True
            self._pause_btn.setText("RESUME")
            self._pause_btn.setStyleSheet(self._action_btn_style("0, 220, 120"))

    def _reset(self):
        self._timer.stop()
        self._running = False
        self._paused = False
        self._remaining_seconds = self._total_seconds
        self._circle.set_total(self._total_seconds)
        self._stack.setCurrentIndex(0)

    def _tick(self):
        self._remaining_seconds -= 1
        if self._remaining_seconds <= 0:
            self._remaining_seconds = 0
            self._timer.stop()
            self._running = False
            progress = 0.0
            self._circle.set_progress(progress, self._remaining_seconds)
            self._stack.setCurrentIndex(0)
            
            # タイマー終了通知
            self._notify_timer_end()
            return

        progress = self._remaining_seconds / self._total_seconds
        self._circle.set_progress(progress, self._remaining_seconds)

    def _notify_timer_end(self):
        """タイマー終了時の通知"""
        # システム音を鳴らす
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
        
        # ウィンドウをアクティブ化（前面に表示）
        self.activateWindow()
        self.raise_()
        
        # ウィンドウをフラッシュさせて注意を引く
        self.setWindowOpacity(0.5)
        QTimer.singleShot(150, lambda: self.setWindowOpacity(1.0))
        QTimer.singleShot(300, lambda: self.setWindowOpacity(0.5))
        QTimer.singleShot(450, lambda: self.setWindowOpacity(1.0))

    # --- ドラッグ移動 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def closeEvent(self, event):
        """ウィンドウを閉じる際にタイマーを停止してアプリケーションを完全終了"""
        self._timer.stop()
        QApplication.quit()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TimerApp()
    window.show()
    sys.exit(app.exec())