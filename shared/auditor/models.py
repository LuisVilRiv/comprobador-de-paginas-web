"""
models.py — Modelo de datos del informe de auditoría.
Extraído de quality_auditor.py para desacoplar la estructura de datos
de la lógica de ejecución.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QualityAuditReport:
    status: str
    score: int
    security_issues: list[str] = field(default_factory=list)
    seo_issues: list[str] = field(default_factory=list)
    content_issues: list[str] = field(default_factory=list)
    image_issues: list[str] = field(default_factory=list)
    structure_issues: list[str] = field(default_factory=list)
    link_issues: list[str] = field(default_factory=list)
    button_issues: list[str] = field(default_factory=list)
    technical_issues: list[str] = field(default_factory=list)
    release_blocked: bool = False
    release_blockers: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "score": self.score,
            "security_issues": self.security_issues,
            "seo_issues": self.seo_issues,
            "content_issues": self.content_issues,
            "image_issues": self.image_issues,
            "structure_issues": self.structure_issues,
            "link_issues": self.link_issues,
            "button_issues": self.button_issues,
            "technical_issues": self.technical_issues,
            "release_blocked": self.release_blocked,
            "release_blockers": self.release_blockers,
            "recommendations": self.recommendations,
            "metrics": self.metrics,
        }
