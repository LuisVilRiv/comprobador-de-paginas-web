import io
import html
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # backend sin GUI, imprescindible en servidor
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, PageBreak, Image,
)


# ── Paleta de colores para las barras del histograma ──────────────────────────
_BAR_COLORS = ["#6366f1", "#22d3ee", "#f59e0b", "#10b981", "#f43f5e"]


def _build_single_section_chart(k: str, label: str, series: list[dict], i: int) -> io.BytesIO:
    """Genera un gráfico individual de tendencia histórica para una sección."""
    # Configurar tamaño de gráfico individual amplio e impecable
    fig, ax = plt.subplots(figsize=(7.5, 2.2), facecolor="#1e1e2e")
    ax.set_facecolor("#1e1e2e")
    
    color = _BAR_COLORS[i % len(_BAR_COLORS)]
    vals = [s["data"].get(k, 0) for s in series]
    
    x_coords = np.arange(len(series))
    x_labels = [s["label"] for s in series]

    # Trazar la línea de tendencia
    ax.plot(
        x_coords, vals,
        marker="o", markersize=6, linewidth=2.5,
        color=color, zorder=3
    )
    
    # Anotación numérica sobre los marcadores
    for j, val in enumerate(vals):
        ax.text(
            j, val + 0.12, str(val),
            ha="center", va="bottom",
            fontsize=9.0, color="white", fontweight="bold",
        )
        
    # Título y formato visual de los ejes (legibilidad excepcional)
    ax.set_title(label, color="white", fontsize=11.5, fontweight="bold", pad=8)
    ax.set_xticks(x_coords)
    ax.set_xticklabels(x_labels, color="white", fontsize=8.5)
    ax.tick_params(colors="white", labelsize=8.5)
    
    # Incrementar ligeramente el límite de Y para evitar cortes
    max_v = max(vals) if vals else 0
    ax.set_ylim(0, max(max_v + 1.4, 3))
    
    # Bordes y cuadrícula
    ax.spines[:].set_color("#444466")
    ax.grid(color="#444466", linestyle="--", alpha=0.25, zorder=0)

    plt.tight_layout(pad=1.4)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf


# ── Generador principal ───────────────────────────────────────────────────────

