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

DEFAULT_HEADERS  = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
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
AUDIT_REQUEST_DELAY_SECONDS = 0.35
AUDIT_MAX_RECURSIVE_LINKS = 40
AUDIT_MAX_CRAWL_DEPTH = 1
AUDIT_BANNED_HOSTS = {"apdigroup.com", "81.0.54.124"}

# ── Estrategia por defecto ────────────────────────────────────────────────────
DEFAULT_STRATEGY = "selenium"       # se sobreescribe por cada entrada del JSON