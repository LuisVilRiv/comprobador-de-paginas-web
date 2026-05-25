from bs4 import BeautifulSoup

from shared.auditor.checks.images import check_images


# Mock helper functions
def mock_is_banned(url):
    return "banned" in url


def mock_classify_speed(elapsed_ms):
    return "fast" if elapsed_ms < 500 else "slow"


def mock_find_line(html_lines, img_tag):
    return 15, "<img>"


def test_images_perfect():
    # Caso 1: Imágenes con alt, lazy loading, dimensiones y formato moderno (WebP)
    html = """
    <html>
        <body>
            <img src="https://example.com/logo.webp" alt="Logotipo oficial" loading="lazy" width="200" height="100" />
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    def mock_check_url(url):
        return True, 100, 200, ""

    check_images(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
    )

    assert len(issues) == 0


def test_images_no_images_warning():
    # Caso 2: No hay imágenes en la página web
    html = "<html><body><h1>Texto sin imágenes</h1></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    check_images(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        is_banned_fn=mock_is_banned,
        check_url_fn=None,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
    )

    assert any("No hay imágenes en la página" in issue for issue in issues)


def test_images_missing_src_or_alt():
    # Caso 3: Imagen sin alt y sin src
    html = """
    <html>
        <body>
            <img alt="Solo alt sin src" />
            <img src="https://example.com/no-alt.webp" />
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    def mock_check_url(url):
        return True, 100, 200, ""

    check_images(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
    )

    assert any("Imagen sin src" in issue for issue in issues)
    assert any("Imagen sin alt" in issue for issue in issues)


def test_images_broken_source():
    # Caso 4: Imagen rota (404)
    html = """
    <html>
        <body>
            <img src="https://example.com/broken.webp" alt="Una imagen rota" loading="lazy" width="100" height="100" />
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    def mock_check_url(url):
        return False, 900, 404, ""

    check_images(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
    )

    assert any("Imagen rota" in issue for issue in issues)
    assert any("estado=404" in issue for issue in issues)


def test_images_missing_attributes():
    # Caso 5: Falta width/height y loading="lazy"
    html = """
    <html>
        <body>
            <img src="https://example.com/photo.webp" alt="Foto bonita" />
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    def mock_check_url(url):
        return True, 100, 200, ""

    check_images(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
    )

    assert any('sin loading="lazy"' in issue for issue in issues)
    assert any("sin width/height explícitos" in issue for issue in issues)


def test_images_legacy_formats():
    # Caso 6: Imagen en formato heredado (png, jpg)
    html = """
    <html>
        <body>
            <img src="https://example.com/photo.jpg" alt="Foto antigua" loading="lazy" width="200" height="200" />
            <img src="https://example.com/photo.png" alt="Foto PNG antigua" loading="lazy" width="200" height="200" />
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    def mock_check_url(url):
        return True, 100, 200, ""

    check_images(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
    )

    assert any("formato heredado (jpg)" in issue for issue in issues)
    assert any("formato heredado (png)" in issue for issue in issues)
