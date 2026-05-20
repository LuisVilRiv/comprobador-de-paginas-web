import pytest
from bs4 import BeautifulSoup
from shared.auditor.auditor_modules.core import QualityAuditor
from shared.auditor.scoring import calculate_score, evaluate_release_gate

def test_inoperative_by_status_code():
    auditor = QualityAuditor()
    html = """
    <html>
        <head>
            <title>Error del Servidor</title>
        </head>
        <body>
            <h1>500 Internal Server Error</h1>
            <p>Se produjo un error interno.</p>
        </body>
    </html>
    """
    metadata = {"status_code": 500}
    report = auditor.build_report(html=html, base_url="https://example.com", metadata=metadata)

    # Debe ser calificado con 5 puntos (Crítico)
    assert report.score == 5
    assert report.status == "crítico"
    assert report.release_blocked is True
    
    # Debe listar la incidencia de inoperatividad
    assert any("Sitio web no operativo" in issue for issue in report.technical_issues)
    assert any("Sitio web no operativo" in issue for issue in report.content_issues)
    assert any("El sitio web no está operativo" in blocker for blocker in report.release_blockers)


def test_inoperative_by_title_error():
    auditor = QualityAuditor()
    html = """
    <html>
        <head>
            <title>404 Not Found</title>
        </head>
        <body>
            <h1>Página no encontrada</h1>
        </body>
    </html>
    """
    # Estatus 200 pero título de error (común en configuraciones incorrectas o SPA sin control de rutas en server)
    metadata = {"status_code": 200}
    report = auditor.build_report(html=html, base_url="https://example.com", metadata=metadata)

    assert report.score == 5
    assert report.status == "crítico"
    assert report.release_blocked is True
    assert any("El título de la página ('404 Not Found') indica un estado de error" in issue for issue in report.technical_issues)


def test_inoperative_by_title_maintenance():
    auditor = QualityAuditor()
    html = """
    <html>
        <head>
            <title>Sitio en Mantenimiento</title>
        </head>
        <body>
            <p>Disculpe las molestias, volveremos pronto.</p>
        </body>
    </html>
    """
    metadata = {"status_code": 200}
    report = auditor.build_report(html=html, base_url="https://example.com", metadata=metadata)

    assert report.score == 5
    assert report.status == "crítico"
    assert report.release_blocked is True
    assert any("El título de la página ('Sitio en Mantenimiento') indica que el sitio está en mantenimiento" in issue for issue in report.technical_issues)


def test_inoperative_by_heading_maintenance_thin_content():
    auditor = QualityAuditor()
    html = """
    <html>
        <head>
            <title>Mi Sitio Web</title>
        </head>
        <body>
            <h1>Estamos en mantenimiento</h1>
            <p>Volveremos pronto con novedades.</p>
        </body>
    </html>
    """
    metadata = {"status_code": 200}
    report = auditor.build_report(html=html, base_url="https://example.com", metadata=metadata)

    assert report.score == 5
    assert report.status == "crítico"
    assert report.release_blocked is True
    assert any("El encabezado principal indica que el sitio está en mantenimiento" in issue for issue in report.technical_issues)


def test_operative_page_is_not_flagged():
    auditor = QualityAuditor()
    html = """
    <html>
        <head>
            <title>Agencia de Viajes - Inicio</title>
        </head>
        <body>
            <h1>Bienvenido a nuestra Agencia de Viajes</h1>
            <p>Encuentra los mejores destinos nacionales e internacionales al mejor precio. Reservas en línea de hoteles, vuelos y paquetes turísticos de forma fácil y segura.</p>
            <p>Visita nuestra sección de contacto para recibir atención personalizada en cualquiera de nuestras oficinas físicas o mediante nuestro formulario web.</p>
            <a href="/aviso-legal">Aviso Legal y Política de Privacidad</a>
            <a href="/contacto">Contacto</a>
        </body>
    </html>
    """
    metadata = {"status_code": 200}
    report = auditor.build_report(html=html, base_url="https://example.com/contacto", metadata=metadata)

    # No debe calificarse con 5, y no debe estar inoperativo
    assert report.score > 50
    assert not any("Sitio web no operativo" in issue for issue in report.technical_issues)
