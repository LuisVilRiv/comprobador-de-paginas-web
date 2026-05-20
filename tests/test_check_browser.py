import pytest
from unittest.mock import MagicMock
from shared.auditor.checks.browser import check_js_console_errors, interact_buttons_selenium


class MockSettings:
    AUDIT_JS_CONSOLE_MAX_ERRORS = 3
    AUDIT_BUTTON_INTERACTION_ENABLED = True
    AUDIT_BUTTON_MAX_CLICKS = 2


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    monkeypatch.setattr("shared.auditor.checks.browser.settings", MockSettings)


def test_browser_check_console_errors():
    # Caso 1: Obtener logs de la consola JS y filtrar los severos/errores
    driver = MagicMock()
    driver.get_log.return_value = [
        {"level": "SEVERE", "message": "ReferenceError: x is not defined"},
        {"level": "WARNING", "message": "Some warnings"},
        {"level": "ERROR", "message": "Failed to load resource: 404"},
    ]
    issues = []
    
    check_js_console_errors(driver, "https://example.com", issues)
    
    assert len(issues) == 2
    assert any("ReferenceError" in issue for issue in issues)
    assert any("Failed to load resource" in issue for issue in issues)


def test_browser_check_console_errors_limit():
    # Caso 2: Respetar el límite de errores configurado (AUDIT_JS_CONSOLE_MAX_ERRORS = 3)
    driver = MagicMock()
    driver.get_log.return_value = [
        {"level": "SEVERE", "message": f"Error {i}"} for i in range(10)
    ]
    issues = []
    
    check_js_console_errors(driver, "https://example.com", issues)
    assert len(issues) == 3  # Límite máximo configurado en MockSettings


def test_browser_check_console_errors_driver_none():
    # Caso 3: Manejo elegante cuando el driver es None
    issues = []
    check_js_console_errors(None, "https://example.com", issues)
    assert len(issues) == 0


def test_browser_interact_buttons_none_or_disabled():
    # Caso 4: Evitar interacciones si el driver es None o la configuración está desactivada
    issues = []
    interact_buttons_selenium(None, "https://example.com", issues, None)
    assert len(issues) == 0


def test_browser_interact_buttons_alert():
    # Caso 5: Simular click en botón que gatilla una alerta no capturada
    driver = MagicMock()
    btn = MagicMock()
    btn.is_displayed.return_value = True
    
    # Mockear find_elements
    driver.find_elements.return_value = [btn]
    
    # Simular alerta al llamar btn.click()
    alert = MagicMock()
    alert.text = "¡Alerta importante!"
    driver.switch_to.alert = alert
    
    issues = []
    interact_buttons_selenium(driver, "https://example.com", issues, None)
    
    assert any("Alerta de navegador no capturada detectada al clicar botón: ¡Alerta importante!" in issue for issue in issues)
    alert.accept.assert_called_once()
