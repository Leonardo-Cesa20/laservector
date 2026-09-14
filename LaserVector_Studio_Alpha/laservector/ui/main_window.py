from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QFileDialog, QMessageBox, QLabel, QPushButton,
    QComboBox, QSlider, QSpinBox, QDoubleSpinBox, QCheckBox, QFormLayout,
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QTabWidget, QStatusBar
)
from laservector.core.models import ProcessingSettings
from laservector.core.image_processor import process_image
from laservector.exporters.svg_exporter import export_svg
from laservector.exporters.dxf_exporter import export_dxf
from .image_view import ImageView

class MainWindow(QMainWindow):
    METHOD_MAP = {
        "Automático": "automatic",
        "Otsu": "otsu",
        "Adaptativo": "adaptive",
        "Manual": "manual",
    }
    MODE_MAP = {
        "Gravação preenchida": "fill",
        "Gravação por contorno": "outline",
        "Corte": "cut",
        "Linha central experimental": "centerline",
        "Reconstrução geométrica experimental": "geometry",
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LaserVector Studio Alpha 5 — Zumaq ZM6040")
        self.resize(1380, 820)
        self.source_path = None
        self.result = None
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        toolbar = QHBoxLayout()
        self.btn_import = QPushButton("Importar imagem")
        self.btn_process = QPushButton("Processar e vetorizar")
        self.btn_svg = QPushButton("Exportar SVG")
        self.btn_dxf = QPushButton("Exportar DXF")
        toolbar.addWidget(self.btn_import)
        toolbar.addWidget(self.btn_process)
        toolbar.addWidget(self.btn_svg)
        toolbar.addWidget(self.btn_dxf)
        toolbar.addStretch()
        outer.addLayout(toolbar)

        content = QHBoxLayout()
        outer.addLayout(content, 1)

        settings_box = QGroupBox("Configurações")
        settings_box.setMaximumWidth(330)
        settings_layout = QFormLayout(settings_box)

        self.method = QComboBox()
        self.method.addItems(self.METHOD_MAP.keys())

        self.mode = QComboBox()
        self.mode.addItems(self.MODE_MAP.keys())

        self.threshold = QSlider(Qt.Horizontal)
        self.threshold.setRange(0, 255)
        self.threshold.setValue(150)
        self.threshold.setEnabled(False)

        self.denoise = QSpinBox()
        self.denoise.setRange(0, 8)
        self.denoise.setValue(1)

        self.close_gaps = QSpinBox()
        self.close_gaps.setRange(0, 8)
        self.close_gaps.setValue(1)

        self.min_area = QSpinBox()
        self.min_area.setRange(1, 5000)
        self.min_area.setValue(20)

        self.simplify = QDoubleSpinBox()
        self.simplify.setRange(0.0, 5.0)
        self.simplify.setSingleStep(0.05)
        self.simplify.setValue(0.35)

        self.width_mm = QDoubleSpinBox()
        self.width_mm.setRange(1.0, 600.0)
        self.width_mm.setValue(100.0)
        self.width_mm.setSuffix(" mm")

        self.invert = QCheckBox("Inverter preto e branco")
        self.auto_crop = QCheckBox("Recortar arte automaticamente")
        self.auto_crop.setChecked(True)

        settings_layout.addRow("Método:", self.method)
        settings_layout.addRow("Modo:", self.mode)
        settings_layout.addRow("Limiar manual:", self.threshold)
        settings_layout.addRow("Remoção de ruído:", self.denoise)
        settings_layout.addRow("Fechar falhas:", self.close_gaps)
        settings_layout.addRow("Área mínima:", self.min_area)
        settings_layout.addRow("Simplificação:", self.simplify)
        settings_layout.addRow("Largura final:", self.width_mm)
        settings_layout.addRow(self.invert)
        settings_layout.addRow(self.auto_crop)

        machine = QLabel(
            "ZM6040\n"
            "Gravação: 550 × 400 mm\n"
            "Corte: 600 × 400 mm"
        )
        machine.setStyleSheet("padding-top:12px; color:#555;")
        settings_layout.addRow(machine)

        content.addWidget(settings_box)

        self.tabs = QTabWidget()
        self.original_view = ImageView("Importe uma imagem")
        self.binary_view = ImageView("A imagem tratada aparecerá aqui")
        self.vector_view = ImageView("O vetor aparecerá aqui")
        self.tabs.addTab(self.original_view, "Original")
        self.tabs.addTab(self.binary_view, "Imagem tratada")
        self.tabs.addTab(self.vector_view, "Prévia vetorial")
        content.addWidget(self.tabs, 1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Pronto para importar uma imagem.")

        self.btn_import.clicked.connect(self.import_image)
        self.btn_process.clicked.connect(self.process)
        self.btn_svg.clicked.connect(self.save_svg)
        self.btn_dxf.clicked.connect(self.save_dxf)
        self.method.currentTextChanged.connect(self._update_method_controls)


    def _update_method_controls(self):
        is_manual = self.method.currentText() == "Manual"
        self.threshold.setEnabled(is_manual)
        if not is_manual:
            self.status.showMessage(
                "O limiar manual é ajustado automaticamente neste método."
            )

    def _settings(self):
        return ProcessingSettings(
            method=self.METHOD_MAP[self.method.currentText()],
            threshold=self.threshold.value(),
            denoise=self.denoise.value(),
            close_gaps=self.close_gaps.value(),
            min_area=self.min_area.value(),
            simplify=self.simplify.value(),
            invert=self.invert.isChecked(),
            auto_crop=self.auto_crop.isChecked(),
            mode=self.MODE_MAP[self.mode.currentText()],
            width_mm=self.width_mm.value(),
        )

    def import_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar imagem", "",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.webp);;Todos os arquivos (*.*)"
        )
        if not path:
            return

        self.source_path = Path(path)
        self.result = None

        import cv2
        image = cv2.imread(path, cv2.IMREAD_COLOR)
        if image is None:
            QMessageBox.critical(self, "Erro", "Não foi possível abrir a imagem.")
            return

        self.original_view.set_bgr(image)
        self.tabs.setCurrentWidget(self.original_view)
        self.status.showMessage(f"Imagem carregada: {self.source_path.name}")

    def process(self):
        if not self.source_path:
            QMessageBox.warning(self, "Atenção", "Importe uma imagem primeiro.")
            return

        try:
            self.status.showMessage("Processando...")
            self.result = process_image(str(self.source_path), self._settings())
            self.binary_view.set_gray(self.result.binary)
            self.vector_view.set_bgr(self.result.vector_preview_bgr)
            self.tabs.setCurrentWidget(self.vector_view)

            if self._settings().mode == "centerline":
                points = sum(len(p) for p in self.result.open_paths)
                message = f"{len(self.result.open_paths)} linhas centrais | {points} pontos"
            elif self._settings().mode == "geometry":
                geometry_points = sum(len(p) for p in self.result.geometry_paths)
                contour_points = sum(len(c) for c in self.result.contours)
                message = (f"{len(self.result.geometry_paths)} linhas reconstruídas + "
                           f"{len(self.result.contours)} formas | "
                           f"{geometry_points + contour_points} pontos")
            else:
                points = sum(len(c) for c in self.result.contours)
                message = f"{len(self.result.contours)} caminhos | {points} pontos"
            self.status.showMessage(message)

            if self.result.warnings:
                QMessageBox.information(
                    self, "Resultado do processamento",
                    message + "\n\n" + "\n".join(self.result.warnings)
                )
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao processar", str(exc))
            self.status.showMessage("Falha no processamento.")

    def save_svg(self):
        if not self.result or (not self.result.contours and not self.result.open_paths and not self.result.geometry_paths):
            QMessageBox.warning(self, "Atenção", "Processe uma imagem antes de exportar.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar SVG", "", "SVG (*.svg)"
        )
        if not path:
            return
        if not path.lower().endswith(".svg"):
            path += ".svg"

        try:
            settings = self._settings()
            export_svg(
                path, self.result.contours, self.result.image_size,
                settings.width_mm, settings.mode, self.result.open_paths, self.result.geometry_paths
            )
            QMessageBox.information(self, "Concluído", "SVG exportado com sucesso.")
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))

    def save_dxf(self):
        if not self.result or (not self.result.contours and not self.result.open_paths and not self.result.geometry_paths):
            QMessageBox.warning(self, "Atenção", "Processe uma imagem antes de exportar.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar DXF", "", "DXF (*.dxf)"
        )
        if not path:
            return
        if not path.lower().endswith(".dxf"):
            path += ".dxf"

        try:
            settings = self._settings()
            export_dxf(
                path, self.result.contours, self.result.image_size,
                settings.width_mm, settings.mode, self.result.open_paths, self.result.geometry_paths
            )
            QMessageBox.information(self, "Concluído", "DXF exportado com sucesso.")
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))