def generate_audit_pdf(run, website, history: list[dict] | None = None) -> io.BytesIO:
    """Genera un reporte PDF profesional para una auditoría."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=50, leftMargin=50,
        topMargin=50, bottomMargin=50,
    )
    styles = getSampleStyleSheet()

    # Estilos personalizados (idempotentes)
    _add_style(styles, "CenterTitle",   parent="Title",    alignment=1, spaceAfter=20)
    _add_style(styles, "SectionHeader", parent="Heading2", spaceBefore=15, spaceAfter=10)
    _add_style(styles, "SubHeader",     parent="Heading3", spaceBefore=10, spaceAfter=5,
               textColor=colors.cadetblue)
    _add_style(styles, "BulletStyle",   parent="Normal",   spaceBefore=5, spaceAfter=5,
               leftIndent=20)

    elements = []

    # ── Título y Encabezado ───────────────────────────────────────────────────
    elements.append(Paragraph("Informe de Auditoría Web", styles["CenterTitle"]))

    fecha_str = run.started_at.strftime("%d/%m/%Y %H:%M:%S") if run.started_at else "N/A"

    header_data = [
        ["URL:",                 website.url if website else "Desconocida"],
        ["Etiqueta:",            (website.label if website else "N/A") or "N/A"],
        ["Fecha:",               fecha_str],
        ["Puntuación:",          f"{run.score or 0}/100"],
        ["Estrategia Utilizada:", (run.strategy_used or "Automática").upper()],
    ]
    tbl = Table(header_data, colWidths=[1.8 * inch, 3.7 * inch])
    tbl.setStyle(TableStyle([
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1),  colors.whitesmoke),
        ("FONTNAME",   (0, 0), (0, -1),  "Helvetica-Bold"),
        ("PADDING",    (0, 0), (-1, -1), 6),
    ]))
    elements.append(tbl)
    elements.append(Spacer(1, 0.4 * inch))

    # ── Propósito y Metodología ───────────────────────────────────────────────
    elements.append(Paragraph("Propósito y Metodología de la Auditoría", styles["SectionHeader"]))
    elements.append(Paragraph(
        "Este informe detalla los resultados de un análisis automatizado exhaustivo. "
        "A continuación se explican los pilares analizados y su importancia estratégica:",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 0.1 * inch))

    for title, desc in [
        ("🛡️ Seguridad:",               "Verificación de cabeceras HTTP, exposición de versiones del servidor y configuraciones críticas para prevenir ataques."),
        ("🔍 SEO:",                      "Evaluación de metadatos (Title, Description) y etiquetas de rastreo para asegurar la visibilidad en motores de búsqueda."),
        ("⚡ Rendimiento:",              "Análisis del tiempo de respuesta inicial y estabilidad del servidor para garantizar una experiencia de usuario fluida."),
        ("🏗️ Estructura HTML:",          "Revisión de la jerarquía semántica (H1-H6) y validación de estándares para una correcta lectura de navegadores."),
        ("♿ Accesibilidad y Contenido:", "Comprobación de textos alternativos (alt) en imágenes, densidad de texto y calidad del contenido visual."),
        ("🔗 Enlaces y Navegación:",     "Detección de enlaces rotos (404) y verificación de la integridad de los elementos interactivos del sitio."),
    ]:
        elements.append(Paragraph(f"<b>{title}</b> {desc}", styles["BulletStyle"]))

    elements.append(Spacer(1, 0.2 * inch))

    # ── Métricas Técnicas ─────────────────────────────────────────────────────
    elements.append(Paragraph("Métricas Técnicas", styles["SectionHeader"]))
    metrics_data = [
        ["Métrica",       "Valor"],
        ["Palabras",      run.word_count or 0],
        ["H1",            run.h1_count or 0],
        ["Imágenes",      run.image_count or 0],
        ["Enlaces",       run.links_count or 0],
        ["Formularios",   run.forms_count or 0],
        ["Tiempo de carga", f"{run.response_time_ms} ms" if run.response_time_ms else "N/A"],
    ]
    mt = Table(metrics_data, colWidths=[2.5 * inch, 3 * inch])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.cadetblue),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME",   (0, 0), (-1, 0),  "Helvetica-Bold"),
    ]))
    elements.append(mt)

    # ── Secciones Detalladas ──────────────────────────────────────────────────
    if run.sections:
        elements.append(PageBreak())
        elements.append(Paragraph("Análisis Detallado de Resultados", styles["SectionHeader"]))
        elements.append(Paragraph(f"Metodología aplicada: {run.strategy_used or 'Híbrida'}", styles["Italic"]))
        elements.append(Spacer(1, 0.1 * inch))

        for sec in run.sections:
            elements.append(Paragraph(f"🔍 {sec.section_label or sec.section_key}", styles["SubHeader"]))
            status_color = colors.green if sec.passed else colors.red
            sec_detail = [
                ["Descripción de la Prueba:", Paragraph(html.escape(sec.check_description or ""), styles["Normal"])],
                ["Resultado obtenido:",       Paragraph(html.escape(sec.result_description or ""), styles["Normal"])],
                ["Estado:", Paragraph(
                    f"<b>{'CORRECTO' if sec.passed else 'INCIDENCIAS DETECTADAS'}</b>",
                    ParagraphStyle(
                        name=f"st_{sec.section_key}",
                        parent=styles["Normal"],
                        textColor=status_color,
                    ),
                )],
                ["Total incidencias:", str(sec.issue_count or 0)],
            ]
            t = Table(sec_detail, colWidths=[1.8 * inch, 3.7 * inch])
            t.setStyle(TableStyle([
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN",     (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1),  colors.whitesmoke),
                ("FONTNAME",   (0, 0), (0, -1),  "Helvetica-Bold"),
                ("PADDING",    (0, 0), (-1, -1), 5),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.15 * inch))

    # ── Gráficas de Evolución Histórica (Una debajo de otra) ───────────────────
    if run.sections and history is not None:
        elements.append(PageBreak())
        elements.append(Paragraph(
            "Evolución de Incidencias por Sección",
            styles["SectionHeader"],
        ))
        n_prev = len(history)
        subtitle = (
            f"Comparativa entre las {n_prev} auditoría{'s' if n_prev != 1 else ''} "
            f"anterior{'es' if n_prev != 1 else ''} y la auditoría actual."
            if n_prev > 0
            else "No hay auditorías anteriores con éxito. Se muestra solo el resultado actual."
        )
        elements.append(Paragraph(subtitle, styles["Normal"]))
        elements.append(Spacer(1, 0.15 * inch))

        # Unión de todas las section_keys conocidas
        all_keys: list[str] = []
        key_to_label: dict[str, str] = {}
        for sec in run.sections:
            k = sec.section_key
            if k not in key_to_label:
                all_keys.append(k)
                key_to_label[k] = sec.section_label or k

        if all_keys:
            # Construir series: historial + actual
            series: list[dict] = []
            for h in history:
                series.append({
                    "label": h["date"],
                    "data": {k: h["sections"].get(k, {}).get("issue_count", 0) for k in all_keys},
                })
            current_data = {sec.section_key: (sec.issue_count or 0) for sec in run.sections}
            series.append({
                "label": "Actual",
                "data": {k: current_data.get(k, 0) for k in all_keys},
            })

            # Generar cada gráfica individual y añadirla al flujo del PDF (una debajo de otra)
            for i, k in enumerate(all_keys):
                label = key_to_label[k]
                chart_buf = _build_single_section_chart(k, label, series, i)
                img = Image(chart_buf, width=6.5 * inch, height=2.1 * inch)
                elements.append(img)
                elements.append(Spacer(1, 0.12 * inch))
        else:
            elements.append(Paragraph(
                "No se pudo generar la gráfica (sin datos de secciones).",
                styles["Normal"],
            ))

        elements.append(Spacer(1, 0.15 * inch))
        elements.append(Paragraph(
            "<b>Nota:</b> Cada gráfico muestra de forma aislada la tendencia histórica de incidencias "
            "para esa sección en particular (de izquierda a derecha). Una curva descendente indica "
            "una mejora (reducción de incidencias), mientras que una ascendente denota una regresión.",
            styles["BulletStyle"],
        ))

    # ── Hallazgos e Incidencias ───────────────────────────────────────────────
    if run.issues:
        elements.append(PageBreak())
        elements.append(Paragraph("Resumen de Hallazgos y Sugerencias", styles["SectionHeader"]))
        issue_data = [["Severidad", "Categoría", "Mensaje Detallado"]]
        for issue in sorted(run.issues, key=lambda x: str(x.severity or "")):
            issue_data.append([
                str(issue.severity or "INFO").upper(),
                str(issue.category or "GENERAL").upper(),
                Paragraph(html.escape(issue.message or ""), styles["Normal"]),
            ])
        it = Table(issue_data, colWidths=[1 * inch, 1 * inch, 3.5 * inch])
        it.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.firebrick),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
            ("FONTNAME",   (0, 0), (-1, 0),  "Helvetica-Bold"),
        ]))
        elements.append(it)

    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_client_report(client_name: str, websites_data: list[dict]) -> io.BytesIO:
    """Genera un reporte PDF consolidado para un cliente con sus sitios web."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=50, leftMargin=50,
        topMargin=50, bottomMargin=50,
    )
    styles = getSampleStyleSheet()
    _add_style(styles, "CenterTitle",   parent="Title",    alignment=1, spaceAfter=20)
    _add_style(styles, "SectionHeader", parent="Heading2", spaceBefore=15, spaceAfter=10)
    _add_style(styles, "SubHeader",     parent="Heading3", spaceBefore=10, spaceAfter=5, textColor=colors.cadetblue)
    _add_style(styles, "BulletStyle",   parent="Normal",   spaceBefore=5, spaceAfter=5, leftIndent=20)
    
    elements = []
    
    # Portada del cliente
    elements.append(Spacer(1, 2 * inch))
    elements.append(Paragraph(f"Reporte Consolidado de Auditoría Web", styles["CenterTitle"]))
    elements.append(Paragraph(f"Cliente: {client_name}", styles["CenterTitle"]))
    elements.append(Paragraph(f"Fecha de Generación: {datetime.now().strftime('%d/%m/%Y')}", styles["CenterTitle"]))
    elements.append(PageBreak())
    
    for w_data in websites_data:
        website = w_data["website"]
        run = w_data["latest_run"]
        history = w_data["history"]
        
        elements.append(Paragraph(f"Sitio Web: {website.url}", styles["SectionHeader"]))
        
        if not run:
            elements.append(Paragraph("No hay auditorías registradas para esta URL.", styles["Normal"]))
            elements.append(PageBreak())
            continue
            
        fecha_str = run.started_at.strftime("%d/%m/%Y %H:%M:%S") if run.started_at else "N/A"
        header_data = [
            ["URL:",                 website.url if website else "Desconocida"],
            ["Etiqueta:",            (website.label if website else "N/A") or "N/A"],
            ["Última Auditoría:",    fecha_str],
            ["Puntuación:",          f"{run.score or 0}/100"],
            ["Incidencias Críticas:", str(len([i for i in run.issues if i.severity == "critical"]))],
        ]
        tbl = Table(header_data, colWidths=[1.8 * inch, 3.7 * inch])
        tbl.setStyle(TableStyle([
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1),  colors.whitesmoke),
            ("FONTNAME",   (0, 0), (0, -1),  "Helvetica-Bold"),
            ("PADDING",    (0, 0), (-1, -1), 6),
        ]))
        elements.append(tbl)
        elements.append(Spacer(1, 0.4 * inch))
        
        # Graficas de Evolución Histórica
        if run.sections and history is not None:
            elements.append(Paragraph("Evolución de Incidencias (Últimas 5 Ejecuciones)", styles["SubHeader"]))
            
            all_keys: list[str] = []
            key_to_label: dict[str, str] = {}
            for sec in run.sections:
                k = sec.section_key
                if k not in key_to_label:
                    all_keys.append(k)
                    key_to_label[k] = sec.section_label or k

            if all_keys:
                series: list[dict] = []
                for h in history:
                    series.append({
                        "label": h["date"],
                        "data": {k: h["sections"].get(k, {}).get("issue_count", 0) for k in all_keys},
                    })
                current_data = {sec.section_key: (sec.issue_count or 0) for sec in run.sections}
                series.append({
                    "label": "Actual",
                    "data": {k: current_data.get(k, 0) for k in all_keys},
                })

                for i, k in enumerate(all_keys):
                    label = key_to_label[k]
                    chart_buf = _build_single_section_chart(k, label, series, i)
                    img = Image(chart_buf, width=6.5 * inch, height=2.1 * inch)
                    elements.append(img)
                    elements.append(Spacer(1, 0.12 * inch))
            else:
                elements.append(Paragraph("No se pudo generar la gráfica (sin datos de secciones).", styles["Normal"]))

        # Resumen de Issues
        if run.issues:
            elements.append(Paragraph("Resumen de Hallazgos Críticos y Altos", styles["SubHeader"]))
            issue_data = [["Severidad", "Mensaje Detallado"]]
            critical_issues = [i for i in run.issues if i.severity in ("critical", "high")]
            if critical_issues:
                for issue in sorted(critical_issues, key=lambda x: str(x.severity or "")):
                    issue_data.append([
                        str(issue.severity or "INFO").upper(),
                        Paragraph(html.escape(issue.message or ""), styles["Normal"]),
                    ])
                it = Table(issue_data, colWidths=[1.5 * inch, 4.0 * inch])
                it.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.firebrick),
                    ("TEXTCOLOR",  (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN",     (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME",   (0, 0), (-1, 0),  "Helvetica-Bold"),
                ]))
                elements.append(it)
            else:
                elements.append(Paragraph("No se encontraron hallazgos críticos ni altos en la última ejecución.", styles["Normal"]))
                
        elements.append(PageBreak())

    doc.build(elements)
    buffer.seek(0)
    return buffer


# ── Helpers ───────────────────────────────────────────────────────────────────

def _add_style(styles, name, parent="Normal", **kwargs):
    """Añade un ParagraphStyle solo si no existe ya."""
    if name not in styles:
        parent_style = styles[parent]
        styles.add(ParagraphStyle(name=name, parent=parent_style, **kwargs))
