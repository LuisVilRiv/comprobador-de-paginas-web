from bs4 import BeautifulSoup

from shared.auditor.checks.buttons import check_buttons


# Mock helper functions
def mock_is_banned(url):
    return "banned" in url


def mock_classify_speed(elapsed_ms):
    return "fast" if elapsed_ms < 500 else "slow"


def mock_find_line(html_lines, tag):
    return 12, "<element>"


def test_buttons_perfect():
    # Caso 1: Botón con texto y formulario con action válido
    html = """
    <html>
        <body>
            <button>Enviar formulario</button>
            <input type="submit" value="Enviar ahora" />
            <form action="/submit-data" method="post"></form>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    def mock_check_url(url, method="get"):
        return True, 100, 200, ""

    check_buttons(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
        blocked_admin_segments=("/admin",),
    )

    assert len(issues) == 0


def test_buttons_missing_buttons_warning():
    # Caso 2: No hay ningún botón en la página
    html = "<html><body><h1>Página informativa</h1></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    check_buttons(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        is_banned_fn=mock_is_banned,
        check_url_fn=None,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
        blocked_admin_segments=("/admin",),
    )

    assert any("No hay botones detectables en el HTML estático" in issue for issue in issues)


def test_buttons_empty_text():
    # Caso 3: Botones o inputs de tipo submit vacíos
    html = """
    <html>
        <body>
            <button></button>
            <input type="submit" />
            <input type="button" value="" />
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    check_buttons(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        is_banned_fn=mock_is_banned,
        check_url_fn=None,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
        blocked_admin_segments=("/admin",),
    )

    # Debe reportar 3 issues de botones sin texto
    assert sum("Botón sin texto visible" in issue for issue in issues) == 3


def test_buttons_form_action_errors():
    # Caso 4: Formulario sin action o con action apuntando a admin bloqueado
    html = """
    <html>
        <body>
            <button>Enviar</button>
            <form id="form1"></form>
            <form id="form2" action="/admin/save"></form>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    check_buttons(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        is_banned_fn=mock_is_banned,
        check_url_fn=None,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
        blocked_admin_segments=("/admin",),
    )

    assert any("Formulario sin action" in issue for issue in issues)
    assert any("Formulario apunta a una ruta prohibida" in issue for issue in issues)


def test_buttons_form_action_broken():
    # Caso 5: Formulario con action que falla al probar (500)
    html = """
    <html>
        <body>
            <button>Enviar</button>
            <form action="/broken-submit" method="post"></form>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    def mock_check_url(url, method="get"):
        return False, 700, 500, ""

    check_buttons(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
        blocked_admin_segments=("/admin",),
    )

    assert any("Fallo al probar el action del formulario" in issue for issue in issues)
    assert any("método=POST" in issue for issue in issues)
    assert any("estado=500" in issue for issue in issues)
