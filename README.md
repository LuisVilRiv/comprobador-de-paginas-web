# Web Auditor — Sistema de Auditoría Web Automatizada 🚀

Este proyecto es una plataforma integral para el escaneo, análisis y auditoría de calidad de sitios web. Permite gestionar clientes, programar auditorías periódicas y generar informes detallados sobre seguridad, SEO, rendimiento y accesibilidad.

## 🏗️ Arquitectura del Sistema

El proyecto sigue una arquitectura de **Sistemas Distribuidos** basada en contenedores, organizada bajo principios de **Alta Mantenibilidad** y **Separación de Responsabilidades (SRP)**.

### Componentes Principales:

1.  **Dashboard Frontend (React/Node)**: Interfaz de usuario intuitiva para la gestión de clientes, visualización de informes y configuración del scheduler.
2.  **Dashboard API (FastAPI)**: Backend RESTful que sirve como puente entre el frontend y la base de datos PostgreSQL.
3.  **Scraper & Auditor (Python/Selenium)**: Motor de ejecución que realiza el scraping de las URLs, ejecuta las pruebas de auditoría y persiste los resultados.
4.  **Shared Package (`/shared`)**: Núcleo de lógica compartida que garantiza consistencia entre la API y el Scraper.

---

## 📂 Organización del Proyecto

```text
/
├── config/             # Configuración global (Settings, Logging)
├── data/               # Volumen de datos (Exports, RAW HTML, Reports)
├── docker/             # Definiciones de contenedores y orquestación
│   ├── dashboard/      # Frontend y API del Dashboard
│   ├── scraper/        # Lógica de ejecución del contenedor Scraper
│   └── docker-compose.yml
├── scraper/            # Motor de scraping (Estrategias Selenium/BS4)
├── shared/             # Paquete compartido (EL CORAZÓN DEL PROYECTO)
│   ├── auditor/        # Motor de auditoría de calidad (Security, SEO, etc.)
│   └── database/       # Capa de persistencia (Modelos, Repositorios modulares)
└── tests/              # Pruebas unitarias y de integración
```

---

## 🧠 Decisiones de Diseño y Racional

### 1. Descomposición de "God Objects" en Repositorios Modulares
*   **Decisión**: Dividir `dashboard.py` y `scraper.py` en paquetes especializados por dominio (`clients`, `websites`, `runs`, `summary`).
*   **Por qué**: Evitar archivos gigantes imposibles de mantener. Cada módulo tiene ahora una **única responsabilidad (SRP)**, lo que facilita encontrar errores y añadir funcionalidades sin efectos secundarios.

### 2. Capa de Servicio (Service Layer) en el Scraper
*   **Decisión**: Extraer la orquestación del pipeline hacia un `AuditService`.
*   **Por qué**: Desacopla la lógica de ejecución del "entrypoint" del contenedor. Esto permite testear el proceso de auditoría de forma aislada y reutilizarlo en diferentes contextos (CLI, Daemon, API).

### 3. Configuración via Variables de Entorno (12-Factor App)
*   **Decisión**: Externalizar todos los parámetros (timeouts, umbrales de score, credenciales) al archivo `.env`.
*   **Por qué**: Permite cambiar el comportamiento del sistema sin tocar una sola línea de código. Facilita el despliegue en diferentes entornos (Dev/Prod) y mejora la seguridad.

### 4. Patrón Fachada (Facade) para Compatibilidad
*   **Decisión**: Mantener puntos de entrada limpios en `shared.database.repositories`.
*   **Por qué**: Permite que los consumidores (API/Scraper) no necesiten conocer la estructura interna de los paquetes de datos. Si la base de datos cambia, solo se actualiza el módulo interno, la interfaz se mantiene.

### 5. Componentización del Frontend
*   **Decisión**: Dividir el monolito `app.js` en módulos de ES6 (`api.js`, `modals.js`, etc.).
*   **Por qué**: Facilita el desarrollo colaborativo y la depuración del estado de React. Cada componente se encarga de su propia lógica visual.

---

## 🚀 Despliegue Rápido

El sistema está completamente contenedorizado con Docker.

1.  **Configuración**:
    ```bash
    cp docker/.env.example docker/.env
    # Ajustar variables si es necesario
    ```

2.  **Levantar el Stack**:
    ```bash
    cd docker
    docker compose up -d
    ```

3.  **Ejecutar el Scraper (Modo Manual)**:
    ```bash
    docker compose --profile scraper run --rm scraper
    ```

---

## 🛠️ Tecnologías Utilizadas

*   **Backend**: Python 3.12, FastAPI, SQLAlchemy, PostgreSQL.
*   **Frontend**: React 18 (via ESM), Vanilla CSS (Modern design).
*   **Scraping**: Selenium (Chrome Headless), BeautifulSoup4.
*   **Infraestructura**: Docker, Docker Compose.

---

*Documentación generada para asegurar la escalabilidad y transferencia de conocimiento del proyecto.*
