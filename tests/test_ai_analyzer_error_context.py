import importlib.util
from pathlib import Path

import pytest


def _load_ai_analyzer_class():
    analyzer_path = Path(__file__).resolve().parent.parent / "docker" / "ai-analyzer" / "analyzer.py"
    spec = importlib.util.spec_from_file_location("ai_analyzer_module", analyzer_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    try:
        spec.loader.exec_module(module)
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.skip(f"ai-analyzer dependencies not installed: {exc}", allow_module_level=True)
    return module.AIContentAnalyzer


AIContentAnalyzer = _load_ai_analyzer_class()


def test_error_code_without_context_is_not_inoperative_signal():
    analyzer = AIContentAnalyzer()
    text = (
        "Nuestra API documenta los códigos 200, 404 y 503 para ejemplos de respuesta. "
        "Estos números son parte de la guía técnica y no representan un fallo actual."
    )

    assert analyzer._has_contextual_error_code(text) is False


def test_error_code_with_context_is_inoperative_signal():
    analyzer = AIContentAnalyzer()
    text = "Error 503 service unavailable. The website is temporarily out of service and will be back soon."

    assert analyzer._has_contextual_error_code(text) is True


def test_status_code_reference_with_404_not_found_context_is_detected():
    analyzer = AIContentAnalyzer()
    text = "Lo sentimos, pagina no encontrada. Codigo 404 not found para el recurso solicitado."

    assert analyzer._has_contextual_error_code(text) is True


def test_educational_http_article_is_not_marked_as_inoperative():
    analyzer = AIContentAnalyzer()
    text = (
        "HTTP 404 es un codigo de estado del protocolo HTTP. "
        "Este articulo de documentacion explica su definicion, ejemplos, RFC y uso. "
        "No representa una caida real del sitio en este contexto."
    )

    assert analyzer._looks_like_educational_content(text, "https://es.wikipedia.org/wiki/HTTP_404") is True


def test_503_template_signature_is_detected_as_strong_error():
    analyzer = AIContentAnalyzer()
    text = (
        "503 Service Temporarily Unavailable Server Error "
        "The server is temporarily unable to service your request due to maintenance downtime "
        "or capacity problems. Please try again later."
    )

    assert analyzer._has_strong_error_signature(text) is True


def test_502_bad_gateway_signature_is_detected():
    analyzer = AIContentAnalyzer()
    text = "502 Bad Gateway. The proxy server received an invalid response from an upstream server."

    assert analyzer._has_strong_error_signature(text) is True


def test_429_rate_limit_signature_is_detected():
    analyzer = AIContentAnalyzer()
    text = "429 Too Many Requests. Rate limit exceeded, please try again later."

    assert analyzer._has_strong_error_signature(text) is True


def test_rfc_article_url_is_treated_as_educational_context():
    analyzer = AIContentAnalyzer()
    text = "RFC 9110 define HTTP semantics y documenta codigo de estado, definicion y especificacion."

    assert analyzer._looks_like_educational_content(text, "https://www.rfc-editor.org/rfc/rfc9110") is True


def test_explanatory_http_text_is_not_strong_runtime_error_signature():
    analyzer = AIContentAnalyzer()
    text = (
        "HTTP 503 is a status code defined in RFC specifications. "
        "This reference explains what service unavailable indicates in protocol semantics."
    )

    assert analyzer._has_strong_error_signature(text) is False


def test_long_reference_style_text_is_educational_without_domain_allowlist():
    analyzer = AIContentAnalyzer()
    text = (
        "RFC 9110 is a technical specification for HTTP semantics and status code definitions. "
        "This documentation explains references, examples and protocol behavior in detail. "
        "It indicates that each status code has specific meaning in the standard."
    ) * 4
    assert analyzer._looks_like_educational_content(text, "https://example.com/article") is True


def test_strong_fallback_resolver_with_mock_classifier():
    analyzer = AIContentAnalyzer()
    analyzer.enable_strong_fallback = True
    analyzer.zero_shot_classifier = lambda *_args, **_kwargs: {
        "labels": ["informational or educational content", "error page or maintenance outage"],
        "scores": [0.82, 0.18],
    }

    decision, confidence = analyzer._resolve_ambiguity_with_strong_model(
        "This document explains HTTP semantics and status code definitions."
    )
    assert decision is False
    assert confidence >= 0.8
