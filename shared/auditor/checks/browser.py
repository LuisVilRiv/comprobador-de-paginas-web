"""
browser.py — Comprobaciones que requieren Selenium (interacción real).
"""
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from config import settings

logger = logging.getLogger(__name__)

def check_js_console_errors(driver, base_url, issues):
    """Extrae y reporta errores de la consola de JavaScript."""
    if not driver:
        return
    try:
        logs = driver.get_log("browser")
        count = 0
        for entry in logs:
            if entry["level"] in ["SEVERE", "ERROR"]:
                msg = entry["message"].replace("\n", " ")
                issues.append(f"Error de consola JS: {msg[:150]}...")
                count += 1
                if count >= settings.AUDIT_JS_CONSOLE_MAX_ERRORS:
                    break
    except Exception as e:
        logger.warning("No se pudieron obtener logs de consola para %s: %s", base_url, e)

def interact_buttons_selenium(driver, base_url, issues, auditor_instance):
    """Intenta interactuar con botones para detectar fallos post-renderizado."""
    if not driver or not settings.AUDIT_BUTTON_INTERACTION_ENABLED:
        return
    
    try:
        # Esperar a que haya botones o inputs
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.TAG_NAME, "button"))
        )
        buttons = driver.find_elements(By.TAG_NAME, "button")
        
        interacted = 0
        for btn in buttons[:settings.AUDIT_BUTTON_MAX_CLICKS]:
            if interacted >= settings.AUDIT_BUTTON_MAX_CLICKS:
                break
            
            # Solo botones visibles y con texto/id
            if not btn.is_displayed():
                continue
            
            try:
                # Comprobar si al clicar hay alertas o cambios bruscos
                # (Simulación básica de humo)
                btn.click()
                interacted += 1
                time.sleep(0.5)
                
                # Si hay una alerta, es mala práctica si no se captura
                try:
                    alert = driver.switch_to.alert
                    issues.append(f"Alerta de navegador no capturada detectada al clicar botón: {alert.text}")
                    alert.accept()
                except:
                    pass
                    
            except Exception:
                pass
    except Exception:
        pass
