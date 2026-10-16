"""
Invoice & Facturas Processing Skill for Vanessa.
Handles Mexican CFDI 3.3 & 4.0 XML invoices and PDF summaries:
- Parses UUID (Folio Fiscal), Emisor RFC & Nombre, Receptor, Fechas, Subtotal, IVA, Total.
- Organizes and scans invoice folders (~/Facturas, ~/Downloads).
- Generates structured Excel (.xlsx) expense reports using openpyxl.
- Generates executive financial summaries in Markdown or speech format.
"""
import os
import glob
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


class InvoiceSkill:
    def __init__(self, default_folder: Optional[str] = None):
        self.default_folder = default_folder or os.path.expanduser("~/Facturas")
        os.makedirs(self.default_folder, exist_ok=True)

    def parse_cfdi_xml(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parses a CFDI 3.3 or 4.0 XML file and extracts standardized invoice fields."""
        if not os.path.isfile(file_path):
            return None

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # CFDI namespaces
            ns = {
                'cfdi': 'http://www.sat.gob.mx/cfd/4',
                'cfdi33': 'http://www.sat.gob.mx/cfd/3',
                'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'
            }

            # Helper to retrieve attribute regardless of namespace version
            def get_attr(elem, *names, default=""):
                if elem is None:
                    return default
                for n in names:
                    if n in elem.attrib:
                        return elem.attrib[n]
                return default

            # Comprobante root attributes
            fecha = get_attr(root, 'Fecha', 'fecha')
            folio = get_attr(root, 'Folio', 'folio')
            serie = get_attr(root, 'Serie', 'serie')
            subtotal = float(get_attr(root, 'SubTotal', 'subTotal', default='0.0'))
            total = float(get_attr(root, 'Total', 'total', default='0.0'))
            moneda = get_attr(root, 'Moneda', 'moneda', default='MXN')
            tipo_comprobante = get_attr(root, 'TipoDeComprobante', 'tipoDeComprobante', default='I')

            # Emisor
            emisor_elem = root.find('.//{http://www.sat.gob.mx/cfd/4}Emisor') or root.find('.//{http://www.sat.gob.mx/cfd/3}Emisor')
            rfc_emisor = get_attr(emisor_elem, 'Rfc', 'rfc')
            nombre_emisor = get_attr(emisor_elem, 'Nombre', 'nombre')

            # Receptor
            receptor_elem = root.find('.//{http://www.sat.gob.mx/cfd/4}Receptor') or root.find('.//{http://www.sat.gob.mx/cfd/3}Receptor')
            rfc_receptor = get_attr(receptor_elem, 'Rfc', 'rfc')
            nombre_receptor = get_attr(receptor_elem, 'Nombre', 'nombre')

            # UUID from TimbreFiscalDigital
            tfd_elem = root.find('.//{http://www.sat.gob.mx/TimbreFiscalDigital}TimbreFiscalDigital')
            uuid = get_attr(tfd_elem, 'UUID', 'uuid', default=os.path.basename(file_path))

            # Conceptos summary
            conceptos = []
            for c in root.iter():
                tag = c.tag.split('}')[-1]
                if tag == 'Concepto':
                    desc = get_attr(c, 'Descripcion', 'descripcion')
                    imp = float(get_attr(c, 'Importe', 'importe', default='0.0'))
                    conceptos.append({"descripcion": desc, "importe": imp})

            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "uuid": uuid,
                "fecha": fecha,
                "folio": f"{serie}{folio}".strip() or "S/F",
                "emisor_rfc": rfc_emisor,
                "emisor_nombre": nombre_emisor or rfc_emisor,
                "receptor_rfc": rfc_receptor,
                "receptor_nombre": nombre_receptor or rfc_receptor,
                "subtotal": subtotal,
                "iva": max(0.0, total - subtotal),
                "total": total,
                "moneda": moneda,
                "tipo": tipo_comprobante,
                "conceptos": conceptos,
            }
        except Exception as e:
            print(f"[InvoiceSkill] Error procesando XML {file_path}: {e}")
            return None

    def scan_invoices(self, folder_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Scans folder for XML invoices and extracts all CFDI metadata."""
        folder = folder_path or self.default_folder
        if not os.path.exists(folder):
            return []

        xml_files = glob.glob(os.path.join(folder, "**/*.xml"), recursive=True)
        invoices = []
        for f in xml_files:
            parsed = self.parse_cfdi_xml(f)
            if parsed and parsed.get("total", 0) > 0:
                invoices.append(parsed)

        # Sort by fecha descending
        invoices.sort(key=lambda x: x.get("fecha", ""), reverse=True)
        return invoices

    def generate_excel_report(self, invoices: List[Dict[str, Any]], output_path: Optional[str] = None) -> str:
        """Generates an executive Excel workbook (.xlsx) summarizing invoices with beautiful styles."""
        if not OPENPYXL_AVAILABLE:
            raise RuntimeError("openpyxl no está instalado.")

        if not output_path:
            output_path = os.path.join(self.default_folder, "Reporte_Facturas_Vanessa.xlsx")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Resumen de Facturas"

        # Theme Colors: Anime Maid Royal Navy & Gold
        header_fill = PatternFill(start_color="1A2A40", end_color="1A2A40", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=16, bold=True, color="1A2A40")
        subtitle_font = Font(name="Calibri", size=10, italic=True, color="555555")
        bold_font = Font(name="Calibri", size=11, bold=True)
        regular_font = Font(name="Calibri", size=10)
        
        thin_border = Border(
            left=Side(style='thin', color="DDDDDD"),
            right=Side(style='thin', color="DDDDDD"),
            top=Side(style='thin', color="DDDDDD"),
            bottom=Side(style='thin', color="DDDDDD")
        )

        # Title Block
        ws["A1"] = "REPORTE DE FACTURAS Y GASTOS - ASISTENTE VANESSA"
        ws["A1"].font = title_font
        ws["A2"] = f"Generado autónomamente para Amo Víctor | Total comprobantes analizados: {len(invoices)}"
        ws["A2"].font = subtitle_font
        ws.row_dimensions[1].height = 25
        ws.row_dimensions[2].height = 18

        # Headers
        headers = ["Fecha", "Folio", "Emisor (Proveedor)", "RFC Emisor", "Concepto Principal", "Subtotal", "IVA", "Total", "Moneda", "UUID / Folio Fiscal"]
        start_row = 4
        ws.row_dimensions[start_row].height = 24

        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=start_row, column=col_idx, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        current_row = start_row + 1
        for inv in invoices:
            ws.row_dimensions[current_row].height = 20
            first_concept = inv["conceptos"][0]["descripcion"] if inv.get("conceptos") else "Comprobante Fiscal"

            ws.cell(row=current_row, column=1, value=inv.get("fecha", "")[:10]).alignment = Alignment(horizontal="center")
            ws.cell(row=current_row, column=2, value=inv.get("folio", "")).alignment = Alignment(horizontal="center")
            ws.cell(row=current_row, column=3, value=inv.get("emisor_nombre", ""))
            ws.cell(row=current_row, column=4, value=inv.get("emisor_rfc", "")).alignment = Alignment(horizontal="center")
            ws.cell(row=current_row, column=5, value=first_concept)
            
            # Numeric fields
            c_sub = ws.cell(row=current_row, column=6, value=inv.get("subtotal", 0.0))
            c_sub.number_format = '"$"#,##0.00'
            c_iva = ws.cell(row=current_row, column=7, value=inv.get("iva", 0.0))
            c_iva.number_format = '"$"#,##0.00'
            c_tot = ws.cell(row=current_row, column=8, value=inv.get("total", 0.0))
            c_tot.number_format = '"$"#,##0.00'

            ws.cell(row=current_row, column=9, value=inv.get("moneda", "MXN")).alignment = Alignment(horizontal="center")
            ws.cell(row=current_row, column=10, value=inv.get("uuid", "")).alignment = Alignment(horizontal="left")

            for col_idx in range(1, 11):
                ws.cell(row=current_row, column=col_idx).border = thin_border
                ws.cell(row=current_row, column=col_idx).font = regular_font

            current_row += 1

        # Summary Row (TOTALS)
        if invoices:
            ws.row_dimensions[current_row].height = 22
            ws.cell(row=current_row, column=5, value="TOTAL GENERAL:").font = bold_font
            ws.cell(row=current_row, column=5).alignment = Alignment(horizontal="right")
            
            c_sub_tot = ws.cell(row=current_row, column=6, value=f"=SUM(F{start_row+1}:F{current_row-1})")
            c_sub_tot.number_format = '"$"#,##0.00'
            c_sub_tot.font = bold_font

            c_iva_tot = ws.cell(row=current_row, column=7, value=f"=SUM(G{start_row+1}:G{current_row-1})")
            c_iva_tot.number_format = '"$"#,##0.00'
            c_iva_tot.font = bold_font

            c_tot_tot = ws.cell(row=current_row, column=8, value=f"=SUM(H{start_row+1}:H{current_row-1})")
            c_tot_tot.number_format = '"$"#,##0.00'
            c_tot_tot.font = bold_font

            gold_fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
            for c_idx in range(5, 9):
                ws.cell(row=current_row, column=c_idx).fill = gold_fill
                ws.cell(row=current_row, column=c_idx).border = thin_border

        # Adjust column widths dynamically
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or "")
                if len(val) > max_len:
                    max_len = len(val)
            ws.column_dimensions[col_letter].width = max(12, min(max_len + 3, 40))

        wb.save(output_path)
        return output_path

    def get_voice_summary(self, folder_path: Optional[str] = None) -> str:
        """Returns a natural, concise spoken summary for Amo Víctor."""
        invoices = self.scan_invoices(folder_path)
        if not invoices:
            return "Amo Víctor, revisé la carpeta de facturas pero aún no encontré archivos XML para analizar. Si gusta, puede colocarlos en la carpeta Facturas y los procesaré de inmediato. ✨"

        total_amount = sum(i["total"] for i in invoices)
        total_iva = sum(i["iva"] for i in invoices)
        count = len(invoices)
        top_vendor = invoices[0]["emisor_nombre"] if invoices else "desconocido"

        return (
            f"¡He analizado {count} facturas para usted, Amo Víctor! "
            f"El total acumulado es de ${total_amount:,.2f} pesos con un IVA de ${total_iva:,.2f}. "
            f"La factura más reciente es de {top_vendor}. ¿Desea que le genere el archivo Excel detallado? ✨"
        )
