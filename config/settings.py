from pathlib import Path

# ── Rutas del proyecto ────────────────────────────────────────────────────────
BASE_DIR         = Path(__file__).resolve().parent.parent
DATA_DIR         = BASE_DIR / "data"
URLS_JSON_PATH   = DATA_DIR / "urls.json"
OUTPUT_DIR       = DATA_DIR / "output"
RAW_DIR          = DATA_DIR / "raw"
REPORTS_DIR      = DATA_DIR / "reports"
LOG_DIR          = BASE_DIR / "logs"

# ── HTTP / Requests ───────────────────────────────────────────────────────────
REQUEST_TIMEOUT  = 15          # segundos
MAX_RETRIES      = 3
RETRY_DELAY      = 2           # segundos entre reintentos

# Pool de User-Agents reales para rotacion anti-deteccion
USER_AGENT_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

DEFAULT_HEADERS  = {
    "User-Agent": USER_AGENT_POOL[0],
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-CH-UA": '"Chromium";v="125", "Not=A?Brand";v="8", "Google Chrome";v="125"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}

# ── Selenium ──────────────────────────────────────────────────────────────────
SELENIUM_HEADLESS         = True
SELENIUM_IMPLICIT_WAIT    = 5       # segundos
SELENIUM_PAGE_LOAD_TIMEOUT = 30     # segundos
SELENIUM_DRIVER_PATH      = None    # None = busca ChromeDriver en PATH

# ── BeautifulSoup ─────────────────────────────────────────────────────────────
BS4_PARSER    = "html.parser"       # o "lxml" si está instalado
BS4_ENCODING  = "utf-8"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL   = "INFO"               # DEBUG | INFO | WARNING | ERROR
LOG_FILE    = LOG_DIR / "scraper.log"
LOG_FORMAT  = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
LOG_TO_FILE = True

# ── Exportación de resultados ─────────────────────────────────────────────────
OUTPUT_FORMAT            = "json"   # "json" | "csv"
OUTPUT_FILENAME_TEMPLATE = "results_{timestamp}.{ext}"

# ── Auditoria de calidad web ──────────────────────────────────────────────────
AUDIT_REQUEST_DELAY_SECONDS  = 0.35
AUDIT_MAX_RECURSIVE_LINKS    = 40
AUDIT_MAX_CRAWL_DEPTH        = 1
AUDIT_BANNED_HOSTS           = {"apdigroup.com", "81.0.54.124"}

# Interaccion real con botones via Selenium
AUDIT_BUTTON_INTERACTION_ENABLED = True
AUDIT_BUTTON_MAX_CLICKS          = 5        # maximo de botones que se pulsaran

# Captura de errores JS de consola (driver.get_log)
AUDIT_JS_LOGS_ENABLED = True

# Contenido delgado
AUDIT_MIN_WORD_COUNT = 150        # palabras minimas para paginas que no son home/contacto

# Keyword stuffing
AUDIT_KEYWORD_DENSITY_MAX = 0.08  # 8 %: densidad maxima de la keyword mas repetida

# Probing de rutas de administracion (se prueban con HTTP HEAD)
AUDIT_ADMIN_PROBE_PATHS = (
    "/admin", "/wp-admin", "/wp-login.php", "/administrator",
    "/admin/login", "/cpanel", "/phpmyadmin", "/backend",
    "/backoffice", "/manage", "/dashboard",
)

# Errores JS de consola (Selenium driver.get_log)
AUDIT_JS_CONSOLE_MAX_ERRORS = 25  # maximo de errores JS individuales a reportar

# ── Estrategia por defecto ────────────────────────────────────────────────────
DEFAULT_STRATEGY = "selenium"       # se sobreescribe por cada entrada del JSON