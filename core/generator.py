"""
Generative AI Artifacts Generator for Vanessa.
Enables creation of:
- Formatted Excel Spreadsheets (.xlsx) via openpyxl
- Rich Word Documents (.docx) via python-docx
- SQLite Databases (.db) & .sql schemas
- Source Code files in Python, JS, Bash, etc.
"""
import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from docx import Document
from docx.shared import Inches, Pt, RGBColor

class ArtifactGenerator:
    def __init__(self, brain=None):
        self.brain = brain
        self.docs_dir = os.path.expanduser("~/Documentos")
        if not os.path.exists(self.docs_dir):
            self.docs_dir = os.path.expanduser("~/Documents")
        if not os.path.exists(self.docs_dir):
            self.docs_dir = os.path.expanduser("~")

    def _get_unique_path(self, filename: str, ext: str) -> str:
        safe_name = "".join(c for c in filename if c.isalnum() or c in (' ', '_', '-')).strip()
        if not safe_name:
            safe_name = f"Generado_{int(datetime.now().timestamp())}"
        base = os.path.join(self.docs_dir, f"{safe_name}.{ext}")
        counter = 1
        final_path = base
        while os.path.exists(final_path):
            final_path = os.path.join(self.docs_dir, f"{safe_name}_{counter}.{ext}")
            counter += 1
        return final_path

    # === 1. EXCEL GENERATION (.xlsx) ===
    def create_excel(
        self,
        title: str,
        headers: List[str],
        rows: List[List[Any]],
        sheet_name: str = "Datos"
    ) -> str:
        """Creates a beautifully styled Excel workbook."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_name

        # Header styling
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        center_align = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        # Write Title row
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        title_cell = ws.cell(row=1, column=1, value=title.upper())
        title_cell.font = Font(name="Segoe UI", size=14, bold=True, color="1E3A8A")
        title_cell.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[1].height = 28

        # Write Headers
        ws.row_dimensions[3].height = 24
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = thin_border

        # Write Rows with alternating fills
        alt_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        for row_idx, row_data in enumerate(rows, 4):
            ws.row_dimensions[row_idx].height = 20
            is_alt = (row_idx % 2 == 0)
            for col_idx, val in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.font = Font(name="Segoe UI", size=10)
                cell.border = thin_border
                if is_alt:
                    cell.fill = alt_fill

        # Auto-adjust column width
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        file_path = self._get_unique_path(title, "xlsx")
        wb.save(file_path)
        return file_path

    # === 2. DATABASE GENERATION (.db & .sql) ===
    def create_database(self, db_name: str, schema_sql: str, seed_sql: Optional[str] = None) -> Dict[str, str]:
        """Creates a standalone SQLite database and exports the .sql schema."""
        db_path = self._get_unique_path(db_name, "db")
        sql_path = db_path.replace(".db", ".sql")

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.executescript(schema_sql)
            if seed_sql:
                cursor.executescript(seed_sql)
            conn.commit()

        with open(sql_path, "w", encoding="utf-8") as f:
            f.write(f"-- Schema para {db_name}\n-- Generado por Vanessa\n\n")
            f.write(schema_sql + "\n\n")
            if seed_sql:
                f.write(seed_sql + "\n")

        return {"db_path": db_path, "sql_path": sql_path}

    # === 3. CODE GENERATION ===
    def create_code_file(self, filename: str, code_content: str) -> str:
        """Saves generated code into workspace or user directory."""
        dest_path = os.path.join(self.docs_dir, filename)
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(code_content)
        return dest_path
