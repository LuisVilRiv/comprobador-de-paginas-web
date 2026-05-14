"""
check_structure — Landmarks semánticos, jerarquía Hx, accesibilidad y HTML obsoleto.
Extraído de QualityAuditor._check_structure.
"""
from __future__ import annotations
from bs4 import BeautifulSoup, Tag


def check_structure(soup: BeautifulSoup, issues: list[str]) -> None:
    if soup.html is None:
        issues.append("Falta la etiqueta <html>. Revisar la plantilla base.")
        return
    if soup.head is None:
        issues.append("Falta <head>.")
    if soup.body is None:
        issues.append("Falta <body>.")
    if not soup.find("h1"):
        issues.append("No existe ningún <h1>.")

    for landmark, label in (
        (lambda s: s.find("main") or s.find(attrs={"role": "main"}), "main"),
        (lambda s: s.find("nav")  or s.find(attrs={"role": "navigation"}), "nav"),
        (lambda s: s.find("header") or s.find(attrs={"role": "banner"}), "header"),
        (lambda s: s.find("footer") or s.find(attrs={"role": "contentinfo"}), "footer"),
    ):
        if not landmark(soup):
            issues.append(f"Falta el landmark <{label}>.")

    generic_texts = {
        "haz clic aquí", "click here", "leer más", "read more", "aquí", "here",
        "más información", "more info", "enlace", "link", "ver más", "seguir leyendo",
    }
    for anchor in soup.find_all("a"):
        link_text = anchor.get_text(" ", strip=True).lower().strip(" .,;")
        if link_text in generic_texts:
            href = (anchor.get("href") or "")[:80]
            issues.append(f"Enlace con texto genérico inutilizable con lector de pantalla: '{link_text}' (href={href})")

    for anchor in soup.find_all("a", attrs={"target": "_blank"}):
        rel = " ".join(anchor.get("rel") or []).lower()
        if "noopener" not in rel or "noreferrer" not in rel:
            issues.append(f"Enlace target='_blank' sin rel='noopener noreferrer': {(anchor.get('href') or '')[:80]}")

    for video in soup.find_all("video"):
        if not video.find("track"):
            issues.append(f"Elemento <video> sin <track>: {(video.get('src') or '(sin src)')[:80]}")

    for tag_name in ("center", "font", "blink", "marquee", "frame", "frameset", "noframes", "big", "strike", "tt"):
        if soup.find(tag_name):
            issues.append(f"Elemento HTML obsoleto <{tag_name}> detectado.")

    for table in soup.find_all("table"):
        if not table.find("th") and not table.find("caption"):
            issues.append("Tabla sin <th> ni <caption>: posible tabla de maquetación.")
            break

    inline_events = ("onclick", "onmouseover", "onmouseout", "onkeydown", "onkeyup", "onchange", "onsubmit")
    inline_count = sum(1 for tag in soup.find_all(True) for ev in inline_events if tag.get(ev))
    if inline_count > 0:
        issues.append(f"{inline_count} elemento(s) con manejadores de eventos en línea.")

    headings = [int(h.name[1]) for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])]
    for idx in range(1, len(headings)):
        if headings[idx] - headings[idx - 1] > 1:
            issues.append(f"Salto brusco en la jerarquía de encabezados: h{headings[idx-1]} -> h{headings[idx]}.")
            break
