# web_auditor — Stack Docker

Herramienta de auditoría de calidad web dockerizada.

**Contenedores separados:** por defecto `docker compose up -d` levanta **tres** procesos en contenedores distintos: PostgreSQL, API FastAPI y frontend Node+React. El **scraper** (Chrome/Selenium, tráfico saliente a Internet) va en un **perfil aparte** para no mezclarlo con el stack web salvo que lo pidas explícitamente.

**Redes:** `web_auditor_backend` conecta la base de datos solo con quien debe hablar con ella (API y scraper). `web_auditor_web` conecta API y frontend; el contenedor del dashboard **no** está en la red del `db`, así que no puede resolver el hostname `db` aunque hubiera un fallo en el proxy.

---

## Estructura del repositorio

```
repo-raiz/
├── config/              ← configuración del proyecto Python
├── scraper/             ← paquete Python (estrategias, modelos)
├── utils/               ← auditor, exportador, url_loader
├── tests/
├── main.py              ← ejecución local (sin Docker, lee data/urls.json)
├── data/                ← gitignored (URLs privadas, outputs, informes)
│   └── urls.json
├── logs/                ← gitignored
├── .gitignore
└── docker/              ← TODO lo relacionado con Docker
    ├── .env.example     ← template de variables de entorno (commiteado)
    ├── .env             ← credenciales reales (gitignored — crearlo manualmente)
    ├── docker-compose.yml
    ├── db-init/
    │   └── 01_schema.sql
    ├── scraper/
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── entrypoint.py   ← lee URLs de PostgreSQL (distinto de main.py)
    │   └── db.py
    └── dashboard/
        ├── Dockerfile      ← frontend Node + React
        ├── server.js
        ├── frontend/
        │   ├── index.html
        │   ├── app.js
        │   └── styles.css
        └── api/
            ├── Dockerfile
            ├── main.py     ← API FastAPI
            └── requirements.txt
```

> **Nota sobre el build context del scraper**  
> El `Dockerfile` del scraper se construye con la raíz del repo como contexto
> (`context: ..` en el compose). Esto permite copiar `config/`, `scraper/` y
> `utils/` al contenedor sin duplicar código.

---

## Requisitos previos

- Docker Engine ≥ 24
- Docker Compose plugin v2 (`docker compose`, no `docker-compose`)

---

## Puesta en marcha

### 1. Crear el fichero `.env`

```bash
cd docker/
cp .env.example .env
# Editar .env con las credenciales reales
```

### 2. Levantar el stack

```bash
# Desde docker/
cd docker/
docker compose up -d

# O desde la raíz del repositorio
docker compose -f docker/docker-compose.yml up -d
```

El primer arranque inicializa la base de datos con el esquema y datos de demo.

Comprueba los contenedores:

```bash
docker compose ps
```

### 3. Abrir el dashboard

```
http://localhost:8080
```

---

## Gestión de URLs (clientes y páginas)

Las URLs ya **no** se leen de `data/urls.json` en modo Docker.  
Se gestionan directamente en PostgreSQL:

```sql
-- Añadir cliente
INSERT INTO clients (name, email, company)
VALUES ('Mi Cliente', 'cliente@ejemplo.com', 'Empresa S.L.');

-- Añadir página web
INSERT INTO websites (client_id, url, label, strategy)
SELECT id, 'https://miweb.es/', 'Mi Web', 'auto'
FROM   clients WHERE name = 'Mi Cliente';

-- Desactivar una URL
UPDATE websites SET active = FALSE WHERE url = 'https://antigua.es/';
```

Acceso a psql desde Docker:

```bash
cd docker/
docker compose exec db psql -U auditor -d web_auditor
```

---

## Ejecutar el scraper

### Una sola vez (manual)

```bash
cd docker/
docker compose --profile scraper run --rm scraper
```

### Modo daemon (intervalo automático)

En `.env`:
```env
RUN_INTERVAL_SECONDS=3600   # cada hora
```

Cambiar `restart: "no"` a `restart: unless-stopped` en `docker-compose.yml`
para el servicio `scraper`, y luego:

```bash
docker compose --profile scraper up -d scraper
```

### Cron del host (alternativa)

```cron
0 3 * * * cd /ruta/al/repo/docker && docker compose --profile scraper run --rm scraper >> /var/log/web_auditor_cron.log 2>&1
```

---

## Comandos habituales

```bash
# Desde docker/

# Ver logs en tiempo real
docker compose --profile scraper logs -f scraper
docker compose logs -f dashboard

# Parar todo
docker compose down

# Parar y borrar la base de datos (¡destructivo!)
docker compose down -v

# Rebuild tras cambios en el código Python del scraper
docker compose --profile scraper build scraper
docker compose --profile scraper run --rm scraper

# Rebuild de frontend dashboard
docker compose build dashboard
docker compose up -d dashboard

# Rebuild de API dashboard
docker compose build dashboard-api
docker compose up -d dashboard-api
```

---

## Variables de entorno

| Variable               | Valor por defecto      | Descripción                              |
|------------------------|------------------------|------------------------------------------|
| `POSTGRES_DB`          | `web_auditor`          | Nombre de la base de datos               |
| `POSTGRES_USER`        | `auditor`              | Usuario de PostgreSQL                    |
| `POSTGRES_PASSWORD`    | —                      | **Cambiar siempre en producción**        |
| `DASHBOARD_PORT`       | `8080`                 | Puerto del host para el dashboard        |
| `LOG_LEVEL`            | `INFO`                 | Nivel de logging (`DEBUG`/`INFO`/…)      |
| `RUN_INTERVAL_SECONDS` | `0`                    | `0` = una ejecución; `>0` = modo daemon  |

---

## Diferencias entre ejecución local y Docker

| Aspecto            | Local (`main.py`)              | Docker (`entrypoint.py`)         |
|--------------------|--------------------------------|----------------------------------|
| Fuente de URLs     | `data/urls.json`               | Tabla `websites` en PostgreSQL   |
| Persistencia       | Ficheros en `data/output/`     | PostgreSQL + `data/` como volumen|
| Selenium           | ChromeDriver local             | Chrome instalado en el contenedor|
| Modo daemon        | No                             | Sí (`RUN_INTERVAL_SECONDS`)      |
