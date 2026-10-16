"""
Document & Proposal Generation Skill for Vanessa.
Uses python-docx to generate executive-grade Word documents (.docx):
- Commercial and technical project proposals
- Formal quotes, service agreements, and executive deliverables
- Automatic calculation of milestone tables, deliverables, and budgets
- Professional layout and formatting with headers, tables, and accents
"""
import os
import datetime
from typing import Dict, Any, List, Optional

try:
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement, parse_xml
    from docx.oxml.ns import qn, nsdecls
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class DocumentSkill:
    def __init__(self, default_folder: Optional[str] = None):
        self.default_folder = default_folder or os.path.expanduser("~/Documentos")
        os.makedirs(self.default_folder, exist_ok=True)

    def _set_cell_background(self, cell, hex_color: str):
        """Sets the background color of a table cell."""
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
        cell._tc.get_or_add_tcPr().append(shading)

    def _set_cell_margins(self, cell, top=100, bottom=100, left=150, right=150):
        """Sets padding inside a table cell."""
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = OxmlElement('w:tcMar')
        for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
            node = OxmlElement(m)
            node.set(qn('w:w'), str(val))
            node.set(qn('w:type'), 'dxa')
            tcMar.append(node)
        tcPr.append(tcMar)

    def create_executive_proposal(
        self,
        client_name: str,
        project_title: str,
        description: str,
        deliverables: Optional[List[str]] = None,
        budget_items: Optional[List[Dict[str, Any]]] = None,
        timeline_weeks: int = 4,
        output_filename: Optional[str] = None
    ) -> str:
        """Generates a comprehensive executive business proposal in Word .docx format."""
        if not DOCX_AVAILABLE:
            raise RuntimeError("python-docx no está disponible en el entorno.")

        doc = docx.Document()

        # Page Setup (Standard Letter, 1 inch margins)
        for section in doc.sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(1.0)

        # Color Palette: Deep Executive Blue and Warm Charcoal
        COLOR_PRIMARY = RGBColor(26, 42, 64)       # #1A2A40
        COLOR_ACCENT = RGBColor(197, 160, 89)      # Warm Gold
        COLOR_BODY = RGBColor(50, 50, 50)          # Soft Black
        HEX_HEADER_BG = "1A2A40"
        HEX_ALT_BG = "F7F9FC"

        # Document Header
        p_top = doc.add_paragraph()
        run_company = p_top.add_run("VÍCTOR & ASSOCIATES | SOLUCIONES TECNOLÓGICAS")
        run_company.font.name = "Arial"
        run_company.font.size = Pt(9)
        run_company.font.bold = True
        run_company.font.color.rgb = COLOR_ACCENT
        p_top.alignment = WD_ALIGN_PARAGRAPH.RIGHT

        # Document Title
        p_title = doc.add_paragraph()
        run_title = p_title.add_run(f"PROPUESTA TÉCNICO-COMERCIAL:\n{project_title.upper()}")
        run_title.font.name = "Arial"
        run_title.font.size = Pt(22)
        run_title.font.bold = True
        run_title.font.color.rgb = COLOR_PRIMARY
        p_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_title.paragraph_format.space_after = Pt(4)

        # Subtitle & Metadata
        date_str = datetime.datetime.now().strftime("%d de %B de %Y")
        p_meta = doc.add_paragraph()
        r_meta = p_meta.add_run(f"Preparado para: {client_name}  |  Fecha: {date_str}  |  Vigencia: 30 días")
        r_meta.font.name = "Arial"
        r_meta.font.size = Pt(10)
        r_meta.font.italic = True
        r_meta.font.color.rgb = RGBColor(100, 100, 100)
        p_meta.paragraph_format.space_after = Pt(24)

        # 1. Executive Summary
        h1 = doc.add_heading(level=1)
        r_h1 = h1.add_run("1. Resumen Ejecutivo")
        r_h1.font.name = "Arial"
        r_h1.font.color.rgb = COLOR_PRIMARY
        r_h1.font.size = Pt(14)
        r_h1.font.bold = True

        p_desc = doc.add_paragraph()
        r_desc = p_desc.add_run(description)
        r_desc.font.name = "Arial"
        r_desc.font.size = Pt(10.5)
        r_desc.font.color.rgb = COLOR_BODY
        p_desc.paragraph_format.line_spacing = 1.15
        p_desc.paragraph_format.space_after = Pt(14)

        # 2. Scope & Key Deliverables
        h2 = doc.add_heading(level=1)
        r_h2 = h2.add_run("2. Alcance y Entregables del Proyecto")
        r_h2.font.name = "Arial"
        r_h2.font.color.rgb = COLOR_PRIMARY
        r_h2.font.size = Pt(14)
        r_h2.font.bold = True

        if not deliverables:
            deliverables = [
                "Arquitectura e implementación técnica del sistema.",
                "Integración con bases de datos y flujos de automatización.",
                "Pruebas de validación, control de calidad y despliegue.",
                "Documentación operativa completa y sesión de transferencia técnica."
            ]

        for d in deliverables:
            p_bullet = doc.add_paragraph(style='List Bullet')
            r_bullet = p_bullet.add_run(d)
            r_bullet.font.name = "Arial"
            r_bullet.font.size = Pt(10)
            r_bullet.font.color.rgb = COLOR_BODY
            p_bullet.paragraph_format.space_after = Pt(3)

        doc.add_paragraph().paragraph_format.space_after = Pt(12)

        # 3. Timeline & Execution Phases
        h3 = doc.add_heading(level=1)
        r_h3 = h3.add_run("3. Cronograma de Trabajo")
        r_h3.font.name = "Arial"
        r_h3.font.color.rgb = COLOR_PRIMARY
        r_h3.font.size = Pt(14)
        r_h3.font.bold = True

        p_time = doc.add_paragraph()
        r_time = p_time.add_run(
            f"El proyecto contempla un ciclo de ejecución de aproximadamente {timeline_weeks} semanas, "
            f"estructurado bajo metodología ágil para garantizar iteraciones continuas y visibilidad total."
        )
        r_time.font.name = "Arial"
        r_time.font.size = Pt(10.5)
        r_time.font.color.rgb = COLOR_BODY
        p_time.paragraph_format.space_after = Pt(14)

        # 4. Investment & Budget Table
        h4 = doc.add_heading(level=1)
        r_h4 = h4.add_run("4. Propuesta Económica")
        r_h4.font.name = "Arial"
        r_h4.font.color.rgb = COLOR_PRIMARY
        r_h4.font.size = Pt(14)
        r_h4.font.bold = True

        if not budget_items:
            budget_items = [
                {"item": "Fase 1: Análisis, Diseño y Arquitectura", "cant": 1, "precio": 12500.0},
                {"item": "Fase 2: Desarrollo Core y Automatizaciones", "cant": 1, "precio": 28000.0},
                {"item": "Fase 3: Pruebas, QA y Despliegue en Servidor", "cant": 1, "precio": 14500.0},
                {"item": "Soporte, Mantenimiento y Capacitación (30 días)", "cant": 1, "precio": 5000.0}
            ]

        # Create Table
        table = doc.add_table(rows=1, cols=4)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_cells = table.rows[0].cells
        col_names = ["Concepto / Entregable", "Cantidad", "Precio Unitario", "Subtotal"]
        
        for idx, name in enumerate(col_names):
            hdr_cells[idx].text = name
            self._set_cell_background(hdr_cells[idx], HEX_HEADER_BG)
            p = hdr_cells[idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.font.name = "Arial"
                run.font.bold = True
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(255, 255, 255)

        total_neto = 0.0
        for i, b in enumerate(budget_items):
            row_cells = table.add_row().cells
            cant = b.get("cant", 1)
            precio = float(b.get("precio", 0.0))
            sub = cant * precio
            total_neto += sub

            row_cells[0].text = b.get("item", "Servicio")
            row_cells[1].text = str(cant)
            row_cells[2].text = f"${precio:,.2f}"
            row_cells[3].text = f"${sub:,.2f}"

            if i % 2 == 1:
                for c in row_cells:
                    self._set_cell_background(c, HEX_ALT_BG)

            for col_i, cell in enumerate(row_cells):
                p = cell.paragraphs[0]
                if col_i in (1, 2, 3):
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                for r in p.runs:
                    r.font.name = "Arial"
                    r.font.size = Pt(9.5)
                    r.font.color.rgb = COLOR_BODY

        # Add Total Row
        iva = total_neto * 0.16
        gran_total = total_neto + iva

        for label, val in [("SUBTOTAL", total_neto), ("I.V.A. (16%)", iva), ("TOTAL GENERAL (MXN)", gran_total)]:
            tot_row = table.add_row().cells
            tot_row[2].text = label
            tot_row[3].text = f"${val:,.2f}"
            tot_row[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            tot_row[3].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            for c_idx in (2, 3):
                tot_row[c_idx].paragraphs[0].runs[0].font.bold = True
                tot_row[c_idx].paragraphs[0].runs[0].font.size = Pt(10)
                if label.startswith("TOTAL GENERAL"):
                    self._set_cell_background(tot_row[c_idx], "FFF3CD")

        doc.add_paragraph().paragraph_format.space_after = Pt(20)

        # 5. Terms & Acceptance
        h5 = doc.add_heading(level=1)
        r_h5 = h5.add_run("5. Términos de Aceptación y Forma de Pago")
        r_h5.font.name = "Arial"
        r_h5.font.color.rgb = COLOR_PRIMARY
        r_h5.font.size = Pt(14)
        r_h5.font.bold = True

        p_terms = doc.add_paragraph()
        r_terms = p_terms.add_run(
            "• Anticipo del 50% al inicio del proyecto y firma del presente documento.\n"
            "• Liquidación del 50% restante a la entrega formal en ambiente de producción.\n"
            "• Cualquier cambio fuera del alcance detallado se cotizará como módulo complementario."
        )
        r_terms.font.name = "Arial"
        r_terms.font.size = Pt(10)
        r_terms.font.color.rgb = COLOR_BODY
        p_terms.paragraph_format.space_after = Pt(36)

        # Signature Block
        sig_table = doc.add_table(rows=1, cols=2)
        sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        sig_cells = sig_table.rows[0].cells

        sig_cells[0].text = "______________________________\nAceptado por el Cliente\nNombre y Firma"
        sig_cells[1].text = "______________________________\nVíctor (Líder de Proyecto)\nVanessa AI Systems"

        for sc in sig_cells:
            p = sc.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.name = "Arial"
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(100, 100, 100)

        # Save document
        if not output_filename:
            safe_title = "".join(c for c in project_title if c.isalnum() or c in (" ", "_", "-")).strip()
            output_filename = f"Propuesta_{safe_title}_{datetime.date.today().strftime('%Y%m%d')}.docx"

        full_path = os.path.join(self.default_folder, output_filename)
        doc.save(full_path)
        return full_path
