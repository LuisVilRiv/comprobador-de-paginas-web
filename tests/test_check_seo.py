import re

import pytest
from bs4 import BeautifulSoup

from shared.auditor.checks.seo import check_seo


class MockRegexSet:
    def __init__(self):
        # Regex para detectar nombres de archivo en el atributo alt
        self.filename_alt_regex = re.compile(r"^[a-zA-Z0-9_\-]+\.(png|jpg|jpeg|gif|webp|svg)$", re.IGNORECASE)


@pytest.fixture
def regex_set():
    return MockRegexSet()


def test_seo_perfect_page(regex_set):
    # Caso 1: Página con SEO óptimo, no debe reportar issues básicos de SEO
    html = """
    <html lang="es">
        <head>
            <title>Título perfecto de longitud ideal para SEO</title>
            <meta name="description" content="Esta es una meta descripción perfecta de una longitud que cumple con los rangos ideales entre 70 y 160 caracteres." />
            <link rel="canonical" href="https://example.com/perfect" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <meta property="og:title" content="Título perfecto" />
            <meta property="og:description" content="Esta es una meta descripción" />
            <meta property="og:image" content="https://example.com/img.jpg" />
            <meta name="twitter:card" content="summary" />
            <link rel="alternate" hreflang="es" href="https://example.com/perfect" />
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": "Perfect Site"
            }
            </script>
        </head>
        <body>
            <h1>Título principal único</h1>
            <img src="img.jpg" alt="Un perro corriendo en el parque" />
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    check_seo(soup, issues, regex_set)
    assert len(issues) == 0


def test_seo_missing_title_and_description(regex_set):
    # Caso 2: Falta de título y descripción
    html = """
    <html lang="es">
        <head>
            <link rel="canonical" href="https://example.com" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <meta name="twitter:card" content="summary" />
        </head>
        <body>
            <h1>Título único</h1>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    check_seo(soup, issues, regex_set)
    assert any("Falta <title>" in issue for issue in issues)
    assert any("Falta meta description" in issue for issue in issues)


def test_seo_short_and_long_title(regex_set):
    # Caso 3: Título demasiado corto y demasiado largo
    soup_short = BeautifulSoup("<title>Corto</title>", "html.parser")
    issues_short = []
    check_seo(soup_short, issues_short, regex_set)
    assert any("Longitud no óptima de <title>" in issue for issue in issues_short)

    soup_long = BeautifulSoup("<title>" + ("A" * 80) + "</title>", "html.parser")
    issues_long = []
    check_seo(soup_long, issues_long, regex_set)
    assert any("Longitud no óptima de <title>" in issue for issue in issues_long)


def test_seo_short_and_long_description(regex_set):
    # Caso 4: Descripción corta y larga
    soup_short = BeautifulSoup('<meta name="description" content="Muy corta" />', "html.parser")
    issues_short = []
    check_seo(soup_short, issues_short, regex_set)
    assert any("Longitud no óptima de meta description" in issue for issue in issues_short)

    soup_long = BeautifulSoup('<meta name="description" content="' + ("B" * 200) + '" />', "html.parser")
    issues_long = []
    check_seo(soup_long, issues_long, regex_set)
    assert any("Longitud no óptima de meta description" in issue for issue in issues_long)


def test_seo_missing_essential_meta_tags(regex_set):
    # Caso 5: Falta canonical, viewport y lang de html
    html = """
    <html>
        <head>
            <title>Título perfecto de longitud ideal para SEO</title>
            <meta name="description" content="Esta es una meta descripción perfecta de una longitud que cumple con los rangos ideales entre 70 y 160 caracteres." />
        </head>
        <body></body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    check_seo(soup, issues, regex_set)
    assert any("La etiqueta <html> no define el atributo lang" in issue for issue in issues)
    assert any("Falta canonical" in issue for issue in issues)
    assert any("Falta meta viewport" in issue for issue in issues)


def test_seo_multiple_h1_tags(regex_set):
    # Caso 6: Múltiples etiquetas H1 detectadas
    html = """
    <html lang="es">
        <head><title>Título perfecto de longitud ideal para SEO</title></head>
        <body>
            <h1>Primer H1</h1>
            <h1>Segundo H1</h1>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    check_seo(soup, issues, regex_set)
    assert any("Múltiples <h1> detectados" in issue for issue in issues)


def test_seo_missing_og_and_twitter_card(regex_set):
    # Caso 7: Falta Open Graph y Twitter card
    html = """
    <html lang="es">
        <head>
            <title>Título perfecto de longitud ideal para SEO</title>
            <meta property="og:title" content="Título" />
            <!-- faltan og:description y og:image -->
        </head>
        <body></body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    check_seo(soup, issues, regex_set)
    assert any("Open Graph incompleto" in issue for issue in issues)
    og_issues = [issue for issue in issues if "Open Graph incompleto" in issue]
    assert len(og_issues) > 0
    assert "og:description" in og_issues[0] or "og:image" in og_issues[0]
    assert any("Falta meta twitter:card" in issue for issue in issues)


def test_seo_jsonld_validation(regex_set):
    # Caso 8: Datos estructurados JSON-LD con sintaxis JSON inválida o sin contexto/tipo
    html_invalid = """
    <html>
        <head>
            <script type="application/ld+json">
            {
                invalid: json
            }
            </script>
        </head>
        <body></body>
    </html>
    """
    soup_invalid = BeautifulSoup(html_invalid, "html.parser")
    issues_invalid = []
    check_seo(soup_invalid, issues_invalid, regex_set)
    assert any("JSON-LD presente pero con sintaxis JSON inválida" in issue for issue in issues_invalid)

    html_missing_fields = """
    <html>
        <head>
            <script type="application/ld+json">
            {
                "name": "No Context No Type"
            }
            </script>
        </head>
        <body></body>
    </html>
    """
    soup_missing = BeautifulSoup(html_missing_fields, "html.parser")
    issues_missing = []
    check_seo(soup_missing, issues_missing, regex_set)
    assert any("JSON-LD presente pero sin @type ni @context válidos" in issue for issue in issues_missing)


def test_seo_image_alt_filename(regex_set):
    # Caso extra: Imagen con nombre de archivo como atributo alt
    html = """
    <html lang="es">
        <body>
            <img src="banner.jpg" alt="imagen_principal.png" />
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    check_seo(soup, issues, regex_set)
    assert any("El alt de una imagen es un nombre de archivo" in issue for issue in issues)
