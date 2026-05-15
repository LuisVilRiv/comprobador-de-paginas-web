"""
scoring.py — Cálculo de puntuación, estado y gate de release.
Extraído de QualityAuditor._calculate_score, _status_from_score
y _evaluate_release_gate.
"""
from config import settings

def calculate_score(
    security_issues:  list[str],
    seo_issues:       list[str],
    content_issues:   list[str],
    image_issues:     list[str],
    structure_issues: list[str],
    link_issues:      list[str],
    button_issues:    list[str],
    technical_issues: list[str],
) -> int:
    categories = {
        "security":  (security_issues,  30.0),
        "seo":       (seo_issues,        20.0),
        "content":   (content_issues,    20.0),
        "images":    (image_issues,      15.0),
        "structure": (structure_issues,  15.0),
        "links":     (link_issues,       20.0),
        "buttons":   (button_issues,     15.0),
        "technical": (technical_issues,  20.0),
    }

    _CRITICAL = (
        "dato sensible", "panel admin", "clave", "password", "token", "roto",
        "fallo al", "error de consola", "no existe en el dom", "bloqueo",
        "vulnerabilidad", "sin autenticacion", "discurso de odio", "explicito",
        "malsonante", "firewall_block",
    )
    _HIGH = (
        "falta cabecera", "hsts", "csp", "x-frame", "integrity (sri)",
        "falta doctype", "falta title", "falta description", "sin label",
        "viewport", "mixed content", "id duplicado", "contenido mixto",
    )
    _MEDIUM = (
        "falta canonical", "favicon", "alt de imagen", "heredado",
        "loading=\"lazy\"", "jerarquía", "semántica", "noopener",
        "lorem ipsum", "relleno", "hreflang",
    )

    total_deduction = 0.0
    for _, (issue_list, cat_limit) in categories.items():
        cat_deduction = 0.0
        type_counts: dict[str, int] = {}
        for issue in issue_list:
            issue_l = issue.lower()
            if "sin incidencias" in issue_l:
                continue
            base_weight = 0.1
            issue_type  = "generic"
            for k in _CRITICAL:
                if k in issue_l:
                    base_weight = 3.0; issue_type = k; break
            if issue_type == "generic":
                for k in _HIGH:
                    if k in issue_l:
                        base_weight = 1.5; issue_type = k; break
            if issue_type == "generic":
                for k in _MEDIUM:
                    if k in issue_l:
                        base_weight = 0.5; issue_type = k; break
            count      = type_counts.get(issue_type, 0)
            multiplier = 1.0 if count < 3 else (0.5 if count < 8 else 0.1)
            cat_deduction += base_weight * multiplier
            type_counts[issue_type] = count + 1
        total_deduction += min(cat_deduction, cat_limit)

    return max(0, min(100, int(100.0 - total_deduction)))


def status_from_score(score: int) -> str:
    if score >= settings.AUDIT_SCORE_EXCELLENT_THRESHOLD: return "excelente"
    if score >= settings.AUDIT_SCORE_GOOD_THRESHOLD: return "bueno"
    if score >= 50: return "mejorable"
    return "crítico"


def evaluate_release_gate(
    score:            int,
    security_issues:  list[str],
    content_issues:   list[str],
    link_issues:      list[str],
    technical_issues: list[str],
    image_issues:     list[str],
    button_issues:    list[str],
) -> tuple[bool, list[str]]:
    blockers: list[str] = []

    if score < settings.AUDIT_RELEASE_GATE_MIN_SCORE:
        blockers.append(f"Puntuación global insuficiente para producción ({score}/{settings.AUDIT_RELEASE_GATE_MIN_SCORE}).")

    security_critical = (
        "dato sensible", "http en lugar de https",
        "panel de administración accesible", "sin autenticacion", "sin autenticación",
    )
    if any(any(f in i.lower() for f in security_critical) for i in security_issues):
        blockers.append("Incidencias de seguridad críticas detectadas.")

    strong_content_flags = (
        "contenido explícito", "porno", "nsfw", "patrón '",
        "incoherencia heurística", "discurso de odio", "palabra malsonante",
    )
    if any(any(f in i.lower() for f in strong_content_flags) for i in content_issues):
        blockers.append("Contenido sensible o inadecuado detectado.")

    broken_links = [i for i in link_issues if "enlace roto confirmado" in i.lower()]
    if broken_links:
        blockers.append(f"Enlaces rotos confirmados ({len(broken_links)}).")

    broken_images = [i for i in image_issues if "imagen rota" in i.lower()]
    if broken_images:
        blockers.append(f"Imágenes rotas detectadas ({len(broken_images)}).")

    critical_tech = ("mixed content", "contenido mixto", "id duplicado", "doctype", "charset", "script bloqueante")
    if any(any(f in i.lower() for f in critical_tech) for i in technical_issues):
        blockers.append("Incidencias técnicas críticas detectadas.")

    form_failures = [i for i in button_issues if "fallo al probar el action" in i.lower()]
    if form_failures:
        blockers.append(f"Formularios con fallos en el action ({len(form_failures)}).")

    return (len(blockers) > 0), blockers


def build_recommendations(
    security_issues: list[str], seo_issues: list[str], content_issues: list[str],
    image_issues: list[str], structure_issues: list[str], link_issues: list[str],
    button_issues: list[str], technical_issues: list[str],
) -> list[str]:
    recs: list[str] = []
    def has_issues(lst): return any("sin incidencias" not in i for i in lst)
    if has_issues(security_issues):  recs.append("Reforzar la seguridad HTTP: cabeceras, HTTPS, SRI.")
    if has_issues(seo_issues):       recs.append("Corregir metadatos SEO: title, description, canonical.")
    if has_issues(structure_issues): recs.append("Reforzar la estructura semántica y jerarquía de encabezados.")
    if has_issues(image_issues):     recs.append("Arreglar imágenes rotas y completar atributos alt.")
    if has_issues(content_issues):   recs.append("Eliminar contenido de relleno, incoherente o inadecuado.")
    if has_issues(link_issues):      recs.append("Corregir los enlaces rotos.")
    if has_issues(button_issues):    recs.append("Revisar botones y formularios.")
    if has_issues(technical_issues): recs.append("Aplicar hardening técnico: doctype, charset, mixed content.")
    return recs
