import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AuditRegexSet:
    gibberish_regex: re.Pattern
    multi_symbol_regex: re.Pattern
    typo_regex: re.Pattern
    character_noise_regex: re.Pattern
    long_token_regex: re.Pattern
    word_regex: re.Pattern
    repeated_chunk_regex: re.Pattern
    consonant_cluster_regex: re.Pattern


def build_audit_regex_set() -> AuditRegexSet:
    return AuditRegexSet(
        gibberish_regex=re.compile(r"(.)\1{4,}"),
        multi_symbol_regex=re.compile(r"[^a-zA-Z0-9\s]{5,}"),
        typo_regex=re.compile(r"\b[a-zA-Z]{1,3}[0-9]{2,}[a-zA-Z0-9]*\b"),
        character_noise_regex=re.compile(r"([@#$%&*_=+~^`|\\/\-])\1{3,}"),
        long_token_regex=re.compile(r"\b[a-zA-Z0-9]{28,}\b"),
        word_regex=re.compile(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ0-9]{4,}"),
        repeated_chunk_regex=re.compile(r"(.{2,4})\1{2,}"),
        consonant_cluster_regex=re.compile(r"[bcdfghjklmnpqrstvwxyz]{6,}", re.IGNORECASE),
    )
