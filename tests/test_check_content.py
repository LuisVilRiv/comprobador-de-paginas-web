import re

import pytest
from bs4 import BeautifulSoup

from shared.auditor.checks.content import check_content


# Helper Mocks
class MockDicts:
    lorem_patterns = ["lorem ipsum", "dolor sit amet"]
    incoherent_patterns = ["asdfghjk", "qwertyuiop"]
    explicit_patterns = ["sexo gratis"]
    profanity_patterns = ["mierda", "puta"]
    hate_patterns = ["odio a"]
    blocked_admin_segments = ["/admin", "/wp-admin"]


class MockRegexSet:
    def __init__(self):
        self.gibberish_regex = re.compile(r"(.)\1{4,}")  # 5+ repeticiones
        self.multi_symbol_regex = re.compile(r"[\#\$\%\&]{4,}")
        self.character_noise_regex = re.compile(r"[\-\_\*\.]{5,}")
        self.typo_regex = re.compile(r"\b[bcdfghjklmnpqrstvwxyz]{5,}\b")  # sin vocales
        self.long_token_regex = re.compile(r"\b\w{25,}\b")
        # Usar grupos no capturadores (?:...) para que findall y finditer retornen la cadena completa
        self.spaced_chars_regex = re.compile(r"\b[a-z](?:\s[a-z]){2,}\b")
        self.dotted_chars_regex = re.compile(r"\b[a-z](?:[.\-_*][a-z]){2,}\b")
        # Densidades
        self.keyword_density_word_regex = re.compile(r"\b[a-z]{3,}\b")
        self.word_regex = re.compile(r"\b\w+\b")
        self.repeated_chunk_regex = re.compile(r"(\w{2,})\1{2,}")  # chunk repetido
        self.consonant_cluster_regex = re.compile(r"[bcdfghjklmnpqrstvwxyz]{6,}")


def mock_normalize(text):
    return text.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")


def mock_find_line(html_lines, pattern):
    return 10, "Línea con el patrón"


@pytest.fixture
def content_deps():
    return MockDicts(), MockRegexSet(), mock_normalize, mock_find_line


def test_content_perfect(content_deps):
    # Caso 1: Texto rico, sin evasiones, sin insultos, con aviso legal y contacto
    html = """
    <html>
        <body>
            <p>Bienvenidos a nuestra plataforma de desarrollo de software profesional en Madrid.</p>
            <p>Ofrecemos servicios de consultoría informática y diseño web a medida para empresas.</p>
            <p>Contamos con un equipo de ingenieros dedicados a resolver problemas de alta escala.</p>
            <p>Si deseas consultarnos tus dudas, visita nuestra página de contacto para más información.</p>
            <footer>
                <a href="/legal">Política de Privacidad y Aviso Legal</a>
            </footer>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    dicts, regex_set, norm_fn, find_fn = content_deps

    # Usar /contacto para evitar la validación de thin content
    check_content(soup, issues, html.splitlines(), "https://example.com/contacto", dicts, regex_set, norm_fn, find_fn)
    assert len(issues) == 0


def test_content_empty_body(content_deps):
    # Caso 2: Cuerpo vacío de texto
    html = "<html><body></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    dicts, regex_set, norm_fn, find_fn = content_deps

    check_content(soup, issues, html.splitlines(), "https://example.com/contacto", dicts, regex_set, norm_fn, find_fn)
    assert any("No se encontró texto visible en el body" in issue for issue in issues)


def test_content_lorem_and_profanity(content_deps):
    # Caso 3: Presencia de lorem ipsum e insultos directos
    html = """
    <html>
        <body>
            <p>lorem ipsum dolor sit amet.</p>
            <p>El servicio es una mierda total.</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    dicts, regex_set, norm_fn, find_fn = content_deps

    check_content(soup, issues, html.splitlines(), "https://example.com/contacto", dicts, regex_set, norm_fn, find_fn)
    assert any("[contenido de relleno] Patrón 'lorem ipsum'" in issue for issue in issues)
    assert any("[palabra malsonante] Patrón 'mierda'" in issue for issue in issues)


def test_content_evasion_spaced_and_dotted(content_deps):
    # Caso 4: Intentos de evasión con letras espaciadas o intercaladas con puntos
    html = """
    <html>
        <body>
            <p>Compre m i e r d a hoy mismo.</p>
            <p>Esto es una p.u.t.a estafa.</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    dicts, regex_set, norm_fn, find_fn = content_deps

    check_content(soup, issues, html.splitlines(), "https://example.com/contacto", dicts, regex_set, norm_fn, find_fn)
    assert any("Evasión con letras espaciadas 'm i e r d a'" in issue for issue in issues)
    assert any("Evasión con puntuación intercalada 'p.u.t.a'" in issue for issue in issues)


def test_content_exposed_admin_path(content_deps):
    # Caso 5: Ruta de administración expuesta en el cuerpo de texto visible
    html = """
    <html>
        <body>
            <p>Accede al panel en la dirección /wp-admin de la web.</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    dicts, regex_set, norm_fn, find_fn = content_deps

    check_content(soup, issues, html.splitlines(), "https://example.com/contacto", dicts, regex_set, norm_fn, find_fn)
    assert any("Ruta de administración expuesta en texto visible '/wp-admin'" in issue for issue in issues)


def test_content_thin_content(content_deps, monkeypatch):
    # Caso 6: Contenido delgado (menos del mínimo de palabras en configuración)
    html = """
    <html>
        <body>
            <p>Demasiado corto</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    dicts, regex_set, norm_fn, find_fn = content_deps

    # Parchear settings de min palabras
    class MockSettings:
        AUDIT_MIN_WORD_COUNT = 50
        AUDIT_KEYWORD_DENSITY_MAX = 0.35

    monkeypatch.setattr("shared.auditor.checks.content.settings", MockSettings)

    check_content(soup, issues, html.splitlines(), "https://example.com/blog", dicts, regex_set, norm_fn, find_fn)
    assert any("Contenido delgado" in issue for issue in issues)


def test_content_keyword_stuffing(content_deps, monkeypatch):
    # Caso 7: keyword stuffing excesivo (densidad muy alta de una misma palabra)
    text = "software software software software software software software software software software software desarrollo madrid"
    html = f"<html><body><p>{text}</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    dicts, regex_set, norm_fn, find_fn = content_deps

    class MockSettings:
        AUDIT_MIN_WORD_COUNT = 10
        AUDIT_KEYWORD_DENSITY_MAX = 0.40

    monkeypatch.setattr("shared.auditor.checks.content.settings", MockSettings)

    check_content(soup, issues, html.splitlines(), "https://example.com/contacto", dicts, regex_set, norm_fn, find_fn)
    assert any("Posible keyword stuffing: 'software'" in issue for issue in issues)


def test_content_missing_legal_and_contact(content_deps):
    # Caso 8: Falta aviso legal o política de privacidad y contacto en la página
    html = """
    <html>
        <body>
            <p>Ofrecemos servicios informáticos. Esto es una página de muestra de un negocio.</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    dicts, regex_set, norm_fn, find_fn = content_deps

    check_content(soup, issues, html.splitlines(), "https://example.com/contacto", dicts, regex_set, norm_fn, find_fn)
    assert any("No se detecta enlace ni texto de aviso legal ni de política de privacidad" in issue for issue in issues)
