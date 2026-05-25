from bs4 import BeautifulSoup

from shared.auditor.checks.technical import check_technical


# Helper Mock Functions
def mock_is_banned(url):
    return False


def mock_classify_speed(elapsed_ms):
    return "fast"


def mock_find_line(html_lines, tag):
    return 14, "<element>"


def test_technical_perfect():
    # Caso 1: Estructura técnica perfecta, favicon, robots, UTF-8, etc.
    html = """<!DOCTYPE html>
    <html lang="es">
        <head>
            <meta charset="utf-8" />
            <meta name="robots" content="index, follow" />
            <title>Página Técnica</title>
            <link rel="icon" href="favicon.ico" />
            <link rel="manifest" href="manifest.json" />
            <link rel="stylesheet" href="style.css" />
            <script src="script.js" defer="defer"></script>
        </head>
        <body>
            <h1>Página Correcta</h1>
            <iframe title="Un mapa interactivo" src="map.html"></iframe>
            <input type="text" id="username" aria-label="Nombre de usuario" />
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    recommendations = []
    asset_stats = {"checked": 0, "broken": 0, "mixed_content": 0}

    def mock_check_url(url):
        return True, 100, 200, ""

    check_technical(
        html=html,
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        asset_stats=asset_stats,
        recommendations=recommendations,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
    )

    assert len(issues) == 0
    assert len(recommendations) == 0


def test_technical_missing_essential_tags():
    # Caso 2: Falta DOCTYPE, meta charset y meta robots
    html = """
    <html>
        <head>
            <title>Sin doctype</title>
        </head>
        <body>
            <h1>Sin charset</h1>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    recommendations = []
    asset_stats = {"checked": 0, "broken": 0, "mixed_content": 0}

    check_technical(
        html=html,
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        asset_stats=asset_stats,
        recommendations=recommendations,
        is_banned_fn=mock_is_banned,
        check_url_fn=lambda u: (True, 50, 200, ""),
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
    )

    assert any("Falta <!DOCTYPE html>" in issue for issue in issues)
    assert any("Falta <meta charset='utf-8'>" in issue for issue in issues)
    assert any("Falta meta robots" in issue for issue in issues)


def test_technical_duplicate_ids_and_iframe_title():
    # Caso 3: Iframe sin title e IDs duplicados
    html = """<!DOCTYPE html>
    <html>
        <head><meta charset="utf-8" /><meta name="robots" content="index" /></head>
        <body>
            <iframe src="map.html"></iframe>
            <div id="duplicate-id">1</div>
            <div id="duplicate-id">2</div>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    recommendations = []
    asset_stats = {"checked": 0, "broken": 0, "mixed_content": 0}

    check_technical(
        html=html,
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        asset_stats=asset_stats,
        recommendations=recommendations,
        is_banned_fn=mock_is_banned,
        check_url_fn=lambda u: (True, 50, 200, ""),
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
    )

    assert any("Iframe sin atributo title" in issue for issue in issues)
    assert any("ID duplicado detectado: #duplicate-id" in issue for issue in issues)


def test_technical_mixed_content_and_blocking_scripts():
    # Caso 4: Contenido mixto (HTTP en base HTTPS) y scripts bloqueantes en head
    html = """<!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8" />
            <meta name="robots" content="index" />
            <link rel="stylesheet" href="http://example.com/style.css" />
            <script src="https://example.com/script.js"></script> <!-- bloqueante en head (sin async/defer) -->
        </head>
        <body></body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    recommendations = []
    asset_stats = {"checked": 0, "broken": 0, "mixed_content": 0}

    check_technical(
        html=html,
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        asset_stats=asset_stats,
        recommendations=recommendations,
        is_banned_fn=mock_is_banned,
        check_url_fn=lambda u: (True, 50, 200, ""),
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
    )

    assert any("Contenido mixto CSS" in issue for issue in issues)
    assert any("Script bloqueante en <head>" in issue for issue in issues)
    assert asset_stats["mixed_content"] == 1


def test_technical_broken_assets():
    # Caso 5: Hojas de estilo y scripts externos inaccesibles (404)
    html = """<!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8" />
            <meta name="robots" content="index" />
            <link rel="stylesheet" href="style.css" />
            <script src="script.js" defer></script>
        </head>
        <body></body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    recommendations = []
    asset_stats = {"checked": 0, "broken": 0, "mixed_content": 0}

    # Simular fallo en check_url
    def mock_check_url_fail(url):
        return False, 900, 404, ""

    check_technical(
        html=html,
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        asset_stats=asset_stats,
        recommendations=recommendations,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url_fail,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
    )

    assert any("CSS inaccesible" in issue for issue in issues)
    assert any("JS inaccesible" in issue for issue in issues)
    assert asset_stats["broken"] == 2


def test_technical_form_accessibility():
    # Caso 6: Campos de formulario sin etiquetas o aria-labels
    html = """<!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8" />
            <meta name="robots" content="index" />
        </head>
        <body>
            <input type="text" /> <!-- sin label ni aria -->
            <input type="password" id="pass" /> <!-- sin label, tiene id pero no label correspondienrte -->
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    recommendations = []
    asset_stats = {"checked": 0, "broken": 0, "mixed_content": 0}

    check_technical(
        html=html,
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        asset_stats=asset_stats,
        recommendations=recommendations,
        is_banned_fn=mock_is_banned,
        check_url_fn=lambda u: (True, 50, 200, ""),
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
    )

    assert sum("Campo de formulario sin label ni aria-label" in issue for issue in issues) == 2
