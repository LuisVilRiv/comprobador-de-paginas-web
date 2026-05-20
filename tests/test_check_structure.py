import pytest
from bs4 import BeautifulSoup
from shared.auditor.checks.structure import check_structure


def test_structure_perfect():
    # Caso 1: Estructura HTML perfecta, landmarks, sin errores jerárquicos o genéricos
    html = """
    <html lang="es">
        <head><title>Título</title></head>
        <body>
            <header role="banner">
                <nav role="navigation">
                    <a href="/">Inicio</a>
                </nav>
            </header>
            <main role="main">
                <h1>Título Principal</h1>
                <h2>Subtítulo de Sección</h2>
                <h3>Detalle de Sección</h3>
                <p>Texto descriptivo</p>
                <video src="promo.mp4"><track kind="captions" src="sub.vtt" /></video>
                <table>
                    <caption>Precios de planes</caption>
                    <tr><th>Plan</th><th>Precio</th></tr>
                    <tr><td>Básico</td><td>$10</td></tr>
                </table>
            </main>
            <footer role="contentinfo">
                <p>© 2026 Compañía</p>
            </footer>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    
    check_structure(soup, issues)
    assert len(issues) == 0


def test_structure_missing_essential_tags():
    # Caso 2: Falta html, head, body o h1
    soup_no_html = BeautifulSoup("<p>Sin estructura</p>", "html.parser")
    # Nota: BeautifulSoup suele auto-envolver en html/body si no están, por lo que podemos pasarle un mock
    class EmptySoup:
        html = None
        head = None
        body = None
    
    issues = []
    check_structure(EmptySoup(), issues)
    assert any("Falta la etiqueta <html>" in issue for issue in issues)


def test_structure_no_h1():
    # Caso 3: Falta h1
    html = """
    <html>
        <head></head>
        <body>
            <header></header><main></main><nav></nav><footer></footer>
            <h2>No hay H1</h2>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    check_structure(soup, issues)
    assert any("No existe ningún <h1>" in issue for issue in issues)


def test_structure_missing_landmarks():
    # Caso 4: Faltan landmarks estructurales (main, nav, header, footer)
    html = """
    <html>
        <head></head>
        <body>
            <h1>Título</h1>
            <div>Contenido general sin etiquetas semánticas</div>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    check_structure(soup, issues)
    assert any("Falta el landmark <main>" in issue for issue in issues)
    assert any("Falta el landmark <nav>" in issue for issue in issues)
    assert any("Falta el landmark <header>" in issue for issue in issues)
    assert any("Falta el landmark <footer>" in issue for issue in issues)


def test_structure_generic_anchor_texts():
    # Caso 5: Enlaces con textos genéricos e inútiles para lectores de pantalla
    html = """
    <html>
        <head></head>
        <body>
            <header></header><main></main><nav></nav><footer></footer>
            <h1>Título</h1>
            <a href="/info">Haz clic aquí</a>
            <a href="/more">Leer más</a>
            <a href="/about">AQUÍ</a>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    check_structure(soup, issues)
    assert sum("Enlace con texto genérico" in issue for issue in issues) == 3


def test_structure_target_blank_no_noopener():
    # Caso 6: Enlace con target='_blank' sin rel='noopener noreferrer'
    html = """
    <html>
        <head></head>
        <body>
            <header></header><main></main><nav></nav><footer></footer>
            <h1>Título</h1>
            <a href="https://externo.com" target="_blank">Enlace inseguro</a>
            <a href="https://externo.com" target="_blank" rel="noopener">Solo noopener</a>
            <a href="https://externo.com" target="_blank" rel="noopener noreferrer">Enlace seguro</a>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    check_structure(soup, issues)
    assert sum("sin rel='noopener noreferrer'" in issue for issue in issues) == 2


def test_structure_obsolete_html_elements():
    # Caso 7: Elementos HTML obsoletos (center, font, marquee)
    html = """
    <html>
        <head></head>
        <body>
            <header></header><main></main><nav></nav><footer></footer>
            <h1>Título</h1>
            <center><p>Texto centrado obsoleto</p></center>
            <font color="red">Texto font</font>
            <marquee>Texto móvil</marquee>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    check_structure(soup, issues)
    assert any("Elemento HTML obsoleto <center>" in issue for issue in issues)
    assert any("Elemento HTML obsoleto <font>" in issue for issue in issues)
    assert any("Elemento HTML obsoleto <marquee>" in issue for issue in issues)


def test_structure_headings_hierarchy_gaps():
    # Caso 8: Salto jerárquico brusco e incorrecto (h1 -> h3)
    html = """
    <html>
        <head></head>
        <body>
            <header></header><main></main><nav></nav><footer></footer>
            <h1>Título principal</h1>
            <h3>Detalle sin pasar por H2 (salto brusco)</h3>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    check_structure(soup, issues)
    assert any("Salto brusco en la jerarquía de encabezados" in issue for issue in issues)
