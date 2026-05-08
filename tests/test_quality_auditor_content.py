from bs4 import BeautifulSoup

from utils.quality_auditor import QualityAuditor


def _run_content_check(html: str) -> list[str]:
    auditor = QualityAuditor()
    soup = BeautifulSoup(html, "html.parser")
    issues: list[str] = []
    auditor._check_content(soup, issues, html.splitlines())
    return issues


def test_detects_lorem_and_explicit_content() -> None:
    html = """
    <html><body>
      <p>Lorem ipsum dolor sit amet</p>
      <p>Este texto incluye contenido explicito y porno.</p>
    </body></html>
    """
    issues = _run_content_check(html)
    joined = " | ".join(issues).lower()
    assert "lorem ipsum" in joined
    assert "contenido explicito" in joined or "porno" in joined


def test_detects_incoherent_and_noise_patterns() -> None:
    html = """
    <html><body>
      <p>asdf qwerty zxcv xxxxx abcabcabc</p>
      <p>%%%%% &&&&& #####</p>
      <p>aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb</p>
    </body></html>
    """
    issues = _run_content_check(html)
    joined = " | ".join(issues).lower()
    assert "texto problematico 'asdf'" in joined
    assert "bloques de simbolos excesivos" in joined or "caracteres repetitivos" in joined
    assert "tokens extremadamente largos" in joined


def test_detects_admin_segments_in_text() -> None:
    html = """
    <html><body>
      <p>Ir a /admin para gestionar.</p>
      <p>Tambien existe /wp-admin en documentacion vieja.</p>
    </body></html>
    """
    issues = _run_content_check(html)
    joined = " | ".join(issues).lower()
    assert "texto prohibido '/admin'" in joined
    assert "texto prohibido '/wp-admin'" in joined
