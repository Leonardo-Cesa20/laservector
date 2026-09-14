import sys
from PySide6.QtWidgets import QApplication
from laservector.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LaserVector Studio")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
