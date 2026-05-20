import pytest
from bs4 import BeautifulSoup
from shared.auditor.checks.links import check_links_recursive


# Mock functions for testing
def mock_is_banned(url):
    return "banned" in url


def mock_classify_speed(elapsed_ms):
    return "fast" if elapsed_ms < 500 else "slow"


def mock_find_line(html_lines, anchor):
    return 10, "<a>mock anchor</a>"


class MockSettings:
    AUDIT_MAX_RECURSIVE_LINKS = 5
    AUDIT_MAX_CRAWL_DEPTH = 2
    BS4_PARSER = "html.parser"


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    monkeypatch.setattr("shared.auditor.checks.links.settings", MockSettings)


def test_links_recursive_base_url_seen():
    # Caso 1: La URL base se añade automáticamente al conjunto 'seen', previniendo auto-rastrearse
    html = """
    <html>
        <body>
            <a href="https://example.com">Inicio (auto-referencial)</a>
            <a href="https://example.com/about">Sobre nosotros</a>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    crawl_stats = {"tested": 0, "skipped": 0, "broken": 0}
    
    called_urls = []
    def mock_check_url(url, include_content=False):
        called_urls.append(url)
        return True, 100, 200, ""  # ok, elapsed_ms, status_code, content
        
    check_links_recursive(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        crawl_stats=crawl_stats,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
        blocked_admin_segments=("/admin",)
    )
    
    # "https://example.com" ya está en seen, por lo que NO se debe rastrear como enlace hijo
    assert "https://example.com" not in called_urls
    assert "https://example.com/about" in called_urls
    assert crawl_stats["tested"] == 1


def test_links_recursive_circular_links_skipped():
    # Caso 2: Los enlaces circulares directos (A -> B -> A) se detectan y descartan
    html_a = """
    <html>
        <body>
            <a href="https://example.com/page-b">Ir a B</a>
        </body>
    </html>
    """
    html_b = """
    <html>
        <body>
            <a href="https://example.com/page-a">Ir de vuelta a A (circular)</a>
        </body>
    </html>
    """
    soup_a = BeautifulSoup(html_a, "html.parser")
    issues = []
    crawl_stats = {"tested": 0, "skipped": 0, "broken": 0}
    
    called_urls = []
    def mock_check_url(url, include_content=False):
        called_urls.append(url)
        if "page-b" in url:
            return True, 100, 200, html_b
        return True, 100, 200, ""
        
    check_links_recursive(
        soup=soup_a,
        base_url="https://example.com/page-a",
        html_lines=html_a.splitlines(),
        issues=issues,
        crawl_stats=crawl_stats,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
        blocked_admin_segments=("/admin",)
    )
    
    # Debe encolar "page-b", obtener su HTML, ver que apunta a "page-a", pero como "page-a" es la URL base (seen), omitirla
    assert "https://example.com/page-b" in called_urls
    assert len(called_urls) == 1
    assert crawl_stats["tested"] == 1


def test_links_recursive_duplicated_urls():
    # Caso 3: Enlaces duplicados en la página base se encolan y visitan una sola vez
    html = """
    <html>
        <body>
            <a href="https://example.com/target">Enlace 1</a>
            <a href="https://example.com/target">Enlace 2 (duplicado)</a>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    crawl_stats = {"tested": 0, "skipped": 0, "broken": 0}
    
    called_urls = []
    def mock_check_url(url, include_content=False):
        called_urls.append(url)
        return True, 100, 200, ""
        
    check_links_recursive(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        crawl_stats=crawl_stats,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
        blocked_admin_segments=("/admin",)
    )
    
    assert called_urls.count("https://example.com/target") == 1
    assert crawl_stats["tested"] == 1


def test_links_recursive_banned_url():
    # Caso 4: Las URLs prohibidas o baneadas por políticas son detectadas al descolar y se registran
    html = """
    <html>
        <body>
            <a href="https://example.com/banned-path">Página Baneada</a>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    crawl_stats = {"tested": 0, "skipped": 0, "broken": 0}
    
    called_urls = []
    def mock_check_url(url, include_content=False):
        called_urls.append(url)
        return True, 100, 200, ""
        
    check_links_recursive(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        crawl_stats=crawl_stats,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
        blocked_admin_segments=("/admin",)
    )
    
    assert "https://example.com/banned-path" not in called_urls
    assert crawl_stats["skipped"] == 1
    assert any("omitido por política de bloqueo" in issue for issue in issues)


def test_links_recursive_external_domains_ignored():
    # Caso 5: Enlaces que apuntan a dominios externos son detectados pero excluidos de la cola de rastreo
    html = """
    <html>
        <body>
            <a href="https://google.com">Google (Externo)</a>
            <a href="https://example.com/internal">Interno</a>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    crawl_stats = {"tested": 0, "skipped": 0, "broken": 0}
    
    called_urls = []
    def mock_check_url(url, include_content=False):
        called_urls.append(url)
        return True, 100, 200, ""
        
    check_links_recursive(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        crawl_stats=crawl_stats,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
        blocked_admin_segments=("/admin",)
    )
    
    assert "https://google.com" in called_urls  # La URL inicial sí se encola y comprueba su estatus (200)
    # Sin embargo, no se rastrean subenlaces de google.com
    assert "https://example.com/internal" in called_urls
    assert crawl_stats["tested"] == 2


