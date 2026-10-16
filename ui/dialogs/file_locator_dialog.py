"""
High-Speed Local & Cloud File Locator Dialog.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QWidget, QApplication
)
from PyQt6.QtGui import QFont, QColor
from core.file_manager import FileManager


class FileLocatorDialog(QDialog):
    def __init__(self, file_mgr: FileManager, parent=None):
        super().__init__(parent)
        self.file_mgr = file_mgr
        self.setWindowTitle("🔍 Localizador de Archivos (Local & Nube)")
        self.resize(750, 480)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI'; }
            QLabel { color: #f8fafc; font-size: 13px; }
            QLineEdit {
                background-color: #1e293b; color: #38bdf8; border: 1px solid #475569;
                border-radius: 6px; padding: 7px 12px; font-size: 13px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #818cf8);
                color: white; border-radius: 6px; padding: 7px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #0284c7; }
            QComboBox {
                background-color: #1e293b; color: white; border: 1px solid #475569;
                border-radius: 6px; padding: 6px;
            }
            QTableWidget {
                background-color: #1e293b; color: #f8fafc; border: 1px solid #334155;
                border-radius: 8px; gridline-color: #334155;
            }
            QHeaderView::section {
                background-color: #0f172a; color: #38bdf8; font-weight: bold;
                border: 1px solid #334155; padding: 4px;
            }
        """)

        layout = QVBoxLayout(self)

        title = QLabel("🔍 Localizador Inteligente de Archivos (Disco Local y Nube)")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        layout.addWidget(title)

        # Search bar row
        search_row = QHBoxLayout()
        self.input_query = QLineEdit()
        self.input_query.setPlaceholderText("Nombre de archivo o extensión (ej: tesis, informe.docx, .png, python)...")
        self.input_query.returnPressed.connect(self.do_search)
        search_row.addWidget(self.input_query)

        self.combo_loc = QComboBox()
        self.combo_loc.addItem("🌐 Todo (Local y Nube)", "all")
        self.combo_loc.addItem("💻 Solo Local (~/)", "local")
        self.combo_loc.addItem("☁️ Solo Nube (Drive/Nextcloud)", "cloud")
        search_row.addWidget(self.combo_loc)

        search_btn = QPushButton("🔎 Buscar")
        search_btn.clicked.connect(self.do_search)
        search_row.addWidget(search_btn)

        layout.addLayout(search_row)

        self.status_lbl = QLabel("Escribe un término y pulsa Buscar o Enter.")
        self.status_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.status_lbl)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Nombre", "Ubicación", "Tamaño", "Modificado", "Acciones"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        btn_box = QHBoxLayout()
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet("background: #334155; color: white;")
        close_btn.clicked.connect(self.accept)
        btn_box.addStretch()
        btn_box.addWidget(close_btn)
        layout.addLayout(btn_box)

    def do_search(self):
        q = self.input_query.text().strip()
        if not q:
            return
        loc = self.combo_loc.currentData()
        self.status_lbl.setText("Buscando a gran velocidad...")
        QApplication.processEvents()

        results = self.file_mgr.search_files(q, location=loc, limit=30)
        self.table.setRowCount(len(results))
        for row, r in enumerate(results):
            f_item = QTableWidgetItem(r["filename"])
            f_item.setToolTip(r["path"])
            self.table.setItem(row, 0, f_item)

            is_cloud = (r["storage_type"] == "nube")
            loc_item = QTableWidgetItem("☁️ Nube" if is_cloud else "💻 Local")
            loc_item.setForeground(QColor("#38bdf8" if is_cloud else "#4ade80"))
            self.table.setItem(row, 1, loc_item)

            self.table.setItem(row, 2, QTableWidgetItem(r["size_str"]))
            self.table.setItem(row, 3, QTableWidgetItem(r["modified_str"]))

            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(2, 2, 2, 2)
            open_btn = QPushButton("▶ Abrir")
            open_btn.setFixedSize(55, 24)
            open_btn.setStyleSheet("background: #0284c7; color: white; font-size: 11px; padding: 2px;")
            p = r["path"]
            open_btn.clicked.connect(lambda ch, fpath=p: self.file_mgr.open_file(fpath))
            cl.addWidget(open_btn)

            show_btn = QPushButton("📂 Ver")
            show_btn.setFixedSize(50, 24)
            show_btn.setStyleSheet("background: #475569; color: white; font-size: 11px; padding: 2px;")
            show_btn.clicked.connect(lambda ch, fpath=p: self.file_mgr.reveal_in_folder(fpath))
            cl.addWidget(show_btn)

            self.table.setCellWidget(row, 4, cell)

        self.status_lbl.setText(f"Encontrados {len(results)} archivo(s).")
