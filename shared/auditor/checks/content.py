"""
check_content — Calidad de contenido: relleno, toxicidad, keyword stuffing,
                requisitos legales y contacto.
Extraído de QualityAuditor._check_content y _detect_incoherent_segments.
"""
from __future__ import annotations
import re
from bs4 import BeautifulSoup
from config import settings


def check_content(
    soup: BeautifulSoup,
    issues: list[str],
    html_lines: list[str],
    base_url: str,
    dicts,
    regex_set,
    normalize_fn,
    find_line_fn,
) -> None:
    text = soup.get_text(" ", strip=True)
    text_l = text.lower()
    if not text_l.strip():
        issues.append("No se encontró texto visible en el body.")
        return

    text_normalized = normalize_fn(text_l)

    all_patterns = (
        *((p, "contenido de relleno")    for p in dicts.lorem_patterns),
        *((p, "contenido incoherente")   for p in dicts.incoherent_patterns),
        *((p, "contenido explícito")     for p in dicts.explicit_patterns),
        *((p, "palabra malsonante")      for p in dicts.profanity_patterns),
        *((p, "discurso de odio")        for p in dicts.hate_patterns),
    )

    for pattern, category in all_patterns:
        in_original   = pattern in text_l
        in_normalized = pattern in text_normalized
        if in_original or in_normalized:
            if _is_false_positive(pattern, text_l):
                continue
            evasion_note = " [detectado via normalización]" if not in_original else ""
            line_no, line = find_line_fn(html_lines, pattern)
            issues.append(
                f"[{category}] Patrón '{pattern}'{evasion_note} "
                f"en línea aproximada {line_no}: {line}"
            )

    if regex_set.gibberish_regex.search(text_l):
        issues.append("Secuencias de caracteres repetidos anormales detectadas.")
    if regex_set.multi_symbol_regex.search(text_l):
        issues.append("Bloques de símbolos excesivos detectados.")
    if regex_set.character_noise_regex.search(text_l):
        issues.append("Caracteres repetitivos no lingüísticos detectados.")
    if len(regex_set.typo_regex.findall(text_l)) >= 5:
        issues.append("Exceso de tokens posiblemente mal escritos o generados automáticamente.")
    if len(regex_set.long_token_regex.findall(text_l)) >= 2:
        issues.append("Tokens extremadamente largos detectados.")

    for match_str in regex_set.spaced_chars_regex.finditer(text_l):
        collapsed = match_str.group().replace(" ", "").replace("\t", "")
        for pattern, category in all_patterns:
            if pattern in collapsed:
                line_no, line = find_line_fn(html_lines, match_str.group().strip())
                issues.append(
                    f"[{category}] Evasión con letras espaciadas '{match_str.group().strip()}' "
                    f"(colapsa en '{collapsed}') en línea aproximada {line_no}: {line}"
                )
                break

    for raw_match in regex_set.dotted_chars_regex.findall(text_l):
        collapsed = re.sub(r"[.\-_*]", "", raw_match)
        for pattern, category in all_patterns:
            if pattern in collapsed:
                line_no, line = find_line_fn(html_lines, raw_match)
                issues.append(
                    f"[{category}] Evasión con puntuación intercalada '{raw_match}' "
                    f"(colapsa en '{collapsed}') en línea aproximada {line_no}: {line}"
                )
                break

    incoherent_samples = _detect_incoherent_segments(text_l, regex_set)
    for reason, token in incoherent_samples[:8]:
        line_no, line = find_line_fn(html_lines, token)
        issues.append(f"Incoherencia heurística ({reason}) en línea aproximada {line_no}: {line}")

    for segment in dicts.blocked_admin_segments:
        in_orig = segment in text_l
        in_norm = segment in text_normalized
        if in_orig or in_norm:
            evasion_note = " [detectado via normalización]" if not in_orig else ""
            line_no, line = find_line_fn(html_lines, segment)
            issues.append(
                f"Ruta de administración expuesta en texto visible '{segment}'{evasion_note} "
                f"en línea aproximada {line_no}: {line}"
            )

    words = regex_set.keyword_density_word_regex.findall(text_l)
    word_count = len(words)
    url_lower = base_url.lower()
    is_short_page = any(kw in url_lower for kw in ("contact", "contacto", "gracias", "thank", "legal", "privacy", "aviso"))
    if not is_short_page and 0 < word_count < settings.AUDIT_MIN_WORD_COUNT:
        issues.append(
            f"Contenido delgado (thin content): solo {word_count} palabras visibles "
            f"(mínimo recomendado {settings.AUDIT_MIN_WORD_COUNT})."
        )

    if words:
        freq: dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        top_word, top_count = max(freq.items(), key=lambda kv: kv[1])
        density = top_count / len(words)
        if density > settings.AUDIT_KEYWORD_DENSITY_MAX:
            issues.append(
                f"Posible keyword stuffing: '{top_word}' aparece {top_count} veces "
                f"({density:.1%} del texto)."
            )

    legal_terms = {"aviso legal", "política de privacidad", "privacy policy", "términos", "cookies", "rgpd", "gdpr"}
    has_legal = any(term in text_l for term in legal_terms) or any(
        any(term in (a.get_text(" ", strip=True).lower()) or term in (a.get("href") or "").lower() for term in legal_terms)
        for a in soup.find_all("a")
    )
    if not has_legal:
        issues.append("No se detecta enlace ni texto de aviso legal ni de política de privacidad. Obligatorio por el RGPD.")

    contact_terms = {"contacto", "contact", "contáctanos", "escríbenos"}
    has_contact = any(term in text_l for term in contact_terms)
    if not has_contact:
        issues.append("No se detecta información de contacto. Recomendado para generar confianza.")


def _is_false_positive(pattern: str, text: str) -> bool:
    if pattern == "sex":
        match = re.search(r"\b(\w*sex\w*)\b", text)
        if match and match.group(1).lower() in {"sexta", "sexto", "sesenta", "sexenio"}:
            return True
    if pattern == "con" and re.search(r"\bcon\b", text):
        return True
    if pattern == "put":
        match = re.search(r"\b(\w*put\w*)\b", text)
        if match and match.group(1).lower() in {"input", "output", "cómputo", "reputación"}:
            return True
    return False


def _detect_incoherent_segments(text_l: str, regex_set) -> list[tuple[str, str]]:
    words = regex_set.word_regex.findall(text_l)
    if not words:
        return []
    suspicious: list[tuple[str, str]] = []
    alnum_noise_count = 0
    for w in words:
        if len(w) >= 7:
            vowel_ratio = sum(1 for c in w if c in "aeiouáéíóúü") / max(1, len(w))
            if vowel_ratio < 0.22:
                suspicious.append(("baja_proporción_vocales", w[:30]))
                continue
        if regex_set.repeated_chunk_regex.search(w):
            suspicious.append(("bloque_repetido", w[:30]))
            continue
        if regex_set.consonant_cluster_regex.search(w):
            suspicious.append(("grupo_consonántico", w[:30]))
            continue
        if any(ch.isalpha() for ch in w) and any(ch.isdigit() for ch in w) and len(w) >= 8:
            alnum_noise_count += 1
    if alnum_noise_count >= 4:
        suspicious.append(("muchos_tokens_alfanuméricos_raros", str(alnum_noise_count)))
    min_hits = max(2, int(len(words) * 0.08))
    return suspicious if len(suspicious) >= min_hits else []