def test_links_recursive_max_loop_iterations(monkeypatch):
    # Caso 6: El disparador max_loop_iterations garantiza la detención del bucle infinito ante colas infinitas mockeadas
    html = """
    <html>
        <body>
            <a href="https://example.com/page-1">1</a>
            <a href="https://example.com/page-2">2</a>
            <a href="https://example.com/page-3">3</a>
            <a href="https://example.com/page-4">4</a>
            <a href="https://example.com/page-5">5</a>
            <a href="https://example.com/page-6">6</a>
        </body>
    </html>
    """
    # Fijar el límite de links testeados en 2
    class TinySettings:
        AUDIT_MAX_RECURSIVE_LINKS = 2
        AUDIT_MAX_CRAWL_DEPTH = 2
        BS4_PARSER = "html.parser"
    monkeypatch.setattr("shared.auditor.checks.links.settings", TinySettings)

    soup = BeautifulSoup(html, "html.parser")
    issues = []
    crawl_stats = {"tested": 0, "skipped": 0, "broken": 0}
    
    called_urls = []
    def mock_check_url(url, include_content=False):
        called_urls.append(url)
        return True, 100, 200, ""
        
    check_links_recursive(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        crawl_stats=crawl_stats,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
        blocked_admin_segments=("/admin",)
    )
    
    # Se debe detener tras comprobar 2 enlaces (el límite máximo de la auditoría)
    assert len(called_urls) == 2
    assert crawl_stats["tested"] == 2


def test_links_recursive_depth_limits():
    # Caso 7: Enlaces con profundidad mayor al límite de rastreo no descargan su contenido (include_content=False)
    html_root = """
    <html>
        <body>
            <a href="https://example.com/depth-1">Ir a Profundidad 1</a>
        </body>
    </html>
    """
    html_d1 = """
    <html>
        <body>
            <a href="https://example.com/depth-2">Ir a Profundidad 2</a>
        </body>
    </html>
    """
    html_d2 = """
    <html>
        <body>
            <a href="https://example.com/depth-3">Ir a Profundidad 3</a>
        </body>
    </html>
    """
    soup = BeautifulSoup(html_root, "html.parser")
    issues = []
    crawl_stats = {"tested": 0, "skipped": 0, "broken": 0}
    
    checked_depths_with_content = []
    def mock_check_url(url, include_content=False):
        if include_content:
            checked_depths_with_content.append(url)
        if "depth-1" in url:
            return True, 100, 200, html_d1
        if "depth-2" in url:
            return True, 100, 200, html_d2
        return True, 100, 200, ""
        
    check_links_recursive(
        soup=soup,
        base_url="https://example.com",
        html_lines=html_root.splitlines(),
        issues=issues,
        crawl_stats=crawl_stats,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
        blocked_admin_segments=("/admin",)
    )
    
    # Con AUDIT_MAX_CRAWL_DEPTH = 2:
    # depth-1 (depth=0) -> include_content = True
    # depth-2 (depth=1) -> include_content = True
    # depth-3 (depth=2) -> include_content = False (No debe descargarse el HTML de profundidad superior a 2)
    assert "https://example.com/depth-1" in checked_depths_with_content
    assert "https://example.com/depth-2" in checked_depths_with_content
    assert "https://example.com/depth-3" not in checked_depths_with_content


def test_links_recursive_broken_link():
    # Caso 8: Los enlaces caídos o inaccesibles (ok=False) se clasifican como enlaces rotos y bajan score
    html = """
    <html>
        <body>
            <a href="https://example.com/broken-url">Enlace Roto</a>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    crawl_stats = {"tested": 0, "skipped": 0, "broken": 0}
    
    def mock_check_url(url, include_content=False):
        return False, 800, 404, ""
        
    check_links_recursive(
        soup=soup,
        base_url="https://example.com",
        html_lines=html.splitlines(),
        issues=issues,
        crawl_stats=crawl_stats,
        is_banned_fn=mock_is_banned,
        check_url_fn=mock_check_url,
        classify_speed_fn=mock_classify_speed,
        find_line_fn=mock_find_line,
        blocked_admin_segments=("/admin",)
    )
    
    assert crawl_stats["broken"] == 1
    assert any("Enlace roto confirmado" in issue for issue in issues)
