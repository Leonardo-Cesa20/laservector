from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea

class ImageView(QScrollArea):
    def __init__(self, placeholder="Sem imagem"):
        super().__init__()
        self.label = QLabel(placeholder)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background:#f5f5f5; color:#777;")
        self.setWidget(self.label)
        self.setWidgetResizable(True)
        self._pixmap = None

    def set_bgr(self, image):
        rgb = image[:, :, ::-1].copy()
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
        self._pixmap = QPixmap.fromImage(qimg)
        self._update_pixmap()

    def set_gray(self, image):
        h, w = image.shape
        qimg = QImage(image.data, w, h, w, QImage.Format_Grayscale8).copy()
        self._pixmap = QPixmap.fromImage(qimg)
        self._update_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pixmap()

    def _update_pixmap(self):
        if self._pixmap is None:
            return
        target = self.viewport().size()
        shown = self._pixmap.scaled(
            target, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.label.setPixmap(shown)
