from unittest.mock import MagicMock, patch

import requests

from shared.auditor.auditor_modules.core import QualityAuditor


def _make_auditor():
    return QualityAuditor()


# ─── 1. Test de Fallback Silencioso ───────────────────────────────────────────


@patch("requests.Session.post")
def test_ai_analyzer_connection_failure_fallback(mock_post):
    """
    Si el microservicio de IA falla (error de conexión), el auditor debe
    continuar de forma transparente con las comprobaciones estáticas.
    """
    # Configurar el mock para que lance un error de conexión
    mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

    auditor = _make_auditor()
    html = """
    <html>
        <head><title>Página Operativa</title></head>
        <body>
            <h1>Bienvenido a mi sitio web</h1>
            <p>Este es un sitio normal que debería funcionar perfectamente.</p>
        </body>
    </html>
    """

    # Aseguramos que la llamada no lance excepciones
    report = auditor.build_report(html=html, base_url="https://example.com", metadata={"status_code": 200})

    # El reporte finalizó correctamente (sin error)
    assert report is not None
    assert report.score > 50  # No penalizado críticamente
    assert not any("Detección por IA" in issue for issue in report.content_issues)


# ─── 2. Test de Integración: Página Inoperativa detectada por IA ───────────────


@patch("requests.Session.post")
def test_ai_analyzer_detects_inoperative_page(mock_post):
    """
    Si la IA detecta que la página está inoperativa (ej: error disfrazado),
    el auditor debe heredar ese estado y forzar un score crítico.
    """
    # Configurar respuesta simulada de la IA
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "is_inoperative": True,
        "inoperative_reason": "Detección semántica de error por IA (Similitud: 0.65)",
        "confidence": 0.95,
        "has_spam": False,
        "has_malicious_content": False,
        "has_incoherent_content": False,
        "detected_language": "es",
        "quality_score": 5,
        "issues": ["Página no operativa: Detección semántica de error por IA (Similitud: 0.65)"],
        "warnings": [],
    }
    mock_post.return_value = mock_resp

    auditor = _make_auditor()
    html = """
    <html>
        <head><title>Servidor no responde</title></head>
        <body>
            <h1>Error interno temporal</h1>
            <p>Lo sentimos, vuelva a intentarlo más tarde.</p>
        </body>
    </html>
    """

    report = auditor.build_report(html=html, base_url="https://example.com", metadata={"status_code": 200})

    # Comprobar que el reporte se marca como inoperativo por IA
    assert report.score == 5
    assert report.status == "crítico"
    assert report.release_blocked is True
    assert any("Detección semántica de error por IA" in i for i in report.technical_issues)
    assert any("Detección semántica de error por IA" in i for i in report.content_issues)

    # Comprobar que los metadatos de IA se guardan correctamente en metrics
    assert report.metrics["ai_quality_score"] == 5
    assert report.metrics["ai_detected_language"] == "es"
    assert report.metrics["ai_confidence"] == 0.95
    assert report.metrics["ai_is_inoperative"] is True


# ─── 3. Test de Integración: Detección de Contenido Malicioso y Spam ───────────


@patch("requests.Session.post")
def test_ai_analyzer_detects_malicious_and_spam(mock_post):
    """
    Si la IA detecta contenido malicioso o spam de SEO, las incidencias
    deben propagarse a las listas de seguridad y contenido.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "is_inoperative": False,
        "inoperative_reason": None,
        "confidence": 0.88,
        "has_spam": True,
        "has_malicious_content": True,
        "has_incoherent_content": False,
        "detected_language": "en",
        "quality_score": 20,
        "issues": [
            "Contenido no apto o malicioso detectado (pornography, Similitud: 0.70)",
            "Spam SEO detectado (seo_spam, Similitud: 0.65)",
        ],
        "warnings": ["Contenido bajo en texto plano (30 palabras)."],
    }
    mock_post.return_value = mock_resp

    auditor = _make_auditor()
    html = """
    <html>
        <head><title>Página Sospechosa</title></head>
        <body>
            <p>Contenido malicioso con spam de farmacias...</p>
        </body>
    </html>
    """

    report = auditor.build_report(html=html, base_url="https://example.com", metadata={"status_code": 200})

    # Las incidencias maliciosas deben estar en seguridad y contenido
    assert any("Contenido no apto o malicioso detectado" in i for i in report.security_issues)
    assert any("Contenido no apto o malicioso detectado" in i for i in report.content_issues)

    # El spam de SEO debe propagarse a contenido
    assert any("Spam SEO detectado" in i for i in report.content_issues)

    # Las advertencias de IA deben propagarse a contenido
    assert any("Contenido bajo en texto" in i for i in report.content_issues)

    # Verificar métricas
    assert report.metrics["ai_quality_score"] == 20
    assert report.metrics["ai_detected_language"] == "en"
    assert report.metrics["ai_has_spam"] is True
    assert report.metrics["ai_has_malicious_content"] is True


@patch("requests.Session.post")
def test_ai_non_inoperative_overrides_classic_heuristic_false_positive(mock_post):
    """
    Si la heurística clásica detecta falso positivo por contenido, pero la IA
    indica que no está inoperativa, debe prevalecer el criterio semántico.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "is_inoperative": False,
        "inoperative_reason": None,
        "confidence": 0.9,
        "has_spam": False,
        "has_malicious_content": False,
        "has_incoherent_content": False,
        "detected_language": "en",
        "quality_score": 92,
        "issues": [],
        "warnings": [],
    }
    mock_post.return_value = mock_resp

    auditor = _make_auditor()
    html = """
    <html>
        <head><title>HTTP 404 - Reference</title></head>
        <body>
            <h1>HTTP status code documentation</h1>
            <p>This page explains 404 Not Found and 503 Service Unavailable semantics.</p>
        </body>
    </html>
    """

    report = auditor.build_report(
        html=html, base_url="https://example.com/docs/http-status", metadata={"status_code": 200}
    )

    assert report.score > 5
    assert not any("Sitio web no operativo" in i for i in report.technical_issues)
