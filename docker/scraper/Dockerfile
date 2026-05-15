# ════════════════════════════════════════════════════════════════════════════
#  Contenedor: scraper
#  Build context: RAÍZ del repositorio  (se especifica en docker-compose.yml)
#  Dockerfile:   docker/scraper/Dockerfile
#
#  El contexto debe ser la raíz para poder copiar:
#    config/   → configuración del proyecto
#    scraper/  → paquete Python principal (estrategias, modelos, contexto)
#    shared/   → modelos, repositorios, auditor y utilidades compartidas
#
#  Ficheros específicos de Docker (entrypoint, db.py) se copian
#  desde docker/scraper/ dentro del mismo contexto.
# ════════════════════════════════════════════════════════════════════════════

FROM python:3.12-slim AS base

# ── Variables de entorno ─────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    CHROME_NO_SANDBOX=1

# ── Dependencias del sistema + Google Chrome ─────────────────────────────────
# Nota: libgconf-2-4 / libappindicator* ya no existen en Debian reciente;
# Chrome headless no los necesita para Selenium en contenedor.
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget curl gnupg ca-certificates unzip \
        libglib2.0-0 libnss3 libfontconfig1 \
        libxss1 \
        fonts-liberation libgtk-3-0 libxshmfence1 \
        libgbm1 xdg-utils \
        libpq-dev gcc \
    && wget -q -O /tmp/google-chrome.deb \
        https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/google-chrome.deb \
    && rm /tmp/google-chrome.deb \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ── Directorio de trabajo ────────────────────────────────────────────────────
WORKDIR /app

# ── Dependencias Python ──────────────────────────────────────────────────────
# Copiamos requirements desde docker/scraper/ (dentro del contexto = repo root)
COPY docker/scraper/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Paquetes Python del proyecto (desde la raíz del repo) ───────────────────
# Nota: "scraper/" aquí es el paquete Python del repo, no la carpeta docker/scraper/
COPY config/   ./config/
COPY scraper/  ./scraper/
COPY shared/   ./shared/

# ── Ficheros específicos del contenedor Docker ───────────────────────────────
COPY docker/scraper/*.py ./

# ── Directorios de datos y logs ──────────────────────────────────────────────
# En producción estos directorios son volúmenes montados desde el host
RUN mkdir -p /app/data/output /app/data/raw /app/data/reports /app/logs

# ── Usuario no-root ──────────────────────────────────────────────────────────
RUN useradd -m -u 1000 scraper && chown -R scraper:scraper /app
USER scraper

# ── Punto de entrada ─────────────────────────────────────────────────────────
CMD ["python", "entrypoint.py"]
