"""
check_seo — Metadatos SEO, Open Graph, canonical, JSON-LD y hreflang.
Extraído de QualityAuditor._check_seo.
"""

from __future__ import annotations

import json

from bs4 import BeautifulSoup, Tag

import shared.auditor.auditor_modules.helpers as helpers


def check_seo(soup: BeautifulSoup, issues: list[str], regex_set) -> None:

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    if not title:
        issues.append("Falta <title>.")
    elif len(title) < 20 or len(title) > 65:
        issues.append(f"Longitud no óptima de <title> ({len(title)} caracteres).")

    meta_desc = soup.find("meta", attrs={"name": "description"})
    desc_text = helpers.attr_to_str(meta_desc.get("content")).strip() if isinstance(meta_desc, Tag) else ""
    if not desc_text:
        issues.append("Falta meta description.")
    elif len(desc_text) < 70 or len(desc_text) > 160:
        issues.append(f"Longitud no óptima de meta description ({len(desc_text)} caracteres).")

    html_tag = soup.find("html")
    if isinstance(html_tag, Tag) and not html_tag.get("lang"):
        issues.append("La etiqueta <html> no define el atributo lang.")
    if not soup.find("link", attrs={"rel": "canonical"}):
        issues.append("Falta canonical (<link rel='canonical'>).")
    if not soup.find("meta", attrs={"name": "viewport"}):
        issues.append("Falta meta viewport para diseño responsivo.")

    h1_list = soup.find_all("h1")
    if len(h1_list) > 1:
        issues.append(f"Múltiples <h1> detectados ({len(h1_list)}). Solo debe haber uno.")

    og_props = {"og:title", "og:description", "og:image"}
    found_og = {helpers.attr_to_str(m.get("property")).lower() for m in soup.find_all("meta", property=True)}
    missing_og = og_props - found_og
    if missing_og:
        issues.append(
            f"Open Graph incompleto. Faltan: {', '.join(sorted(missing_og))}. "
            "Afecta a cómo se muestra al compartir en redes sociales."
        )

    if not soup.find("meta", attrs={"name": "twitter:card"}):
        issues.append("Falta meta twitter:card.")

    jsonld_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not jsonld_scripts:
        issues.append("No se detectan datos estructurados JSON-LD (Schema.org).")
    else:
        for js_tag in jsonld_scripts:
            raw_json = js_tag.get_text(strip=True)
            if raw_json:
                try:
                    data = json.loads(raw_json)
                    if not isinstance(data, dict) or ("@type" not in data and "@context" not in data):
                        issues.append("JSON-LD presente pero sin @type ni @context válidos.")
                except (json.JSONDecodeError, ValueError):
                    issues.append("JSON-LD presente pero con sintaxis JSON inválida.")

    page_lang = helpers.attr_to_str(html_tag.get("lang")).strip() if isinstance(html_tag, Tag) else ""
    hreflang_links = soup.find_all("link", attrs={"rel": "alternate", "hreflang": True})
    if page_lang and not hreflang_links:
        issues.append(f'La página declara lang="{page_lang}" pero no tiene etiquetas hreflang.')

    for img in soup.find_all("img"):
        alt = helpers.attr_to_str(img.get("alt")).strip()
        if alt and regex_set.filename_alt_regex.match(alt):
            src_hint = helpers.attr_to_str(img.get("src"))[:80]
            issues.append(f'El alt de una imagen es un nombre de archivo ("{alt}"), no descriptivo. src={src_hint}')
