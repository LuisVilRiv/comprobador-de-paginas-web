"""
SETTINGS.PY - Configuración Global del Sistema

DESCRIPCIÓN:
Este módulo centraliza toda la configuración del sistema de auditoría web.
Las variables se pueden sobrescribir mediante variables de entorno para facilitar
el despliegue en diferentes entornos (desarrollo, producción, Docker).

SECCIONES:
- Rutas del proyecto: Directorios para datos, logs y reportes
- HTTP/Requests: Timeouts, reintentos y pool de User-Agents
- Selenium: Configuración del navegador headless
- BeautifulSoup: Configuración del parser HTML
- Logging: Nivel y formato de logs
- Auditoría: Umbrales de puntuación y parámetros de escaneo
- AI Analyzer: Configuración del servicio de análisis con IA

@version 1.0.1
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════════

import os
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# RUTAS DEL PROYECTO
# ═══════════════════════════════════════════════════════════════════════════════

# Directorio base del proyecto (dos niveles arriba de config/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Directorio para almacenamiento de datos
DATA_DIR = BASE_DIR / "data"
URLS_JSON_PATH = DATA_DIR / "urls.json"
OUTPUT_DIR = DATA_DIR / "output"
RAW_DIR = DATA_DIR / "raw"
REPORTS_DIR = DATA_DIR / "reports"

# Directorio para logs
LOG_DIR = BASE_DIR / "logs"

# ═══════════════════════════════════════════════════════════════════════════════
# HTTP / REQUESTS
# ═══════════════════════════════════════════════════════════════════════════════

# Timeout para solicitudes HTTP (segundos)
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "15"))

# Número máximo de reintentos para solicitudes fallidas
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))

# Delay entre reintentos (segundos)
RETRY_DELAY = int(os.environ.get("RETRY_DELAY", "2"))

# Pool de User-Agents reales para rotación anti-detección
USER_AGENT_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# Cabeceras HTTP por defecto para simular navegador real
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT_POOL[0],
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-CH-UA": '''"Chromium";v="125", "Not=A?Brand";v="8", "Google Chrome";v="125"''',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '''"Windows"''',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}

# ═══════════════════════════════════════════════════════════════════════════════
# SELENIUM
# ═══════════════════════════════════════════════════════════════════════════════

# Ejecutar Chrome en modo headless (sin interfaz gráfica)
SELENIUM_HEADLESS = os.environ.get("SELENIUM_HEADLESS", "true").lower() == "true"

# Tiempo de espera implícito para elementos (segundos)
SELENIUM_IMPLICIT_WAIT = int(os.environ.get("SELENIUM_IMPLICIT_WAIT", "5"))

# Timeout máximo para carga de página (segundos)
SELENIUM_PAGE_LOAD_TIMEOUT = int(os.environ.get("SELENIUM_PAGE_LOAD_TIMEOUT", "30"))

# Ruta al driver de Chrome (si es None, se busca en PATH)
SELENIUM_DRIVER_PATH = os.environ.get("SELENIUM_DRIVER_PATH")

# ═══════════════════════════════════════════════════════════════════════════════
# BEAUTIFULSOUP
# ═══════════════════════════════════════════════════════════════════════════════

# Parser HTML a utilizar
BS4_PARSER = os.environ.get("BS4_PARSER", "html.parser")

# Encoding por defecto para análisis HTML
BS4_ENCODING = os.environ.get("BS4_ENCODING", "utf-8")

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

# Nivel de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Archivo de log
LOG_FILE = LOG_DIR / "scraper.log"

# Formato de los mensajes de log (usando guion simple para máxima compatibilidad)
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"

# Habilitar escritura de logs a archivo
LOG_TO_FILE = os.environ.get("LOG_TO_FILE", "true").lower() == "true"

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN DE RESULTADOS
# ═══════════════════════════════════════════════════════════════════════════════

# Formato de salida (json, csv, xml)
OUTPUT_FORMAT = os.environ.get("OUTPUT_FORMAT", "json")

# Plantilla para nombres de archivo de resultados
OUTPUT_FILENAME_TEMPLATE = "results_{timestamp}.{ext}"

# ═══════════════════════════════════════════════════════════════════════════════
# AUDITORÍA DE CALIDAD WEB
# ═══════════════════════════════════════════════════════════════════════════════

# Delay entre solicitudes HTTP durante auditoría (segundos)
AUDIT_REQUEST_DELAY_SECONDS = float(os.environ.get("AUDIT_REQUEST_DELAY", "0.35"))

# Número máximo de enlaces recursivos a seguir
AUDIT_MAX_RECURSIVE_LINKS = int(os.environ.get("AUDIT_MAX_LINKS", "40"))

# Profundidad máxima de crawl
AUDIT_MAX_CRAWL_DEPTH = int(os.environ.get("AUDIT_MAX_DEPTH", "1"))

# Hosts prohibidos para el crawl (separados por coma)
AUDIT_BANNED_HOSTS = set(os.environ.get("AUDIT_BANNED_HOSTS", "apdigroup.com,81.0.54.124").split(","))

# Dominios prohibidos para el crawl (separados por coma)
AUDIT_BANNED_DOMAINS = set(os.environ.get("AUDIT_BANNED_DOMAINS", "").split(","))

# Número máximo de confirmaciones de navegador (alerts/confirm)
AUDIT_MAX_BROWSER_CONFIRMS = int(os.environ.get("AUDIT_MAX_BROWSER_CONFIRMS", "15"))

# ═══════════════════════════════════════════════════════════════════════════════
# UMBRALES DE PUNTUACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

# Puntuación mínima para considerar "excelente"
AUDIT_SCORE_EXCELLENT_THRESHOLD = int(os.environ.get("AUDIT_SCORE_EXCELLENT", "85"))

# Puntuación mínima para considerar "buena"
AUDIT_SCORE_GOOD_THRESHOLD = int(os.environ.get("AUDIT_SCORE_GOOD", "70"))

# Puntuación mínima para liberar el gate de calidad
AUDIT_RELEASE_GATE_MIN_SCORE = int(os.environ.get("AUDIT_RELEASE_GATE_MIN_SCORE", "70"))

# ═══════════════════════════════════════════════════════════════════════════════
# INTERACCIÓN CON BOTONES
# ═══════════════════════════════════════════════════════════════════════════════

# Habilitar interacción real con botones via Selenium
AUDIT_BUTTON_INTERACTION_ENABLED = os.environ.get("AUDIT_BUTTONS_ENABLED", "true").lower() == "true"

# Número máximo de clics en botones por auditoría
AUDIT_BUTTON_MAX_CLICKS = int(os.environ.get("AUDIT_BUTTON_MAX_CLICKS", "5"))

# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS DE CONTENIDO
# ═══════════════════════════════════════════════════════════════════════════════

# Habilitar captura de errores JS de consola
AUDIT_JS_LOGS_ENABLED = os.environ.get("AUDIT_JS_LOGS_ENABLED", "true").lower() == "true"

# Número mínimo de palabras para considerar contenido "suficiente"
AUDIT_MIN_WORD_COUNT = int(os.environ.get("AUDIT_MIN_WORD_COUNT", "150"))

# Densidad máxima de keywords (porcentaje)
AUDIT_KEYWORD_DENSITY_MAX = float(os.environ.get("AUDIT_KEYWORD_DENSITY_MAX", "0.08"))

# Rutas de administración a probar (separadas por coma)
_admin_paths_env = os.environ.get("AUDIT_ADMIN_PATHS")
AUDIT_ADMIN_PROBE_PATHS = (
    tuple(_admin_paths_env.split(","))
    if _admin_paths_env
    else (
        "/admin",
        "/wp-admin",
        "/wp-login.php",
        "/administrator",
        "/admin/login",
        "/cpanel",
        "/phpmyadmin",
        "/backend",
        "/backoffice",
        "/manage",
        "/dashboard",
    )
)

# Número máximo de errores JS en consola antes de marcar como fallo
AUDIT_JS_CONSOLE_MAX_ERRORS = int(os.environ.get("AUDIT_JS_CONSOLE_MAX_ERRORS", "25"))

# ═══════════════════════════════════════════════════════════════════════════════
# AI ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

# URL del servicio de análisis con IA
AI_ANALYZER_URL = os.environ.get("AI_ANALYZER_URL", "http://ai-analyzer:8080")

# Timeout para solicitudes al AI Analyzer (segundos)
AI_ANALYZER_TIMEOUT = float(os.environ.get("AI_ANALYZER_TIMEOUT", "6.0"))

# Habilitar análisis con IA
AI_ANALYZER_ENABLED = os.environ.get("AI_ANALYZER_ENABLED", "true").lower() == "true"

# ═══════════════════════════════════════════════════════════════════════════════
# ESTRATEGIA POR DEFECTO
# ═══════════════════════════════════════════════════════════════════════════════

# Estrategia de scraping por defecto (selenium, bs4, auto)
DEFAULT_STRATEGY = os.environ.get("DEFAULT_STRATEGY", "selenium")
