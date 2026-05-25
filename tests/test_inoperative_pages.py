from shared.auditor.auditor_modules.core import QualityAuditor


def _make_auditor():
    return QualityAuditor()


# ─── 1. Detección por código HTTP ≥ 400 ────────────────────────────────────────


def test_inoperative_by_status_code():
    """Un HTTP 500 debe forzar score=5 y bloquear la release."""
    auditor = _make_auditor()
    html = """
    <html>
        <head><title>Error del Servidor</title></head>
        <body>
            <h1>500 Internal Server Error</h1>
            <p>Se produjo un error interno.</p>
        </body>
    </html>
    """
    report = auditor.build_report(html=html, base_url="https://example.com", metadata={"status_code": 500})

    assert report.score == 5
    assert report.status == "crítico"
    assert report.release_blocked is True
    assert any("Sitio web no operativo" in i for i in report.technical_issues)
    assert any("Sitio web no operativo" in i for i in report.content_issues)
    assert any("El sitio web no está operativo" in b for b in report.release_blockers)


# ─── 2. Detección por TÍTULO de error (status_code=200, caso Selenium) ────────


def test_inoperative_by_title_error():
    """Título '404 Not Found' con status 200 → inoperativo (ej. SPA mal configurada)."""
    auditor = _make_auditor()
    html = """
    <html>
        <head><title>404 Not Found</title></head>
        <body><h1>Página no encontrada</h1></body>
    </html>
    """
    report = auditor.build_report(html=html, base_url="https://example.com", metadata={"status_code": 200})

    assert report.score == 5
    assert report.status == "crítico"
    assert report.release_blocked is True
    assert any(
        "El título de la página ('404 Not Found') indica un estado de error del servidor" in i
        for i in report.technical_issues
    )


def test_inoperative_503_title_with_200_status():
    """503 Service Unavailable en título con status 200 → caso típico de Selenium."""
    auditor = _make_auditor()
    html = """
    <html>
        <head><title>503 Service Unavailable</title></head>
        <body><p>El servicio no está disponible temporalmente.</p></body>
    </html>
    """
    report = auditor.build_report(html=html, base_url="https://example.com", metadata={"status_code": 200})

    assert report.score == 5
    assert report.status == "crítico"
    assert report.release_blocked is True
    assert any("Sitio web no operativo" in i for i in report.technical_issues)


# ─── 3. Detección por CUERPO de la página (sin límite de palabras) ─────────────


def test_inoperative_503_in_body_text_no_word_limit():
    """
    'service unavailable' en el cuerpo debe detectarse aunque la página tenga
    muchas palabras (ej. página de error con layout completo renderizado por Selenium).
    """
    auditor = _make_auditor()
    # Simulamos una página de error con bastante texto (> 300 palabras)
    extra_text = " Lorem ipsum dolor sit amet consectetur." * 30  # ~180 palabras extra
    html = f"""
    <html>
        <head><title>Mi Portal</title></head>
        <body>
            <nav>Inicio Servicios Contacto</nav>
            <main>
                <p>Service Unavailable - El servidor está bajo mantenimiento.</p>
                <p>{extra_text}</p>
            </main>
        </body>
    </html>
    """
    report = auditor.build_report(html=html, base_url="https://example.com", metadata={"status_code": 200})

    assert report.score == 5
    assert report.status == "crítico"
    assert report.release_blocked is True
    assert any("Sitio web no operativo" in i for i in report.technical_issues)


# ─── 4. Detección por TÍTULO de mantenimiento ──────────────────────────────────


def test_inoperative_by_title_maintenance():
    """Título con 'Mantenimiento' y página pequeña → inoperativo."""
    auditor = _make_auditor()
    html = """
    <html>
        <head><title>Sitio en Mantenimiento</title></head>
        <body><p>Disculpe las molestias, volveremos pronto.</p></body>
    </html>
    """
    report = auditor.build_report(html=html, base_url="https://example.com", metadata={"status_code": 200})

    assert report.score == 5
    assert report.status == "crítico"
    assert report.release_blocked is True
    assert any("indica que el sitio está en mantenimiento" in i for i in report.technical_issues)


# ─── 5. Detección por ENCABEZADO de mantenimiento en página pequeña ────────────


