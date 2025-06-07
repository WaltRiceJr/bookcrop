#!/usr/bin/env python3
import sys
from PyQt6.QtWidgets import QApplication
from bookcrop_app import BookCropApp

def main():
    app = QApplication(sys.argv)
    window = BookCropApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()