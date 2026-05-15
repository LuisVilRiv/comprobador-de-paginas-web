from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, ListFlowable, ListItem
from datetime import datetime
import io
import html

def generate_audit_pdf(run, website) -> io.BytesIO:
    """Genera un reporte PDF profesional para una auditoría."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    if 'CenterTitle' not in styles:
        styles.add(ParagraphStyle(name='CenterTitle', parent=styles['Title'], alignment=1, spaceAfter=20))
    if 'SectionHeader' not in styles:
        styles.add(ParagraphStyle(name='SectionHeader', parent=styles['Heading2'], spaceBefore=15, spaceAfter=10))
    if 'SubHeader' not in styles:
        styles.add(ParagraphStyle(name='SubHeader', parent=styles['Heading3'], spaceBefore=10, spaceAfter=5, color=colors.cadetblue))
    if 'BulletStyle' not in styles:
        styles.add(ParagraphStyle(name='BulletStyle', parent=styles['Normal'], spaceBefore=5, spaceAfter=5, leftIndent=20))
    
    elements = []
    
    # ── Título y Encabezado ──────────────────────────────────────────────────
    elements.append(Paragraph("Informe de Auditoría Web", styles['CenterTitle']))
    
    fecha_str = run.started_at.strftime("%d/%m/%Y %H:%M:%S") if run.started_at else "N/A"
    
    data = [
        ["URL:", website.url if website else "Desconocida"],
        ["Etiqueta:", (website.label if website else "N/A") or "N/A"],
        ["Fecha:", fecha_str],
        ["Puntuación:", f"{run.score or 0}/100"],
        ["Estrategia Utilizada:", (run.strategy_used or "Automática").upper()],
    ]
    
    table = Table(data, colWidths=[1.8 * inch, 3.7 * inch])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.4 * inch))
    
    # ── NUEVA SECCIÓN: Propósito de la Auditoría ─────────────────────────────
    elements.append(Paragraph("Propósito y Metodología de la Auditoría", styles['SectionHeader']))
    elements.append(Paragraph(
        "Este informe detalla los resultados de un análisis automatizado exhaustivo. "
        "A continuación se explican los pilares analizados y su importancia estratégica:",
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.1 * inch))
    
    glossary = [
        ("🛡️ Seguridad:", "Verificación de cabeceras HTTP, exposición de versiones del servidor y configuraciones críticas para prevenir ataques."),
        ("🔍 SEO:", "Evaluación de metadatos (Title, Description) y etiquetas de rastreo para asegurar la visibilidad en motores de búsqueda."),
        ("⚡ Rendimiento:", "Análisis del tiempo de respuesta inicial y estabilidad del servidor para garantizar una experiencia de usuario fluida."),
        ("🏗️ Estructura HTML:", "Revisión de la jerarquía semántica (H1-H6) y validación de estándares para una correcta lectura de navegadores."),
        ("♿ Accesibilidad y Contenido:", "Comprobación de textos alternativos (alt) en imágenes, densidad de texto y calidad del contenido visual."),
        ("🔗 Enlaces y Navegación:", "Detección de enlaces rotos (404) y verificación de la integridad de los elementos interactivos del sitio.")
    ]
    
    for title, desc in glossary:
        elements.append(Paragraph(f"<b>{title}</b> {desc}", styles['BulletStyle']))
    
    elements.append(Spacer(1, 0.2 * inch))
    
    # ── Resumen de Métricas ──────────────────────────────────────────────────
    elements.append(Paragraph("Métricas Técnicas", styles['SectionHeader']))
    metrics_data = [
        ["Métrica", "Valor"],
        ["Palabras", run.word_count or 0],
        ["H1", run.h1_count or 0],
        ["Imágenes", run.image_count or 0],
        ["Enlaces", run.links_count or 0],
        ["Formularios", run.forms_count or 0],
        ["Tiempo de carga", f"{run.response_time_ms} ms" if run.response_time_ms else "N/A"],
    ]
    metrics_table = Table(metrics_data, colWidths=[2.5 * inch, 3 * inch])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.cadetblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    elements.append(metrics_table)
    
    # ── Secciones de Auditoría Detalladas ────────────────────────────────────
    if run.sections:
        elements.append(PageBreak())
        elements.append(Paragraph("Análisis Detallado de Resultados", styles['SectionHeader']))
        elements.append(Paragraph(f"Metodología aplicada: {run.strategy_used or 'Híbrida'}", styles['Italic']))
        elements.append(Spacer(1, 0.1 * inch))
        
        for sec in run.sections:
            elements.append(Paragraph(f"🔍 {sec.section_label or sec.section_key}", styles['SubHeader']))
            
            status_color = colors.green if sec.passed else colors.red
            sec_detail = [
                ["Descripción de la Prueba:", Paragraph(html.escape(sec.check_description or ""), styles['Normal'])],
                ["Resultado obtenido:", Paragraph(html.escape(sec.result_description or ""), styles['Normal'])],
                ["Estado:", Paragraph(f"<b>{'CORRECTO' if sec.passed else 'INCIDENCIAS DETECTADAS'}</b>", ParagraphStyle(name=f'st_{sec.section_key}', parent=styles['Normal'], textColor=status_color))],
                ["Total incidencias:", str(sec.issue_count or 0)]
            ]
            
            t = Table(sec_detail, colWidths=[1.8 * inch, 3.7 * inch])
            t.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.15 * inch))
    
    # ── Listado Completo de Incidencias ─────────────────────────────────────
    if run.issues:
        elements.append(PageBreak())
        elements.append(Paragraph("Resumen de Hallazgos y Sugerencias", styles['SectionHeader']))
        issue_data = [["Severidad", "Categoría", "Mensaje Detallado"]]
        
        sorted_issues = sorted(run.issues, key=lambda x: str(x.severity or ""))
        
        for issue in sorted_issues:
            escaped_msg = html.escape(issue.message or "")
            msg_p = Paragraph(escaped_msg, styles['Normal'])
            issue_data.append([
                str(issue.severity or "INFO").upper(), 
                str(issue.category or "GENERAL").upper(), 
                msg_p
            ])
            
        issue_table = Table(issue_data, colWidths=[1 * inch, 1 * inch, 3.5 * inch])
        issue_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.firebrick),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(issue_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer
