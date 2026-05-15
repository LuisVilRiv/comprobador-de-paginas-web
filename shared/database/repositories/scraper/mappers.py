"""
scraper/mappers.py — Lógica de transformación y mapeo para los resultados de auditoría.
"""
from typing import Any

def classify_severity(message: str) -> str:
    """Clasifica la severidad de una incidencia basada en palabras clave."""
    m = message.lower()
    if any(k in m for k in (
        "critico", "dato sensible", "panel admin",
        "sin autenticacion", "enlace roto", "imagen rota",
    )):
        return "critical"
    if any(k in m for k in ("falta cabecera", "hsts", "csp", "mixed content", "id duplicado")):
        return "high"
    if any(k in m for k in ("falta canonical", "favicon", "open graph", "lorem ipsum")):
        return "medium"
    if "sin incidencias" in m or m.startswith("ok"):
        return "ok"
    return "low"

def build_audit_sections(report: dict | None, scrape_metadata: dict) -> list[dict[str, Any]]:
    """Construye la lista de secciones de auditoría para persistencia."""
    if not report:
        return [{
            "section_key":        "audit_execution",
            "section_label":      "Ejecución de auditoría",
            "passed":             False,
            "status":             "failed",
            "issue_count":        1,
            "check_description":  "Validar que la auditoría se ejecute correctamente.",
            "result_description": "La auditoría no generó informe utilizable.",
            "details_json":       {"status_code": scrape_metadata.get("status_code")},
        }]

    section_specs = [
        ("security",  "Seguridad",  "security_issues",  "Revisar HTTPS, cabeceras y exposición sensible."),
        ("seo",       "SEO",        "seo_issues",        "Comprobar metadatos SEO y semántica."),
        ("content",   "Contenido",  "content_issues",    "Detectar contenido tóxico o de baja calidad."),
        ("images",    "Imágenes",   "image_issues",      "Comprobar imágenes etiquetadas y optimizadas."),
        ("structure", "Estructura", "structure_issues",  "Verificar semántica y estructura HTML."),
        ("links",     "Links",      "link_issues",       "Revisar enlaces rotos y redirecciones."),
        ("buttons",   "Botones",    "button_issues",     "Analizar accesibilidad interactiva."),
        ("technical", "Técnico",    "technical_issues",  "Comprobar errores técnicos y de runtime."),
    ]
    sections = [{
        "section_key":        "audit_execution",
        "section_label":      "Ejecución de auditoría",
        "passed":             True,
        "status":             "ok",
        "issue_count":        0,
        "check_description":  "Validar que la auditoría se ejecutó correctamente.",
        "result_description": "Ejecución correcta.",
        "details_json":       {"status_code": scrape_metadata.get("status_code")},
    }]
    for key, label, issue_key, description in section_specs:
        issues = (report or {}).get(issue_key, [])
        passed = len(issues) == 0
        sections.append({
            "section_key":        key,
            "section_label":      label,
            "passed":             passed,
        "status":             "ok",
        "issue_count":        len(issues),
        "check_description":  description,
        "result_description": ("No se detectan problemas."
                               if passed else f"Se han encontrado {len(issues)} incidencias."),
            "details_json":       {"issues": issues},
        })
    return sections

def safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
