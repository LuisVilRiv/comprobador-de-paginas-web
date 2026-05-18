FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Build context = raíz del repositorio (definido en docker-compose.yml)

# Dependencias Python
COPY docker/dashboard/api/requirements.txt ./requirements.txt
COPY docker/scraper/requirements.txt ./scraper-requirements.txt
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -r scraper-requirements.txt

# Paquete compartido (modelos, repositorios, auditor)
COPY shared/ ./shared/

# Código del scraper (paquete y scripts de orquestación)
COPY scraper/ ./scraper/
COPY docker/scraper/entrypoint.py ./entrypoint.py
COPY docker/scraper/service.py ./service.py
COPY docker/scraper/scheduler.py ./scheduler.py

# Lógica de la API
COPY docker/dashboard/api/main.py ./main.py
COPY docker/dashboard/api/app.py ./app.py
COPY docker/dashboard/api/schemas/ ./schemas/
COPY docker/dashboard/api/routes/ ./routes/

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
