import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AuditRegexSet:
    # ── Patrones de ruido / incoherencia ─────────────────────────────────────
    gibberish_regex: re.Pattern  # Caracteres repetidos en bloque (aaaa…)
    multi_symbol_regex: re.Pattern  # Símbolos no alfanuméricos en bloque
    typo_regex: re.Pattern  # Tokens malformados (ab12, x3r…)
    character_noise_regex: re.Pattern  # Ruido de caracteres especiales repetidos
    long_token_regex: re.Pattern  # Tokens extremadamente largos
    word_regex: re.Pattern  # Palabras reconocibles (≥4 chars)
    repeated_chunk_regex: re.Pattern  # Secuencias repetidas (abcabcabc)
    consonant_cluster_regex: re.Pattern  # Cúmulos de consonantes sin vocales
    # ── Patrones de evasión / leetspeak ──────────────────────────────────────
    spaced_chars_regex: re.Pattern  # Letras individuales separadas por espacios: "p o r n"
    dotted_chars_regex: re.Pattern  # Letras separadas por puntos/guiones: "p.o.r.n"
    leet_chars_regex: re.Pattern  # Presencia de sustituciones leetspeak comunes
    unicode_lookalike_regex: re.Pattern  # Caracteres unicode que imitan letras latinas
    # ── Datos sensibles ───────────────────────────────────────────────────────
    sensitive_data_regexes: tuple  # Tupla de (nombre, Pattern) para datos sensibles
    filename_alt_regex: re.Pattern  # Alt de imagen que parece nombre de archivo
    keyword_density_word_regex: re.Pattern  # Tokenizador para cálculo de keyword density


def build_audit_regex_set() -> AuditRegexSet:
    # Patrones de datos sensibles: cada entrada es (etiqueta, pattern)
    sensitive_patterns = (
        ("OpenAI API key", re.compile(r"sk-[a-zA-Z0-9]{20,}")),
        ("Bearer token", re.compile(r"Bearer\s+[a-zA-Z0-9\-._~+/]{20,}")),
        ("API key genérica", re.compile(r"(?:API_KEY|APIKEY|api_key)\s*[=:]\s*\S{8,}", re.IGNORECASE)),
        ("GitHub token", re.compile(r"ghp_[a-zA-Z0-9]{36}")),
        ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}")),
        ("Contraseña hardcodeada", re.compile(r"password\s*[=:]\s*['\"]?\S{6,}", re.IGNORECASE)),
        ("Email expuesto", re.compile(r"[a-zA-Z0-9._%+\-]{2,}@[a-zA-Z0-9.\-]+\.[a-z]{2,6}")),
        ("Teléfono ES expuesto", re.compile(r"(?:\+34|0034)?\s?[6-9]\d{2}[\s\-]?\d{3}[\s\-]?\d{3}")),
        ("Token genérico", re.compile(r"(?:token|secret|passwd|pwd)\s*[=:]\s*['\"]?\S{8,}", re.IGNORECASE)),
    )

    return AuditRegexSet(
        # ── Ruido / incoherencia ──────────────────────────────────────────────
        gibberish_regex=re.compile(r"(.)\1{4,}"),
        multi_symbol_regex=re.compile(r"[^a-zA-Z0-9\s]{5,}"),
        typo_regex=re.compile(r"\b[a-zA-Z]{1,3}[0-9]{2,}[a-zA-Z0-9]*\b"),
        character_noise_regex=re.compile(r"([@#$%&*_=+~^`|\\/\-])\1{3,}"),
        long_token_regex=re.compile(r"\b[a-zA-Z0-9]{28,}\b"),
        word_regex=re.compile(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ0-9]{4,}"),
        repeated_chunk_regex=re.compile(r"(.{2,4})\1{2,}"),
        consonant_cluster_regex=re.compile(r"[bcdfghjklmnpqrstvwxyz]{6,}", re.IGNORECASE),
        # ── Evasión / leetspeak ───────────────────────────────────────────────
        # Detecta letras individuales separadas por 1-2 espacios: "p o r n o"
        spaced_chars_regex=re.compile(r"(?<!\w)\w(?!\w)(?:[ \t]{1,2}(?<!\w)\w(?!\w)){2,}"),
        # Detecta letras separadas por punto, guion o asterisco: "p.o.r.n" / "p-o-r-n"
        dotted_chars_regex=re.compile(r"[a-zA-Z][.\-_*][a-zA-Z](?:[.\-_*][a-zA-Z])+"),
        # Detecta presencia de sustituciones leetspeak: 0,1,3,4,5,7,@,$,!,|
        leet_chars_regex=re.compile(r"[013457@$!|]"),
        # Detecta lookalikes unicode frecuentes usados para evadir filtros
        unicode_lookalike_regex=re.compile(
            r"[ａ-ｚＡ-Ｚ０-９\u0400-\u04FF\u0370-\u03FF]"  # Fullwidth + cirílico + griego
        ),
        # ── Datos sensibles ───────────────────────────────────────────────────
        sensitive_data_regexes=sensitive_patterns,
        # Alt que parece nombre de archivo: "img_001.jpg", "DSC_2341.png", "photo.jpeg"
        filename_alt_regex=re.compile(
            r"^[\w\-]{1,60}\.(jpe?g|png|gif|webp|avif|svg|bmp|tiff?)$",
            re.IGNORECASE,
        ),
        # Tokenizador simple para keyword density (palabras de ≥3 chars)
        keyword_density_word_regex=re.compile(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]{3,}"),
    )


# ── Tabla de sustitución leetspeak ───────────────────────────────────────────
LEET_TRANSLATION_TABLE: dict[int, str] = str.maketrans(
    {  # type: ignore[arg-type]
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "6": "b",
        "7": "t",
        "8": "b",
        "9": "g",
        "@": "a",
        "$": "s",
        "!": "i",
        "|": "i",
        "+": "t",
        "¡": "i",
        "€": "e",
        "ø": "o",
        "ð": "d",
        "þ": "p",
    }
)