def test_inoperative_by_heading_maintenance_thin_content():
    """H1 con 'mantenimiento' y título genérico → inoperativo (page < 500 palabras)."""
    auditor = _make_auditor()
    html = """
    <html>
        <head><title>Mi Sitio Web</title></head>
        <body>
            <h1>Estamos en mantenimiento</h1>
            <p>Volveremos pronto con novedades.</p>
        </body>
    </html>
    """
    report = auditor.build_report(html=html, base_url="https://example.com", metadata={"status_code": 200})

    assert report.score == 5
    assert report.status == "crítico"
    assert report.release_blocked is True
    assert any("Sitio web no operativo" in i for i in report.technical_issues)


# ─── 6. Página operativa normal NO debe ser penalizada ─────────────────────────


def test_operative_page_is_not_flagged():
    """Una página real y funcional no debe ser marcada como inoperativa."""
    auditor = _make_auditor()
    html = """
    <html>
        <head><title>Agencia de Viajes - Inicio</title></head>
        <body>
            <h1>Bienvenido a nuestra Agencia de Viajes</h1>
            <p>Encuentra los mejores destinos nacionales e internacionales al mejor precio.
               Reservas en línea de hoteles, vuelos y paquetes turísticos de forma fácil y segura.</p>
            <p>Visita nuestra sección de contacto para recibir atención personalizada en cualquiera
               de nuestras oficinas físicas o mediante nuestro formulario web.</p>
            <a href="/aviso-legal">Aviso Legal y Política de Privacidad</a>
            <a href="/contacto">Contacto</a>
        </body>
    </html>
    """
    report = auditor.build_report(html=html, base_url="https://example.com/contacto", metadata={"status_code": 200})

    # No debe calificarse con 5, y no debe estar inoperativo
    assert report.score > 50
    assert not any("Sitio web no operativo" in i for i in report.technical_issues)


def test_wikipedia_http_article_is_not_flagged_as_inoperative():
    """Un artículo educativo sobre HTTP 404 no debe marcarse como caída del sitio."""
    auditor = _make_auditor()
    html = """
    <html>
        <head><title>HTTP 404 - Wikipedia, la enciclopedia libre</title></head>
        <body>
            <h1>HTTP 404</h1>
            <p>HTTP 404 Not Found es un código de estado HTTP que indica que el recurso no existe.</p>
            <p>Este artículo documenta su definición, contexto, referencias RFC y ejemplos.</p>
            <p>Wikipedia es una enciclopedia colaborativa en línea.</p>
        </body>
    </html>
    """
    report = auditor.build_report(
        html=html,
        base_url="https://es.wikipedia.org/wiki/HTTP_404",
        metadata={"status_code": 200},
    )

    assert report.score > 5
    assert not any("Sitio web no operativo" in i for i in report.technical_issues)


def test_rfc_http_article_is_not_flagged_as_inoperative():
    """Un RFC técnico que describe códigos HTTP no debe marcarse como caída."""
    auditor = _make_auditor()
    html = """
    <html>
        <head><title>RFC 9110 - HTTP Semantics</title></head>
        <body>
            <h1>HTTP Semantics</h1>
            <p>This RFC defines status codes including 404 Not Found and 503 Service Unavailable.</p>
            <p>It is a technical specification and documentation reference, not an outage page.</p>
        </body>
    </html>
    """
    report = auditor.build_report(
        html=html,
        base_url="https://www.rfc-editor.org/rfc/rfc9110",
        metadata={"status_code": 200},
    )

    assert report.score > 5
    assert not any("Sitio web no operativo" in i for i in report.technical_issues)


def test_long_rfc_like_spec_with_status_phrases_is_not_inoperative():
    """
    Especificaciones tipo RFC mencionan '503 Service Unavailable' como definición;
    debe reconocerse como documentación técnica larga y no como caída.
    """
    auditor = _make_auditor()
    spec_chunk = (
        "This document defines HTTP semantics for each request method and response status code. "
        "The reason phrase is advisory. The request-target selects the origin resource. "
        "A client receiving 503 Service Unavailable may retry later. "
        "A server may respond with 404 Not Found when the representation is absent. "
        "Normative requirements apply to field names as defined in Appendix. "
        "Informative examples illustrate common cases for intermediaries and caches. "
    )
    html = f"""
    <html>
        <head><title>RFC Draft</title></head>
        <body>
            <h2>Semantics</h2>
            <p>{spec_chunk * 55}</p>
        </body>
    </html>
    """
    report = auditor.build_report(
        html=html,
        base_url="https://example.net/spec/http-semantics/",
        metadata={"status_code": 200},
    )
    assert not any("Sitio web no operativo" in i for i in report.technical_issues)
