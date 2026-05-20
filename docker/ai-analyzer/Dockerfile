FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/model_cache \
    CUDA_VISIBLE_DEVICES=""

WORKDIR /app

# Instalar dependencias del sistema mínimas necesarias para curl (healthchecks) y compresión
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Crear carpeta para la caché del modelo y dar permisos de escritura
RUN mkdir -p /app/model_cache

# Instalar dependencias de Python
# Torch CPU explícito: si va en requirements sin índice, pip instala CUDA (~4GB) y "exporting layers" tarda muchísimo.
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código del microservicio
COPY main.py ./
COPY app.py ./
COPY analyzer.py ./

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
