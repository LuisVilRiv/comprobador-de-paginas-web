# Resumen del proyecto

# Resumen del proyecto

Archivos fuente relevantes

*   [.gitignore](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/.gitignore)
*   [README.md](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/README.md?plain=1)
*   [docker/docker-compose.yml](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml)

La plataforma **Web Auditor** es un sistema distribuido diseñado para el aseguramiento automatizado de la calidad web. Ofrece una suite completa para escanear, analizar y auditar sitios web con el fin de generar informes detallados sobre seguridad, SEO, rendimiento e integridad del contenido.

La plataforma está construida utilizando una arquitectura orientada a microservicios, aprovechando **FastAPI** para el backend, **React** para el panel de control y un motor **especializado de Python/Selenium** para scraping en la web profunda y análisis impulsados por IA.

## Capacidades Básicas

El sistema automatiza el ciclo de vida de una auditoría web mediante las siguientes funciones de alto nivel:

*   **Extracción automatizada**: Utiliza estrategias tanto estáticas (BeautifulSoup) como dinámicas (Selenium) para capturar contenido web.
*   **Auditoría Multidimensional**: Evalúa sitios en varias categorías, incluyendo cabeceras de seguridad, SEO, estructura HTML, calidad del contenido e integridad de enlaces.
*   **Análisis mejorado por IA**: Integra un microservicio de análisis semántico para detectar páginas inoperativas, modos de mantenimiento o patrones maliciosos que las heurísticas tradicionales podrían pasar por alto.
*   **Seguimiento histórico**: Persiste las auditorías para proporcionar vistas "diferenciales", permitiendo a los usuarios ver problemas nuevos, persistentes o resueltos a lo largo del tiempo.
*   **Informes**: Genera informes profesionales en PDF para clientes y resúmenes de alto nivel para los administradores.

## Arquitectura del sistema

El proyecto sigue una arquitectura **de Sistemas Distribuidos** organizada bajo principios de alta mantenibilidad y **Separación de Responsabilidades (SRP)**\[README.md:5-7\]. Se despliega como un conjunto de contenedores Docker que interactúan sobre redes virtuales aisladas.

### Interacción de Componentes de Alto Nivel

El siguiente diagrama ilustra cómo interactúan las entidades y servicios centrales a través de los límites de red definidos en la infraestructura.

**Diagrama: Mapa de componentes del sistema**

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["web_auditor_backend (Red)"]
        DB["PostgreSQL (web_auditor_db)"]
        IA["Analizador de IA (FastAPI/NLP)"]
        Raspador["Raspador/Auditor (AuditService)"]
    fin
    subgrafo subGraph1 ["web_auditor_web (Red)"]
        Panel de control["Panel (React/Node)"]
        API["Dashboard API (FastAPI)"]
    fin
    subgrafo subGraph0 ["Red Externa"]
        Internet["Internet (Sitios web objetivo)"]
    fin
    Panel de control -->|" API REST"| API
    API -->|" SQLAlchemy"| DB
    Raspador -->|" SQLAlchemy"| DB
    Raspador -->|" HTTP POST /analyze"| IA
    Raspador -->|" Selenio/Solicitudes"| Internet
    API -->|" Proxy Interno"| Raspador
```

*Fuentes: [README.md9-14](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/README.md?plain=1#L9-L14)[docker/docker-compose.yml26-30](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L26-L30)*

## Componentes clave

La base de código se divide en paquetes especializados para evitar anti-patrones de "God Object" \[README.md:39-41\].

| Componente | Entidad de código / Ruta | Responsabilidad |
| --- | --- | --- |
| Interfaz de panel | /docker/dashboard/frontend | UI para gestión de clientes y visualización de informes \[README.md:11\]. |
| API de panel | /docker/dashboard/api | Puente RESTful entre la interfaz y la base de datos \[README.md:12\]. |
| Motor rascador | /scraper | Orquesta el rastreo de sitios web y la extracción de contenido \[README.md:28\]. |
| Motor de auditoría | shared.auditor | La lógica central que ejecuta controles de calidad y calcula las puntuaciones \[README.md:30\]. |
| Sidecar de IA | /ai-analyzer | Proporciona clasificación semántica del contenido de la página \[docker/docker-compose.yml:61\]. |
| Capa de persistencia | shared.database | Modelos y repositorios SQLAlchemy centralizados \[README.md:31\]. |

Para un análisis profundo de cómo están estructurados estos componentes y sus topologías específicas de red, véase [Arquitectura y Mapa de Componentes](/LuisVilRiv/comprobador-de-paginas-web/1.1-architecture-and-component-map).

## Flujo de trabajo operativo

El sistema está diseñado para ser compatible con la "aplicación de 12 factores", externalizando todas las configuraciones mediante variables de entorno \[README.md:47-49\].

**Diagrama: Pipeline de Ejecución de Auditoría**

```mermaid
Diagrama de secuencia
    participante U como usuario (Panel de control)
    participante A como API del Panel de Control
    participante S como AuditService (Scraper)
    participante Q como Auditor de Calidad (Compartida)
    participante D como base de datos
    U->>A: Desencadenante de auditoría (POST /websites/{id}/audit)
    A->>D: Create AuditRun (estado=pendiente)
    S->>D: Encuesta para las campañas pendientes
    S->>S: Ejecutar ScrapeStrategy (Selenium/BS4)
    S->>Q: build_report(html_content)
    P->>P: Ejecutar una pipeline de 8 pasos (SEO, Seguridad, etc.)
    P->>D: Guardar AuditoríaRunSección y IssueAuditIssue
    S->>D: Actualizar AuditRun (estado=completado, puntuación=X)
    A->>U: Actualizar la interfaz mediante sondeos
```

*Fuentes: [README.md43-45](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/README.md?plain=1#L43-L45)[docker/docker-compose.yml118](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L118-L118)*

El modo de ejecución del raspador está controlado por la `variable de entorno RUN_INTERVAL_SECONDS`. Si se establece en `>0`, el sistema actúa como un demonio; si `<=0`, realiza una ejecución de una sola vez y sale de \[docker/docker-compose.yml:100-101\].

Para instrucciones detalladas de configuración y modos de despliegue, consulta [Comienzo y Despliegue](/LuisVilRiv/comprobador-de-paginas-web/1.2-getting-started-and-deployment).

* * *

# Arquitectura-&-Component-Map

# Arquitectura y Mapa de Componentes

Archivos fuente relevantes

*   [docker/.gitignore](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/.gitignore)
*   [docker/README.md](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/README.md?plain=1)
*   [docker/ai-analyzer/Dockerfile](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/Dockerfile)
*   [docker/dashboard/Dockerfile](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/Dockerfile)
*   [docker/dashboard/api/Dockerfile](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/Dockerfile)
*   [docker/docker-compose.yml](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml)

La plataforma Web Auditor está diseñada como un sistema distribuido y contenedorizado para el aseguramiento automatizado de la calidad web. Sigue una arquitectura orientada a microservicios donde las responsabilidades se reparten entre interfaz de usuario, orquestación de datos, adquisición de contenido y análisis semántico.

## Topología de sistemas y comunicación

El sistema se despliega utilizando una topología de doble red para hacer cumplir los límites de seguridad entre el panel público y la capa interna de persistencia de datos.

*   **`web_auditor_web` Red**: Conecta el `panel` de control (Frontend) y la `API del panel`. La interfaz no tiene acceso directo a la base de datos [docker/docker-compose.yml29-30](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L29-L30)[docker/docker-compose.yml145-146](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L145-L146)
*   **`web_auditor_backend` Red**: Conecta la `base de datos`, `la API del panel` de control y el `analizador de IA`. Esta red aísla la instancia de PostgreSQL de acceso externo [directo docker/docker-compose.yml27-28](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L27-L28)[docker/docker-compose.yml39-40](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L39-L40)

### Mapa de Interacción de Componentes

El siguiente diagrama ilustra el flujo de datos desde una solicitud de usuario en el panel de control hasta el proceso de scraping en segundo plano y análisis de IA.

**Diagrama: Entidad del Sistema y Mapa de Comunicación**

```mermaid
diagrama de flujo LR
    Internet["Sitios web externos"]
    subgrafo subGraph2 ["Red Backend (web_auditor_backend)"]
        DB["web_auditor_db<br>PostgreSQL"]
        AIAnalyzer["#91; AI-Analyzer#93; <br>Sidecar FastAPI"]
        ScraperProcess["#91; Demonio-Raspador#93; <br>entrypoint.py"]
    fin
    subgrafo subGraph1 ["Red Web (web_auditor_web)"]
        Panel de control["#91; Panel de control#93; <br>Nodo/Servidor Expreso"]
        DashboardAPI["#91; dashboard-api#93; <br>Aplicación FastAPI"]
    fin
    subgrafo subGraph0 ["Red pública (Puerto 3000/8080)"]
        Usuario["Navegador de usuarios"]
    fin
    Usuario -->|" HTTP"| Salpicadero
    Panel de control -->|" Solicitudes de API proxy"| DashboardAPI
    DashboardAPI -->|" SQL (SQLAlchemy)"| DB
    ScraperProcess -->|" SQL (SQLAlchemy)"| DB
    ScraperProcess -->|" POST /analyze"| AIAnalyzer
    ScraperProcess -->|" HTTP/HTTPS"| Internet
```

**Fuentes:**[docker/docker-compose.yml26-31](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L26-L31)[docker/docker-compose.yml125-147](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L125-L147)[docker/README.md6-8](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/README.md?plain=1#L6-L8)

* * *

## Servicios Principales

### 1\. Interfaz de panel de control (panel de `control`)

Una aplicación Node.js/Express que sirve a una aplicación de página única basada en React. Actúa como la interfaz principal para gestionar clientes, sitios web y visualizar los resultados de auditorías.

*   **Implementación**: Sirve archivos estáticos desde `/app/frontend` a través `de server.js`[docker/dashboard/Dockerfile8-9](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/Dockerfile#L8-L9)
*   **Responsabilidad**: Visualiza las puntuaciones de auditoría, diferencias entre ejecuciones y proporciona disparadores de exportación en PDF.

### 2\. API de panel de control (`dashboard-api`)

Una aplicación FastAPI que actúa como orquestador central. Gestiona la interfaz RESTful para el frontend y comparte el mismo entorno de contenedor que el demonio scraper para un desarrollo [simplificado de docker/docker-compose.yml84-118](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L84-L118)

*   **Archivos clave**: `main.py`[docker/dashboard/api/](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/main.py)`main.py`[app.py docker/dashboard/api/app.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/app.py) y rutas modulares en `routes/`[docker/dashboard/api/routes/](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/)[docker/dashboard/api/Dockerfile38-41](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/Dockerfile#L38-L41)

### 3\. Raspador y Auditor (`raspador`)

El motor responsable de la adquisición de contenido y la evaluación de calidad. Puede ejecutarse como una herramienta de CLI de un solo uso o como un demonio en segundo plano.

*   **Ejecución en modo dual**: Controlado por `RUN_INTERVAL_SECONDS`. Si `> 0`, se ejecuta como un demonio; de lo contrario, ejecuta un único ciclo [de auditoría docker/docker-compose.yml101](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L101-L101)[docker/README.md197](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/README.md?plain=1#L197-L197)
*   **Punto de entrada**: `entrypoint.py`[docker/scraper/entrypoint.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/entrypoint.py) que coordina el [docker/dashboard/api/Dockerfile33-35 de AuditService y AuditScheduler](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/Dockerfile#L33-L35)
*   **Capacidades**: Incluye una instalación completa de Google Chrome para el scraping basado en Selenium de [los SPAs docker/dashboard/api/Dockerfile15-18](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/Dockerfile#L15-L18)

### 4\. Analizador de IA (`analizador de IA`)

Un microservicio especializado en Python que proporciona inteligencia semántica.

*   **Implementación**: Utiliza `SentenceTransformers` y `Torch` (optimizados para CPU) para realizar clasificación sin disparos y análisis basado en [incrustación docker/analizador de IA/Dockerfile19-23](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/Dockerfile#L19-L23)
*   **Comunicación**: Expone un endpoint `POST /analyze` utilizado por `el QualityAuditor` para detectar páginas inoperativas o contenido malicioso [docker/docker-compose.yml61-78](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L61-L78)

**Fuentes:**[docker/docker-compose.yml61-147](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L61-L147)[docker/dashboard/api/Dockerfile1-45](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/Dockerfile#L1-L45)[docker/ai-analyzer/Dockerfile1-33](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/Dockerfile#L1-L33)

* * *

## Estrategia de código compartido

Para mantener la coherencia entre los componentes distribuidos (API y Scraper), el proyecto utiliza un paquete `compartido/`. Este paquete se monta en contenedores para evitar la duplicación de código [docker/docker-compose.yml105](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L105-L105)

**Diagrama: Mapa de dependencia de entidades de código**

```mermaid
Diagrama de clases.
    class SharedPackage {
        <<Folder>>
        compartido/base de datos/modelos
        compartido/base de datos/repositorios
        compartido/auditor/Auditor de Calidad
    }
    class DashboardAPI {
        <<Service>>
        app.py
        Rutas/websites.py
    }
    class ScraperDaemon {
        <<Service>>
        entrypoint.py
        scheduler.py
    }
    DashboardAPI .. > SharedPackage: importa modelos/repositorios
    ScraperDaemon... > SharedPackage : importa QualityAuditor
    ScraperDaemon... > SharedPackage : importa repositorios
```

**Fuentes:**[docker/dashboard/api/Dockerfile29-35](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/Dockerfile#L29-L35)[docker/README.md48-51](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/README.md?plain=1#L48-L51)

* * *

## Enfoque de configuración de 12 factores

El sistema sigue los principios de la aplicación de 12 factores separando estrictamente la configuración del código usando variables de entorno, gestionadas mediante un [docker de archivo .env/README.md188-198](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/README.md?plain=1#L188-L198)

| Variable | Servicio | Propósito |
| --- | --- | --- |
| DB\_HOST | API / Raspador | Nombre de host del contenedor (db) de PostgreSQL docker/docker-compose.yml94 |
| AI\_ANALYZER\_URL | API / Raspador | URL interna para el sidecar de IA (http://ai-analyzer:8080) docker/docker-compose.yml99 |
| RUN\_INTERVAL\_SECONDS | Raspador | Define la frecuencia de auditoría; 0 desactiva el scheduler docker/docker-compose.yml101 |
| API\_BASE\_URL | Salpicadero | Backend endpoint for frontend proxying docker/docker-compose.yml137 |

**Fuentes:**[docker/docker-compose.yml93-102](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L93-L102)[docker/README.md190-198](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/README.md?plain=1#L190-L198)

* * *

# Inicio-y-despliegue

# Comienzo y despliegue

Archivos fuente relevantes

*   [config/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/__init__.py)
*   [configuración/logging\_config.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/logging_config.py)
*   [configuración/settings.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py)
*   [docker/.env.ejemplo](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/.env.example)
*   [Docker/Panel de control/package.json](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/package.json)
*   [docker/docker-compose.yml](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml)

Esta página ofrece una guía técnica completa para configurar la plataforma Web Auditor en un entorno local de desarrollo o producción. Cubre la configuración del entorno, el despliegue basado en Docker y los modos de ejecución del motor de auditoría.

## Configuración del entorno

El sistema utiliza un enfoque de aplicación de 12 factores para la configuración, basándose en variables de entorno para gestionar las credenciales de la base de datos, los umbrales de auditoría y los parámetros de scraping.

### Pasos de preparación

1.  **Clonar el repositorio**: Asegúrate de tener toda la estructura de directorios.
2.  **Inicializar variables de entorno**: Copiar el archivo plantilla `docker/.env.example` a `docker/.env`[docker/.env.example1-34](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/.env.example#L1-L34)
3.  **Personalizar configuración**: `Edita docker/.env` para definir tus parámetros locales. Las variables clave incluyen:

*   `POSTGRES_PASSWORD`: Docker de credenciales de seguridad [de bases de datos/.env.example4](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/.env.example#L4-L4)
*   `DASHBOARD_PORT`: puerto host para el frontend de React (por defecto: 3000) [docker/.env.example7](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/.env.example#L7-L7)
*   `RUN_INTERVAL_SECONDS`: Controla el programador de auditoría de frecuencia [docker/.env.example11](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/.env.example#L11-L11)

### Mapeo de configuración

El backend de Python carga estas variables mediante `config/settings.py`, que proporciona valores predeterminados y conversión de tipos para el resto de la [aplicación config/settings.py1-110](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L1-L110)

| Variable | Entidad de código | Propósito |
| --- | --- | --- |
| RUN\_INTERVAL\_SECONDS | dashboard-api (Env) | Retraso entre ciclos de auditoría en modo daemon docker/docker-compose.yml101 |
| AUDIT\_MAX\_LINKS | Configuraciones. AUDIT\_MAX\_RECURSIVE\_LINKS | Máximo de enlaces internos rastreados por sitio, config/settings.py67 |
| AI\_ANALYZER\_URL | Configuraciones. AI\_ANALYZER\_URL | Endpoint para el análisis semántico sidecar config/settings.py104 |
| SELENIUM\_HEADLESS | Configuraciones. SELENIUM\_HEADLESS | Activa el modo sin interfaz gráfica para Chromeconfig/settings.py46 |

**Fuentes:**[docker/.env.example1-34](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/.env.example#L1-L34)[config/settings.py1-110](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L1-L110)[docker/docker-compose.yml93-102](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L93-L102)

* * *

## Despliegue de Docker

El proyecto utiliza Docker Compose para orquestar cuatro servicios principales en dos redes distintas: `web_auditor_backend` y `web_auditor_web`[docker/docker-compose.yml26-31](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L26-L31)

### Arquitectura de pila de servicios

El siguiente diagrama ilustra cómo los servicios Docker se corresponden con las entidades de código y cómo están conectados en red.

**Mapeo de entidad sistema a código: pila de despliegue**

**Fuentes:**[docker/docker-compose.yml26-147](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L26-L147)[docker/dashboard/package.json1-26](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/package.json#L1-L26)

### Comandos de Despliegue

Para empezar toda la pila, navega hasta el directorio `/docker` y ejecuta:

```
docker compose up -d
```

Esto inicializa la base de datos con los scripts en `./db-init`[docker/docker-compose.yml49](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L49-L49), inicia el analizador de IA y lanza la API del panel de control.

**Fuentes:**[docker/docker-compose.yml16-17](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L16-L17)[docker/docker-compose.yml35-58](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L35-L58)

* * *

## Modos de ejecución: One-Shot vs. Daemon

El sistema gestiona la ejecución del motor Scraper/Auditor a través de la variable `de entorno RUN_INTERVAL_SECONDS`, que se interpreta mediante el script `de entrypoint.py` dentro del `dashboard-api` container [docker/docker-compose.yml101-118](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L101-L118)

### Lógica de modos

El comportamiento está determinado por el valor de `RUN_INTERVAL_SECONDS`:

1.  **Modo One-Shot (`<= 0`)**: El scraper se ejecuta exactamente una vez al iniciar el contenedor y luego termina, dejando solo la API activa.
2.  **Modo Daemon (`> 0`)**: El scraper entra en un bucle, permaneciendo en reposo durante el número especificado de segundos entre ciclos de auditoría.

### Flujo de datos de ejecución

El contenedor `dashboard-api` ejecuta dos procesos concurrentes: el servidor `uvicorn` para la API REST y el script `python /app/entrypoint.py` para el planificador de auditoría [docker/docker-compose.yml118](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L118-L118)

**Flujo de ejecución de auditoría**

```mermaid
Diagrama de secuencia
    participante E como "entrypoint.py"
    participante S como "AuditScheduler"
    participante P como "AuditService.process_website"
    Base de datos participante como "web_auditor_db"
    E->>S: "Inicializar con RUN_INTERVAL_SECONDS"
    S->>DB: "Consulta a auditorías pendientes"
    DB-->>S: "Lista de sitios web"
    S->>P: "Ejecutar la cadena de auditoría"
    P->>DB: "Guardar AuditRun y Issues"
    S->>S: "Dormir(RUN_INTERVAL_SECONDS)"
```

**Fuentes:**[docker/docker-compose.yml100-118](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L100-L118)[config/settings.py66-75](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L66-L75)

* * *

## Registro y persistencia

### Configuración de registro

Los registros se gestionan mediante `config/logging_config.py`, que configura tanto un `StreamHandler` (consola) como un `RotatingFileHandler`[config/logging\_config.py27-41](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/logging_config.py#L27-L41)

*   **Nivel de registro**: Definido por `LOG_LEVEL` (por defecto: `INFO)` [config/settings.py56](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L56-L56)
*   **Rotación**: Los archivos rotan a 5MB, manteniendo 3 [copias de seguridad de configuración/logging\_config.py36-37](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/logging_config.py#L36-L37)

### Volúmenes persistentes

Los volúmenes Docker aseguran que los datos sobrevivan a los reinicios de contenedores:

*   `pg_data`: Almacena los archivos de la base de datos PostgreSQL [docker/docker-compose.yml47](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L47-L47)
*   `ai_model_cache`: Almacena modelos de PLN descargados para el `ai-analyzer`[docker/docker-compose.yml70](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L70-L70)
*   `scraper_logs`: Almacena el `archivo scraper.log` [docker/docker-compose.yml111](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L111-L111)

**Fuentes:**[config/logging\_config.py1-44](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/logging_config.py#L1-L44)[docker/docker-compose.yml149-156](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/docker-compose.yml#L149-L156)[config/settings.py55-59](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L55-L59)

* * *

# Motor de Auditoría Principal

# Motor de Auditoría Principal

Archivos fuente relevantes

*   [compartido/auditor/auditor\_modules/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/__init__.py)
*   [compartido/auditor/auditor\_modules/core.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py)
*   [compartido/auditor/models.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/models.py)
*   [Pruebas/test\_inoperative\_pages.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_inoperative_pages.py)

El **Motor de Auditoría Núcleo** es la inteligencia central de la plataforma, responsable de transformar el HTML en bruto y los metadatos del navegador en informes estructurados de calidad. Está encapsulado dentro del paquete `compartido/auditor` y gestionado por la clase `QualityAuditor`.

El motor funciona como una tubería modular que evalúa un sitio web en múltiples dimensiones: seguridad, SEO, integridad del contenido, rendimiento técnico y experiencia del usuario.

## La clase QualityAuditor

`El QualityAuditor`[shared/auditor/auditor\_modules/core.py101-111](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L101-L111) es el punto de entrada principal para la lógica de auditoría. Mantiene una `solicitud persistente. Sesión` para el rendimiento y gestiona el ciclo de vida de una única ejecución de auditoría.

### Mapeo del sistema: lógica de auditoría a entidades de código

El siguiente diagrama ilustra cómo el concepto abstracto de una "Auditoría de Sitio Web" se asigna a clases y módulos específicos dentro de la base de código.

**Mapa de relaciones de la entidad de auditoría**

```mermaid
diagrama de flujo LR
    subgrafo subGraph1 ["Espacio de Entidades de Código"]
        QA["class QualityAuditor"]
        QAR["dataclass QualityAuditReport"]
        Pasos["build_report() Pipeline"]
        Cálculo["calculate_score()"]
    fin
    subgrafo subGraph0 ["Espacio de lenguaje natural"]
        Auditoría["Auditoría de sitios web"]
        Heurísticas["Heurísticas inoperativas"]
        Puntuación["Quality Score"]
    fin
    Auditoría --> QA
    QA --> Pasos
    Pasos --> QAR
    Heurísticas -- > pasos
    Puntuación --> Cálculo
    Cálculo --> QAR
```

**Fuentes:**[compartido/auditor/auditor\_modules/core.py101-113](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L101-L113)[compartido/auditor/models.py11-25](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/models.py#L11-L25)[compartido/auditor/scorering.py32-35](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L32-L35)

## La tubería de 8 pasos

El motor ejecuta una pipeline estrictamente secuenciada de 8 pasos dentro del método [build\_report shared/auditor/auditor\_modules/core.py113-126](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L113-L126). Esta pipeline garantiza que se realicen comprobaciones fundamentales (como determinar si el sitio está siquiera "activo") antes de un análisis profundo de contenido.

1.  **Inicialización y detección inoperativa**: Comprobación heurística para errores 404/500, modos de mantenimiento o páginas de error "delgadas" [compartidas/auditor/auditor\_modules/core.py149-210](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L149-L210)
2.  **Seguridad y encabezados**: Análisis de SSL, HSTS y opciones de tramas X.
3.  **SEO y Metadatos**: Validación de títulos, descripciones y etiquetas OpenGraph.
4.  **Estructura y accesibilidad**: Evaluación de la semántica y las jerarquías de encabezados HTML5.
5.  **Análisis de contenido**: detección de relleno de palabras clave, coincidencia de patrones tóxicos y recuento de palabras.
6.  **Medios y rendimiento**: Optimización de imágenes, texto ALT e indicadores de desplazamiento de diseño.
7.  **Conectividad (Crawler):** Recorrido recursivo de BFS para encontrar enlaces internos/externos rotos.
8.  **Interactividad**: Validación de botones y formularios, incluyendo monitorización de errores en la consola JS.

Para un análisis profundo del ciclo de vida de la tubería y las heurísticas de detección de errores, véase **[QualityAuditor Pipeline](/LuisVilRiv/comprobador-de-paginas-web/2.1-qualityauditor-pipeline)**.

## Módulos de Verificación de Auditoría

La lógica para comprobaciones específicas se desacopla de la clase core y reside en módulos especializados dentro `de shared/auditor/checks/`[shared/auditor/auditor\_modules/core.py23-27](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L23-L27) Esta modularidad permite ampliar el motor con nuevas reglas de auditoría sin modificar la lógica de orquestación.

| Módulo | Responsabilidad | Funciones clave |
| --- | --- | --- |
| Seguridad | Cabecera y seguridad SSL | check\_security |
| SEO | Visibilidad en motores de búsqueda | check\_seo |
| Contenido | Calidad semántica y spam | check\_content |
| Enlaces | Conectividad y enlaces muertos | check\_links\_recursive |
| Técnico | Rendimiento y errores en JS | check\_technical, check\_js\_console\_errors |

Para detalles sobre lógica de comprobación individual y patrones regex, véase **[Módulos de Comprobación de Auditoría](/LuisVilRiv/comprobador-de-paginas-web/2.2-audit-check-modules)**.

## Puntuación y Puertas de Lanzamiento

Una vez completadas todas las comprobaciones, el motor agrega los resultados en una puntuación numérica (0-100) utilizando un modelo de deducción [ponderada compartido/auditor/puntuación.py32-35](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L32-L35)

La función `evaluate_release_gate` determina si los resultados de la auditoría deben "bloquear" un despliegue o una versión en producción basándose en fallos críticos (por ejemplo, vulnerabilidades de seguridad o un sitio inoperativo) [compartido/auditor/auditor\_modules/core.py255-265](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L255-L265)

Para más detalles sobre el algoritmo de puntuación y los umbrales de bloqueadores, **[véase Scoring & Release Gate](/LuisVilRiv/comprobador-de-paginas-web/2.3-scoring-and-release-gate)**.

## Implementación del Link Crawler

El motor incluye un rastreador integrado de búsqueda en amplitud (BFS) para validar la integridad del sitio. Se encarga de la deduplicación, el enrutamiento interno vs. externo, y respeta restricciones de seguridad como `AUDIT_MAX_CRAWL_DEPTH` para evitar bucles infinitos.

**Flujo de ejecución de rastreo**

```mermaid
diagrama de flujo LR
    Informe["QualityAuditReport"]
    Subgráfico shared_auditor_checks_ ["compartido/auditor/comprobaciones/"]
        Inicio["check_links_recursive"]
        Cola ["Cola de enlaces"]
        Visto["Conjunto visto"]
        Requerimiento["HTTP HEAD/GET"]
    fin
    Cola de inicio -->
    Cola --> Visto
    Visto -->|" Nuevo enlace"| Requisito
    Requisición --->|" Éxito"| Cola
    Requisición --->|" 404/Rota"| Informe
```

**Fuentes:**[compartido/auditor/auditor\_modules/core.py23-31](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L23-L31)[compartido/auditor/checks/links.py1-50](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L1-L50) (implícito por importaciones)

Para detalles de implementación en el rastreador, véase **[Link Crawler](/LuisVilRiv/comprobador-de-paginas-web/2.4-link-crawler)**.

## Páginas Infantiles

*   **[Pipeline de QualityAuditor](/LuisVilRiv/comprobador-de-paginas-web/2.1-qualityauditor-pipeline)**: Heurísticas, sobreescrituras de IA y el ciclo de vida de 8 pasos.
*   **[Módulos de Auditoría de Comprobación](/LuisVilRiv/comprobador-de-paginas-web/2.2-audit-check-modules)**: Desglose técnico de seguridad, SEO y comprobaciones de contenido.
*   **[Puntuación y Puerta de Liberación](/LuisVilRiv/comprobador-de-paginas-web/2.3-scoring-and-release-gate)**: Cómo se calculan las puntuaciones y qué desencadena un estado de "Bloqueado".
*   **[Link Crawler](/LuisVilRiv/comprobador-de-paginas-web/2.4-link-crawler)**: Profundiza en el validador recursivo de enlaces BFS.

* * *

# QualityAuditor-Pipeline

# QualityAuditor Pipeline

Archivos fuente relevantes

*   [compartido/auditor/auditor\_modules/core.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py)
*   [compartido/auditor/auditor\_modules/helpers.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py)
*   [compartido/auditor/cheques/links.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py)
*   [compartido/auditor/dictionaries.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/dictionaries.py)
*   [compartido/auditor/regex.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/regex.py)
*   [compartido/base de datos/repositorios/panel/helpers.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/helpers.py)
*   [compartido/base de datos/repositorios/scraper/websites.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/websites.py)
*   [Pruebas/test\_inoperative\_pages.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_inoperative_pages.py)

`El QualityAuditor` es la inteligencia central del motor de auditoría. Orquesta la transformación de HTML y metadatos en bruto en un `QualityAuditReportInforme` estructurado. La tubería está diseñada para manejar diversos estados web, que van desde SPAs modernos totalmente funcionales hasta páginas de servidor rotas y marcadores de mantenimiento.

## El ciclo de vida build\_report

El método `QualityAuditor.build_report` sigue una estricta cadena secuencial de 8 pasos para evaluar un sitio web. Gestiona el estado a lo largo de estos pasos, recopilando problemas y métricas en un modelo unificado.

### Flujo de datos y pasos de la tubería

| Escalón | Funcionamiento | Responsabilidad clave |
| --- | --- | --- |
| 0 | Inicialización | Reinicia los contadores internos (\_browser\_confirms) y borra encabezados de respuesta anteriores compartidos/auditor/auditor\_modules/core.py114-116 |
| 1 | Detección inoperativa | Ejecuta comprobaciones heurísticas para determinar si el sitio está en estado de error o en modo de mantenimiento compartido/auditor/auditor\_modules/core.py150-250 |
| 2 | Técnico y de Seguridad | Evalúa cabeceras HTTP, SSL e infraestructura HTML básica compartida/auditor/auditor\_modules/core.py270-280 |
| 3 | SEO y Metadatos | Comprobaciones de títulos, descripciones y directrices de indexación compartidos/auditor/auditor\_modules/core.py284-288 |
| 4 | Calidad del contenido | Analiza el texto en busca de "contenido superficial", relleno de palabras clave y patrones tóxicos compartidos/auditor/auditor\_modules/core.py292-297 |
| 5 | Medios y activos | Valida imágenes, atributos alternativos y accesibilidad de activos compartidos/auditor/auditor\_modules/core.py301-306 |
| 6 | Conectividad (enlaces) | Realiza rastreo recursivo de BFS para encontrar enlaces internos/externos rotos compartidos/auditor/auditor\_modules/core.py310-316 |
| 7 | Interactividad | Revisa botones y formularios; si usas Selenium, intenta interactuar compartido/auditor/auditor\_modules/core.py320-330 |
| 8 | Puntuación final | Calcula la puntuación final y determina el estado "Puerta de liberación" compartido/auditor/auditor\_modules/core.py340-360 |

**Fuentes:**[compartido/auditor/auditor\_modules/core.py113-360](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L113-L360)

* * *

## Heurísticas de detección de sitios inoperativos

El auditor emplea un motor heurístico de múltiples capas para identificar sitios web "muertos", impidiendo que el sistema audite el contenido provisional como si fuera un sitio real.

### 1\. Patrones de error fuertes (señales duras)

Si se cumple alguna de estas condiciones, `is_inoperative` se pone inmediatamente en `Verdadero` y la puntuación se fuerza a un nivel crítico (normalmente 5/100).

*   **Estado HTTP:** ¿Cualquier código $\ge 400$ [de estado compartido/auditor/auditor\_modules/core.py174-177](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L174-L177)
*   **Cadenas de error duras:** Busca patrones como `"404 No encontrado",` `"Error interno del servidor"` o `"Puerta de enlace defectuosa"` en `las etiquetas <title>`, `<h1>` o `<h2>` [shared/auditor/auditor\_modules/core.py181-193](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L181-L193)

### 2\. Patrones de mantenimiento suave

Detectado mediante una combinación de coincidencia de palabras clave y longitud de página:

*   **Palabras clave:** `"mantenimiento",` `"no disponible",` `"intentar de nuevo más tarde",` `"en construcción"`[shared/auditor/auditor\_modules/core.py80-99](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L80-L99)
*   **Limitación:** Estos patrones solo desencadenan un estado "Inoperativo" si el recuento de palabras está por debajo del `umbral de MAX_BODY_STRONG_ERROR_WORDS` (900 palabras) [compartido/auditor/auditor\_modules/core.py68-69](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L68-L69)[compartido/auditor/auditor\_modules/core.py204-207](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L204-L207)

### 3\. Lista blanca de contexto educativo

Para evitar falsos positivos (por ejemplo, un artículo de Wikipedia *sobre* errores HTTP 404), el auditor utiliza una lista blanca de términos de "contexto educativo".

*   **Términos en lista blanca:** `"rfc",` `"wikipedia",` `"documentación",` `"código de estado",` `"ietf"`[shared/auditor/auditor\_modules/core.py39-65](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L39-L65)
*   **Lógica:** Si la página tiene $\ge 2$ coincidencias y $\ge 180$ palabras educativas, o parece un documento de especificación técnica, las banderas inoperativas se [ignoran como share/auditor/auditor\_modules/core.py168-172](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L168-L172)

**Fuentes:**[compartido/auditor/auditor\_modules/core.py39-99](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L39-L99)[compartido/auditor/auditor\_modules/core.py150-220](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L150-L220)[pruebas/test\_inoperative\_pages.py11-101](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_inoperative_pages.py#L11-L101)

* * *

## Anulaciones de integración de IA

La tubería puede llamar opcionalmente a un `AIContentAnalyzer` externo (a través del microservicio `analizador de IA`) para realizar la validación semántica.

*   **Mecanismo de anulación:** Si `ENABLE_STRONG_AI_FALLBACK` está activo, los resultados del motor heurístico pueden ser anulados por la clasificación semántica de la IA [shared/auditor/auditor\_modules/core.py230-245](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L230-L245)
*   **Anclajes semánticos:** La IA clasifica el contenido en categorías `de ERROR`, `EDUCATIVO` o `MALICIOSO`.
*   **Resolución de ambigüedad:** Si las heurísticas no están claras, la "Puntuación de Coherencia" de la IA determina si el contenido es legítimo o se genera ruido.

**Fuentes:**[compartido/auditor/auditor\_modules/core.py225-250](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L225-L250)

* * *

## Formateador de informes: report\_to\_text

La función `report_to_text` (que se encuentra en el módulo `QualityAuditor`) convierte el complejo objeto `QualityAuditReport` en un resumen legible para humanos.

### Lógica de formato

1.  **Cabecera:** Muestra la URL y la `puntuación` calculada (0-100) y `el estado` (por ejemplo, "crítico", "mejorable") [compartido/auditor/auditor\_modules/core.py380-390](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L380-L390)
2.  **Puerta de lanzamiento:** Indica claramente si la versión está `BLOQUEADA` o `APROBADA`[compartida/auditor/auditor\_modules/core.py392-395](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L392-L395)
3.  **Agrupación de temas:** Sigue iterando listas de categorías (`security_issues`, `content_issues`, etc.). Si una lista está vacía, utiliza `ensure_non_empty` para enviar un mensaje de "No se detectan problemas[" shared/auditor/auditor\_modules/helpers.py50-53](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py#L50-L53)
4.  **Recomendaciones:** Añade una lista con viñetas de mejoras [accionables compartidas/auditor/auditor\_modules/core.py410-415](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L410-L415)

**Fuentes:**[compartido/auditor/auditor\_modules/core.py375-420](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L375-L420)[compartido/auditor/auditor\_modules/helpers.py50-53](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py#L50-L53)

* * *

## Diagramas técnicos

### Flujo lógico de la tubería de auditor

Este diagrama asigna la lógica de alto nivel de `QualityAuditor.build_report` a las entidades específicas de código implicadas en el proceso.

```mermaid
diagrama de flujo TD
    A["QualityAuditor.build_report()"]
    D["check_structure()"]
    E["check_seo()"]
    Yo["evaluate_release_gate()"]
    subgrafo subGraph0 ["Entidades de código"]
        B["Heurísticas inoperativas"]
        C["check_security()"]
        F["check_content()"]
        G["check_links_recursive()"]
        H["calculate_score()"]
        B_Code["core.py:150"]
        C_Code["cheques/security.py"]
        F_Code["cheques/content.py"]
        G_Code["comprobaciones/links.py"]
        H_Code["scoring.py"]
    fin
    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> yo
    B -.-> B_Code
    C -.-> C_Code
    F -.-> F_Code
    G -.-> G_Code
    H -.-> H_Code
```

**Fuentes:**[compartido/auditor/auditor\_modules/core.py113-360](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L113-L360)[compartido/auditor/checks/links.py11](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L11-L11)

### Flujo de datos de detección inoperativo

Mapear las variables heurísticas al proceso de toma de decisiones en `core.py`.

```mermaid
diagrama de flujo LR
    HTML["Cadena HTML en bruto"]
    Sopa["BeautifulSoup(BS4_PARSER)"]
    Lógica["¿Inoperativa?"]
    Bloqueado["release_blocked = Verdadero"]
    Continuar["Continuar la Producción"]
    subgrafo subGraph1 ["Referencia de código"]
        WC_Var["core.py:160"]
        EC_Var["core.py:161"]
        PC_Var["core.py:181"]
    fin
    subgrafo subGraph0 ["Chequeos heurísticos"]
        Texto["soup.get_text()"]
        WC["word_count"]
        EC["educational_hits"]
        PC["strong_err_patterns"]
    fin
    HTML --> Sopa
    Sopa --> Texto
    Texto --> WC
    Texto --> EC
    Texto --> PC
    WC --> Lógica
    EC --> Lógica
    PC --> Lógica
    Lógica -->|" Sí (Puntuación = 5)"| Bloqueado
    Lógica -->|" No"| Continúa
    WC -.-> WC_Var
    EC -.-> EC_Var
    PC -.-> PC_Var
```

**Fuentes:**[compartido/auditor/auditor\_modules/core.py147-210](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L147-L210)[compartido/auditor/auditor\_modules/helpers.py98-109](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py#L98-L109)

* * *

# Módulos de Auditoría-Comprobación

# Módulos de Verificación de Auditoría

Archivos fuente relevantes

*   [compartido/auditor/auditor\_modules/helpers.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py)
*   [compartido/auditor/cheques/**inIT**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/__init__.py)
*   [compartido/auditor/cheques/browser.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/browser.py)
*   [compartido/auditor/cheques/buttons.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/buttons.py)
*   [compartido/auditor/cheques/content.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/content.py)
*   [compartido/auditor/cheques/images.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/images.py)
*   [compartido/auditor/cheques/links.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py)
*   [compartido/auditor/cheques/security.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/security.py)
*   [compartido/auditor/cheques/seo.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/seo.py)
*   [compartido/auditor/cheques/structure.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/structure.py)
*   [compartido/auditor/cheques/technical.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/technical.py)
*   [compartido/base de datos/repositorios/panel/helpers.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/helpers.py)
*   [compartido/base de datos/repositorios/scraper/websites.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/websites.py)

El directorio `compartido/auditor/comprobación/`contiene módulos especializados que realizan inspecciones detalladas de contenido web extraído. Cada módulo expone una función `check_*` que sigue un patrón consistente: acepta un objeto `BeautifulSoup`, HTML en bruto y una lista de `problemas` a los que añade hallazgos.

## Arquitectura de ejecución de comprobación

`El Auditor de Calidad` orquesta estas comprobaciones pasando estados compartidos (sesión, cabeceras, controladores) a cada función especializada. Este enfoque modular permite realizar pruebas dirigidas de atributos web específicos sin sobrecargar la tubería principal.

### Flujo de datos e inyección de dependencias

Muchas funciones de comprobación requieren funciones de utilidad para la validación de URL o la resolución de números de línea. Estos se presentan como argumentos funcionales para desacoplar la lógica de comprobación del estado interno del auditor.

Título: Flujo de datos de comprobación de auditoría

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["Auxiliares de utilidad"]
        H1["is_banned_url"]
        H2["check_url"]
        H3["find_line"]
    fin
    subgrafo subGraph1 ["Módulos de comprobación"]
        C1["check_security"]
        C2["check_seo"]
        C3["check_content"]
        C4["check_links_recursive"]
        C5["check_technical"]
    fin
    subgrafo subGraph0 ["Núcleo del Auditor"]
        QA["QualityAuditor"]
    fin
    QA -->|" Inyecta sopa, problemas, ayudantes"| C1
    QA -->|" Inyecta sopa, problemas, ayudantes"| C2
    QA -->|" Inyecta sopa, problemas, ayudantes"| C3
    QA -->|" Inyecta sopa, problemas, ayudantes"| C4
    QA -->|" Inyecta sopa, problemas, ayudantes"| C5
    C1 -->|" Llamadas"| H1
    C4 -->|" Llamadas"| H1
    C5 -->|" Llamadas"| H1
    C1 -->|" Llamadas"| H2
    C4 -->|" Llamadas"| H2
    C5 -->|" Llamadas"| H2
    C1 -->|" Llamadas"| H3
    C4 -->|" Llamadas"| H3
    C5 -->|" Llamadas"| H3
```

**Fuentes:** [compartido/auditor/checks/init.py1-25](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/__init__.py#L1-L25) [compartido/auditor/auditor\_modules/helpers.py12-32](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py#L12-L32)

* * *

## Seguridad y cabeceras (`security.py`)

La función `check_security` se centra en las protecciones a nivel HTTP y la integridad SSL/TLS.

*   **Validación de cabecera:** Comprueba la presencia de `Política de Seguridad de Contenido`, Opciones de `Marco X`, Opciones de tipo `de contenido` X y Política `de Referencia`[compartidas/auditoras/verificaciones/security.py39-56](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/security.py#L39-L56)
*   **Inspección SSL/TLS:** El `asistente de _verify_tls` establece una conexión de socket para verificar la fecha de caducidad del certificado y confiar en la cadena [compartida/auditor/verificaciones/security.py61-111](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/security.py#L61-L111)
*   **HSTS:** Comprueba si `Strict-Transport-Security` está activo para sitios [HTTPS compartidos/auditor/checks/security.py184-189](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/security.py#L184-L189)
*   **Detección de WAF:** Utiliza `_html_has_firewall_challenge` para identificar si el scraper está bloqueado por Cloudflare, BitNinja o Imunify360 [shared/auditor/checks/security.py123-140](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/security.py#L123-L140)

**Fuentes:**[compartido/auditor/checks/security.py157-189](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/security.py#L157-L189)

* * *

## Calidad del contenido y patrones tóxicos (`content.py`)

Este módulo realiza análisis semánticos y heurísticos de texto visible.

*   **Coincidencia de patrones:** Escaneos en busca de "Lorem Ipsum", lenguaje vulgar, discurso de odio y segmentos incoherentes usando diccionarios [predefinidos shared/auditor/checks/content.py30-55](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/content.py#L30-L55)
*   **Detección de evasión:** Detecta intentos de saltarse filtros usando caracteres espaciados (por ejemplo, `s p a m`) o caracteres punteados (por ejemplo, `s.p.a.m`) [compartidos/auditor/checks/content.py68-89](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/content.py#L68-L89)
*   **Contenido Superficial:** Marca páginas con el recuento de palabras debajo `de la configuración. AUDIT_MIN_WORD_COUNT` (por defecto 200), excluyendo las páginas de contacto/[legales compartidas/auditor/checks/content.py106-114](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/content.py#L106-L114)
*   **Relleno de palabras clave:** Calcula la densidad para la palabra más frecuente; se detecta si supera `la configuración. AUDIT_KEYWORD_DENSITY_MAX`[compartido/auditor/checks/content.py116-127](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/content.py#L116-L127)

**Fuentes:**[compartido/auditor/checks/content.py12-140](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/content.py#L12-L140)

* * *

## Link Crawler (`links.py`)

La función `check_links_recursive` implementa un rastreador de búsqueda en amplitud (BFS) para identificar enlaces rotos y rutas prohibidas.

| Característica | Detalles de implementación |
| --- | --- |
| Deduplicación | Utiliza un conjunto visto para evitar bucles infinitos compartidos/auditor/checks/links.py29 |
| Límites de recursión | Limitado por AUDIT\_MAX\_RECURSIVE\_LINKS y AUDIT\_MAX\_CRAWL\_DEPTHcompartido/auditor/checks/links.py53 |
| Validación de ancla | Comprueba si realmente existen objetivos internos de #fragment en el DOM compartido/auditor/comprobaciones/enlaces.py35-40 |
| Bloqueo de dominio | Solo rastrea enlaces internos (coincidiendo base\_host) para evitar entrar en sitios externos compartidos/auditor/checks/links.py84-88 |

**Fuentes:**[compartido/auditor/comprobaciones/enlaces.py11-89](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L11-L89)

* * *

## Imágenes y recursos (`images.py` y `technical.py`)

Estos módulos gestionan la validación de medios y métricas de rendimiento front-end.

*   **Protección contra CLS:** Señala imágenes que carecen de atributos `explícitos de ancho` o `altura` que causan Desplazamiento de Layout [Cumulativo compartido/auditor/checks/images.py54-58](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/images.py#L54-L58)
*   **Formatos modernos:** Recomienda WebP/AVIF si se detectan formatos heredados (JPG, PNG[) compartidos/auditor/checks/images.py59-63](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/images.py#L59-L63)
*   **Contenido Mixto:** Flags `http://` assets cargados en una `página de https://` [compartido/auditor/checks/technical.py79-81](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/technical.py#L79-L81)
*   **Guiones de bloqueo:** Identifica scripts en `<head>` que carecen de atributos `asíncronos` o `de` [diferir compartidos/auditor/checks/technical.py102-103](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/technical.py#L102-L103)

**Fuentes:**[compartido/auditor/checks/images.py10-64](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/images.py#L10-L64)[compartido/auditor/checks/technical.py63-105](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/technical.py#L63-L105)

* * *

## Comprobaciones técnicas y de navegador (`browser.py`)

Estas comprobaciones requieren un controlador `de Selenium` en funcionamiento para la interacción o la extracción de logs.

*   **Errores en la consola JS:** Extrae registros `de nivel GRAVE` o `ERROR` del búfer interno del navegador [shared/auditor/checks/browser.py13-26](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/browser.py#L13-L26)
*   **Interacción con botones:** La función `interact_buttons_selenium` intenta hacer clic en botones visibles para detectar alertas no gestionadas o fallos post-renderizado [compartidos/auditor/checks/browser.py30-64](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/browser.py#L30-L64)

Título: Secuencia de comprobación de interacción con el navegador

```mermaid
Diagrama de secuencia
    Asistente de calidad participante como Auditor de Calidad
    participante B como browser.py
    participante D como SeleniumDriver
    QA->>B: interact_buttons_selenium(driver, problemas)
    B->>D: find_elements(By.TAG_NAME, "botón")
    B->>D: btn.click()
    B->>D: switch_to.alerta
    D-->>B: alert_text
    B->>QA: añadir número ("Alerta no capturada")
    D-->>B: éxito
```

**Fuentes:**[compartido/auditor/checks/browser.py30-70](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/browser.py#L30-L70)

* * *

## SEO y accesibilidad (`seo.py` y `buttons.py`)

*   **Metadatos:** Valida `<title>` (20-65 caracteres) y `metadescripción` (70-160 caracteres) [compartido/auditor/checks/seo.py13-24](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/seo.py#L13-L24)
*   **Datos estructurados:** Valida JSON-LD para detectar errores de sintaxis y la presencia de `@type` o `@context`[compartido/auditor/checks/seo.py50-63](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/seo.py#L50-L63)
*   **Accesibilidad a formularios:** El `ayudante de _check_forms_accessibility` asegura que cada entrada tenga un `correspondiente <label>` o un `aria-etiqueta`[compartido/auditor/checks/technical.py106-116](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/technical.py#L106-L116)
*   **Texto del botón:** Señala botones o entradas de tipo `enviar` que carecen de texto visible `o de valor` [compartido/auditor/comprobaciones/botones.py27-35](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/buttons.py#L27-L35)

**Fuentes:**[compartido/auditor/cheques/seo.py11-76](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/seo.py#L11-L76)[compartido/auditor/cheques/buttons.py10-60](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/buttons.py#L10-L60)

* * *

# Puntuación y Lanzamiento

# Puntuación y Puerta de Liberación

Archivos fuente relevantes

*   [compartido/auditor/models.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/models.py)
*   [compartido/auditor/scoring.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py)

El sistema **Scoring & Release Gate** es la fase final de la cadena de auditoría. Transforma listas en bruto de los problemas en una puntuación numérica, un estado cualitativo y una decisión binaria de "liberación". Esta lógica garantiza que los sitios web se evalúen de forma consistente y que fallos críticos (como paneles de administración expuestos o formularios rotos) impidan un estado de auditoría exitoso.

## Lógica de puntuación (`calculate_score`)

El modelo de puntuación utiliza un **enfoque de deducción ponderada** con rendimientos decrecientes para problemas repetitivos y límites estrictos por categoría para evitar que una sola categoría hunda completamente la puntuación mientras que otras son perfectas.

### 1\. Categorización de problemas y pesos

Los números se clasifican en ocho dominios, cada uno con un límite máximo de deducción (`cat_limit`) [compartido/auditor/puntuación.py18-27](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L18-L27) Dentro de estas categorías, los números reciben ponderaciones basadas en la coincidencia de palabras clave:

| Gravedad | Peso | Palabras clave de ejemplo |
| --- | --- | --- |
| Crítica | 3.0 | Dato Sensible, Administrador de Panel, Vulnerabilidad, firewall\_block |
| Alto | 1.5 | falta cabecera, hsts, csp, contenido mixto, falta título |
| Medio | 0.5 | falta canonical, alt de imagen, lorem ipsum, semántica |
| Genérico | 0.1 | ¿Algún otro problema detectado |

### 2\. Rendimientos Decrecientes (Multiplicadores)

Para evitar penalizar en exceso el mismo tipo de error (por ejemplo, 50 etiquetas `alts` de imagen faltantes), el sistema aplica un multiplicador basado en la frecuencia de la `issue_type`[compartido/auditor/puntuación.py67-70](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L67-L70):

*   **De la primera a la tercera ocurrencia:** 1,0 veces el peso.
*   **4ª - 8ª ocurrencia:** 0,5 veces el peso.
*   **Novena+:** 0,1x peso.

### 3\. Anulación del sitio inoperativo

Si alguna lista de incidencias contiene la cadena `"sitio web no operativo"` (detectada durante la fase heurística), la función omite todos los cálculos y devuelve una puntuación fija de **5/100**[compartido/auditor/puntuación.py73-83](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L73-L83)

### Diagrama de flujo de puntuación

El siguiente diagrama muestra cómo `calculate_score` procesa los problemas en un entero final.

**Diagrama: Lógica de deducción de puntuación**

**Fuentes:**[compartido/auditor/puntuación.py8-85](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L8-L85)

* * *

## Umbrales de estado (`status_from_score`)

Una vez calculada la puntuación numérica, se asigna a un estado legible para humanos usando umbrales definidos en la configuración de entorno [shared/auditor/scorering.py88-92](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L88-L92)

| Estado | Condición umbral |
| --- | --- |
| Excelente | puntuación >= AUDIT\_SCORE\_EXCELLENT\_THRESHOLD (Valor predeterminado: 90) |
| Bueno | puntuación >= AUDIT\_SCORE\_GOOD\_THRESHOLD (Predeterminada: 75) |
| Mejorable | puntuación >= 50 |
| Crítica | Puntuación < 50 |

**Fuentes:**[compartido/auditor/scorering.py88-92](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L88-L92)

* * *

## Evaluación de la puerta de lanzamiento (`evaluate_release_gate`)

La Puerta de Lanzamiento es un mecanismo de seguridad que determina si un sitio web está "listo para producción". Incluso un sitio con puntuación alta puede ser bloqueado si contiene problemas específicos de "bloqueadores".

### Criterios de bloqueador

La función `evaluate_release_gate` verifica las siguientes condiciones [compartidas/auditor/score.py95-143](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L95-L143):

1.  **Puntuación global:** Debe estar por encima `de AUDIT_RELEASE_GATE_MIN_SCORE`[compartido/auditor/puntuación.py106-107](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L106-L107)
2.  **Seguridad:** Presencia de datos sensibles, paneles de administración expuestos o falta de [autenticación compartido/auditor/puntuación.py109-114](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L109-L114)
3.  **Contenido:** Detección de contenido explícito, discurso de odio o incoherencia heurística detectada [por IA compartida/auditor/scoring.py116-121](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L116-L121)
4.  **Fallos funcionales:** Enlaces rotos [confirmados compartidos/auditor/scoring.py123-125](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L123-L125) imágenes rotas [compartidas/auditor/scoring.py127-129](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L127-L129) o fallos de acción [compartidos/auditor/scoring.py135-137](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L135-L137)
5.  **Técnico:** Contenido mixto (HTTP sobre HTTPS), falta de doctype, o scripts [bloqueando compartido/auditor/scoring.py131-133](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L131-L133)
6.  **Operativo:** Flags explícitos de "sitio web no operativo[" compartido/auditor/scoring.py140-141](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L140-L141)

**Fuentes:**[compartido/auditor/puntuación.py95-143](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L95-L143)

* * *

## Modelo de datos y recomendaciones

Los resultados de estos cálculos se almacenan en la clase `de datos QualityAuditReport`, que sirve como el objeto principal de transferencia de datos (DTO) para el motor de auditoría.

### Estructura de QualityAuditReport

Este modelo agrega todos los problemas y los resultados finales [de la evaluación compartidos/auditor/models.py11-25](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/models.py#L11-L25)

```mermaid
Diagrama de clases.
    clase QualityAuditReport {
        Estado +fuerza
        +puntuación de inteligencia
        +<str>Lista security_issues
        +<str>seo_issues
        +<str>lista content_issues
        +<str>image_issues
        +<str>lista structure_issues
        +<str>link_issues
        +<str>button_issues
        +<str>lista technical_issues
        +bool release_blocked
        +<str>lista release_blockers
        Recomendaciones de +lista<str>
        Métricas +dict
        +to_dict() : dictado
    }
```

### Motor de Recomendación (`build_recommendations`)

La función `build_recommendations` genera acciones de alto nivel basadas en la presencia de incidencias en categorías específicas [compartidas/auditoras/puntuaciones.py146-161](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L146-L161) Filtra las categorías marcadas como "incidentes de pecado" (sin problemas) para proporcionar una lista concisa de mejoras.

**Fuentes:**[compartido/auditor/models.py11-43](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/models.py#L11-L43)[compartido/auditor/scoring.py146-161](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L146-L161)

* * *

# Link-Crawler

# Link Crawler

Archivos fuente relevantes

*   [compartido/auditor/auditor\_modules/helpers.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py)
*   [compartido/auditor/cheques/links.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py)
*   [compartido/base de datos/repositorios/panel/helpers.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/helpers.py)
*   [compartido/base de datos/repositorios/scraper/websites.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/websites.py)
*   [Pruebas/test\_links\_recursive\_robust.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_links_recursive_robust.py)

El Link Crawler es un módulo especializado dentro del motor `QualityAuditor` responsable de identificar enlaces rotos, validar fragmentos de ancla y realizar un rastreo de búsqueda en amplitud (BFS) de páginas internas para garantizar la integridad del sitio. Opera bajo estrictas restricciones de seguridad para evitar bucles infinitos y un consumo excesivo de recursos.

## Implementación recursiva de BFS

El punto de entrada principal es la `función check_links_recursive`. A diferencia de un simple comprobador de enlaces que solo valida la página actual, este módulo recorre la estructura del sitio web hasta una profundidad definida.

### Gestión de colas y deduplicación

El rastreador utiliza un enfoque estándar de BFS con una cola y un "visto" configurado para gestionar el estado:

*   **Cola (`cola`):** Almacena tuplas de `(url, current_depth)` para [procesar compartido/auditor/checks/links.py28](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L28-L28)
*   **Conjunto visto (`visto`):** Almacena todas las URL encontradas para evitar comprobaciones redundantes y referencias circulares (por ejemplo, Página A -> Página B -> Página A) [compartidas/auditor/checks/links.py29](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L29-L29)
*   **Seed inicial**: El `base_url` se añade inmediatamente al conjunto `visible` para evitar que el rastreador vuelva a auditar la página [inicial shared/auditor/checks/links.py29](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L29-L29)

### Lógica de manejo de enlaces

El rastreador distingue entre varios tipos de enlaces:

1.  **Enlaces funcionales**: `mailto:`, `tel:`, y `javascript:` los enlaces se [ignoran compartidos/auditor/checks/links.py33-34](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L33-L34)
2.  **Interno vs externo**:

*   **Externo**: El rastreador valida el código de estado (por ejemplo, 200 OK) pero no extrae más enlaces de la página externa [compartido/auditor/checks/links.py84-86](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L84-L86)
*   **Interno**: Si el anfitrión de enlaces coincide con el `base_host` y la profundidad actual es menor que `AUDIT_MAX_CRAWL_DEPTH`, el rastreador recupera el contenido y extrae nuevos enlaces para añadir a la cola [shared/auditor/checks/links.py75-88](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L75-L88)

3.  **Anclajes rotos**: Para fragmentos internos (por ejemplo, `<a href="#section1">`), el rastreador verifica si existe un elemento con `id="section1"` o `name="section1"` en la `sopa actual` [shared/auditor/checks/links.py35-40](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L35-L40)

**Fuentes:**[compartidas/auditoras/comprobaciones/enlaces.pruebas py11-89](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L11-L89)[/test\_links\_recursive\_robust.py68-112](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_links_recursive_robust.py#L68-L112)

## Flujo de datos: Canal de validación de enlaces

El siguiente diagrama ilustra cómo se procesa un enlace descubierto desde la extracción hasta la notificación de incidencias.

### Ciclo de vida del procesamiento de enlaces

```mermaid
diagrama de flujo TD
    INICIO["soup.find_all('a')"]
    FILTER["¿Es un protocolo válido?"]
    IGNORAR["Saltar"]
    PRESENTADOR["¿Es Anchor (#)?"]
    FIND_ID["soup.find(id=fragmento)"]
    ISSUE_ANCHOR["Añadir el número de 'Ancla rota'"]
    PROHIBIDO["¿is_banned_url?"]
    ISSUE_BANNED["Añadir 'Enlace omitido' Issue"]
    VISTO["¿En el set visto?"]
    COLA["Push to queue"]
    POP["Pop (url, profundidad)"]
    CHECK_URL["check_url_fn()"]
    OK["¿Estado OK?"]
    ISSUE_BROKEN["Añadir 'Enlace roto' Issue"]
    PROFUNDIDAD["¿Profundidad < MAX_DEPTH?"]
    INTERNO["¿Es el anfitrión interno?"]
    EXTRACT["Extraer enlaces del contenido"]
    START --> FILTER
    FILTRO -->|" No (tel/mailto)"| IGNORA
    FILTRO -->|" Sí"| PRESENTADOR
    PRESENTADOR -->|" Sí"| FIND_ID
    FIND_ID -->|" No encontrado"| ISSUE_ANCHOR
    PRESENTADOR -->|" No"| PROHIBIDO
    PROHIBIDO -->|" Sí"| ISSUE_BANNED
    PROHIBIDO -->|" No"| VISTO
    VISTO -->|" No"| QUEUE
    COLA --> POP
    POP --> CHECK_URL
    CHECK_URL --> Vale
    Vale -->|" No"| ISSUE_BROKEN
    Vale -->|" Sí"| PROFUNDIDAD
    PROFUNDIDAD -->|" Sí"| INTERNO
    INTERNO -->|" Sí"| EXTRACTO
    EXTRACTO: > VISTOS
```

**Fuentes:**[compartido/auditor/comprobaciones/enlaces.py31-89](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L31-L89)[compartido/auditor/auditor\_modules/helpers.py55-70](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py#L55-L70)

## Restricciones de seguridad y filtrado

Para asegurar que el auditor no se bloquee ni se bloquee por los servidores objetivo, se aplican varias restricciones.

### Límites de profundidad y volumen

El rastreador respeta dos variables principales del entorno:

*   **`AUDIT_MAX_RECURSIVE_LINKS`**: El número máximo de enlaces totales que el rastreador intentará validar mediante solicitudes HTTP [compartidas/auditor/checks/links.py53](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L53-L53)
*   **`AUDIT_MAX_CRAWL_DEPTH`**: ¿Cuántos "clics" de la página principal irá el rastreador para encontrar nuevos [enlaces compartidos/auditores/comprobaciones/enlaces.py75](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L75-L75)
*   **`max_loop_iterations`**: Un límite estricto de seguridad (establecido a 3 veces el máximo de enlaces) para salir del bucle `while` si la lógica [falla shared/auditor/checks/links.py50-51](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L50-L51)

### Filtrado de anfitriones prohibidos

Antes de hacer cualquier solicitud, el `asistente de is_banned_url` comprueba la URL con `la configuración. AUDIT_BANNED_HOSTS`. Esto evita que el rastreador interactúe con paneles administrativos restringidos, dominios maliciosos conocidos o infraestructura [sensible compartida/auditor/auditor\_modules/helpers.py12-30](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py#L12-L30)

### Clasificación del tiempo de respuesta

Cada comprobación de enlace está cronometrada. La función `classify_speed` categoriza el tiempo de respuesta en "excelente", "buena", "mejorable" o "lenta[" compartido/auditor/auditor\_modules/helpers.py72-77](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py#L72-L77) Estos metadatos se incluyen en los problemas reportados para ayudar a los usuarios a identificar recursos [compartidos/auditor/checks/enlaces que cargan lentamente](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L70-L73)

**Fuentes:**[compartido/auditor/comprobaciones/enlaces.py50-60](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L50-L60)[compartido/auditor/auditor\_modules/helpers.py12-32](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py#L12-L32)[compartido/auditor/auditor\_modules/helpers.py72-77](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py#L72-L77)

## Mapa de entidad de código

El rastreador de enlace depende de funciones inyectadas para mantener la separación entre la lógica de auditoría y las funciones de utilidad.

### Interacción de componentes

| Entidad de código | Ruta de archivo | Función |
| --- | --- | --- |
| check\_links\_recursive | compartido/auditor/cheques/links.py | Lógica principal de extracción de bucles y enlaces de BFS. |
| check\_url | compartido/auditor/auditor\_modules/helpers.py | Ejecuta la petición HTTP y devuelve el estado/contenido. |
| is\_banned\_url | compartido/auditor/auditor\_modules/helpers.py | Lógica para exclusión basada en el host (coincidencia netloc). |
| find\_line | compartido/auditor/auditor\_modules/helpers.py | Mapea una etiqueta BeautifulSoup de vuelta a su número de línea en HTML en bruto. |
| crawl\_stats | compartido/auditor/cheques/links.py | Seguimiento del diccionario probado, saltado y conteo roto. |

### Diagrama de lógica del sistema

```mermaid
Diagrama de clases.
    class LinkCrawler {
        +check_links_recursive()
    }
    clase Helpers {
        +check_url(sesión, URL)
        +is_banned_url(url)
        +classify_speed(ms)
        +find_line(líneas, etiqueta)
    }
    class Config {
        +AUDIT_MAX_RECURSIVE_LINKS
        +AUDIT_MAX_CRAWL_DEPTH
        +AUDIT_BANNED_HOSTS
    }
    LinkCrawler... > Ayudantes: llamadas
    LinkCrawler... > Configuración: límites de lectura
    Ayudantes... > Configuración: lecturas de tiempos de espera
```

**Fuentes:**[compartido/auditor/comprobaciones/enlaces.py11-22](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py#L11-L22)[compartido/auditor/auditor\_modules/helpers.py55-88](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py#L55-L88)[pruebas/test\_links\_recursive\_robust.py19-22](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_links_recursive_robust.py#L19-L22)

* * *

# Motor raspador

# Motor rascador

Archivos fuente relevantes

*   [Docker/raspador/scheduler.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py)
*   [Docker/raspador/service.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py)
*   [Raspador/base/base\_scraper.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/base/base_scraper.py)
*   [Raspador/Contexto/scraper\_context.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/context/scraper_context.py)
*   [Raspador/modelos/scrape\_result.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/models/scrape_result.py)
*   [Scraper/estrategias/beautifulsoup\_strategy.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/beautifulsoup_strategy.py)

El **Scraper Engine** es la capa de adquisición de datos de la plataforma. Está diseñado en torno al **Patrón de Estrategia**, que permite al sistema cambiar entre peticiones HTTP ligeras y emulación completa del navegador según la complejidad del sitio web objetivo. Gestiona la programación mediante expresiones cron y orquesta la transición de la recuperación en bruto de HTML a la elaboración de informes de auditoría estructurada.

## Arquitectura central

El motor desacopla el "cómo" del raspado del "cuándo" y el "qué". El `ScraperContext` actúa como la interfaz principal, delegando la ejecución a una `ScraperStrategy` específica.

### Mapa de Entidad Scraper

Este diagrama mapea el proceso de scraping lógico a las clases y métodos específicos de la base de código.

**Fuentes:**[raspador/contexto/scraper\_context.py8-28](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/context/scraper_context.py#L8-L28)[raspador/modelos/scrape\_result.py7-21](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/models/scrape_result.py#L7-L21)[raspador/base/base\_scraper.py11-20](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/base/base_scraper.py#L11-L20)

## Patrón de estrategia de raspador

El motor implementa un patrón estratégico estricto para manejar diferentes tipos de contenido web. Cada estrategia debe devolver un objeto `ScrapeResult`, asegurando que `el Auditor de Calidad` reciba un esquema consistente independientemente del método de adquisición.

| Componente | Función | Referencia del archivo |
| --- | --- | --- |
| ScraperContext | Gestiona la estrategia activa y proporciona el método execute(). | scraper/context/scraper\_context.py8-12 |
| BaseScraper | Proporciona lógica común como intentos de \_is\_valid\_url, \_is\_banned\_url y retroceso lineal. | Raspador/base/base\_scraper.py11-29 |
| ScrapeResult | Contenedor de datos estandarizado para contenido HTML, metadatos y códigos de estado. | Raspador/Modelos/scrape\_result.Py7-21 |

### Flujo de selección de estrategias

`El Servicio de Auditoría` contiene la inteligencia necesaria para seleccionar la estrategia óptima. Por defecto, utiliza un mecanismo de "pre-lectura" para detectar si un sitio es una Aplicación de Página Única (SPA).

```mermaid
diagrama de flujo TD
    A["AuditService.process_website"]
    B["Strategy == 'auto'?"]
    C["classify_and_scrape()"]
    D["Pre-fetch de BeautifulSoup"]
    E["¿Es SPA/Dinámico?"]
    F["Seleccionar Estrategia de Selenio"]
    G["Seleccionar EstrategiaBellaSoupa"]
    h["Usa estrategia explícita"]
    I["ScraperContext.execute()"]
    A --> B
    B -->|" Sí"| C
    C --> D
    D --> E
    E -->|" Sí"| F
    E -->|" No"| G
    B -->|" No"| H
    ¡A la >
    G --> I
    H --> yo
```

**Fuentes:**[docker/scraper/service.py22-46](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L22-L46)[docker/scraper/service.py104-121](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L104-L121)

## Componentes clave

### 1\. Estrategias de raspado

Actualmente, el sistema soporta dos estrategias principales:

*   **BeautifulSoupStrategy**: Rápido, usa `peticiones` para HTML estático. Reutiliza sesiones para pooling [de conexiones, scraper/strategies/beautifulsoup\_strategy.py14-28](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/beautifulsoup_strategy.py#L14-L28)
*   **SeleniumStrategy**: Utiliza Chrome sin interfaz para gestionar sitios y SPAs con mucho JavaScript.

Para un análisis profundo de la lógica de detección SPA y las funciones anti-detección, **véase \[Estrategias de Raspado (#3.1)\]**.

### 2\. Programador y Servicio de Auditoría

`El AuditScheduler` gestiona el ciclo de vida de ejecución usando `croniter` para el análisis de expresiones cron [docker/scraper/scheduler.py13-29](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L13-L29). Mantiene un `_web_cache` para seguir el siguiente tiempo de ejecución de cada sitio web basado en configuraciones globales o granulares (por cliente) [docker/scraper/scheduler.py39-46](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L39-L46)

`El AuditService` orquesta la cadena propiamente dicha:

1.  **Create Run**: Inicializa un registro en la base de datos a través `de db.create_run`[docker/scraper/service.py110](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L110-L110)
2.  **Scrape**: Ejecuta la estrategia seleccionada [docker/scraper/service.py126](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L126-L126)
3.  **Auditoría**: Transmite el `resultado de raspado` al `Auditor de Calidad`.
4.  **Guardar**: Persiste el informe final.

Para más detalles sobre el demonio del planificador y la cadena de procesamiento, **véase \[Audit Scheduler & Service (#3.2)\]**.

### 3\. Modelo ScrapeResult

Cada intento de raspado produce un `Resultado de Raspado`. Este modelo incluye:

*   `contenido`: El HTML en bruto o el [DOM, scraper/models/scrape\_result.py15](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/models/scrape_result.py#L15-L15)
*   `metadatos`: Diccionario que contiene `response_time_ms`, `status_code` y `js_rendered` [flags scraper/strategies/beautifulsoup\_strategy.py56-62](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/beautifulsoup_strategy.py#L56-L62)
*   `Estado`: Indica "éxito" o "error" para el manejo de prueba [de fallo de scraper/modelos/scrape\_result.py16](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/models/scrape_result.py#L16-L16)

**Fuentes:**[scraper/models/scrape\_result.py6-21](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/models/scrape_result.py#L6-L21)[docker/scraper/scheduler.py86-120](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L86-L120)[docker/scraper/service.py104-150](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L104-L150)

* * *

# Estrategias de raspado

# Estrategias de raspado

Archivos fuente relevantes

*   [Docker/raspador/scheduler.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py)
*   [Docker/raspador/service.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py)
*   [scraper/strategies/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/__init__.py)
*   [Scraper/estrategias/beautifulsoup\_strategy.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/beautifulsoup_strategy.py)
*   [Scraper/estrategias/selenium\_strategy.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/selenium_strategy.py)
*   [Pruebas/test\_strategy\_classifier.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_strategy_classifier.py)

La plataforma Web Auditor emplea una arquitectura basada en estrategias para manejar los diversos entornos técnicos de los sitios web modernos. El sistema elige dinámicamente entre análisis estático de alto rendimiento y emulación completa del navegador en función de las características detectadas de la URL objetivo.

## Lógica de selección de estrategias

`El AuditService` implementa un motor de autoclasificación que determina el método óptimo de scraping antes de comprometer recursos pesados. Esta lógica está encapsulada en el método `classify_and_scrape`.

### Heurísticas de detección SPA

El sistema realiza una "pre-lectura rápida" usando `BeautifulSoupStrategy` y analiza el HTML en bruto frente a tres criterios principales para identificar Aplicaciones de Página Única (SPA) o sitios dinámicos:

1.  **Nodos raíz vacíos**: Busca puntos de montaje comunes del framework (por ejemplo, `id="root",` `id="app",` `app-root`, `__next`). Si se encuentra con menos de 100 caracteres de texto, el sitio se marca como [dynamic docker/scraper/service.py53-63](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L53-L63)
2.  **Relación código-contenido**: Si la página contiene menos de 80 palabras pero más de 5.000 caracteres de JavaScript en línea, se clasifica como [un docker/scraper/service.py65-76 dinámico del sitio.](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L65-L76)
3.  **Fingerprinting de Framework**: Escanea `<script src="...">` etiquetas para palabras clave como `react`, `vue`, `angular` o `webpack`. Si se encuentra junto a pocos conteos de palabras (<150 palabras), el sistema activa un [docker/scraper/service.py79-87 de Selenium de respaldo](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L79-L87)

### Flujo de Decisión de Estrategia

El siguiente diagrama ilustra cómo `AuditService.process_website` utiliza `classify_and_scrape` para orquestar la ejecución.

**Mapeo de entidades: Lógica de selección al código**

```mermaid
diagrama de flujo LR
    subgrafo subGraph1 ["Espacio de Entidades de Código"]
        A1["AuditService.process_website()"]
        B1["AuditService.classify_and_scrape()"]
        C1["EstrategiaBellaSoup.raspado()"]
        D1["SeleniumStrategy.scrape()"]
        E1["_last_bs_prefetch"]
    fin
    subgrafo subGraph0 ["Espacio de lenguaje natural"]
        R["Solicitud de auditoría"]
        B["Auto-clasificación"]
        C["Ruta estática"]
        D["Camino Dinámico"]
        E["Failsafe"]
    fin
    A --> A1
    B --> B1
    C --> C1
    D --> D1
    E --> E1
    A1 --> B1
    B1 -->|" Estática detectada"| C1
    B1 -->|" Dinámica detectada"| D1
    D1 -->|" Fracaso"| E1
    E1 -->|" Recuperación"| C1
```

Fuentes: [docker/scraper/service.py22-102](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L22-L102)[docker/scraper/service.py104-152](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L104-L152)

* * *

## BeautifulSoupStrategy (HTML estático)

`El BeautifulSoupStrategy` es el motor principal para los sitios tradicionales de renderizado en el lado del servidor (SSR). Es significativamente más rápido y consume menos recursos del sistema que el scraping basado en navegador.

### Detalles de implementación

*   **Gestión de sesiones**: Utiliza `solicitudes persistentes. Sesión` para aprovechar la agrupación de conexiones HTTP [scraper/strategies/beautifulsoup\_strategy.py28-32](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/beautifulsoup_strategy.py#L28-L32)
*   **Anti-Detección**: Implementa la rotación `User-Agent` por sesión seleccionada de un pool predefinido en `la configuración. USER_AGENT_POOL`[scraper/strategies/beautifulsoup\_strategy.py68-75](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/beautifulsoup_strategy.py#L68-L75)
*   **Modelo de datos**: Devuelve un `ScrapeResult` que contiene el HTML y metadatos embellecidos como `response_time_ms` y `status_code`[scraper/strategies/beautifulsoup\_strategy.py52-63](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/beautifulsoup_strategy.py#L52-L63)

Fuentes: [scraper/strategies/beautifulsoup\_strategy.py14-63](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/beautifulsoup_strategy.py#L14-L63)

* * *

## SeleniumStrategy (renderizado dinámico)

`La SeleniumStrategy` utiliza una instancia de Chrome sin interfaz para auditar sitios web que dependen de JavaScript para renderizado de contenido, cargas perezosas o navegación compleja.

### Detalles de implementación

*   **Ciclo de vida**: El controlador se crea y destruye para cada solicitud para asegurar un estado limpio y evitar fugas de memoria [scraper/strategies/selenium\_strategy.py25-27](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/selenium_strategy.py#L25-L27)
*   **Enmascaramiento de huellas digitales**: Utiliza comandos Chrome DevTools Protocol (CDP) para eliminar la bandera `navigator.webdriver` y plugins/lenguajes simulados, haciendo que la instancia sin interfaz visualmente parezca un [scraper legítimo de usuario/strategies/selenium\_strategy.py138-148](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/selenium_strategy.py#L138-L148)
*   **Recuperación de código de estado CDP**: Dado que Selenium no proporciona códigos de estado HTTP de forma nativa, la estrategia analiza los `registros de rendimiento` de `los eventos Network.responseReceived` para extraer el código de estado [real scraper/strategies/selenium\_strategy.py77-91](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/selenium_strategy.py#L77-L91)
*   **Optimización sin interfaz de usuario**: Configura `--no-sandbox`, `--desactivar-gpu`, y `--desactivar-dev-shm-uso` para un funcionamiento estable dentro de contenedores [Docker scraper/strategies/selenium\_strategy.py167-172](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/selenium_strategy.py#L167-L172)

### Ciclo de vida del raspado

El siguiente diagrama mapea el ciclo de vida de la interacción del navegador a llamadas específicas de Selenium.

**Mapeado de entidades: ciclo de vida del navegador al código**

```mermaid
Diagrama de secuencia
    participante AS como AuditService
    participante SS como SeleniumStrategy
    participante WD como webdriver. Chrome
    participante BS como BeautifulSoup
    AS->>SS: raspar (url)
    SS->>WD: _create_driver()
    Nota sobre WD: execute_cdp_cmd (Anti-Detection)
    SS->>WD: get(url)
    SS->>WD: WebDriverWait (presence_of_element_located)
    WD-->>SS: page_source
    SS->>WD: get_log("performance")
    Nota sobre SS: Extraer status_code mediante registros CDP
    SS->>WD: renunciar()
    SS->>BS: BeautifulSoup(raw_html)
    BS-->>SS: pretify()
    SS-->>AS: ScrapeResult
```

Fuentes: [scraper/strategies/selenium\_strategy.py62-125](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/selenium_strategy.py#L62-L125)[scraper/strategies/selenium\_strategy.py129-148](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/selenium_strategy.py#L129-L148)

* * *

## Mecanismos de seguridad y respaldo

El sistema está diseñado para una alta disponibilidad incluso cuando las estrategias pesadas fallan:

| Escenario | Lógica | Fuente |
| --- | --- | --- |
| Tiempo muerto del selenio | Si Selenium no entrega el cuerpo, AuditService intenta recuperar el resultado \_last\_bs\_prefetch. | docker/scraper/service.py133-136 |
| Piloto ausente | Si detecta automáticamente un sitio dinámico pero el selenio no está registrado en el entorno, vuelve a usar beautifulsoup. | docker/raspador/servicio.py97-99 |
| Estado 200 Ambigüedad | Si los registros CDP no proporcionan un código de estado, la estrategia ejecuta una llamada requests.head() como verificación secundaria. | scraper/estrategias/selenium\_strategy.py100-109 |

Fuentes: [docker/scraper/service.py113-152](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L113-L152)[scraper/strategies/selenium\_strategy.py99-110](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/selenium_strategy.py#L99-L110)

* * *

# Auditoría-Programador-&-Servicio

# Programador y Servicio de Auditoría

Archivos fuente relevantes

*   [docker/dashboard/api/main.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/main.py)
*   [docker/db-init/01\_schema.sql](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql)
*   [Docker/raspador/entrypoint.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/entrypoint.py)
*   [Docker/raspador/scheduler.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py)
*   [Docker/raspador/service.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py)
*   [Scraper/estrategias/beautifulsoup\_strategy.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/beautifulsoup_strategy.py)
*   [compartido/base de datos/repositorios/scraper/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/__init__.py)
*   [compartido/base de datos/repositorios/scraper/runs.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/runs.py)
*   [compartido/base de datos/repositorios/scraper/settings.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/settings.py)

**El Planificador de Auditoría** y **el Servicio de Auditoría** constituyen la capa de orquestación del contenedor del raspador. Mientras que las estrategias gestionan la extracción técnica de datos, estos componentes gestionan la ejecución temporal (cron), la lógica de decisión para seleccionar estrategias (auto-clasificación) y la cadena de procesamiento de extremo a extremo desde la inicialización de la base de datos hasta la persistencia del informe final.

## AuditScheduler: Daemon basado en crons

La clase `AuditScheduler` es responsable de gestionar los ciclos de auditoría utilizando expresiones cron. Soporta una configuración jerárquica donde los ajustes granulares (a nivel de sitio web o cliente) anulan los valores globales por [defecto docker/scraper/scheduler.py13-17](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L13-L17)

### Lógica de planificación y granularidad

El planificador opera con un intervalo de sondeo (por defecto de 5 segundos) [docker/scraper/scheduler.py28-37](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L28-L37). Durante cada "tick", evalúa el siguiente tiempo de ejecución para cada sitio web del sistema.

*   **Prioridad 1: Auditorías pendientes**: El planificador siempre procesa las solicitudes manuales (activadas a través del Panel de Control) primero [docker/scraper/scheduler.py87-88](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L87-L88)
*   **Prioridad 2: Cron granular vs Global** Cron:

1.  Si un `website_cron` está definido en la tabla `del sitio web`, tiene prioridad [docker/scraper/scheduler.py69-71](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L69-L71)
2.  De lo contrario, si se define un `client_cron` en la `tabla de clientes`, se utiliza [docker/scraper/scheduler.py72-74](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L72-L74)
3.  Finalmente, vuelve a la `configuración de global_active` o `global_inactive` desde el `global_settings` table [docker/scraper/scheduler.py76-77](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L76-L77)

### El `mecanismo _web_cache`

Para evitar costosos recálculos de expresiones cron, el planificador mantiene un `website_id` interno `de mapeo de _web_cache` a su siguiente tiempo de ejecución programado y a la cadena cron [actual docker/scraper/scheduler.py39-40](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L39-L40). Si la configuración cron cambia en la base de datos, la caché se invalida y se [actualiza docker/scraper/scheduler.py111-114](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L111-L114)

**Fuentes:**

*   [docker/scraper/scheduler.py13-133](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L13-L133)
*   [docker/db-init/01\_schema.sql20-40](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql#L20-L40)

## AuditService: La Cadena de Ejecución

`El AuditService` orquesta el ciclo de vida de una única ejecución de auditoría. Conecta el `ScraperContext` (extracción) con `el QualityAuditor` (análisis) y los repositorios `del scraper` (persistencia) [docker/scraper/service.py14-19](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L14-L19)

### process\_website Pipeline

Cuando se activa una auditoría, la función `process_website` ejecuta la siguiente secuencia:

1.  **Create Run**: Inicializa un registro en la `tabla audit_runs` con un estado [en ejecución docker/scraper/service.py110](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L110-L110)
2.  **Extractor**: Ejecuta la estrategia seleccionada (o lógica "auto") para recuperar el HTML y los [metadatos docker/scraper/service.py116-127](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L116-L127)
3.  **Auditoría**: Transmite el `ScrapeResult` a `QualityAuditor.build_report`[docker/scraper/service.py164](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L164-L164)
4.  **Guardar**: Persiste el informe estructurado, los problemas individuales y las puntuaciones calculadas en la base de [datos docker/scraper/service.py183](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L183-L183)

### Seguimiento en tiempo real: on\_progress Callback

El servicio utiliza una devolución `de llamada on_progress` durante la fase de auditoría. Esto actualiza en tiempo real las `columnas sections_passed` y `sections_total` de la tabla `audit_runs`, permitiendo que la interfaz del Panel muestre barras de progreso para auditorías [activas docker/scraper/service.py164-173](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L164-L173)[shared/database/repositories/scraper/runs.py28-40](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/runs.py#L28-L40)

### Respaldo de seguridad

Si la estrategia principal (por ejemplo, Selenium) falla, el servicio incluye un mecanismo de "seguridad". Si una pre-lectura de clasificación "automática" con `BeautifulSoup` tuvo éxito antes, el servicio recuperará esos datos para asegurar que la auditoría se complete, incluso si la estrategia pesada del navegador encuentra errores [en docker/scraper/service.py133-136](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L133-L136)

**Fuentes:**

*   [docker/raspador/servicio.py104-190](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L104-L190)
*   [compartido/database/repositories/scraper/runs.py10-26](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/runs.py#L10-L26)
*   [compartido/base de datos/repositorios/scraper/runs.py42-103](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/runs.py#L42-L103)

## Flujo de datos: Del disparador a la persistencia

El siguiente diagrama ilustra la interacción entre el Planificador, el Servicio y los Repositorios de la Base de Datos.

### Mapeo de entidades del sistema: Planificador a servicio

| Entidad de código | Responsabilidad |
| --- | --- |
| AuditScheduler | Las encuestas, la base de datos y los disparos se ejecutan basándose en cálculos de croniter. |
| AuditService | Gestiona el ScraperContext y llama a QualityAuditor. |
| db.create\_run | Crea el registro inicial de AuditRun con status='running'. |
| db.save\_audit\_run | Finaliza la ejecución, guarda los registros de AuditIssue y AuditRunSection. |

### Diagrama de flujo de ejecución

```mermaid
Diagrama de secuencia
    participante S como AuditScheduler
    participante AS como AuditService
    DB participante como scraper_repository
    Asistente de calidad participante como Auditor de Calidad
    S->>DB: get_pending_audit_websites()
    DB-->>S: Lista[entrada]
    S->>AS: process_website(entrada)
    AS->>DB: create_run(website_id, estrategia)
    AS->>AS: classify_and_scrape(URL)
    Nota sobre AS: Ejecuta BeautifulSoupStrategy
    AS->>QA: build_report(contenido, metadatos, on_progress)
    QA-->>DB: update_run_progress(run_id, p, t)
    QA-->>AS: report_dict
    AS->>DB: save_audit_run(run_id, informe, metadatos)
    Nota sobre la base de datos: Persiste AuditRun, Problemas,
```

**Fuentes:**

*   [docker/scraper/scheduler.py86-120](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L86-L120)
*   [docker/scraper/service.py104-183](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L104-L183)
*   [compartido/base de datos/repositorios/scraper/runs.py42-103](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/runs.py#L42-L103)

## Lógica de selección de estrategias

El método `AuditService.classify_and_scrape` implementa la lógica de la estrategia "Auto". Realiza un "Pre-fetch rápido" usando `BeautifulSoup` y analiza la respuesta para detectar si el sitio es un [docker/scraper/service.py22-46 de aplicación de página única (SPA)](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L22-L46)

### Heurísticas de detección SPA

Un sitio se clasifica como `selenio` (dinámico) si:

1.  **Nodos raíz vacíos**: Elementos como `<div id="app">` o `<div id="root">` contienen menos de 100 caracteres [docker/scraper/service.py54-63](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L54-L63)
2.  **JS pesado/Contenido delgado**: El recuento de palabras es < 80 pero el total de caracteres en las etiquetas `<script>` supera los 5.000 [docker/scraper/service.py73-76](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L73-L76)
3.  **Paquetes de framework**: La presencia de cadenas como `react`, `vue` o `webpack` en las fuentes de scripts combinada con pocos conteos de [palabras docker/scraper/service.py79-87](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L79-L87)

### Asociación de Entidades de Código

```mermaid
diagrama de flujo TD
    subgrafo subGraph1 ["Espacio de Entidad de Código: scraper/service.py"]
        C["AuditService.process_website"]
        D["AuditService.classify_and_scrape"]
        E["BeautifulSoupStrategy.scrape (Pre-fetch)"]
        F["¿Es SPA?"]
        G["SeleniumStrategy"]
        H["EstrategiaHermosaSopa"]
    fin
    subgrafo subGraph0 ["Lenguaje natural: Lógica de selección"]
        A["Elección manual"]
        B["Clasificación de autos"]
    fin
    A --> C
    B --> D
    D --> E
    E --> F
    F -->|" Sí"| G
    F -->|" No"| H
```

**Fuentes:**

*   [docker/scraper/service.py22-102](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L22-L102)
*   [scraper/strategies/beautifulsoup\_strategy.py32-63](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/beautifulsoup_strategy.py#L32-L63)

* * *

# Analizador-Microservicio de IA

# Microservicio de analizador de IA

Archivos fuente relevantes

*   [docker/ai-analyzer/Dockerfile](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/Dockerfile)
*   [docker/ai-analyzer/app.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py)
*   [docker/ai-analyzer/main.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/main.py)
*   [Docker/analizador de IA/requirements.txt](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/requirements.txt)

El **microservicio AI Analyzer** es un contenedor sidecar especializado dentro de la arquitectura Web Auditor, diseñado para proporcionar una inteligencia semántica profunda que va más allá de las heurísticas basadas en regex. Mientras el auditor principal realiza comprobaciones estructurales y técnicas, este servicio utiliza Procesamiento de Lenguaje Natural (PLN) para determinar si un sitio es realmente funcional, educativa o malicioso, analizando el significado real de su contenido textual.

## Visión general y función

El servicio está construido usando **FastAPI**[docker/ai-analyzer/app.py11-15](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L11-L15) y funciona como un microservicio independiente (contenedor mediante `docker/ai-analyzer/Dockerfile`). Actúa como "asesor experto" para la cadena `de QualityAuditor`. Durante una auditoría, el scraper envía el HTML y los metadatos en bruto al endpoint `/`analyze de este servicio para recibir una evaluación semántica de alto nivel.

### Responsabilidades clave

*   **Detección Semántica Inoperativa**: Distinguir entre una página 404 real y un "Soft 404" (donde una página devuelve 200 OK pero contiene texto "En construcción" o "Dominio en venta").
*   **Puntuación de calidad**: Asignar una puntuación semántica de calidad basada en la coherencia del texto y la presencia de spam o relleno de palabras clave.
*   **Seguridad de contenido**: Identificar patrones maliciosos o tipos de contenido no conformes.
*   **Identificación del idioma**: Detección del idioma principal del contenido de la página.

### Arquitectura de servicios

El diagrama siguiente ilustra cómo el AI Analyzer se integra en el sistema más amplio y cómo sirve de puente entre el HTML puro y la clasificación semántica.

**Flujo de integración de analizadores de IA**

```mermaid
diagrama de flujo TD
    subgrafo subGraph1 ["Microservicio analizador de IA (Sidecar)"]
        FAST["FastAPI (app.py)"]
        ANALIZADOR["AIContentAnalyzer (analyzer.py)"]
        MODELO["Modelo MiniLM-L12-v2"]
    fin
    subgrafo subGraph0 ["Espacio de entidad de código (Servicio de Auditor)"]
        QA["QualityAuditor"]
        AS["AuditService"]
    fin
    COMO -->|" llama"| QA
    QA -->|" POST /analyze"| RÁPIDO
    RÁPIDO -->|" invoca"| ANALIZADOR
    ANALIZADOR -->|" usos"| MODELO
    ANALIZADOR -->|" retorna AnalysisResponse"| RÁPIDO
    RÁPIDO -->|" Respuesta de JSON"| QA
```

Fuentes: [docker/ai-analyzer/app.py11-18](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L11-L18)[docker/ai-analyzer/app.py56-71](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L56-L71)

## API Endpoints

El microservicio expone una API REST ligera diseñada para una comunicación local de alto rendimiento dentro de la red Docker.

### `GET /salud`

Usado por las revisiones de salud de Docker y el orquestador principal para verificar la preparación del servicio. Comprueba específicamente si los modelos pesados de Transformer se han cargado correctamente en memory [docker/ai-analyzer/app.py41-53](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L41-L53)

### `POST /analyze`

El punto final principal de procesamiento. Acepta una `AnalysisRequest` que contiene el HTML en bruto y devuelve un [AnalysisResponse docker/ai-analyzer/app.py56-71](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L56-L71)

**Mapeo de modelos de datos**

| Entidad de código | Descripción | Campos |
| --- | --- | --- |
| Analysis Request | Aportaciones del Auditor | html, url, status\_code, metadatosdocker/ai-analyzer/app.py21-25 |
| AnálisisRespuesta | Resultados al auditor | is\_inoperative, confianza, quality\_score, problemasdocker/ai-analyzer/app.py28-38 |

Fuentes: [docker/ai-analyzer/app.py21-38](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L21-L38)[docker/ai-analyzer/app.py41-71](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L41-L71)

## Lógica interna y modelos

El microservicio está optimizado para la ejecución en CPU y así minimizar la sobrecarga de recursos en entornos de despliegue estándar. `El Dockerfile` instala explícitamente la **versión solo CPU de PyTorch** para evitar el enorme espacio de 4GB [de CUDA docker/ai-analyzer/Dockerfile19-23](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/Dockerfile#L19-L23)

### Motor Semántico

La lógica central reside en la clase `AIContentAnalyzer` [docker/ai-analyzer/app.py18](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L18-L18). Utiliza:

*   **Transformadores de oraciones**: Específicamente `parafraseando-multilingüe-MiniLM-L12-v2` para generar incrustaciones que funcionen en varios [idiomas docker/ai-analyzer/app.py52](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L52-L52)
*   **Clasificación de disparo cero**: Un mecanismo de respaldo (usando XLM-RoBERTa) para resolver contenido ambiguo cuando las incrustaciones estándar son insuficientes.

Para una profundización en la arquitectura de PLN, la puntuación de coherencia y cómo se resuelve la "banda de ambigüedad", véase **[AIContentAnalyzer: Semantic Detection](/LuisVilRiv/comprobador-de-paginas-web/4.1-aicontentanalyzer:-semantic-detection)**.

### Integración con auditores

El `QualityAuditor` en la base de código principal utiliza los resultados de este microservicio para anular sus propias banderas basadas en heurísticas. Por ejemplo, si la IA detecta una "Página de Aparcamiento" con alta confianza, el auditor marcará el sitio como inoperativo incluso si las comprobaciones técnicas han pasado.

Para detalles sobre el esquema JSON y cómo el auditor gestiona los tiempos de espera o errores de la IA, véase **[AI Analyzer API Contract](/LuisVilRiv/comprobador-de-paginas-web/4.2-ai-analyzer-api-contract)**.

**Pipeline de Análisis de IA**

```mermaid
diagrama de flujo LR
    RES["AnalysisResponse"]
    subgrafo subGraph1 ["Espacio de Entidades de Código"]
        BS4["BeautifulSoup4 (limpiador)"]
        S_TRANS["TransformadorSentence"]
        LOGIC["AIContentAnalyzer.analyze()"]
    fin
    subgrafo subGraph0 ["Espacio de lenguaje natural"]
        HTML["Contenido HTML en bruto"]
        TEXTO["Texto Limpio"]
        VEC["Vector Semántico (Incrustado)"]
    fin
    HTML --> BS4
    BS4 --> TEXTO
    TEXTO --> S_TRANS
    S_TRANS --> VEC
    VEC --> LÓGICA
    LÓGICA -->|" Resultado"| RES
```

Fuentes: [docker/ai-analyzer/requirements.txt5-9](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/requirements.txt#L5-L9)[docker/ai-analyzer/app.py64-69](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L64-L69)[docker/ai-analyzer/Dockerfile20-28](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/Dockerfile#L20-L28)

* * *

**Páginas Infantiles:**

*   **[AIContentAnalyzer: Detección semántica](/LuisVilRiv/comprobador-de-paginas-web/4.1-aicontentanalyzer:-semantic-detection)**: Análisis detallado de la arquitectura de PLN de dos niveles y la lógica de puntuación.
*   **[Contrato de API de AI Analyzer](/LuisVilRiv/comprobador-de-paginas-web/4.2-ai-analyzer-api-contract)**: Documentación técnica de la interfaz REST y los patrones de integración.

* * *

# Analizador-Detección Semántica AIContent

# AIContentAnalyzer: Detección Semántica

Archivos fuente relevantes

*   [docker/ai-analyzer/analyzer.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py)
*   [Pruebas/test\_ai\_analyzer\_error\_context.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_error_context.py)
*   [Pruebas/test\_ai\_analyzer\_integration.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_integration.py)

El `AIContentAnalyzer` es un microservicio especializado dentro del contenedor `de analizadores de IA` diseñado para realizar una evaluación semántica profunda de contenido web extraído. Su función principal es resolver ambigüedades que las comprobaciones heurísticas estáticas no pueden manejar—distinguiendo específicamente entre errores reales de servidor (por ejemplo, una página de mantenimiento 503) y contenido educativo (por ejemplo, un artículo de Wikipedia que explique qué es un error 503). Utiliza una arquitectura NLP de dos niveles para clasificar contenidos, detectar patrones maliciosos y calcular una puntuación de calidad completa.

## Arquitectura de PLN de dos niveles

El analizador emplea una estrategia escalonada para equilibrar rendimiento y precisión. Por defecto, utiliza incrustaciones de alta velocidad para la coincidencia de similitudes y solo escala a modelos de transformadores pesados cuando la confianza es baja.

### Nivel 1: Incrustaciones Semánticas de MiniLM

El sistema utiliza el modelo `parafrase-multilingüe MiniLM-L12-v2` [docker/ai-analyzer/analyzer.py215-218](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L215-L218) para generar representaciones vectoriales del texto extraído. Estas incrustaciones se comparan con "anclajes semánticos" precalculados usando similitud coseno.

*   **Carga de modelos:** El modelo se carga de forma perezosa en la primera petición al `endpoint /`[analyze docker/ai-analyzer/analyzer.py212-231](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L212-L231)
*   **Comparación de espacios vectoriales:** El texto se compara con tres conjuntos principales de ancla: `ERROR_ANCHORS`, `EDUCATIONAL_ANCHORS` y `MALICIOUS_ANCHORS`[docker/ai-analyzer/analyzer.py233-255](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L233-L255)

### Nivel 2: Reserva XLM-RoBERTa Zero-Shot

Cuando la puntuación de similitud cae en una "banda de ambigüedad" (donde el Nivel 1 no puede decidir con confianza si una página es un error o es educativo), el sistema activa el Strong AI [Fallback docker/ai-analyzer/analyzer.py202-206](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L202-L206)

*   **Plantilla:**`joeddav/xlm-roberta-large-xnli`.
*   **Mecanismo:** Realiza NLI (Inferencia de Lenguaje Natural) para clasificar el texto en etiquetas como "contenido informativo o educativo" frente a "página de error o interrupción de mantenimiento" [docker/ai-analyzer/analyzer.py387-390](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L387-L390)
*   **Configuración:** Este comportamiento está controlado por la variable `de entorno ENABLE_STRONG_AI_FALLBACK` [docker/ai-analyzer/analyzer.py202](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L202-L202)

### Flujo de datos de detección semántica

El siguiente diagrama ilustra cómo el `AIContentAnalyzer` procesa el texto desde la petición inicial hasta la clasificación final.

**Flujo de Análisis de Contenidos con IA**

```mermaid
diagrama de flujo TD
    subgrafo subGraph2 ["Entidades de código"]
        ERROR_ANCHORS["ERROR_ANCHORS"]
        MALICIOUS_ANCHORS["MALICIOUS_ANCHORS"]
    fin
    subgrafo subGraph1 ["Microservicio de analizador de IA"]
        R["POST /analyze"]
        B["AIContentAnalyzer.analyze_content()"]
        C["_load_model() #91; MiniLM#93;"]
        F["¿ENABLE_STRONG_AI_FALLBACK?"]
        G["_resolve_ambiguity_with_strong_model()"]
        H["XLM-RoBERTa Zero-Shot"]
        I["Clasificación final"]
        J["_calculate_quality_score()"]
        K["Respuesta de Análisis de Retorno"]
        subgrafo subGraph0 ["Nivel 1: Incrustaciones"]
            D["_calculate_similarity_scores()"]
            E["¿Alta confianza?"]
        fin
    fin
    A --> B
    B --> C
    C --> D
    D --> E
    E -->|" No (Ambigüedad Band)"| F
    F -->|" Cierto"| G
    G --> H
    E -->|" Sí"| I
    H --> yo
    Yo... > J
    J --> K
    B -->|" usos"| ERROR_ANCHORS
    B -->|" usos"| MALICIOUS_ANCHORS
```

Fuentes: [docker/ai-analyzer/analyzer.py19-55](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L19-L55)[docker/ai-analyzer/analyzer.py169-194](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L169-L194)[docker/ai-analyzer/analyzer.py270-305](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L270-L305)[docker/ai-analyzer/analyzer.py373-405](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L373-L405)

* * *

## Anclajes semánticos y lógica

El analizador utiliza conjuntos específicos de "anclas"—cadenas que representan ejemplos arquetípicos de ciertos tipos de contenido—para construir su espacio vectorial interno.

### Errores y Anclas Educativas

Estos anclajes evitan falsos positivos cuando la documentación técnica se confunda con un sitio web roto.

| Categoría | Descripción | Ejemplos |
| --- | --- | --- |
| ERROR | Fallos reales, páginas de aparcamiento o suspensiones. | "404 página no encontrada", "fallida conexión a la base de datos", "este dominio está aparcado" docker/ai-analyzer/analyzer.py19-55 |
| EDUCATIONAL | Referencias técnicas y entradas de enciclopedia. | "Documentación del código de estado http", "especificación RFC", "artículo explicando conceptos" docker/ai-analyzer/analyzer.py58-69 |

### Detección de maliciosos y spam

El analizador verifica patrones de contenido tóxicos que normalmente evitan filtros simples de palabras clave usando proximidad semántica a `MALICIOUS_ANCHORS`[docker/ai-analyzer/analyzer.py169-194](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L169-L194)

*   **Phishing:** Detectando un contexto de acceso falso o robo de credenciales.
*   **Spam SEO:** Identificación de patrones de "Viagra/Cialis" o "relojes réplica" [docker/ai-analyzer/analyzer.py190-193](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L190-L193)
*   **Malware:** Detectando menciones de "programas crackeados" o "instaladores maliciosos".

### Resolución de ambigüedad

El `método _is_ambiguous` determina si se necesita el Nivel 2. Si la diferencia entre la puntuación de error más alta y la puntuación educativa más alta es menor que un umbral, el sistema marca el resultado como [incierto docker/ai-analyzer/analyzer.py365-371](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L365-L371)

Fuentes: [docker/ai-analyzer/analyzer.py19-69](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L19-L69)[docker/ai-analyzer/analyzer.py169-194](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L169-L194)[docker/ai-analyzer/analyzer.py365-371](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L365-L371)

* * *

## Puntuación de calidad y coherencia

Más allá de la clasificación, el analizador evalúa la "salud" del texto mediante dos métricas principales:

### Puntuación de coherencia

La función `_calculate_coherence_score` mide el flujo lógico del [docker de texto/analizador de IA/analizador.py448-472](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L448-L472)

1.  El texto está dividido en párrafos.
2.  Se generan incrustaciones para cada párrafo.
3.  Se calcula la similitud del coseno entre párrafos consecutivos.
4.  Una similitud media baja indica contenido "fragmentado" o "manipulado" (común en el spam SEO de baja calidad).

### Cálculo de la puntuación final de calidad

El `método _calculate_quality_score` [docker/ai-analyzer/analyzer.py407-446](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L407-L446) agrega múltiples factores:

*   **Marcador base:** Empieza en 100.
*   **Deducciones:**
*   **Inoperativo:** -90 puntos (Crítico).
*   **Malicioso:** -80 puntos.
*   **Spam:** -50 puntos.
*   **Baja coherencia:** Hasta -30 puntos según la brecha de coherencia.
*   **Penalización por el idioma:** Se aplica una penalización si el lenguaje detectado no coincide con el perfil esperado del sitio [docker/ai-analyzer/analyzer.py433-437](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L433-L437)

Fuentes: [docker/ai-analyzer/analyzer.py407-472](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L407-L472)

* * *

## Integración con QualityAuditor

El `QualityAuditor` en el motor central llama al microservicio de IA durante la fase de auditoría de contenido. Esta interacción está diseñada para ser "a prueba de fallos".

**Puente Auditor-AI**

```mermaid
Diagrama de secuencia
    Asistente de Calidad de Asistente como Auditor de Calidad [core.py]
    participante S como peticiones. Sesión
    IA participante como analizador de IA [/analyze]
    QA->>S: post(AI_ANALYZER_URL, json=payload)
    Nota sobre S,AI: La carga útil incluye clean_text y URL
    IA-->>S: 200 OK (AnalysisResponse)
    S-->>QA: Datos JSON
    QA->>QA: override_heuristics(ai_data)
    S-->>QA: requests.exceptions.ConnectionError
    QA->>QA: log_warning("AI Fallback")
```

Fuentes: [compartido/auditor/auditor\_modules/core.py112-145](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L112-L145)[tests/test\_ai\_analyzer\_integration.py15-45](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_integration.py#L15-L45)

### Anulaciones heurísticas

Si la IA identifica una página como inoperativa, anula la puntuación interna del `QualityAuditor`, forzando una puntuación de 5 y marcando la liberación como [pruebas bloqueadas/test\_ai\_analyzer\_integration.py83-101](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_integration.py#L83-L101). Por el contrario, si las heurísticas estáticas marcan una página (por ejemplo, porque contiene la cadena "404"), pero la IA la identifica como `EDUCATIVA`, prevalece la decisión semántica de la IA, prevención de [falsos positivos/test\_ai\_analyzer\_integration.py164-204](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_integration.py#L164-L204)

Fuentes: [pruebas/test\_ai\_analyzer\_integration.py47-101](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_integration.py#L47-L101)[pruebas/test\_ai\_analyzer\_integration.py164-204](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_integration.py#L164-L204)

* * *

## Configuración del entorno

El comportamiento del `AIContentAnalyzer` se ajusta mediante variables de entorno:

| Variable | Default | Descripción |
| --- | --- | --- |
| ENABLE\_STRONG\_AI\_FALLBACK | Cierto | Activa/desactiva el modelo XLM-RoBERTa zero-shot docker/ai-analyzer/analyzer.py202 |
| MODEL\_CACHE\_DIR | /app/model\_cache | Directorio donde se almacenan los modelos de HuggingFace para evitar volver a descargarse. |
| STRONG\_FALLBACK\_MODEL | joeddav/xlm-roberta-large-xnli | El modelo específico utilizado para la clasificación de disparo cero de alta precisión docker/ai-analyzer/analyzer.py203-206 |

Fuentes: [docker/ai-analyzer/analyzer.py201-206](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L201-L206)

* * *

# AI-Analyzer-API-Contract

# Contrato de API para analizadores de IA

Archivos fuente relevantes

*   [docker/ai-analyzer/app.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py)
*   [compartido/auditor/auditor\_modules/core.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py)
*   [Pruebas/test\_inoperative\_pages.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_inoperative_pages.py)

El microservicio **AI Analyzer** actúa como un sidecar semántico del motor principal de auditoría. Mientras que `el QualityAuditor` utiliza patrones regex y heurísticos para la velocidad, el AI Analyzer ofrece un recurso de aprendizaje profundo para resolver ambigüedades, como distinguir entre una página real de error 404 y un artículo educativo sobre errores 404. Esta página documenta la interfaz FastAPI utilizada para esta comunicación.

## Interfaz de servicio

El servicio está construido usando **FastAPI** y expone una interfaz RESTful al `QualityAuditor`. Envuelve la clase `AIContentAnalyzer`, que gestiona el ciclo de vida de los modelos Transformer (MiniLM y XLM-RoBERTa).

### Flujo de datos: Auditor a analizador de IA

El auditor principal inicia una solicitud durante la `build_report` pipeline si la `variable de entorno AI_ANALYZER_URL` está configurada.

Título: Flujo de integración de analizadores de IA

```mermaid
diagrama de flujo TD
    G["QualityAuditor Overrides"]
    H["Informe Final de Auditoría de Calidad"]
    subgrafo subGraph1 ["Servicio de Analizador de IA (FastAPI)"]
        C["app.analyze_page"]
        D["AIContentAnalyzer.analyzer"]
        E["Lógica de Incrustación Semántica"]
        F["AnalysisResponse"]
    fin
    subgrafo subGraph0 ["Servicio de Raspador/Auditor"]
        A["QualityAuditor.build_report"]
        B["AnálisisRequest"]
    fin
    Un -->|" POST /analyze"| B
    B --> C
    C --> D
    D --> E
    E --> F
    F -->|" Respuesta JSON"| G
    G --> H
```

Fuentes: [compartido/auditor/auditor\_modules/core.py241-274](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L241-L274)[docker/ai-analyzer/app.py56-71](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L56-L71)

## API Endpoints

### 1\. Control de salud

`GET /salud`

Utilizado por la orquestación de Docker y la API del Dashboard para verificar la preparación del servicio. Comprueba específicamente si los modelos pesados de Transformer han terminado de cargarse en la memoria.

**Esquema de respuesta:**

*   `Estado`: "Saludable"
*   `model_loaded`: Booleano (Verdadero si `analyzer.model` está inicializado).
*   `Dispositivo`: "CPU"
*   `model_name`: El identificador específico del modelo HuggingFace.

Fuentes: [docker/ai-analyzer/app.py41-53](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L41-L53)

### 2\. Analizar el contenido

`POST /analyze`

El objetivo principal para la evaluación semántica. Recibe HTML y metadatos en bruto, devolviendo un juicio estructurado sobre el estado operativo de la página y la calidad del contenido.

#### Esquema de Solicitud (`AnalysisRequest`)

El auditor envía la siguiente estructura definida en `docker/ai-analyzer/app.py`:

| Campo | Tipo | Descripción |
| --- | --- | --- |
| html | str | Código HTML completo de la página. |
| url | str | La URL que se analiza. |
| status\_code | int | El código de estado HTTP (por defecto 200). |
| Metadatos | Dictado | Metadatos de extracción opcional. |

Fuentes: [docker/ai-analyzer/app.py21-25](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L21-L25)

#### Esquema de Respuesta (`AnalysisResponse`)

El servicio devuelve un perfil semántico que puede anular las banderas heurísticas del auditor:

| Campo | Tipo | Descripción |
| --- | --- | --- |
| is\_inoperative | bool | Bandera de alta confianza para 404/500/Mantenimiento. |
| inoperative\_reason | str | Razón legible para humanos para el fracaso. |
| confianza | Flotador | Confianza en la predicción (0,0 a 1,0). |
| has\_spam | bool | Detección de patrones de relleno de palabras clave o spam. |
| has\_malicious | bool | Detección de contenido tóxico o malicioso. |
| quality\_score | int | Puntuación de calidad semántica (de 5 a 100). |
| detected\_language | str | Código de idioma ISO de 2 letras. |

Fuentes: [docker/ai-analyzer/app.py28-38](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L28-L38)

## Detalle de implementación: Integración con auditores

`El QualityAuditor` integra la respuesta de la IA en su `método build_report`. Si el servicio de IA es accesible, sus resultados tienen prioridad sobre las `heurísticas locales is_inoperative`.

### Mapeo lógico: Espacio de IA a Espacio de Auditor

El siguiente diagrama conecta la salida semántica de la IA con la entidad `QualityAuditReport` utilizada por la base de datos y el frontend.

Título: Respuesta de IA a mapeo de informes de auditoría

```mermaid
Diagrama de clases.
    clase AnalysisResponse {
        +bool is_inoperative
        +string inoperative_reason
        +int quality_score
        Problemas con +lista
    }
    clase QualityAuditReport {
        +puntuación de inteligencia
        Estado de +cadena
        +Lista technical_issues
        +content_issues
        +bool release_blocked
    }
    AnalysisResponse --|> QualityAuditReport : "Anula las heurísticas"
```

### Flujo de trabajo de integración

1.  **Comprobación heurística**: El auditor primero realiza comprobaciones locales de regex para "404", "Mantenimiento", etc. [compartido/auditor/auditor\_modules/core.py174-210](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L174-L210)
2.  **Solicitud de IA**: Si `se configura. AI_ANALYZER_URL` está configurado, llama al microservicio [shared/auditor/auditor\_modules/core.py241-255](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L241-L255)
3.  **Lógica de anulación**:

*   Si la IA devuelve `is_inoperative=Verdadero`, el auditor fuerza `report.score = 5` y establece el `estado` en "crítico[" compartido/auditor/auditor\_modules/core.py261-267](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L261-L267)
*   Si la IA devuelve `is_inoperative=Falso`, borra cualquier bandera de "Sitio web no operativo" previamente establecida por heurísticas, evitando falsos positivos en contenido [educativo compartido/auditor/auditor\_modules/core.py270-274](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L270-L274)

Fuentes: [compartido/auditor/auditor\_modules/core.py241-274](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L241-L274)[docker/ai-analyzer/app.py56-77](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L56-L77)

## Manejo de errores

*   **Tiempo de espera/error de conexión**: Si el analizador de IA está caído o lento, el `Auditor de Calidad` detecta la excepción, registra una advertencia y recurre completamente a la detección basada en [heurística compartido/auditor/auditor\_modules/core.py276-278](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L276-L278)
*   **Errores internos del modelo**: El microservicio devuelve un `error interno de servidor 500` con una cadena de detalle si la tubería Transformer [falla en docker/ai-analyzer/app.py72-77](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L72-L77)

Fuentes: [compartido/auditor/auditor\_modules/core.py276-278](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L276-L278)[docker/ai-analyzer/app.py72-77](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/app.py#L72-L77)

* * *

# Dashboard-API-(Backend)

# API de panel de control (Backend)

Archivos fuente relevantes

*   [docker/dashboard/api/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/__init__.py)
*   [docker/dashboard/api/app.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/app.py)
*   [docker/dashboard/api/routes/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/__init__.py)
*   [Docker/dashboard/API/rutas/clientes/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/clients/__init__.py)
*   [Docker/dashboard/API/rutas/clientes/clients\_endpoints.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/clients/clients_endpoints.py)
*   [Docker/dashboard/API/rutas/salud/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/health/__init__.py)
*   [Docker/dashboard/API/rutas/salud/health\_endpoints.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/health/health_endpoints.py)
*   [Docker/dashboard/API/rutas/ajustes/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/settings/__init__.py)
*   [Docker/dashboard/API/rutas/ajustes/settings\_endpoints.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/settings/settings_endpoints.py)
*   [Docker/Dashboard/API/Rutas/Resumen/summary\_endpoints.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/summary/summary_endpoints.py)
*   [Docker/Dashboard/API/Esquemas/clients.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/schemas/clients.py)

La **API del Panel** es un microservicio basado en FastAPI que sirve como centro de orquestación para la plataforma Web Auditor. Proporciona una interfaz RESTful para que el frontend React gestione clientes, sitios web y resultados de auditoría, mientras interactúa con la capa compartida de la base de datos PostgreSQL.

## Estructura de la aplicación e inicialización

El backend está ubicado dentro del `docker/dashboard/api/`directorio. Un aspecto crítico de su diseño es el patrón **de Inicialización de Camino Compartido** utilizado en el punto de entrada. Dado que el proyecto utiliza una biblioteca compartida (`compartida/`) situada en la raíz del repositorio, la API ajusta `dinámicamente sys.path` en tiempo de ejecución para asegurar que estos módulos sean importables sin necesidad de empaquetados complejos en Python.

### Patrón de inicialización de caminos

El `archivo app.py` recorre el árbol de directorios hacia arriba para localizar el `directorio compartido` e inyectarlo en la ruta del sistema: [docker/dashboard/api/app.py7-12](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/app.py#L7-L12)

### Registro de routers

La aplicación sigue un patrón modular de router. Cada dominio funcional (clientes, ejecuciones, sitios web, etc.) se define en un subpaquete dentro `de rutas` y se agrega en `docker/dashboard/api/routes/__init__.py`.

| Router | Propósito | Archivo |
| --- | --- | --- |
| health\_router | Chequeos de salud del sistema | Docker/Dashboard/API/Rutas/Salud/health\_endpoints.py6-8 |
| clients\_router | Exportaciones CRUD y PDF del cliente | Docker/Dashboard/API/Rutas/Clientes/clients\_endpoints.py13 |
| websites\_router | Gestión de sitios web y desencadenantes de auditoría | docker/dashboard/api/app.py41 |
| summary\_router | Estadísticas agregadas para widgets de panel | docker/dashboard/api/routes/summary/summary\_endpoints.py8-10 |
| runs\_router | Datos detallados de la ejecución de auditoría y diferencias de problemas | docker/dashboard/api/app.py43 |
| settings\_router | Configuración global de cron | Docker/Dashboard/API/Rutas/Ajustes/settings\_endpoints.py9-11 |

**Fuentes:**

*   [docker/dashboard/api/app.py1-45](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/app.py#L1-L45)
*   [docker/dashboard/api/routes/init.py1-17](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/__init__.py#L1-L17)

## Mapeo de la arquitectura del sistema

Los siguientes diagramas ilustran cómo los conceptos de API de alto nivel se corresponden con entidades específicas de código y cómo el backend se integra con la infraestructura compartida.

### Mapa de componentes del backend

Este diagrama une la estructura lógica de la API con los detalles de implementación `de FastAPI`.

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["Lógica compartida (compartida/)"]
        DB_REPO["shared.database.repositories.dashboard"]
        PDF_GEN["shared.utils.pdf_generator"]
        MODELS["shared.database.models"]
    fin
    subgrafo subGraph1 ["Controladores de Ruta (rutas/)"]
        C_END["clients_endpoints.py"]
        W_END["websites_endpoints.py"]
        R_END["runs_endpoints.py"]
        S_END["summary_endpoints.py"]
    fin
    subgrafo subGraph0 ["Aplicación FastAPI (app.py)"]
        APP["app = FastAPI()"]
        CORS["CORSMiddleware"]
    fin
    APP --> CORS
    APP --> C_END
    APP --> W_END
    APP --> R_END
    APP --> S_END
    C_END --> DB_REPO
    C_END --> PDF_GEN
    W_END --> DB_REPO
    R_END --> DB_REPO
    S_END --> DB_REPO
    DB_REPO --> MODELOS
```

**Fuentes:**

*   [docker/dashboard/api/app.py26-45](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/app.py#L26-L45)
*   [docker/dashboard/api/routes/clients/clients\_endpoints.py6-10](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/clients/clients_endpoints.py#L6-L10)
*   [docker/dashboard/api/routes/summary/summary\_endpoints.py3-10](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/summary/summary_endpoints.py#L3-L10)

### Flujo de datos: Gestión de clientes

Este diagrama muestra la relación entre los esquemas Pydantic, las rutas de API y el patrón de Repositorio.

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["Capa de persistencia"]
        REPO["repo.create_client"]
        SQL["SQLAlchemy (Modelo Cliente)"]
    fin
    subgrafo subGraph1 ["Capa API"]
        C_POST["create_client()"]
    fin
    subgrafo subGraph0 ["Capa de Solicitud"]
        JSON["JSON Payload"]
        CC_SCHEMA["ClienteCreate Schema"]
    fin
    JSON --> CC_SCHEMA
    CC_SCHEMA --> C_POST
    C_POST --> REPOSITORIO
    REPO --> SQL
```

**Fuentes:**

*   [docker/dashboard/api/schemas/clients.py4-10](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/schemas/clients.py#L4-L10)
*   [docker/dashboard/api/routes/clients/clients\_endpoints.py21-31](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/clients/clients_endpoints.py#L21-L31)

## Configuración CORS

La API está configurada para permitir solicitudes de origen cruzado desde el Dashboard Frontend. Utiliza una política permisiva para la simplicidad del desarrollo, permitiendo todos los orígenes (`*`) y métodos REST estándar.

[docker/dashboard/api/app.py32-37](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/app.py#L32-L37)

**Fuentes:**

*   [docker/dashboard/api/app.py32-37](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/app.py#L32-L37)

## Subsistemas detallados

La funcionalidad de la API del Panel se divide además en áreas especializadas cubiertas en las siguientes páginas hijas:

### REST API Endpoints

Documentación completa de todas las rutas disponibles, incluyendo:

*   **Clientes**: operaciones CRUD y el endpoint `/export` para informes PDF a nivel de cliente.
*   **Sitios web**: Gestión de URLs a auditar y el disparador manual para nuevas auditorías.
*   **Runs**: Acceso a los detalles `de AuditRun`, incluyendo listas `de AuditIssue` y puntuaciones modulares de secciones.
*   **Configuración**: Gestión de los intervalos `globales de cron_active` y `cron_inactive`.

Para más detalles, consulte [REST API Endpoints](/LuisVilRiv/comprobador-de-paginas-web/5.1-rest-api-endpoints).

### Generación de informes PDF

Explica la integración con `ReportLab` a través del módulo `shared.utils.pdf_generator`. Explica cómo `generate_client_report` y `generate_audit_pdf` transforman modelos de bases de datos en flujos binarios para `StreamingResponse`.

Para más detalles, consulte [Generación de Informes en PDF](/LuisVilRiv/comprobador-de-paginas-web/5.2-pdf-report-generation).

**Fuentes:**

*   [Docker/Dashboard/API/Rutas/Clientes/clients\_endpoints.py55-86](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/clients/clients_endpoints.py#L55-L86)
*   [Docker/Dashboard/API/Rutas/Ajustes/settings\_endpoints.py1-21](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/settings/settings_endpoints.py#L1-L21)

* * *

# REST-API-Endpoints

# REST API Endpoints

Archivos fuente relevantes

*   [docker/dashboard/api/app.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/app.py)
*   [Docker/dashboard/API/rutas/clientes/clients\_endpoints.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/clients/clients_endpoints.py)
*   [Docker/dashboard/API/rutas/ejecuciones/runs\_endpoints.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/runs/runs_endpoints.py)
*   [docker/dashboard/api/routes/summary/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/summary/__init__.py)
*   [Docker/dashboard/API/rutas/sitios web/websites\_endpoints.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/websites/websites_endpoints.py)
*   [Docker/Dashboard/API/Esquemas/settings.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/schemas/settings.py)
*   [Docker/Dashboard/API/Esquemas/websites.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/schemas/websites.py)
*   [Docker/tablero de control/frontend/JS/api.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/api.js)
*   [docker/dashboard/frontend/js/modals.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/modals.js)

La API de Dashboard es un servicio basado en FastAPI que actúa como centro de gestión central para la plataforma Web Auditor. Proporciona una interfaz RESTful integral para gestionar clientes, configurar sitios web, activar auditorías y recuperar informes detallados. La API sigue una estructura modular donde los routers se registran en el punto de entrada `principal app.py`\[docker/dashboard/api/app.py:17-24\].

## Arquitectura y enrutamiento de API

La aplicación utiliza un patrón estándar de router FastAPI para segregar las preocupaciones. Cada grupo de recursos (clientes, sitios web, ejecuciones, etc.) está gestionado por un módulo dedicado al router.

### Mapa de enrutamiento de la API del panel de control

Este diagrama asigna los puntos finales REST a sus respectivos archivos de router y a las funciones del repositorio que invocan.

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["Capa de Repositorio #91; shared.database.repositories.dashboard#93;"]
        CREPO["clientes repositorios"]
        WREPO["repositorio de sitios web"]
        RREPO["gestiona el repositorio"]
        SREPO["resumen repositorio"]
        STREPO["repositorio de configuración"]
    fin
    subgrafo subGraph1 ["Routers #91; rutas/#93;"]
        CR["clients_router"]
        WR["websites_router"]
        RR["runs_router"]
        SR["summary_router"]
        STR["settings_router"]
    fin
    subgrafo subGraph0 ["Aplicación FastAPI #91; app.py#93;"]
        APP["Instancia FastAPI"]
    fin
    APP --> CR
    APP --> WR
    APP --> RR
    APP --> SR
    APP --> STR
    CR -->|" /clientes"| CREPO
    WR -->|" /sitios web"| WREPO
    RR -->|" /corre"| RREPO
    SR -->|" /resumen"| SREPO
    STR -->|" /configuración"| STREPO
```

**Fuentes:**\[docker/dashboard/api/app.py:17-44\], \[docker/dashboard/api/routes/clients/clients\_endpoints.py:13\], \[docker/dashboard/api/routes/websites/websites\_endpoints.py:6\], \[docker/dashboard/api/routes/runs/runs\_endpoints.py:16\].

* * *

## Referencia de punto final

### 1\. Clientes (`/clientes`)

Se encarga de las operaciones CRUD para entidades clientes y de la generación consolidada de informes.

| Método | Camino | Descripción |
| --- | --- | --- |
| GET | /clients | Lista todos los clientes registrados. |
| POST | /clients | Crea un nuevo cliente. |
| PUT | /clients/{id} | Actualiza los datos del cliente (nombre, correo electrónico, etc.). |
| DELETE | /clients/{id} | Eliminar a un cliente. |
| GET | /clients/{id}/export | Genera un informe PDF consolidado para todos los sitios web de los clientes. |

*   **Implementación:** La función `export_client_report` utiliza `runs_repo.runs_history_for_pdf` para recopilar contexto histórico antes de llamar `a generate_client_report`\[docker/dashboard/api/routes/clients/clients\_endpoints.py:55-86\].
*   **Fuentes:**\[docker/dashboard/api/routes/clients/clients\_endpoints.py:16-56\], \[docker/dashboard/frontend/js/api.js:26-29\].

### 2\. Sitios web (`/sitios web`)

Gestiona las URLs objetivo a auditar, sus estrategias de scraping y los disparadores de auditoría.

| Método | Camino | Descripción | Parámetros de consulta |
| --- | --- | --- | --- |
| GET | /websites | Haz listas de sitios web. | client\_id (opcional) |
| POST | /websites | Regístrate en una nueva página web. | \- |
| GET | /sitios web/{id}/estado | Consulta el estado actual de una página web. | \- |
| GET | /websites/{id}/corre | Haz una lista del historial de auditorías de una página web. | límite, desplazamiento |
| POST | /sitios web/{id}/auditoría | Activa manualmente una auditoría inmediata. | \- |

*   **Disparador manual:** El `endpoint trigger_manual_audit` actualiza la `bandera de pending_audit` en la base de datos, que el `AuditScheduler` en el servicio scraper consulta para \[docker/dashboard/api/routes/websites/websites\_endpoints.py:71-82\].
*   **Fuentes:**\[docker/dashboard/api/routes/websites/websites\_endpoints.py:9-82\], \[docker/dashboard/api/schemas/websites.py:4-11\].

### 3\. Ejecuciones de auditoría (`/ejecuciones`)

Proporciona acceso profundo a resultados específicos de auditoría, incluyendo secciones modulares y cuestiones granulares.

| Método | Camino | Descripción | Parámetros de consulta |
| --- | --- | --- | --- |
| GET | /runs/{id} | Detalle completo de una auditoría concreta. | \- |
| GET | /runs/{id}/secciones | Puntuaciones de alto nivel (SEO, Seguridad, etc.). | \- |
| GET | /runs/{id}/problemas | Lista de problemas específicos detectados. | Categoría, gravedad |
| GET | /runs/{id}/export | Exporta un único informe de auditoría en formato PDF. | \- |

*   **Flujo de datos:** El `endpoint get_run_issues` permite filtrar por categoría (por ejemplo`, seguridad`, `SEO`) y severidad (por ejemplo, `crítico`, `alto`) \[docker/dashboard/api/routes/runs/runs/runs\_endpoints.py:35-44\].
*   **Exportación en PDF:** Utiliza `generate_audit_pdf` e incluye las últimas 4 partidas anteriores como contexto histórico \[docker/dashboard/api/routes/runs/runs\_endpoints.py:47-73\].
*   **Fuentes:**\[docker/dashboard/api/routes/runs/runs\_endpoints.py:19-73\], \[docker/dashboard/frontend/js/api.js:44-52\].

### 4\. Sistema y Ajustes

Configuración global y monitorización de la salud.

| Método | Camino | Descripción |
| --- | --- | --- |
| GET | /summary | Estadísticas agregadas (totales de sitios web, puntuaciones medias). |
| GET | /settings | Recuperar configuraciones globales de cron. |
| PUT | /settings | Actualizar los intervalos cron globales. |
| GET | /health | Chequeo de salud del servicio. |

*   **Fuentes:**\[docker/dashboard/api/app.py:39-44\], \[docker/dashboard/frontend/js/api.js:56-61\], \[docker/dashboard/api/schemas/settings.py:4-7\].

* * *

## Flujo de datos: Disparador manual de auditoría

Este diagrama ilustra la interacción entre el frontend, la API del Panel de Control y la base de datos cuando un usuario hace clic en "Ejecutar auditoría" en la interfaz.

```mermaid
Diagrama de secuencia
    interfazente de usuario como "Frontend [api.js]"
    participant API como "Dashboard API [websites_endpoints.py]"
    participante REPO como "Repositorio [repositorio de panel]"
    Participant DB como "PostgreSQL [Modelo de sitio web]"
    UI->>API: POST /websites/{id}/audit
    API->>REPO: trigger_manual_audit(website_id)
    REPO->>DB: ACTUALIZAR SITIOS WEB ESTABLECIDO pending_audit = VERDADERO DONDE id = website_id
    DB-->>REPOSITORIO: Fila actualizada
    REPO-->>API: { "pending_audit": cierto, ... }
    API-->>UI: 200 OK (Auditoría solicitada)
```

**Fuentes:**\[docker/dashboard/api/routes/websites/websites\_endpoints.py:71-82\], \[docker/dashboard/frontend/js/api.js:38\].

* * *

## Manejo de errores

La API utiliza códigos de estado HTTP estándar y esquemas validados por Pydantic para garantizar la integridad de los datos.

*   **400 malas peticiones:** Se devuelven por errores de validación (por ejemplo, URLs duplicadas) o cargas útiles de actualización vacías \[docker/dashboard/api/routes/websites/websites\_endpoints.py:44-46\]\[docker/dashboard/api/routes/clients/clients\_endpoints.py:32-33\].
*   **404 No encontrados:** Se devuelve cuando no existe un `client_id`, `website_id` o `run_id` solicitado en la base de datos \[docker/dashboard/api/routes/runs/runs\_endpoints.py:23-24\]\[docker/dashboard/api/routes/websites/websites\_endpoints.py:17-18\].
*   **CORS:** Configurado para permitir solicitudes de origen cruzado desde el frontend, soportando métodos `GET`, `POST`, `PUT` y DELETE \[docker/dashboard/api/app.py:32-37\].

**Fuentes:**\[docker/dashboard/api/app.py:32-37\], \[docker/dashboard/api/routes/websites/websites\_endpoints.py:42-46\], \[docker/dashboard/api/routes/clients/clients\_endpoints.py:32-33\].

* * *

# Generación de informes PDF

# Generación de informes PDF

Archivos fuente relevantes

*   [docker/dashboard/api/app.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/app.py)
*   [Docker/dashboard/API/rutas/clientes/clients\_endpoints.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/clients/clients_endpoints.py)
*   [compartido/utiles/pdf\_generator.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/utils/pdf_generator.py)

El sistema de Generación de Informes PDF proporciona documentación profesional y automatizada de auditoría tanto para las gestiones individuales de sitios web como para carteras consolidadas de clientes. Transforma datos complejos de auditoría —incluyendo puntuaciones, métricas técnicas, tendencias históricas y listas de incidencias— en flujos estructurados en binarios PDF.

## Visión general y flujo de datos

El proceso de generación sigue un patrón "Datos a Flujo". El sistema obtiene los resultados de auditoría de la base de datos PostgreSQL, procesa datos históricos para análisis de tendencias, genera gráficos visuales usando `matplotlib` y ensambla el documento final usando `Reportlab`.

### Diagrama de arquitectura del sistema

El siguiente diagrama ilustra cómo la API del Panel de Control se coordina con la base de datos y la utilidad PDF para servir informes.

**Flujo de generación de PDF**

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["Espacio de base de datos"]
        DB_RUN["Tabla de AuditRun"]
        DB_SEC["Tabla de AuditRunSection"]
        DB_ISS["Tabla de Emisión de Auditoría"]
        RH_PDF["runs_history_for_pdf()"]
    fin
    subgrafo subGraph1 ["Lógica y Espacio de Utilidad"]
        GAP["generate_audit_pdf()"]
        GCR["generate_client_report()"]
        BSSC["_build_single_section_chart()"]
    fin
    subgrafo subGraph0 ["Espacio API del Panel de Control"]
        R_RUN["/runs/{run_id}/export"]
        R_CLI["/clients/{client_id}/export"]
        SR["StreamingResponse"]
    fin
    R_RUN -->|" Busca Carrera"| DB_RUN
    R_RUN -->|" Llamadas"| GAP
    R_CLI -->|" Llamadas"| RH_PDF
    RH_PDF -->|" Agregados"| DB_RUN
    R_CLI -->|" Llamadas"| GCR
    GAP -->|" Usos"| BSSC
    GCR -->|" Usos"| GAP
    GAP -->|" Retorna BytesIO"| SR
    GCR -->|" Retorna BytesIO"| SR
```

**Fuentes:**[docker/dashboard/api/routes/clients/clients\_endpoints.py55-86](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/clients/clients_endpoints.py#L55-L86)[compartido/utils/pdf\_generator.py77-84](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/utils/pdf_generator.py#L77-L84)

## Detalles principales de la implementación

### Utilidades de generación de PDF

El sistema depende de `compartidos/utils/pdf_generator.py` para manejar el trabajo pesado del ensamblaje de documentos.

*   **`generate_audit_pdf(run, web, historial)`**: La función principal para los informes de una sola ejecución. Construye un `SimpleDocPlantilla` y lo llena con elementos `de ornitorrinco` como Tablas, Párrafos e Imágenes [compartidas/utils/pdf\_generator.py77-84](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/utils/pdf_generator.py#L77-L84)
*   **`generate_client_report(client_name, websites_data)`**: Un orquestador de alto nivel que itera por todos los sitios web asociados a un cliente, generando un informe [consolidado de varias páginas compartido/utils/pdf\_generator.py10](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/utils/pdf_generator.py#L10-L10)
*   **`_build_single_section_chart(k, etiqueta, serie, i):`** Utiliza `matplotlib` con el backend `de Agg` para generar líneas de tendencia PNG para métricas de auditoría específicas (por ejemplo, puntuación de tendencias a lo largo del tiempo) [compartidas/utils/pdf\_generator.py25-72](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/utils/pdf_generator.py#L25-L72)

### Contexto histórico y consultas

Para aportar valor más allá de un único momento en el tiempo, los informes incluyen tendencias históricas.

*   **`runs_history_for_pdf`**: Esta función de repositorio (que se encuentra en `runs_repo`) se utiliza para obtener las últimas 5-10 ejecuciones de un sitio web específico para llenar los gráficos de tendencias [docker/dashboard/api/routes/clients/clients\_endpoints.py76](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/clients/clients_endpoints.py#L76-L76)
*   **Estructura de datos**: El historial se presenta como una lista de diccionarios que contienen etiquetas (fechas) y puntos de datos (puntuaciones/conteos) [compartidos/utils/pdf\_generator.py32-35](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/utils/pdf_generator.py#L32-L35)

## Integración API y streaming

La API del Panel expone estos informes a través de endpoints `GET`. En lugar de guardar archivos en disco, la API genera el PDF en memoria y lo transmite directamente al cliente.

### Mapeo de puntos finales

| Punto final | Función | Lógica de repositorios |
| --- | --- | --- |
| /clients/{id}/export | export\_client\_report | Obtiene el cliente, todos los sitios web y su runs\_history\_for\_pdfdocker/dashboard/api/routes/clients/clients\_endpoints.py55-76 |
| /runs/{id}/export | export\_run\_pdf | Obtiene un AuditRun específico y sus registros asociados de AuditIssue. |

### El patrón StreamingResponse

La API utiliza `StreamingResponse` de FastAPI para gestionar la salida binaria de `io. Buffers de BytesIO`. Esto garantiza una baja sobrecarga de memoria y disparadores inmediatos de descarga en el navegador.

```
# Ejemplo de implementación de la base de código
pdf = generate_client_report(client.name o "Cliente", websites_data)
nombre de archivo = f"client_{client_id}_report.pdf"
return StreamingResponse(
    pdf, 
    media_type="aplicación/pdf", 
    encabezados={"Content-Disposition": f"attachment; nombre de archivo={nombre de archivo}"}
)
```

**Fuentes:**[docker/dashboard/api/routes/clients/clients\_endpoints.py84-86](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/clients/clients_endpoints.py#L84-L86)

## Componentes visuales y estilo

Los informes utilizan un lenguaje de diseño "Premium" con paletas de colores y diseños específicos.

*   **Paleta de colores**: Se utiliza un `_BAR_COLORS` constante (Índigo, Cian, Ámbar, Esmeralda, Rosa) para los gráficos y así asegurar la consistencia [compartido/utils/pdf\_generator.py22](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/utils/pdf_generator.py#L22-L22)
*   **Tabla de métricas técnicas**: Tabla resumen que incluye el recuento de palabras, etiquetas H1, recuentos de imágenes y tiempos [de respuesta compartidos/utils/pdf\_generator.py142-159](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/utils/pdf_generator.py#L142-L159)
*   **Categorización de Incidencias**: Los problemas se agrupan por gravedad y sección, con indicadores visuales claros para el estado "Crítico" frente a "Advertencia".

**Entidad de código para informar el mapeo de secciones**

```mermaid
Diagrama de clases.
    class AuditRun {
        +uuid id
        +puntuación flotante
        +fecha started_at
        +int word_count
    }
    clase AuditRunSection {
        +string section_name
        Estado de +cadena
    }
    Clase PDF_Report {
        +HeaderTable(AuditRun)
        +TrendChart (Historia)
        +MétricasTable(AuditRun)
        +ProblemasDetallados(AuditRunSection)
    }
    AuditRun --> AuditRunSection : proporciona datos para
    AuditRun --> PDF_Report : se transforma en
```

**Fuentes:**[compartido/utils/pdf\_generator.py102-116](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/utils/pdf_generator.py#L102-L116)[compartido/utils/pdf\_generator.py141-159](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/utils/pdf_generator.py#L141-L159)

* * *

# Capa de bases de datos

# Capa de base de datos

Archivos fuente relevantes

*   [Docker/raspador/requirements.txt](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/requirements.txt)
*   [compartido/auditor/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/__init__.py)
*   [compartido/base de datos/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/__init__.py)
*   [compartido/base de datos/connection.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/connection.py)
*   [compartido/base de datos/models.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py)

La capa de base de datos proporciona un mecanismo centralizado de persistencia para toda la plataforma Web Auditor. Se implementa como un paquete compartido (`compartido/base de datos`) que utilizan tanto los servicios Scraper como Dashboard para garantizar la coherencia de los datos. La arquitectura se basa en **PostgreSQL** como motor principal de almacenamiento, **SQLAlchemy 2.0** como Object-Relational Mapper (ORM), y un **patrón de repositorio** para abstraer la lógica de acceso a datos de la lógica de negocio.

### Gestión de conexiones

Las conexiones a bases de datos se gestionan mediante una configuración centralizada de motor en `compartida/base de datos/connection.py`. El sistema utiliza el controlador `psycopg2` [docker/scraper/requirements.txt9](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/requirements.txt#L9-L9) para comunicarse con PostgreSQL.

El gestor de contexto `get_db()` es la forma principal en que los servicios adquieren una sesión de base de datos, asegurando que las conexiones se cierren correctamente después de usar [shared/database/connection.py28-35](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/connection.py#L28-L35) La configuración está impulsada por variables de entorno como `DB_HOST`, `DB_PORT` y `DB_NAME`[shared/database/connection.py13-17](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/connection.py#L13-L17)

**Flujo de Conexión a la Base de Datos**

```mermaid
diagrama de flujo LR
    subgrafo Infraestructura
        POSTGRES["Instancia PostgreSQL"]
    fin
    subgrafo subGraph0 ["Espacio de Entidades de Código"]
        ENV["Variables de entorno"]
        MOTOR["SQLAlchemy Engine"]
        SESIÓN["SessionLocal (creador de sesión)"]
        GET_DB["get_db() Gestor de contexto"]
    fin
    ENV -->|" defines"| MOTOR
    MOTOR -->|" vincula"| SESIÓN
    SESIÓN -->|" cede"| GET_DB
    GET_DB -->|" conecta"| POSTGRES
```

Fuentes: [compartido/database/connection.py13-35](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/connection.py#L13-L35)[compartido/database/**init.py11**](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/__init__.py#L11-L11)

* * *

### Modelos de datos y jerarquía

La base de código utiliza la base declarativa de SQLAlchemy para definir un esquema relacional centrado en los clientes y sus sitios web monitorizados. La jerarquía sigue una estricta estructura de relaciones de uno a muchos para rastrear los datos históricos de auditoría.

*   **Clientes y sitios web**: `Un cliente` puede poseer múltiples registros `de sitios web` [compartidos/database/models.py38](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L38-L38)
*   **Granularidad de la auditoría**: El sistema almacena las auditorías en tres niveles de detalle:

1.  **`AuditRun`**: Datos agregados para una única ejecución (puntuación, estado, metadatos) [compartido/base de datos/modelos.py59-92](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L59-L92)
2.  **`AuditRunSection`**: Resultados modulares para categorías específicas de comprobación (SEO, Seguridad, etc.) [compartido/database/models.py99-111](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L99-L111)
3.  **`AuditoriaIssue`**: Hallazgos detallados incluyendo números de línea y [pistas compartidas/database/models.py116-125](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L116-L125)

*   **Configuración global**: Un almacén clave de valor sencillo usando `JSONB` para configuraciones a nivel de plataforma como cron schedules [globales compartidos/database/models.py130-135](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L130-L135)

Para un análisis profundo de campos, restricciones y estructuras JSONB, **[véase Esquema de Base de Datos y Modelos ORM](/LuisVilRiv/comprobador-de-paginas-web/6.1-database-schema-and-orm-models)**.

**Resumen de la relación de la entidad**

Fuentes: [shared/database/models.py25-136](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L25-L136)

* * *

### Patrón de repositorio

En lugar de realizar consultas en bruto o llamadas ORM directas en las rutas API o la lógica de scraping, el proyecto implementa un **Patrón de Repositorio** ubicado en `compartidos/bases de datos/repositorios`/. Esto actúa como una fachada que proporciona una API limpia para las operaciones de datos.

Los repositorios están especializados por dominio:

*   **Repositorios Scraper**: Centrados en recuperar tareas pendientes (`get_pending_audit_websites`) y persistir resultados de auditoría compleja (`save_audit_run`).
*   **Repositorios de Paneles**: Centrados en operaciones CRUD para la gestión de UI y estadísticas agregadas para la vista resumen.

Para detalles sobre las funciones específicas disponibles en cada repositorio y cómo asignan modelos internos a respuestas de diccionario, véase **[Patrón de Repositorio y Acceso a Datos](/LuisVilRiv/comprobador-de-paginas-web/6.2-repository-pattern-and-data-access)**.

**Estrategia de Acceso a Datos**

```mermaid
diagrama de flujo TD
    Subgrafo shared_database_ ["compartido/base de datos/"]
        MODELOS["SQLAlchemy Models"]
        CONN["Connection (Sesión)"]
    fin
    Subgrafo shared_database_repositories_ ["Compartido/Base de datos/Repositorios/"]
        REPOS["Fachada de Repositorio"]
    fin
    subgrafo Consumidores
        API["API del Panel de Control"]
        RASPADOR["Servicio de raspador"]
    fin
    API --> REPOS
    SCRAPER --> REPOS
    REPOS --> MODELOS
    REPOS --> CONN
```

Fuentes: [compartido/database/init.py21-32](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/__init__.py#L21-L32) [compartido/database/repositories/](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/) (referencia de directorio)

* * *

### Resumen de los componentes

| Componente | Responsabilidad | Archivos clave |
| --- | --- | --- |
| Conexión | Inicialización del motor y gestión del ciclo de vida de la sesión. | compartido/base de datos/connection.py |
| Modelos ORM | Definición de tablas, relaciones y tipos específicos de PostgreSQL (UUID, JSONB). | compartido/base de datos/models.py |
| Repositorios | Abstracción de acceso a datos para servicios de Scraper y Dashboard. | compartido/base de datos/repositorios/ |
| Migraciones de esquemas | Configuración inicial de SQL y actualizaciones posteriores del esquema. | 01\_schema.sql, 02\_migrate\_optional\_client.sql |

Fuentes: [shared/database/init.py1-33](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/__init__.py#L1-L33)

* * *

# Esquema-&-ORM-Modelos de bases de datos

# Esquema de bases de datos y modelos ORM

Archivos fuente relevantes

*   [docker/dashboard/api/main.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/main.py)
*   [docker/db-init/01\_schema.sql](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql)
*   [docker/db-init/02\_migrate\_optional\_client.sql](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/02_migrate_optional_client.sql)
*   [Docker/raspador/entrypoint.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/entrypoint.py)
*   [compartido/base de datos/models.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py)

Esta página documenta el esquema PostgreSQL y la implementación SQLAlchemy ORM para la plataforma Web Auditor. La base de datos sirve como punto central de sincronización de estados entre la **API del Panel** de Control y el **Scraper Engine**.

## Resumen del esquema

La base de datos utiliza PostgreSQL con la extensión `pgcrypto` para gestionar la generación `de UUID` de forma [nativa docker/db-init/01\_schema.sql7-8](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql#L7-L8). La arquitectura sigue un modelo relacional con datos de gran volumen almacenados en campos `JSONB` para mayor flexibilidad.

### Decisiones arquitectónicas clave

*   **Claves primarias UUID**: Todas las tablas utilizan UUIDs (v4) para evitar la enumeración de ID y facilitar la sincronización distribuida [futura de shared/database/models.py28-62](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L28-L62)
*   **Reglas en cascada**: Eliminar un `sitio web` provoca una eliminación en cascada de todos sus registros `AuditRun`. Sin embargo, eliminar un `cliente` establece el `client_id` en `el sitio web` en `NULL` para preservar los datos [históricos docker/db-init/02\_migrate\_optional\_client.sql11-20](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/02_migrate_optional_client.sql#L11-L20)
*   **Integración JSONB**: Usada para configuración (crons) y detalles de auditoría complejos que no requieren un indexado relacional [estricto shared/database/models.py34-91](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L34-L91)

### Mapeo de Relación Entidad

El siguiente diagrama conecta el Espacio de Lenguaje Natural (conceptos de negocio) con el Espacio de Entidades de Código (clases SQLAlchemy).

**Mapeo de entidades: lógica de negocio a ORM**

```mermaid
diagrama de flujo LR
    subgrafo subGraph1 ["Espacio de Entidad de Código (compartido/base de datos/models.py)"]
        Cliente["clase Cliente"]
        Sitio web["página web de la clase"]
        AuditRun["class AuditRun"]
        AuditRunSection["clase AuditRunSection"]
        AuditIssue["class AuditIssue"]
    fin
    subgrafo subGraph0 ["Espacio de lenguaje natural"]
        UsuarioCliente["Cliente/Empresa"]
        TargetSite["Sitio web/URL"]
        Ejecución["Ejecución de Auditoría"]
        ResultadMódulo["Resultado de la sección"]
        Hallazgo["Problema/Hallazgo"]
    fin
    ClientUserClient -.-> Cliente
    Sitio web -.-> TargetSite
    Ejecución -.-> AuditRun
    ResultaMódulo -.-> AuditRunSection
    Encontrar -.-> AuditoríaProblema
    Cliente -->|" 1:N (back_populates='cliente')"| Sitio web
    Sitio web -->|" 1:N (back_populates='sitio web')"| AuditRun
    AuditRun -->|" 1:N (back_populates='correr')"| AuditRunSection
    AuditRun -->|" 1:N (back_populates='correr')"| AuditIssue
```

Fuentes: [shared/database/models.py25-128](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L25-L128)[docker/db-init/01\_schema.sql13-142](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql#L13-L142)

* * *

## Modelos de datos

### 1\. Cliente y Sitio Web (Capa de Gestión)

La `tabla de cliente` almacena metadatos organizativos. La `tabla de Sitio Web` rastrea las URLs objetivo y su configuración de scraping.

| Tabla | Modelo Class | Campos clave | Propósito |
| --- | --- | --- | --- |
| Clientes | Cliente | Nombre, custom\_cron, correo electrónico | Grupos web para reportar shared/database/models.py25-39 |
| Sitios web | Sitio web | URL, estrategia, pending\_audit | Define qué extraer y cómo shared/database/models.py41-57 |

*   **`Estrategia`**: Puede ser `selenium`, `beautifulsoup` o `auto`[docker/db-init/01\_schema.sql35-36](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql#L35-L36)
*   **`pending_audit`**: Una bandera booleana utilizada por `el AuditScheduler` para activar ejecuciones manuales [inmediatas docker/scraper/entrypoint.py32-44](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/entrypoint.py#L32-L44)

### 2\. Granularidad de auditoría en tres niveles

El sistema almacena los resultados de auditoría en tres niveles de detalle distintos para apoyar tanto paneles de alto nivel como informes técnicos profundos.

**Flujo de datos: Granularidad de auditoría**

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["Nivel 3: Granular (AuditIssue)"]
        IA["TablaEjecuciónAuditoría"]
        Sev["gravedad (crítica... info)"]
        Línea["line_no / line_hint"]
    fin
    subgrafo subGraph1 ["Nivel 2: Modular (AuditRunSection)"]
        ARS["Tabla de Secciones AuditRun"]
        SKey["section_key (por ejemplo, 'imágenes')"]
        Aprobado["aprobado: bool"]
    fin
    subgrafo subGraph0 ["Nivel 1: Agregado (AuditRun)"]
        AR["AuditRun Table"]
        Puntuación["puntuación: 0-100"]
        Cuentas["issue_counts (SEO, Seguridad, etc)"]
    fin
    AR -->|" agregados"| ARS
    ARS -->|" contiene"| IA
```

Fuentes: [shared/database/models.py59-128](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L59-L128)[docker/db-init/01\_schema.sql54-142](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql#L54-L142)

#### Nivel 1: AuditRun (Agregado)

Almacena el resultado final de la cadena `de QualityAuditor`.

*   **Métricas de rendimiento**: `response_time_ms`, `status_code` `word_count`[shared/database/models.py76-78](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L76-L78)
*   **Contadores de resumen**: `security_issue_count`, `seo_issue_count`, etc., para renderizado rápido de [paneles compartido/database/models.py83-90](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L83-L90)
*   **Persistencia**: `report_json` (salida bruta) y `report_text` (resumen legible por humanos) [compartido/database/models.py91-92](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L91-L92)

#### Nivel 2: AuditRunSection (Modular)

Representa un módulo de comprobación específico (por ejemplo, "Cabeceras de Seguridad").

*   **`: Puede estar`** Estado`advertencia`bien`fallido`, `, o` [en docker/base de datos/01\_schema.sql109](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql#L109-L109)
*   **`details_json`**: Almacena metadatos específicos de módulo (por ejemplo, una lista de cabeceras faltantes) [compartido/database/models.py111](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L111-L111)

#### Nivel 3: AuditoriaProblema (Granular)

El nivel más detallado, documentando fallos específicos.

*   **`Gravedad`**: Las restricciones incluyen `crítico`, `alto`, `medio`, `bajo`, `info` y `ok`[docker/db-init/01\_schema.sql131-132](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql#L131-L132)
*   **`line_hint`**: Fragmento de HTML o código donde se detectó el problema [compartido/database/models.py125](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L125-L125)

* * *

## Entornos globales

La tabla `global_settings` utiliza una estructura simple de pares clave-valor donde el valor es un objeto [JSONB compartido/database/models.py130-136](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py#L130-L136). Esto se usa principalmente para la configuración global de cron que dicta el comportamiento `de AuditScheduler` cuando no se define ningún cron específico de sitio o cliente.

## Indexación y rendimiento

El esquema incluye varios índices para optimizar las consultas en el panel de control:

*   **`idx_websites_pending_audit`**: Un índice parcial en `pending_audit = TRUE` para permitir que el scraper encuentre rápidamente peticiones [manuales docker/db-init/01\_schema.sql47](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql#L47-L47)
*   **`idx_runs_started`**: Un índice descendente en `started_at` para acelerar las consultas "Últimas ejecuciones" [docker/db-init/01\_schema.sql94](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql#L94-L94)
*   **`idx_issues_severity`**: Optimiza el filtrado de problemas críticos en el [docker de la interfaz/base de datos/01\_schema.sql140](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql#L140-L140)

Fuentes: [docker/db-init/01\_schema.sql45-140](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql#L45-L140)

* * *

# Acceso a Patrón-y-Datos a Repositorio

# Patrón de repositorio y acceso a datos

Archivos fuente relevantes

*   [compartido/auditor/auditor\_modules/helpers.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py)
*   [compartido/auditor/cheques/links.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/links.py)
*   [compartido/base de datos/repositorios/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/__init__.py)
*   [compartido/base de datos/repositorios/panel de control/clients.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/clients.py)
*   [compartido/base de datos/repositorios/panel/helpers.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/helpers.py)
*   [compartido/base de datos/repositorios/panel/runs.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/runs.py)
*   [compartido/base de datos/repositorios/panel/settings.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/settings.py)
*   [compartido/base de datos/repositorios/panel de control/summary.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/summary.py)
*   [compartido/base de datos/repositorios/panel/websites.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/websites.py)
*   [compartido/base de datos/repositorios/scraper/mappers.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/mappers.py)
*   [compartido/base de datos/repositorios/scraper/websites.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/websites.py)

La plataforma Web Auditor emplea el **Patrón de Repositorio** para desacoplar la lógica de negocio (Scraper Engine y API Dashboard) de la base de datos SQLAlchemy ORM y PostgreSQL. Esta capa actúa como una fachada, proporcionando métodos especializados de acceso a datos para diferentes requisitos de dominio: el **Repositorio Scraper** para persistencia de auditorías de alto rendimiento y el **Repositorio Dashboard** para consultas y reportes de gestión complejos.

## Arquitectura y flujo de datos

La capa de repositorio se divide en dos espacios de nombres principales bajo `shared/database/repositories`[shared/database/repositories/init.py1-12](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/__init__.py#L1-L12)

1.  **Repositorio de Dashboard**: Enfocado en operaciones CRUD para clientes/sitios web, cálculo de estadísticas agregadas para la interfaz de usuario y obtención de datos históricos para la generación de PDFs.
2.  **Repositorio Scraper**: Centrado en seleccionar sitios web para la cola de auditoría, mapear los resultados brutos de auditoría al esquema relacional y ejecutar auditorías persistentes.

### Mapa de componentes del repositorio

El siguiente diagrama mapea los componentes lógicos de acceso a datos a sus respectivas entidades de código y archivos.

**Mapa de la Fachada del Repositorio**

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["Dominio Scraper"]
        SCRP_W["websites.py"]
        get_active_websites["get_active_websites()"]
        get_pending_audit["get_pending_audit_websites()"]
        SCRP_M["mappers.py"]
        build_sections["build_audit_sections()"]
    fin
    subgrafo subGraph1 ["Dominio del Panel de Control"]
        DASH_W["websites.py"]
        list_websites["list_websites()"]
        DASH_R["runs.py"]
        website_runs["website_runs()"]
        DASH_S["summary.py"]
        global_summary["global_summary()"]
    fin
    subgrafo subGraph0 ["Fachada de acceso a datos"]
        REPOS["compartido/base de datos/repositorios"]
        GUION["dashboard/"]
        SCRP["raspador/"]
    fin
    DASH_W --> list_websites
    DASH_R --> website_runs
    DASH_S --> global_summary
    SCRP_W --> get_active_websites
    SCRP_W --> get_pending_audit
    SCRP_M --> build_sections
    REPOS --> GUION
    REPOS --> SCRP
    GUION --> DASH_W
    GUION --> DASH_R
    GUION --> DASH_S
    SCRP --> SCRP_W
    SCRP --> SCRP_M
```

Fuentes: [compartido/database/repositories/init.py1-12](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/__init__.py#L1-L12) [compartido/database/repositories/dashboard/websites.py1-12](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/websites.py#L1-L12)[compartido/database/repositories/scraper/websites.py1-10](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/websites.py#L1-L10)

## Repositorios de paneles

Los repositorios de paneles se encargan del trabajo pesado para el frontend de React, incluyendo uniones complejas para resolver la lógica de planificación y el historial de auditorías.

### Gestión y programación de sitios web

La función `list_websites` en `el panel de control/websites.py` es la consulta más compleja del sistema. Realiza un `outerjoin` con `AuditRun` para recuperar los resultados más recientes de la auditoría mientras resuelve simultáneamente la **lógica de precedencia de Cron**:

1.  **Cron personalizado a nivel web**.
2.  **Cron personalizado a nivel de cliente** (si la web no tiene ninguno).
3.  Cron predeterminado **a nivel global** (basado `en el estado` activo del sitio) [compartido/database/repositories/dashboard/websites.py65-78](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/websites.py#L65-L78)

El `ayudante de cron_next_timestamp` se utiliza para calcular el campo `next_audit` analizando estas expresiones cron usando la biblioteca [croniter shared/database/repositories/dashboard/helpers.py11-19](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/helpers.py#L11-L19)

### Resumen y Análisis

La función `global_summary` en `el panel de control/summary.py` proporciona una instantánea de todo el sistema. Utiliza `SQLAlchemy func.count` y subconsultas para calcular:

*   Conteo total y activo de sitios [web compartidos/base de datos/repositorios/dashboard/summary.py11-15](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/summary.py#L11-L15)
*   Recuento de auditorías "Excelentes" (basadas en puntuaciones) [compartidas/bases de datos/repositorios/panel/summary.py50-51](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/summary.py#L50-L51)
*   Recuento de sitios web "Bloqueados" donde la `bandera de release_blocked` es [verdadera compartido/base de datos/repositorios/panel/summary.py52-53](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/summary.py#L52-L53)

### Historial de Carreras y Soporte en PDF

Para el motor de informes PDF, `runs_history_for_pdf` recupera las últimas $N$ ejecuciones exitosas de un sitio web específico, desegregando los recuentos de incidencias por `section_key` (por ejemplo, SEO, Seguridad) para proporcionar datos [históricos de tendencias compartidas/base de datos/repositorios/panel/runs.py87-121](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/runs.py#L87-L121)

Fuentes: [compartido/base de datos/repositorios/dashboard/websites.py12-98](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/websites.py#L12-L98)[compartido/base de datos/repositorios/dashboard/summary.py9-67](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/summary.py#L9-L67)[compartido/database/repositories/dashboard/runs.py87-121](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/runs.py#L87-L121)[compartido/database/repositories/dashboard/helpers.py11-19](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/helpers.py#L11-L19)

## Repositorios de Raspadores

Los repositorios de scraper están diseñados para que `el AuditScheduler` y `el AuditService` interactúen con la base de datos durante el ciclo de vida de la auditoría.

### Selección de la Cola de Auditoría

El raspador utiliza tres funciones principales para determinar qué emplazamientos auditar:

*   `get_active_websites()`: Devuelve todos los sitios activos que no están marcados actualmente como [compartidos/bases de datos/repositorios/scraper/websites.py10-26](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/websites.py#L10-L26)
*   `get_pending_audit_websites()`: Sitios de devoluciones donde se activó una auditoría manual a través del panel de control (donde `pending_audit == Cierto`) [compartido/base de datos/repositorios/scraper/websites.py46-56](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/websites.py#L46-L56)
*   `clear_pending_audit(website_id)`: Reinicia la bandera de activación manual una vez que comienza la auditoría [shared/database/repositories/scraper/websites.py58-65](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/websites.py#L58-L65)

### Mapeo de resultados y clasificación de gravedad

Antes de guardar una auditoría, el módulo `mappers.py` transforma el informe JSON en bruto en entidades estructuradas de base de datos:

*   **`classify_severity(mensaje)`**: Asigna un nivel de gravedad (`crítico`, `alto`, `medio`, `bajo`) a un problema basado en la coincidencia de palabras clave (por ejemplo, "panel admin" o "enlace roto" se marcan como `críticos`) [compartidos/bases de datos/repositorios/scraper/mappers.py6-20](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/mappers.py#L6-L20)
*   **`build_audit_sections(reporte, scrape_metadata)`**: Mapea las 8 categorías de auditoría (Seguridad, SEO, Contenido, etc.) en `los registros de AuditRunSection`, calculando el estado `y issue_count aprobados` para cada [compartido/base de datos/repositorios/scraper/mappers.py22-70](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/mappers.py#L22-L70)

**Flujo de persistencia de resultados de auditoría**

```mermaid
Diagrama de secuencia
    participante S como AuditService
    participante M como raspador/mappers.py
    participante R como raspador/runs.py
    Participant DB como PostgreSQL
    S->>M: build_audit_sections(report_dict)
    M-->>S: Lista[SectionData]
    S->>M: classify_severity(issue_msg)
    M-->>S: severity_string
    S->>R: save_audit_run(website_id, datos)
    R->>DB: INSERTAR EN audit_runs
    R->>DB: INSERTAR EN audit_run_sections
    R->>DB: INSERTAR EN audit_issues
    DB-->>R: COMMIT
    R-->>S: run_id
```

Fuentes: [compartido/base de datos/repositorios/scraper/websites.py10-65](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/websites.py#L10-L65)[compartido/base de datos/repositorios/scraper/mappers.py6-70](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/mappers.py#L6-L70)

## Funciones y utilidades clave

### Transformación de datos

*   **`row_to_dict(row)`**: Una utilidad en `dashboard/helpers.py` que convierte objetos `SQLAlchemy Row` o `RowMapping` en diccionarios estándar de Python, facilitando la serialización JSON para la API [shared/database/repositories/dashboard/helpers.py7-9](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/helpers.py#L7-L9)
*   **`safe_int(valor)`**: Garantiza una conversión robusta de cadenas numéricas a enteros durante la ingestión de datos [compartidos/base de datos/repositorios/scraper/mappers.py72-76](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/mappers.py#L72-L76)

### Lógica compartida

*   **`is_banned_url(url)`**: Usado en repositorios y en el rastreador de enlaces para evitar auditar hosts restringidos definidos en `la configuración. AUDIT_BANNED_HOSTS`[compartido/auditor/auditor\_modules/helpers.py12-32](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py#L12-L32)
*   **`check_url(sesión, url)`**: Una utilidad compartida para realizar solicitudes HTTP con medición de rendimiento y recuperación de código [de estado compartido/auditor/auditor\_modules/helpers.py55-70](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py#L55-L70)

Fuentes: [compartido/base de datos/repositorios/dashboard/helpers.py7-9](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/dashboard/helpers.py#L7-L9)[compartido/database/repositories/scraper/mappers.py72-76](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/repositories/scraper/mappers.py#L72-L76)[compartido/auditor/auditor\_modules/helpers.py12-70](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/helpers.py#L12-L70)

* * *

# Panel de control-Interfaz

# Interfaz de panel

Archivos fuente relevantes

*   [docker/dashboard/frontend/app.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js)
*   [docker/dashboard/frontend/index.html](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/index.html)
*   [Docker/tablero de control/frontend/styles.css](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css)
*   [Docker/Panel de control/server.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/server.js)

El **Dashboard Frontend** es una aplicación React moderna y responsiva que proporciona una interfaz centralizada para gestionar clientes, sitios web y resultados de auditoría. Está servido por un servidor Node.js/Express que actúa como un proxy inverso para la API del Dashboard, asegurando una experiencia de desarrollo y despliegue fluida sin complicaciones con el CORS.

## Resumen de la arquitectura

El frontend se construye utilizando una arquitectura basada en componentes con React, utilizando módulos ES a través `de esm.sh` para evitar pasos [complejos de compilación: docker/dashboard/frontend/app.js4-5](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L4-L5). El sistema está diseñado alrededor de un modelo de aplicación de una sola página (SPA) donde el estado se gestiona principalmente mediante ganchos React dentro del componente `raíz de la App`.

### Mapa de componentes frontales

El siguiente diagrama ilustra la relación entre los componentes de la interfaz y los módulos API y lógico subyacentes.

**Mapeo de componente de interfaz a entidad de código**

**Fuentes:**[docker/dashboard/frontend/app.js7-25](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L7-L25)[docker/dashboard/server.js13-20](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/server.js#L13-L20)

## Servidor Node.js/Express

El frontend está servido por un [servidor Express docker/dashboard/server.js6](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/server.js#L6-L6) que desempeña tres funciones críticas:

1.  **Alojamiento estático**: Sirve al `directorio frontend`, incluyendo `módulos index.html`, `styles.css` y JavaScript [docker/dashboard/server.js30](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/server.js#L30-L30)
2.  **API Proxy**: Utiliza `http-proxy-middleware` para reenviar solicitudes desde `/api/*` al `servicio dashboard-api` [docker/dashboard/server.js13-20](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/server.js#L13-L20) Este destino es configurable mediante `API_BASE_URL`[docker/dashboard/server.js11](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/server.js#L11-L11)
3.  **Control de caché**: Desactiva la caché del navegador para asegurar que las actualizaciones de la interfaz de usuario o CSS se reflejen inmediatamente durante el desarrollo y despliegue [docker/dashboard/server.js23-28](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/server.js#L23-L28)

**Fuentes:**[docker/dashboard/server.js1-38](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/server.js#L1-L38)

## Características del sistema

### Estado y Encuestas

La aplicación mantiene el estado global para `estadísticas resumenes`, `sitios web`, `clientes` y `configuraciones`[docker/dashboard/frontend/app.js30-39](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L30-L39). Implementa un mecanismo inteligente de sondeo: cuando se detecta una auditoría como "en ejecución", el frontend actualiza los datos cada 3 segundos para proporcionar actualizaciones de estado en tiempo real [docker/dashboard/frontend/app.js78-84](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L78-L84)

### Sistema de temas

La interfaz cuenta con un lenguaje de diseño "Premium" con un sistema de doble tema (Oscuro/Claro).

*   **Tema oscuro**: La interfaz predeterminada de alto contraste usando acentos de pizarra profunda y azul [docker/dashboard/frontend/styles.css2-27](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L2-L27)
*   **Tema de luz**: Una paleta de "pergamino" diseñada para reducir la fatiga visual usando fondos de pizarra más suaves en lugar de [docker/tablero/frontend/styles.css31-57](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L31-L57) La preferencia de tema se mantiene en `localStorage` y se aplica mediante un atributo `data-theme` en el [docker/dashboard/frontend/app.js143-147 del documento.](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L143-L147)

### Internacionalización (i18n)

El sistema admite inglés y español de fábrica. `El I18nProvider` envuelve la aplicación, proporcionando una función `t()` para traducciones y una utilidad `toggleLang` para cambiar dinámicamente entre [lenguajes docker/dashboard/frontend/app.js25-28](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L25-L28)

**Fuentes:**[docker/dashboard/frontend/app.js143-147](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L143-L147)[docker/dashboard/frontend/styles.css1-57](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L1-L57)

## Detalles del subsistema

Para información técnica más profunda sobre partes específicas del frontend, consulte las siguientes páginas hijas:

### [Componente de la aplicación y gestión del estado](/LuisVilRiv/comprobador-de-paginas-web/7.1-app-component-and-state-management)

Detalla la lógica raíz del panel de control, incluyendo el flujo CRUD para clientes y sitios web, la driver.js de la visita de incorporación y los temporizadores de cuenta atrás para el cron scheduler global.

*   **Archivos clave**: `app.js`, `js/modals.js`, `js/scheduler.js`.

### [Interfaz de Detalle de Auditoría e Historial de Ejecución](/LuisVilRiv/comprobador-de-paginas-web/7.2-audit-detail-and-run-history-ui)

Explica cómo el frontend renderiza informes de auditoría complejos, gestiona la lógica de diferenciación de problemas (Nuevo vs. Resuelto) e integra con los endpoints de generación de PDF.

*   **Archivos clave**: `js/audit.js`, `js/websites.js`.

### [Estilismo frontal e internacionalización](/LuisVilRiv/comprobador-de-paginas-web/7.3-frontend-styling-and-internationalization)

Documenta la arquitectura de variables CSS, el sistema de cuadrícula responsiva y la implementación del diccionario de traducción.

*   **Archivos clave**: `styles.css`, `js/i18n.js`.

* * *

**Fuentes:**

*   `docker/dashboard/frontend/app.js`
*   `Docker/tablero de control/frontend/styles.css`
*   `Docker/Panel de control/server.js`
*   `docker/dashboard/frontend/index.html`

* * *

# Gestión de Componentes de Aplicación y Estado

# Componente de la aplicación y gestión del estado

Archivos fuente relevantes

*   [docker/dashboard/frontend/app.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js)
*   [docker/dashboard/frontend/js/scheduler.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/scheduler.js)
*   [docker/dashboard/frontend/js/websites.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/websites.js)

El componente `App` en `docker/dashboard/frontend/app.js` sirve como la raíz de la aplicación React, orquestando el estado global, la obtención de datos y el ciclo de vida principal del panel. Gestiona la sincronización entre el estado local de la interfaz y la API Backend, gestiona las encuestas periódicas para tareas de auditoría en segundo plano y proporciona el contexto para la internacionalización de temas y de la internacionalización.

## Arquitectura estatal

La aplicación utiliza componentes funcionales y ganchos de React para gestionar varias categorías distintas de estado.

### Estado de los datos principales

El componente raíz mantiene los conjuntos de datos principales necesarios para renderizar el panel de control:

*   **Resumen**: Estadísticas agregadas (por ejemplo, total de sitios web, puntuación media) obtenidas de `fetchSummary`[docker/dashboard/frontend/app.js30](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L30-L30)
*   **Sitios web**: La lista de todos los sitios monitorizados, filtrada por cliente o consulta [de búsqueda docker/dashboard/frontend/app.js31](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L31-L31)
*   **Clientes**: La lista de clientes disponibles para [categorización docker/dashboard/frontend/app.js32](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L32-L32)
*   **Configuración**: Configuración global de crons para sitios activos e [inactivos docker/dashboard/frontend/app.js39](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L39-L39)

### UI y Estado Modal

La visibilidad de las distintas interfaces de gestión se controla mediante banderas booleanas:

*   **Modales**: Activas para `showAddClient`, `showAddWebsite`, `showSettings` y `deleteConfirm`[docker/dashboard/frontend/app.js46-50](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L46-L50)
*   **Datos de formularios**: Búferes temporales para creación y edición, como `newClientForm` y `editWebsiteForm`[docker/dashboard/frontend/app.js52-55](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L52-L55)
*   **Carga/Retroalimentación**: `loading`, `formError` y `successMessage` gestionan [docker/dashboard/frontend/app.js35-37 con retroalimentación asíncrona](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L35-L37)

### Seguimiento de auditoría

Para proporcionar actualizaciones en tiempo real sin actualizaciones manuales, la aplicación rastrea las auditorías activas:

*   **auditingIds**: `Un conjunto` de IDs de sitios web que actualmente están siendo auditados por el [userdocker/dashboard/frontend/app.js43](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L43-L43)
*   **run\_status**: El componente inspecciona la propiedad `run_status` de los objetos web para identificar tareas en segundo [plano como docker/dashboard/frontend/app.js79](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L79-L79)

**Fuentes:**

*   [docker/dashboard/frontend/app.js27-57](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L27-L57)

## Flujo de datos y sondeo

La aplicación implementa una estrategia de doble sondeo para mantener la interfaz reactiva a los procesos en segundo plano.

### Carga inicial y sincronización

La función `loadAll` realiza una `búsqueda Promise.all` para sincronizar el panel de control con el estado de la base [de datos docker/dashboard/frontend/app.js59-68](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L59-L68). Esto se activa al montar y cada vez que el filtro `clientId` seleccionado cambia [docker/dashboard/frontend/app.js75](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L75-L75)

### Encuestas de auditoría de antecedentes

Si algún sitio web en la vista actual tiene un estado `de "en funcionamiento"` o está contenido dentro del conjunto `auditingIds`, la aplicación inicia un intervalo de sondeo de 3 segundos [docker/dashboard/frontend/app.js78-84](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L78-L84). Esto garantiza que las barras de progreso (renderizadas por `AuditProgress` en `websites.js`) se actualicen a medida que el scraper completa las secciones [de auditoría docker/dashboard/frontend/js/websites.js17-32](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/websites.js#L17-L32)

### Cronómetros de cuenta atrás Cron

Un intervalo de 1 segundo actualiza el `estado actual` y calcula la cuenta atrás legible por humanos para las siguientes auditorías programadas basándose en el `objeto de configuración` [docker/dashboard/frontend/app.js86-104](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L86-L104)

**Diagrama de interacción de entidades**

El siguiente diagrama ilustra cómo interactúa el componente `App` con módulos especializados y la API.

Título: Estado del frontend e interacción con API

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["Módulos de UI"]
        H["Sitios WebTabla #91; websites.js#93;"]
        I["SchedulerModal #91; scheduler.js#93;"]
        J["useAuditDetail #91; audit.js#93;"]
    fin
    subgrafo subGraph1 ["API Capa #91; api.js#93;"]
        E["fetchWebsites()"]
        F["triggerAudit()"]
        G["fetchSummary()"]
    fin
    subgrafo subGraph0 ["Componente de la Aplicación #91; app.js#93;"]
        R["Estado de la aplicación (sitios web, resumen, configuración)"]
        B["loadAll()"]
        c["handleAuditWebsite()"]
        D["Efecto de encuesta (3s)"]
    fin
    B --> E
    B --> G
    C --> F
    D -->|" reactivar"| B
    A --> H
    Un --> yo
    J -->|" carreras, problemas"| A
```

**Fuentes:**

*   [docker/dashboard/frontend/app.js59-84](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L59-L84)
*   [docker/dashboard/frontend/app.js113-122](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L113-L122)
*   [docker/dashboard/frontend/js/api.js7-14](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/api.js#L7-L14)

## Flujo de disparo de auditoría

Cuando un usuario hace clic en el botón "Auditar" en `la Fila del Sitio Web`, ocurre la siguiente secuencia:

1.  El ID del sitio web se añade al estado local de `auditingIds` para desactivar inmediatamente el botón [docker/dashboard/frontend/app.js115](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L115-L115)
2.  se llama `a triggerAudit(id`), que envía una solicitud POST al [docker/dashboard/frontend de la API Backend docker/dashboard/frontend/app.js117](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L117-L117)
3.  Al tener éxito, se muestra una notificación y se invoca `loadAll(`) para actualizar el `run_status`[docker/dashboard/frontend/app.js118-119](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L118-L119)
4.  El efecto de sondeo detecta el estado `de "en funcionamiento"` y mantiene las actualizaciones de la interfaz hasta completar [docker/dashboard/frontend/app.js79-82](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L79-L82)

**Fuentes:**

*   [docker/dashboard/frontend/app.js113-122](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L113-L122)
*   [docker/dashboard/frontend/js/websites.js149-154](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/websites.js#L149-L154)

## Tema y persistencia

El salpicadero soporta un lenguaje de diseño "Premium" con modos de luz y sombra. El estado del tema se mantiene en `localStorage`[docker/dashboard/frontend/app.js143-147](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L143-L147)

*   **Implementación**: El tema se aplica estableciendo el atributo `data-theme` en el `document.documentElement`, que activa los desplazamientos variables [CSS docker/dashboard/frontend/app.js145](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L145-L145)
*   **Por defecto**: Por defecto se pone `en "oscuro"` si no se almacena ninguna preferencia[. docker/dashboard/frontend/app.js143](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L143-L143)

**Fuentes:**

*   [docker/dashboard/frontend/app.js142-150](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L142-L150)

## Visita de Incorporación (driver.js)

La aplicación `integra driver.js` para ofrecer una guía guiada para nuevos usuarios. La función `startTour` define una secuencia de pasos dirigidos a IDs específicos de [DOM docker/dashboard/frontend/app.js152-178](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L152-L178)

Los pasos clave incluyen:

*   **Configuración global**: Resaltar el panel de configuración [docker/dashboard/frontend/app.js165](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L165-L165)
*   **Cron Manager**: Explicando la frecuencia del planificador y el modo [experto docker/dashboard/frontend/app.js167-175](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L167-L175)
*   **Control Programático**: El tour puede forzar estados de la interfaz (por ejemplo, `setShowSettings(true)`) para asegurar que los elementos sean visibles antes de resaltarlos [en docker/dashboard/frontend/app.js170](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L170-L170)

**Fuentes:**

*   [docker/dashboard/frontend/app.js152-178](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L152-L178)

## Mapeo de estado a componente

El siguiente diagrama asigna variables internas de estado de React a las entidades específicas de la interfaz que controlan.

Título: Mapeo de estado de componentes

```mermaid
diagrama de flujo LR
    subgrafo subGraph1 ["Entidades de código"]
        C1["Sitios WebTabla #91; websites.js#93;"]
        C2["AuditProgress #91; websites.js#93;"]
        C3["SchedulerModal #91; scheduler.js#93;"]
        C4["document.documentElement"]
    fin
    subgrafo subGraph0 ["Variables de estado"]
        S1["sitios web"]
        S2["auditingIds"]
        S3["ambientación"]
        S4["tema"]
    fin
    S1 -->|" mapas a filas"| C1
    S2 -->|" Flag isAuditing"| C2
    T3 -->|" cronValue props"| C3
    S4 -->|" atributo data-tema"| C4
```

**Fuentes:**

*   [docker/dashboard/frontend/app.js31-147](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/app.js#L31-L147)
*   [docker/dashboard/frontend/js/websites.js34-36](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/websites.js#L34-L36)
*   [docker/dashboard/frontend/js/scheduler.js67-70](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/scheduler.js#L67-L70)

* * *

# UI de Auditoría-Detalle-&-Run-History-UI

# Interfaz de Detalle de Auditoría e Historial de Ejecución

Archivos fuente relevantes

*   [Docker/dashboard/API/rutas/ejecuciones/runs\_endpoints.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/runs/runs_endpoints.py)
*   [Docker/tablero de control/frontend/JS/api.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/api.js)
*   [docker/dashboard/frontend/js/audit.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js)
*   [docker/dashboard/frontend/js/i18n.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.js)
*   [docker/dashboard/frontend/js/modals.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/modals.js)

La **interfaz de Detalle de Auditoría e Historial de Ejecución** es un módulo especializado dentro del Dashboard Frontend que proporciona una visibilidad profunda de los resultados de la cadena `de QualityAuditor`. Gestiona la presentación de las auditorías históricas, resultados granulares de secciones (SEO, Seguridad, etc.) y cuestiones individuales, incluyendo una lógica diferencial que destaca problemas resueltos frente a nuevos.

## Arquitectura de componentes

La interfaz está construida como una jerarquía de componentes de React definida en `audit.js`. Sigue un flujo de datos donde `el AuditHistoryModal` actúa como contenedor principal, obteniendo datos a través del `gancho useAuditDetail` y desentrañándolos en componentes especializados de presentación.

### Jerarquía de componentes

| Componente | Función |
| --- | --- |
| AuditoríaHistoriaModal | Contenedor raíz para la vista del historial de auditoría. Gestiona el estado de la ejecución seleccionada y la visibilidad. |
| RunList | Muestra una lista desplazable de componentes de RunCard que representa el historial del sitio web. |
| RunCard | Resume una única AuditRun. Muestra la puntuación, la fecha y activa la vista de detalles. |
| RunSectionsTable | La cuadrícula de datos central muestra los registros de AuditRunSection y las listas anidadas de IssueRow. |
| IssueRow | Muestra un único AuditIssue con indicadores de gravedad e iconos de estado diferencial. |
| Panel de AuditoríaInfo | Panel educativo estático explicando las categorías de la auditoría. |

### Diagrama de flujo de datos: Recuperación de detalles de auditoría

Este diagrama ilustra cómo interactúan los componentes de la interfaz con la API de Backend y los Repositorios de la Base de Datos.

```mermaid
diagrama de flujo TD
    subgrafo subGraph2 ["Base de datos (SQLAlchemy)"]
        I["Tabla de AuditRun"]
        J["Tabla de Secciones AuditRun"]
        K["Tabula de Cuestiones de Auditoría"]
    fin
    subgrafo subGraph1 ["API de backend (runs_endpoints.py)"]
        F["repo.website_runs"]
        G["repo.run_sections"]
        H["repo.run_issues"]
    fin
    subgrafo subGraph0 ["Frontend (audit.js)"]
        R["AuditHistoryModal"]
        B["useAuditDetail (Hook)"]
        C["fetchWebsiteRuns"]
        D["fetchRunSections"]
        E["fetchRunIssues"]
    fin
    A --> B
    B --> C
    B --> D
    B --> E
    C -->|" GET /websites/{id}/runs"| F
    D -->|" GET /runs/{id}/sections"| G
    E -->|" GET /runs/{id}/issues"| H
    ¡A la >
    G --> J
    H --> K
```

**Fuentes:**[docker/dashboard/frontend/js/audit.js140-160](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js#L140-L160)[docker/dashboard/api/routes/runs/runs\_endpoints.py19-44](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/runs/runs_endpoints.py#L19-L44)[docker/dashboard/frontend/js/api.js39-52](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/api.js#L39-L52)

* * *

## Detalles de implementación

### El gancho `useAuditDetail`

Este gancho personalizado centraliza la gestión estatal para el historial de auditoría de un sitio web específico. Por defecto, recupera las últimas 5 ejecuciones y gestiona el estado de carga de secciones y problemas cuando un usuario expande una `RunCard` específica.

*   **Búsqueda inicial:** Llama a `fetchWebsiteRuns`[docker/dashboard/frontend/js/api.js39-40](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/api.js#L39-L40) cuando cambia el ID del sitio web.
*   **Carga perezosa:** Las secciones y problemas para una partida específica solo se obtienen cuando `se invoca toggleSections(runId)` [docker/dashboard/frontend/js/audit.js210-225](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js#L210-L225)

### Lógica diferencial (Nuevo vs. Resuelto)

La interfaz distingue entre problemas en función de su `atributo diff_status`. Esta lógica se visualiza en `IssueRow`[docker/dashboard/frontend/js/audit.js33-59](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js#L33-L59):

*   **Nuevos temas:** Marcado con un círculo rojo (`🔴`) y texto estándar.
*   **Problemas persistentes:** Marcado con un círculo blanco (`⚪`).
*   **Problemas resueltos:** Marcado con un círculo verde (), `🟢` mostrado con una `decoración de línea a` través y prefijado con "RESUELTA:" [docker/dashboard/frontend/js/audit.js39-52](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js#L39-L52)

### Detección de secciones bloqueadas

`La RunSectionsTable` incluye lógica heurística para identificar si una sección falló debido a un bloqueo externo (cortafuegos, WAFs o errores prohibidos 403) en lugar de un fallo técnico del auditor.

Una sección se marca como **Bloqueada** si el estado es "fallido" y cualquiera de las siguientes cadenas aparece en los `mensajes de result_description` o de emisión anidada:

*   "bloqueado" / "bloqueado"
*   "cortafuegos"
*   "403"

Esto activa la clase `.status-badge.blocked` [CSS docker/dashboard/frontend/js/audit.js87-107](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js#L87-L107)

**Fuentes:**[docker/dashboard/frontend/js/audit.js33-59](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js#L33-L59)[docker/dashboard/frontend/js/audit.js84-111](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js#L84-L111)

* * *

## Mapeo de clases de puntuación

La interfaz aplica un estilo semántico a las puntuaciones de auditoría para proporcionar retroalimentación visual inmediata sobre la salud del sitio.

| Rango de puntuación | Clase | Color Variable |
| --- | --- | --- |
| 80 - 100 | Bien | var(--éxito) |
| 50 - 79 | Advertir | var(--advertencia) |
| 0 - 49 | mala | var(--peligro) |

Esta asignación se aplica en `RunCard`[docker/dashboard/frontend/js/audit.js142](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js#L142-L142) y determina el color de la insignia de puntuación.

**Fuentes:**[docker/dashboard/frontend/js/audit.js142-155](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js#L142-L155)

* * *

## Integración de exportación PDF

La interfaz de Auditoría de Detalle proporciona un disparador directo para generar un informe PDF de una ejecución específica.

1.  **Disparador frontal:** El botón "Exportar PDF" llama `a exportRunPdf(runId)`[docker/dashboard/frontend/js/audit.js180-190](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js#L180-L190)
2.  **Procesamiento de API:** La solicitud aparece `en GET /runs/{run_id}/export`[docker/dashboard/api/routes/runs/runs\_endpoints.py47-48](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/runs/runs_endpoints.py#L47-L48)
3.  **Recogida de datos:** El backend obtiene el detalle de la ejecución, la página web asociada y un contexto histórico de las 4 ejecuciones anteriores a través `de repo.runs_history_for_pdf`[docker/dashboard/api/routes/runs/runs\_endpoints.py58-62](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/runs/runs_endpoints.py#L58-L62)
4.  **Streaming:** La utilidad `generate_audit_pdf` crea el flujo binario, que se devuelve como `StreamingResponse` con el tipo `de medio de aplicación/`[pdf docker/tablero/api/routes/runs/runs\_endpoints.py69-73](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/runs/runs_endpoints.py#L69-L73)

### Secuencia de exportación PDF

```mermaid
Diagrama de secuencia
    participante U como usuario (UI)
    participante A como api.js
    participante R como runs_endpoints.py
    participante P como pdf_generator.py
    U->>A: Haz clic en "Exportar PDF"
    A->>R: GET /api/runs/{id}/export
    R->>R: repo.runs_history_for_pdf()
    R->>P: generate_audit_pdf(carrera, web, historial)
    P-->>R: Búfer de BytesIO
    R-->>A: StreamingResponse (PDF)
    A-->>U: Descarga del navegador
```

**Fuentes:**[docker/dashboard/api/routes/runs/runs\_endpoints.py47-74](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/routes/runs/runs_endpoints.py#L47-L74)[docker/dashboard/frontend/js/api.js63-70](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/api.js#L63-L70)[docker/dashboard/frontend/js/audit.js180-190](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js#L180-L190)

* * *

# Estilismo y internacionalización frontend

# Estilismo frontal e internacionalización

Archivos fuente relevantes

*   [Docker/panel de control/babel.config.json](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/babel.config.json)
*   [docker/dashboard/frontend/js/i18n.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.js)
*   [Docker/tablero de control/frontend/styles.css](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css)

La interfaz Web Auditor implementa un lenguaje de diseño cohesivo denominado "Premium Design" y un sistema robusto de internacionalización (i18n). La arquitectura de estilo aprovecha variables CSS para soportar temas dinámicos (Luz/Oscuro), mientras que el sistema i18n utiliza React Context para proporcionar soporte multilingüe (inglés/español) en todos los componentes de la interfaz de usuario.

## Sistema de Variables y Temas CSS

El estilo se centra en un conjunto de variables CSS definidas en los selectores `:root` y `[data-theme="light"`\]. Esto permite un cambio instantáneo de temas sin necesidad de recargar la aplicación.

### Paletas de diseño

El sistema soporta dos modos visuales principales:

1.  **Modo oscuro (por defecto):** Una estética oscura "Premium" que utiliza azules profundos y negros (`#0a0b10`) para resaltar datos de auditoría con colores de alto contraste en [docker/dashboard/frontend/styles.css2-27](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L2-L27)
2.  **Modo Luz (Pergamino):** Un modo "Luz tenue/suave" diseñado para reducir la fatiga visual. Utiliza una paleta basada en pizarra (`#e2e8f0`) en lugar de blanco puro, creando una sensación cálida de tinta sobre pergamino [en docker/dashboard/frontend/styles.css31-57](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L31-L57)

| Variable | Modo oscuro (por defecto) | Modo Luz (Pergamino) |
| --- | --- | --- |
| \--bg-main | #0a0b10 | #e2e8f0 (Slate-200) |
| \--bg-card | #161922 | #f1f5f9 (Slate-100) |
| \--texto-principal | #e2e8f0 | #1e293b (Slate-800) |
| \--primaria | #3b82f6 | #1e40af (Azul-800) |
| \--éxito | #10b981 | #166534 (Verde-800) |

**Fuentes:**[docker/dashboard/frontend/styles.css2-57](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L2-L57)

## Diseño de componentes

### Lenguaje de diseño premium

La interfaz utiliza un lenguaje de diseño "Premium" caracterizado por:

*   **Cartas:** Esquinas redondeadas (`--radio: 12px`), bordes sutiles y elevaciones flotantes usando `translateY(-4px)`[docker/dashboard/frontend/styles.css93-102](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L93-L102)
*   **Entradas: la clase** `premium-input` proporciona un aspecto consistente para el texto y los campos selectos, incluyendo una flecha SVG personalizada para los [desplegables docker/dashboard/frontend/styles.css120-148](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L120-L148)
*   **Botones:** Una jerarquía de estilos de botones que incluye colores sólidos (`btn-primary`, `btn-success`) y botones "Fantasma" para acciones [secundarias docker/dashboard/frontend/styles.css166-188](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L166-L188) En Modo Luz, estos se adaptan automáticamente a un estilo delineado con rellenos de hover [docker/dashboard/frontend/styles.css190-231](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L190-L231)

### Visualización de datos y retroalimentación

*   **Barras de progreso:** Los `elementos personalizados .progress-container` y `.progress-bar` visualizan las puntuaciones de auditoría con colores dinámicos basados en el valor de [puntuación docker/dashboard/frontend/styles.css371-390](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L371-L390)
*   **Insignias de diferencial:** Usado en el historial de auditoría para mostrar cambios de estado (por ejemplo, `badge-new`, `badge-resolved`, `badge-persistent`) [docker/dashboard/frontend/styles.css411-428](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L411-L428)
*   **Mapeo de clases de puntuación:** Las puntuaciones se clasifican visualmente en `puntuación excelente` (90+), `puntuación buena` (70-89), `advertencia de puntuación` (50-69) y `puntuación-peligro` (<50) [docker/dashboard/frontend/styles.css392-395](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L392-L395)

**Fuentes:**[docker/dashboard/frontend/styles.css93-102](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L93-L102)[docker/dashboard/frontend/styles.css120-148](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L120-L148)[docker/dashboard/frontend/styles.css371-395](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L371-L395)[docker/dashboard/frontend/styles.css411-428](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L411-L428)

## Internacionalización (i18n)

El sistema i18n está implementado como proveedor de contexto React en `i18n.js`. Gestiona el estado actual del lenguaje y proporciona una función de traducción `t()` a los componentes.

### Detalles de implementación

*   **Diccionarios:** Las cadenas de traducción se almacenan en un objeto `de diccionario` que contiene espacios de nombres anidados para `app`, `tabla`, `modales`, `planificador`, etc. [docker/dashboard/frontend/js/i18n.js6-150](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.js#L6-L150)
*   **Persistencia del lenguaje:** El sistema detecta el lenguaje del navegador del usuario en la primera carga y mantiene cambios manuales en `localStorage` bajo la tecla `preferred_lang`[docker/dashboard/frontend/js/i18n.js159-166](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.js#L159-L166)
*   **Función de traslación (`t`):** Una función de búsqueda recursiva que recorre el diccionario basada en una cadena de notación de puntos (por ejemplo, `t('app.title')`[) docker/dashboard/frontend/js/i18n.js174-184](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.js#L174-L184)

### El flujo I18nProvider

Este diagrama ilustra cómo el `I18nProvider` gestiona el estado del lenguaje y lo expone a la aplicación.

**Arquitectura de flujo de datos I18n**

```mermaid
diagrama de flujo TD
    subgrafo subGraph2 ["Componentes de la interfaz"]
        I["Título de la app"]
        J["Cabeceras de Tablas"]
        K["Botón de alternancia de idioma"]
    fin
    subgrafo Consumo
        F["useI18n() Hook"]
        G["t(path) Function"]
        H["toggleLang() Función"]
    fin
    subgrafo subGraph0 ["Gestión de estados del lenguaje"]
        A["I18nProvider"]
        B["localStorage#91;' preferred_lang'#93;?"]
        C["navigator.language"]
        D["Lengua almacenada"]
        E["lang State"]
    fin
    Un -->|" init"| B
    B -->|" No"| C
    B -->|" Sí"| D
    C --> E
    D --> E
    E --> F
    F --> G
    ¡A la > H
    G --> I
    G --> J
    H --> K
    K -->|" llama"| H
    H -->|" actualizaciones"| E
    H -->|" salvaciones"| B
```

**Fuentes:**[docker/dashboard/frontend/js/i18n.js152-198](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.js#L152-L198)

## Integración y mapeo de código

El siguiente diagrama une los conceptos de estilo e i18n con entidades específicas de código en el panel de control.

**Mapeo de configuración frontend**

```mermaid
diagrama de flujo TD
    subgrafo subGraph2 ["Entrada de React"]
        APP["Componente de la Aplicación"]
        APP_JS["app.js"]
    fin
    subgrafo subGraph1 ["Entidades I18n"]
        DICTA["diccionarios (es/en)"]
        I18N_JS["i18n.js"]
        T_FUNC["t(key)"]
        PROVEEDOR["I18nProvider"]
    fin
    subgrafo subGraph0 ["Entidades de Estilo"]
        CSS_VAR[":variables raíz"]
        STYLES_CSS["styles.css"]
        THEME_ATTR["#91; data-theme#93; atributo"]
        COMP_CARDS[".card / .input-premium"]
    fin
    CSS_VAR --> STYLES_CSS
    THEME_ATTR --> STYLES_CSS
    COMP_CARDS --> STYLES_CSS
    DICTADO --> I18N_JS
    T_FUNC --> I18N_JS
    PROVEEDOR --> I18N_JS
    APP --> APP_JS
    APP_JS -->|" Envuelve con "| PROVEEDOR
    APP_JS -->|" Aplica el tema a"| THEME_ATTR
    APP_JS -->|" Usos"| T_FUNC
```

**Fuentes:**[docker/dashboard/frontend/js/i18n.js4-200](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.js#L4-L200)[docker/dashboard/frontend/styles.css1-60](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L1-L60)

### Funciones y clases clave

| Entidad | Ubicación | Propósito |
| --- | --- | --- |
| I18nProvider | i18n.jsdocker/dashboard/frontend/js/i18n.js152 | El proveedor React Context envolve la aplicación para el estado i18n. |
| t(camino) | i18n.jsdocker/dashboard/frontend/js/i18n.js174 | Resuelve una clave de traducción (por ejemplo, table.url) en la cadena localizada. |
| toggleLang() | i18n.jsdocker/dashboard/frontend/js/i18n.js168 | Cambia entre en y es y actualiza localStorage. |
| \[tema de datos\] | styles.cssdocker/dashboard/frontend/styles.css31 | Selector CSS utilizado para anular variables predeterminadas en Modo Luz. |
| .distintivo-diff | styles.cssdocker/dashboard/frontend/styles.css411 | Clase base para indicadores de estado de emisiones de auditoría. |

**Fuentes:**[docker/dashboard/frontend/js/i18n.js152-184](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.js#L152-L184)[docker/dashboard/frontend/styles.css31-411](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/styles.css#L31-L411)

* * *

# Pruebas

# Pruebas

Archivos fuente relevantes

*   [.gitignore](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/.gitignore)
*   [Docker/Panel de control/jest.config.json](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/jest.config.json)
*   [Pruebas/conftest.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/conftest.py)

La plataforma Web Auditor emplea una estrategia de pruebas de doble pila para garantizar la fiabilidad de su arquitectura distribuida. La suite de pruebas se divide en una suite backend basada en Python que utiliza `pytest` para los servicios auditor, scraper y API, y una suite frontend basada en JavaScript que utiliza `Jest` para el panel de React.

## Visión general de la infraestructura de pruebas

El entorno de pruebas está configurado para reflejar la arquitectura de producción mientras proporciona ejecución aislada para pruebas unitarias e integradas.

### Infraestructura Python (pytest)

El conjunto de pruebas en Python está orquestado mediante `pytest`. Para asegurar que los paquetes `compartidos`, `scraper`, `dashboard` y `analizador de IA` sean descubribles, el `archivo tests/conftest.py` inyecta dinámicamente la raíz del proyecto en `sys.path`[tests/conftest.py4-6](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/conftest.py#L4-L6)

*   **Heurísticas y análisis**: Valida la lógica `de QualityAuditor`, específicamente la detección de páginas inoperativas y la clasificación de contenidos impulsada por IA.
*   **Módulos de Auditoría**: Pruebas individuales para las ocho categorías de auditoría (Seguridad, SEO, Estructura, etc.) ubicadas en `compartido/auditor/cheques/`.
*   **Rastreador y Raspado**: Pruebas para el rastreador de enlaces recursivo BFS y la lógica de selección de estrategias (BeautifulSoup vs. Selenium).
*   **Endpoints API**: pruebas de integración para las rutas FastAPI y utilidades de generación de PDF.

### Infraestructura JavaScript (Jest)

El entorno de pruebas frontend utiliza `Jest` con el `entorno jsdom` para simular un [contexto del navegador docker/dashboard/jest.config.json2](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/jest.config.json#L2-L2) Dado que el frontend utiliza módulos ESM de `esm.sh`, la configuración incluye un `moduleNameMapper` para redirigir estas importaciones a módulos nodos locales durante la ejecución de pruebas [docker/dashboard/jest.config.json6-11](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/jest.config.json#L6-L11)

*   **Cliente API**: Valida la comunicación entre el frontend de React y la API del Dashboard.
*   **UI Logic**: Prueba los cálculos de crons del planificador y la cobertura de internacionalización (i18n).

## Relaciones entre conjuntos de pruebas

El siguiente diagrama ilustra cómo la infraestructura de pruebas se mapea a los distintos componentes del sistema y entidades de código.

### Mapeo de sistema a prueba

```mermaid
diagrama de flujo LR
    subgrafo subGraph1 ["Espacio de prueba"]
        PYT["Suite pytest"]
        JST["Jest Suite"]
        CONF["conftest.py"]
        JCONF["jest.config.json"]
    fin
    subgrafo subGraph0 ["Espacio de Entidades de Código"]
        QA["QualityAuditor"]
        SC["ScraperContext"]
        LC["LinkCrawler"]
        API["FastAPI Routes"]
        FE["Panel de Control de React"]
    fin
    QA -->|" Validado por"| PYT
    SC -->|" Validado por"| PYT
    LC -->|" Validado por"| PYT
    API -->|" Validado por"| PYT
    FE -->|" Validado por"| JST
    CONF -->|" Establece sys.path para"| PYT
    JCONF -->|" Configures jsdom for"| JST
```

Fuentes: [tests/conftest.py4-6](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/conftest.py#L4-L6)[docker/dashboard/jest.config.json1-12](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/jest.config.json#L1-L12)

## Categorías de pruebas

El conjunto de pruebas se categoriza según las áreas funcionales específicas de la plataforma:

| Categoría | Marco | Entidades clave de código objetivo |
| --- | --- | --- |
| Lógica del auditor | pytest | QualityAuditor, check\_inoperative\_page, calculate\_score |
| Estrategias de raspado | pytest | EstrategiaBellaSoup, Estrategia de Selenio, classify\_strategy |
| Rastreo de enlaces | pytest | check\_links\_recursive, LinkCrawler |
| Backend API | pytest | Panel de control/rutas/, compartido/utilitarios/pdf\_generator.py |
| API frontal | Broma | Panel de control/estática/JS/api.js |
| Componentes de la interfaz | Broma | Panel de control/estático/JS/app.js, Panel de control/estático/JS/i18n.js |

### Diagrama del ciclo de vida de pruebas

Este diagrama muestra cómo las suites de pruebas conectan los requisitos de "Lenguaje Natural" (por ejemplo, "El scraping debe manejar SPAs") con la implementación de la "Entidad de Código".

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["Ejecución de pruebas"]
        T1["más piante"]
        T2["Broma"]
    fin
    subgrafo subGraph1 ["Espacio de Entidades de Código"]
        E1["seo_checks.py"]
        E2["test_inoperative_pages.py"]
        E3["i18n.test.js"]
    fin
    subgrafo subGraph0 ["Requisitos de lenguaje natural"]
        R1["Verificar etiquetas SEO"]
        R2["Detectar sitios inoperativos"]
        R3["Traducir la interfaz de usuario al español"]
    fin
    R1 --> E1
    R2 --> E2
    R3 --> E3
    E1 -.-> T1
    E2 -.-> T1
    E3 -.-> T2
```

Fuentes: [tests/conftest.py1-7](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/conftest.py#L1-L7)[docker/dashboard/jest.config.json1-12](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/jest.config.json#L1-L12)

## Suites de pruebas detalladas

Para documentación detallada sobre implementaciones de pruebas específicas, aserciones e instrucciones de ejecución, consulte las páginas hijas:

*   **[Python Test Suite](/LuisVilRiv/comprobador-de-paginas-web/8.1-python-test-suite)**: Desglose detallado de heurísticas de auditores, módulos de comprobación, pruebas de estrategia de scraping e integración de API.
*   **[Suite de pruebas de JavaScript](/LuisVilRiv/comprobador-de-paginas-web/8.2-javascript-test-suite)**: Desglose detallado de la configuración Jest, mocking de clientes API y verificación lógica del frontend.

Fuentes: [tests/conftest.py1-7](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/conftest.py#L1-L7)[docker/dashboard/jest.config.json1-12](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/jest.config.json#L1-L12)

* * *

# Python-Test-Suite

# Suite de pruebas de Python

Archivos fuente relevantes

*   [scratch/test\_formare.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scratch/test_formare.py)
*   [scratch/test\_selenium\_503.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scratch/test_selenium_503.py)
*   [compartido/auditor/auditor\_modules/core.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py)
*   [Pruebas/test\_ai\_analyzer\_error\_context.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_error_context.py)
*   [Pruebas/test\_ai\_analyzer\_integration.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_integration.py)
*   [Pruebas/test\_api\_endpoints.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_api_endpoints.py)
*   [Pruebas/test\_check\_browser.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_browser.py)
*   [Pruebas/test\_check\_buttons.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_buttons.py)
*   [Pruebas/test\_check\_content.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_content.py)
*   [Pruebas/test\_check\_images.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_images.py)
*   [Pruebas/test\_check\_seo.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_seo.py)
*   [Pruebas/test\_check\_structure.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_structure.py)
*   [Pruebas/test\_check\_technical.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_technical.py)
*   [Pruebas/test\_inoperative\_pages.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_inoperative_pages.py)
*   [Pruebas/test\_links\_recursive\_robust.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_links_recursive_robust.py)
*   [Pruebas/test\_selenium.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_selenium.py)
*   [Pruebas/test\_selenium\_503\_detection.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_selenium_503_detection.py)
*   [Pruebas/test\_strategy\_classifier.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_strategy_classifier.py)

La suite de pruebas de Python proporciona una validación completa para la lógica central del Web Auditor, cubriendo desde módulos individuales de comprobación de auditoría hasta la detección semántica del analizador de IA y los endpoints REST de la API. Utiliza `pytest` para garantizar la fiabilidad de la cadena de auditoría de 8 pasos y la robustez de las estrategias de scraping.

## Heurísticas de páginas inoperativas

`El QualityAuditor` incluye un complejo motor heurístico para detectar páginas que técnicamente están "activas" (devolviendo HTTP 200) pero que están funcionalmente inoperativas, como páginas personalizadas de 404, pantallas de mantenimiento o plantillas de servidor por defecto.

### Flujo lógico de detección

El auditor evalúa varias señales para determinar si una página está inoperativa:

1.  **Señales duras**: códigos $\ge 400$
2.  **Patrones fuertes**: cadenas específicas en `el <title>`, `<h1>` o `<body>` (por ejemplo, "502 Bad Gateway", "Database Error") [compartido/auditor/auditor\_modules/core.py181-196](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L181-L196)
3.  **Patrones suaves**: Mensajes de mantenimiento combinados con bajo número de palabras [compartidos/auditor/auditor\_modules/core.py202-212](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L202-L212)
4.  **Contexto educativo**: Una lista blanca que evita que los artículos sobre errores HTTP (como páginas de Wikipedia) busquen términos como "RFC", "documentación" o "código de estado" [compartido/auditor/auditor\_modules/core.py39-65](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L39-L65)

### Escenarios de prueba

El `módulo test_inoperative_pages.py` valida estas heurísticas:

| Caso de prueba | Condición de entrada | Resultado esperado |
| --- | --- | --- |
| test\_inoperative\_by\_status\_code | Metadatos HTTP 500 | Puntuación 5, "crítico", liberar pruebas bloqueadas/test\_inoperative\_pages.py11-32 |
| test\_inoperative\_by\_title\_error | Título "404 No encontrado" (Estado 200) | Puntuación 5, detectada como pruebas de error del servidor/test\_inoperative\_pages.py36-53 |
| test\_inoperative\_by\_title\_maintenance | Title "Sitio en Mantenimiento" | Puntuación 5, liberar pruebas bloqueadas/test\_inoperative\_pages.py106-122 |
| test\_wikipedia\_http\_article\_is\_not\_flagged | Términos académicos + alto número de palabras | Puntuación > 50, pruebas no operativas/test\_inoperative\_pages.py174-190 |

**Fuentes:**[compartido/auditor/auditor\_modules/core.py149-220](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L149-L220)[tests/test\_inoperative\_pages.py1-190](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_inoperative_pages.py#L1-L190)

## Módulos de Verificación de Auditoría

Cada check-in `modular en shared/auditor/checks/`checks tiene un conjunto de pruebas correspondiente para verificar modos de fallo específicos.

### Pruebas de contenido y seguridad

*   **Contenido (`test_check_content.py`):** Valida la detección de "contenido ligero" (bajo conteo de palabras), el relleno de palabras clave (umbrales de densidad) y patrones "tóxicos" como groserías o intentos de evasión (por ejemplo, pruebas de "m i e r d d a") [y test\_check\_content.py82-118](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_content.py#L82-L118) También garantiza que los enlaces legales obligatorios sean [pruebas presentes/test\_check\_content.py48-69](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_content.py#L48-L69)
*   **Imágenes (`test_check_images.py`)**: Comprueba la ausencia de atributos `alternativos`, falta de `loading="lazy"` y uso de formatos heredados (JPG/PNG) en lugar de [pruebas WebP/test\_check\_images.py129-188](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_images.py#L129-L188)
*   **Botones y Formularios (`test_check_buttons.py`):** Detecta botones vacíos, formularios `sin` atributos de acción o formularios que apuntan a pruebas `sensibles /` de rutas [administrativas / test\_check\_buttons.py72-130](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_buttons.py#L72-L130)

### Pruebas específicas de navegador

El `módulo test_check_browser.py` utiliza `MagicMock` para simular el comportamiento de `los controladores web` de Selenium sin necesidad de un navegador activo.

*   **Errores en la consola JS**: Simula `driver.get_log('browser')` para asegurar que el auditor capture y limite el número de errores JS reportados basándose en `pruebas de AUDIT_JS_CONSOLE_MAX_ERRORS`[/test\_check\_browser.py17-45](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_browser.py#L17-L45)
*   **Interacciones con selenio**: Prueba `interact_buttons_selenium` simulando alertas de navegador no gestionadas que aparecen al hacer clic [en botones tests/test\_check\_browser.py60-79](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_browser.py#L60-L79)

**Fuentes:**[pruebas/test\_check\_content.py1-180](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_content.py#L1-L180)[pruebas/test\_check\_images.py1-188](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_images.py#L1-L188)[pruebas/test\_check\_browser.py1-79](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_check_browser.py#L1-L79)

## Integración con analizadores de IA

Las pruebas de integración verifican cómo el `Auditor de Calidad` se comunica con el microservicio `analizador de IA` y cómo gestiona los fallos.

### Flujo de detección semántica

Título: Flujo de datos de análisis semántico de IA

```mermaid
diagrama de flujo TD
    H["Respuesta JSON"]
    Yo["¿is_inoperative?"]
    J["Puntuación de la Fuerza 5"]
    K["Continúa con heurísticas"]
    subgrafo subGraph1 ["Servicio de Analizador de IA"]
        D["AIContentAnalyzer"]
        E["_has_strong_error_signature"]
        F["_looks_like_educational_content"]
        G["Clasificación de disparos cero"]
    fin
    subgrafo subGraph0 ["Auditor Central"]
        A["QualityAuditor.build_report"]
        B["¿AI_ANALYZER_URL set?"]
        C["POST /analyze"]
    fin
    A --> B
    B -->|" Sí"| C
    C --> D
    D --> E
    D --> F
    E --> G
    F --> G
    G --> H
    H --> yo
    Yo -->|" Cierto"| J
    Yo -->|" Falso"| K
```

### Pruebas de integración clave

*   **Fallo de conexión**: `test_ai_analyzer_connection_failure_fallback` asegura que si el servicio de IA está caído, el auditor continúa usando heurísticas estáticas sin pruebas de [fallo/test\_ai\_analyzer\_integration.py14-45](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_integration.py#L14-L45)
*   **Anulaciones semánticas**: `test_ai_non_inoperative_overrides_classic_heuristic_false_positive` confirma que si la IA identifica una página como documentación válida, sobrescribe una bandera estática de ["inoperativa" tests/test\_ai\_analyzer\_integration.py164-204](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_integration.py#L164-L204)
*   **Contenido malicioso**: Verifica que el spam o patrones maliciosos detectados por IA estén correctamente mapeados a `security_issues` y `content_issues`[tests/test\_ai\_analyzer\_integration.py106-161](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_integration.py#L106-L161)

**Fuentes:**[pruebas/test\_ai\_analyzer\_integration.py1-204](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_integration.py#L1-L204)[pruebas/test\_ai\_analyzer\_error\_context.py19-132](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_ai_analyzer_error_context.py#L19-L132)

## Selenio y pruebas estratégicas

La suite incluye pruebas para la capa de scraping, centradas específicamente en `SeleniumStrategy` y su capacidad para recuperar códigos de estado que normalmente están ocultos por navegadores headless.

### Detección 503 mediante respaldo

Dado que Selenium no proporciona códigos de estado HTTP de forma nativa, `SeleniumStrategy` realiza un fallback de `peticiones HEAD`.

*   `test_selenium_fallback_503_detection` (marcado como `@pytest.mark.slow`) utiliza `httpstat.us/503` para verificar que la estrategia identifica correctamente el estado 503, lo que luego activa una puntuación crítica en las pruebas de auditor[/test\_selenium\_503\_detection.py8-27](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_selenium_503_detection.py#L8-L27)

**Fuentes:**[pruebas/test\_selenium\_503\_detection.py1-27](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_selenium_503_detection.py#L1-L27)[scratch/test\_selenium\_503.py8-22](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scratch/test_selenium_503.py#L8-L22)

## Pruebas de endpoint API

El módulo `test_api_endpoints.py` utiliza `TestClient` y `unittest.mock` de FastAPI para validar la API del Dashboard sin una base de datos activa.

### Mapa de Cobertura API

Título: Ruta API hacia el mapeo de repositorios

```mermaid
diagrama de flujo LR
    subgrafo subGraph1 ["Repositorios simulados"]
        M1["dashboard.get_settings"]
        M2["dashboard.create_client"]
        M3["dashboard.delete_website"]
    fin
    subgrafo subGraph0 ["Rutas FastAPI"]
        R1["GET /settings"]
        R2["POST /clientes"]
        R3["ELIMINAR /websites/{id}"]
    fin
    R1 --> M1
    R2 --> M2
    R3 --> M3
```

### Puntos Finales Validados

*   **Configuración**: `GET /settings` y `PUT /settings` para gestionar cron [schedules globales de pruebas/test\_api\_endpoints.py19-50](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_api_endpoints.py#L19-L50)
*   **Clientes**: Operaciones CRUD para entidades clientes, asegurando que los datos de la carga útil se pasen correctamente a las pruebas del [repositorio/test\_api\_endpoints.py52-101](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_api_endpoints.py#L52-L101)
*   **Sitios web**: Creación y eliminación de sitios web objetivo, incluyendo la validación de `pruebas de cadenas de custom_cron`[/test\_api\_endpoints.py103-150](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_api_endpoints.py#L103-L150)

**Fuentes:**[pruebas/test\_api\_endpoints.py1-150](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_api_endpoints.py#L1-L150)

* * *

# Suite de pruebas de JavaScript

# Suite de pruebas de JavaScript

Archivos fuente relevantes

*   [Docker/panel de control/babel.config.json](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/babel.config.json)
*   [docker/dashboard/frontend/js/api.test.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/api.test.js)
*   [Docker/tablero de control/frontend/JS/i18n.test.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.test.js)
*   [docker/dashboard/frontend/js/scheduler.test.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/scheduler.test.js)
*   [Docker/Panel de control/jest.config.json](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/jest.config.json)

La suite de pruebas de JavaScript ofrece una cobertura completa para la interfaz basada en React y su lógica de soporte. Utiliza **Jest** como ejecutor de pruebas y **Babel** para la transpilación, asegurando que los módulos ES y componentes de React dirigidos al navegador se validen correctamente en un entorno Node.js.

## Configuración del entorno de pruebas

La infraestructura de pruebas está configurada para simular un entorno de navegador usando `jsdom`, lo que permite la manipulación del DOM y la simulación de eventos sin necesidad de un navegador físico.

### Babel & Montaje de la broma

La configuración sirve de puente entre el uso de ESM en el frontend (a través de `importaciones esm.sh`) y los requisitos del entorno de pruebas.

*   **Configuración de Babel**: Utiliza `@babel/preset-env` dirigido a la versión actual de Node y `@babel/preset-react` con el entorno automático para gestionar JSX [docker/dashboard/babel.config.json1-6](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/babel.config.json#L1-L6)
    
*   **Configuración Jest**:
    
*   **Entorno**: Configurado en `jsdom`[docker/dashboard/jest.config.json2](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/jest.config.json#L2-L2)
    
*   **Transformación**: Utiliza `babel-jest` para todos los archivos `.js` y `.jsx` [docker/dashboard/jest.config.json3-5](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/jest.config.json#L3-L5)
    
*   **Mapeo de módulos**: Un `moduleNameMapper` crítico traduce URLs `de esm.sh` remotas usadas en el código fuente (por ejemplo, `https://esm.sh/react@18.3.1`) en paquetes `locales de node_modules` durante la ejecución de pruebas [docker/dashboard/jest.config.json6-11](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/jest.config.json#L6-L11)
    

**Fuentes:**

*   [docker/dashboard/babel.config.json1-6](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/babel.config.json#L1-L6)
*   [docker/dashboard/jest.config.json1-13](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/jest.config.json#L1-L13)

* * *

## API de validación de clientes (`api.test.js`)

La `suite api.test.js` valida la capa de comunicación del frontend. Simula la API global `de fetch` para asegurar que las solicitudes se despachen con métodos, cabeceras y cargas útiles correctos.

### Escenarios clave de prueba

| Función | Lógica verificada |
| --- | --- |
| apiFetch | Valida el análisis JSON en el éxito docker/dashboard/frontend/js/api.test.js33-46 y la introducción de errores en códigos de estado no aceptables docker/dashboard/frontend/js/api.test.js63-71 |
| fetchWebsites | Asegura que client\_id parámetros de consulta se añadan correctamente a la URL docker/dashboard/frontend/js/api.test.js97-105 |
| triggerAudit | Verifica que una solicitud POST se envía al endpoint de auditoría web específico docker/dashboard/frontend/js/api.test.js107-115 |
| fetchRunIssues | Comprueba que los filtros de categoría y gravedad se transforman en cadenas de consulta docker/dashboard/frontend/js/api.test.js117-128 |
| exportClientReport | Valida la gestión de respuestas binarias de Blob para descargas de PDF: docker/dashboard/frontend/js/api.test.js144-154 |

### Flujo de datos: simulación de API

El siguiente diagrama ilustra cómo `api.test.js` aísla la lógica de la API de la red.

**Diagrama: Flujo de validación de solicitudes API**

```mermaid
diagrama de flujo TD
    subgrafo subGraph1 ["Espacio de Aserción"]
        D["expect(fetch).toHaveBeenCalledWith()"]
        E["Respuesta simulada"]
        F["expect(res).toEqual()"]
    fin
    subgrafo subGraph0 ["Espacio de prueba (Jest)"]
        A["api.test.js"]
        B["api.js Funciones"]
        C["global.fetch (Mock)"]
    fin
    Un -->|" Llamadas"| B
    B -->|" Llamadas"| C
    C -->|" Argumentos capturados"| D
    E -->|" Regresó a"| B
    B -->|" Resultado"| F
```

**Fuentes:**

*   [docker/dashboard/frontend/js/api.test.js1-156](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/api.test.js#L1-L156)

* * *

## Cobertura de Internacionalización (`i18n.test.js`)

La `suite i18n.test.js` prueba el `gancho I18nProvider` y `useI18n` usando `@testing-library/react`. Garantiza que la aplicación responda correctamente a los cambios de idioma y mantenga las preferencias del usuario.

### Detalles de implementación

*   **Persistencia de estado**: Las pruebas verifican que cambiar el lenguaje actualiza tanto `localStorage`[docker/dashboard/frontend/js/i18n.test.js82-94](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.test.js#L82-L94) como el `atributo lang` del `elemento <html>` [docker/dashboard/frontend/js/i18n.test.js96-108](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.test.js#L96-L108)
    
*   **Lógica de traducción**:
    
*   **Búsqueda exitosa**: Confirma que claves como `app.title` devolven la cadena correcta para el lenguaje [activo docker/dashboard/frontend/js/i18n.test.js35-42](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.test.js#L35-L42)
    
*   **Mecanismo de respaldo**: Si falta una clave, el sistema debe devolver la cadena de claves en bruto en lugar de bloquear [docker/dashboard/frontend/js/i18n.test.js44-51](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.test.js#L44-L51)
    
*   **Claves Anidadas**: Valida que el recorrido profundo de objetos (por ejemplo, `modals.close`) funciona tanto en inglés [como en español docker/dashboard/frontend/js/i18n.test.js110-122](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.test.js#L110-L122)
    

**Fuentes:**

*   [docker/dashboard/frontend/js/i18n.test.js1-149](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/i18n.test.js#L1-L149)

* * *

## Planificador y lógica cron (`scheduler.test.js`)

Esta suite se centra en la lógica compleja necesaria para conectar la interfaz de usuario fácil de programar auditorías con el formato técnico Cron utilizado por el backend.

### Funciones de utilidad de Cron

Las pruebas cubren el ciclo de vida de la transformación de un calendario:

1.  **ParseCron** convierte una cadena como `"15 14 1 5 *"` en un objeto `estructurado { min, hour, dom, month, dow }`[docker/dashboard/frontend/js/scheduler.test.js16-19](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/scheduler.test.js#L16-L19)
2.  **Detección de frecuencia**: `detectFrequency` analiza objetos cron para identificar patrones como "semanal", "monthly\_periodic" o "anual" [docker/dashboard/frontend/js/scheduler.test.js36-59](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/scheduler.test.js#L36-L59)
3.  **Gestión semanal de las reglas**:

*   `expandWeeklyRule`: Divide una regla de varios días (por ejemplo, `dow: "1,3"`) en objetos de regla [individuales docker/dashboard/frontend/js/scheduler.test.js78-84](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/scheduler.test.js#L78-L84)
*   `normalizeWeeklyRules`: Ordena las reglas cronológicamente por día de la semana [docker/dashboard/frontend/js/scheduler.test.js86-94](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/scheduler.test.js#L86-L94)

**Diagrama: Mapeo de entidades de lógica cron**

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["Espacio Backend"]
        CRON["'0 0 * * 1, 0 0 * * 3'"]
    fin
    subgrafo subGraph1 ["Espacio de Entidades de Código (scheduler.js)"]
        F1["creaReglaSemanal('1')"]
        F2["createWeeklyRule('3')"]
        F3["serializeCronRule()"]
        F4["splitCronRules()"]
    fin
    subgrafo subGraph0 ["Espacio de lenguaje natural"]
        NL["'Todos los lunes y miércoles'"]
    fin
    NL --> F1
    NL --> F2
    F1 --> F3
    F2 --> F3
    F3 --> CRON
    CRON --> F4
```

**Fuentes:**

*   [docker/dashboard/frontend/js/scheduler.test.js1-101](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/scheduler.test.js#L1-L101)

* * *

# Configuración-Referencia

# Referencia de configuración

Archivos fuente relevantes

*   [config/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/__init__.py)
*   [configuración/logging\_config.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/logging_config.py)
*   [configuración/settings.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py)
*   [docker/.env.ejemplo](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/.env.example)
*   [docker/dashboard/api/requirements.txt](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/requirements.txt)
*   [Docker/Panel de control/package.json](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/package.json)
*   [docker/scraper/Dockerfile](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/Dockerfile)
*   [Docker/raspador/requirements.txt](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/requirements.txt)
*   [requirements.txt](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/requirements.txt)
*   [compartido/auditor/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/__init__.py)
*   [compartido/base de datos/**init**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/__init__.py)

Esta página proporciona una referencia técnica completa para todas las variables del entorno, constantes del sistema y parámetros de configuración que rigen el comportamiento de la plataforma Web Auditor. El sistema sigue un enfoque de aplicación de 12 factores, utilizando principalmente `configuración/settings.py` para conectar variables del entorno con la lógica de la aplicación.

## Arquitectura de configuración

La configuración está centralizada en `configuración/settings.py`, que sirve como la única fuente de verdad tanto para la API del Scraper como para la del Dashboard. Define rutas de proyecto, tiempos de espera de red y los umbrales de lógica de negocio utilizados por la pipeline `de QualityAuditor`.

### Flujo de datos de configuración

El siguiente diagrama ilustra cómo las variables del entorno se propagan desde la capa de infraestructura hasta la lógica central de auditoría.

**Mapa de propagación de configuración**

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["Espacio de Entidades de Código: Ejecución"]
        QA["compartido/auditor/auditor_modules.py:QualityAuditor"]
        SEL["scraper/estrategias/selenium_strategy.py:SeleniumStrategy"]
        BS4["raspador/estrategias/bs4_strategy.py:EstrategiaBellaSoup"]
        IA["compartido/auditor/cheques/content.py:check_content_quality"]
    fin
    subgrafo subGraph1 ["Espacio de Entidades de Código: Configuración"]
        CONFIGURACIÓN["config/settings.py"]
    fin
    subgrafo subGraph0 ["Capa de Entorno"]
        ENV[".env / Docker ENV"]
    fin
    ENV --> AJUSTES
    CONFIGURACIÓN -->|" AUDIT_MIN_WORD_COUNT"| IA
    CONFIGURACIÓN -->|" SELENIUM_HEADLESS"| SEL
    CONFIGURACIÓN -->|" BS4_PARSER"| BS4
    CONFIGURACIÓN -->|" AUDIT_SCORE_EXCELLENT"| QA
```

**Fuentes:**[config/settings.py1-110](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L1-L110)[compartido/auditor/auditor\_modules.py6-9](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules.py#L6-L9)

* * *

## HTTP y parámetros de solicitud

Estos ajustes controlan el comportamiento de la red a bajo nivel para la `BeautifulSoupStrategy` y la conectividad general.

| Variable | Default | Descripción |
| --- | --- | --- |
| REQUEST\_TIMEOUT | 15 | Tiempo límite en segundos para las solicitudes HTTP config/settings.py14 |
| MAX\_RETRIES | 3 | Número de intentos de reintento por peticiones fallidas config/settings.py15 |
| RETRY\_DELAY | 2 | Retraso en segundos entre intentos config/settings.py16 |

El sistema utiliza un `USER_AGENT_POOL` para rotar cabeceras y evitar la detección [anti-bot config/settings.py19-26](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L19-L26) Los `DEFAULT_HEADERS` incluyen señales estándar de navegador como `Sec-CH-UA` y `Upgrade-Insecure-Requests`[config/settings.py28-43](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L28-L43)

* * *

## Selenium y opciones de navegador

Configuración para `SeleniumStrategy`, que gestiona sitios con mucho JavaScript (SPAs).

*   **Modo sin cabeza**: `SELENIUM_HEADLESS` (por defecto: `true`) activa la visibilidad de la [configuración/settings del navegador. py46](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L46-L46)
    
*   **Tiempos muertos**:
    
*   `SELENIUM_IMPLICIT_WAIT`: `5s`[config/settings.py47](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L47-L47)
    
*   `SELENIUM_PAGE_LOAD_TIMEOUT`: `30s`[config/settings.py48](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L48-L48)
    
*   **Interacciones**:
    
*   `AUDIT_BUTTONS_ENABLED`: Activar/desactivar pulsar botones para encontrar [contenido oculto config/settings.py78](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L78-L78)
    
*   `AUDIT_BUTTON_MAX_CLICKS`: Limita las interacciones a `5` para evitar bucles [infinitos config/settings.py79](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L79-L79)
    
*   **Observabilidad**:
    
*   `AUDIT_JS_LOGS_ENABLED`: Captura los registros de la consola del [navegador config/settings.py82](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L82-L82)
    
*   `AUDIT_JS_CONSOLE_MAX_ERRORS`: Limita los errores capturados a `25`[config/settings.py101](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L101-L101)
    

**Fuentes:**[config/settings.py45-50](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L45-L50)[config/settings.py77-83](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L77-L83)[config/settings.py100-101](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L100-L101)

* * *

## Umbrales de auditoría y puntuación

Estas variables definen los criterios de "Aprobado/Suspendido" para `el QualityAuditor` y cómo se categorizan las puntuaciones en la interfaz de usuario.

### Niveles de puntuación y puerta de lanzamiento

El `Auditor de Calidad` utiliza estos umbrales para determinar el estado final de una ejecución de auditoría.

| Constante | Valor | Impacto lógico |
| --- | --- | --- |
| AUDIT\_SCORE\_EXCELLENT | 85 | Puntuación >= 85 está marcada como "Excelente" config/settings.py73 |
| AUDIT\_SCORE\_GOOD | 70 | Puntuación >= 70 está marcada como "Good" config/settings.py74 |
| AUDIT\_RELEASE\_GATE\_MIN\_SCORE | 70 | Puntuación mínima requerida para aprobar la configuración de la puerta de lanzamiento/settings.py75 |

### Límites de contenido y SEO

*   **Recuento de palabras**: `AUDIT_MIN_WORD_COUNT` (Por defecto: `150`) define el umbral para "Thin Content" [config/settings.py85](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L85-L85)
*   **Densidad de palabras clave**: `AUDIT_KEYWORD_DENSITY_MAX` (por defecto: `0,08` u 8%) marca el potencial relleno de palabras [clave config/settings.py88](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L88-L88)
*   **Límites del rastreador**: `AUDIT_MAX_LINKS` (por defecto: `40`) y `AUDIT_MAX_DEPTH` (por defecto: `1`) limitan el `LinkCrawler` para evitar el agotamiento de [recursos config/settings.py67-68](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L67-L68)

**Fuentes:**[config/settings.py65-75](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L65-L75)[config/settings.py84-89](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L84-L89)

* * *

## Rutas de Sondas Administrativas

El auditor realiza una "Sonda de Administración" para comprobar la presencia de directorios sensibles expuestos usando solicitudes `HTTP HEAD`. Si `no se proporciona AUDIT_ADMIN_PATHS` en el entorno, el sistema utiliza por defecto una tupla de rutas comunes que incluyen `/admin`, `/wp-admin` y `/cpanel`.

**Implementación de la sonda de administrador**

```mermaid
diagrama de flujo LR
    Objetivo["Sitio web /camino"]
    subgrafo subGraph0 ["Espacio de Entidades de Código"]
        S["config/settings.py:AUDIT_ADMIN_PROBE_PATHS"]
        C["compartido/auditor/cheques/technical.py:check_admin_exposure"]
    fin
    S -->|" Lista de inyecciones"| C
    C -->|" HTTP HEAD"| Objetivo
```

**Fuentes:**[config/settings.py91-98](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L91-L98)

* * *

## Conexión con analizador de IA

`El QualityAuditor` se integra con el microservicio `analizador de IA` para realizar análisis semánticos.

*   **URL**: `AI_ANALYZER_URL` (Por defecto: `http://ai-analyzer:8080`) [config/settings.py104](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L104-L104)
*   **Tiempo de espera**: `AI_ANALYZER_TIMEOUT` (Por defecto: `6.0s`) [config/settings.py105](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L105-L105)
*   **Alternar**: `AI_ANALYZER_ENABLED` (Por defecto: `true`) [config/settings.py106](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L106-L106)

Cuando está activado, el auditor envía el texto de la página al servicio de IA para detectar si la página es una pantalla de "Mantenimiento", una página de "Aparcamiento" o contiene contenido "malicioso", lo que puede anular las puntuaciones heurísticas.

**Fuentes:**[config/settings.py103-107](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L103-L107)

* * *

## Configuración de registro

El registro se gestiona mediante `config/logging_config.py`, que inicializa los loggers estándar en Python según las siguientes configuraciones:

*   **Nivel**: `LOG_LEVEL` (Por defecto: `INFO)` [config/settings.py56](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L56-L56)
*   **Formato**: `%(asctime)s [%(levelname)s] %(name)s — %(message)s`[config/settings.py58](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L58-L58)
*   **Persistencia**: `LOG_TO_FILE` (por defecto: `true`) permite escribir en `logs/scraper.log`[config/settings.py57-59](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L57-L59)
*   **Rotación**: La función `setup_logger` implementa un `RotatingFileHandler` con un límite `de 5MB` y `3` [copias de seguridad config/logging\_config.py34-39](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/logging_config.py#L34-L39)

**Fuentes:**[config/settings.py55-60](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/settings.py#L55-L60)[config/logging\_config.py1-44](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/config/logging_config.py#L1-L44)

* * *

# Glosario

# Glosario

Archivos fuente relevantes

*   [docker/ai-analyzer/analyzer.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py)
*   [docker/dashboard/api/main.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/api/main.py)
*   [docker/dashboard/frontend/js/audit.js](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js)
*   [docker/db-init/01\_schema.sql](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql)
*   [Docker/raspador/entrypoint.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/entrypoint.py)
*   [Docker/raspador/scheduler.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py)
*   [Docker/raspador/service.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py)
*   [Scraper/estrategias/beautifulsoup\_strategy.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/beautifulsoup_strategy.py)
*   [Scraper/estrategias/selenium\_strategy.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/selenium_strategy.py)
*   [compartido/auditor/auditor\_modules/core.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py)
*   [compartido/auditor/cheques/**inIT**.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/__init__.py)
*   [compartido/auditor/cheques/buttons.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/buttons.py)
*   [compartido/auditor/cheques/content.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/content.py)
*   [compartido/auditor/cheques/images.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/images.py)
*   [compartido/auditor/cheques/technical.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/checks/technical.py)
*   [compartido/auditor/scoring.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py)
*   [compartido/base de datos/models.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/database/models.py)
*   [Pruebas/test\_inoperative\_pages.py](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_inoperative_pages.py)

Esta página proporciona una referencia completa de términos técnicos, conceptos de dominio y jerga arquitectónica utilizada en toda la base de código de Web Auditor. Sirve como puente entre la lógica de negocio de alto nivel (por ejemplo, "Sitio inoperativo") y detalles específicos de implementación (por ejemplo, `heurísticas is_inoperative`).

## Conceptos del dominio del sistema

### Ejecución de auditoría (Ejecución)

Una única ejecución de la cadena de auditoría contra una URL específica. Captura una instantánea de la calidad del sitio web en un momento concreto.

*   **Implementación**: Representado por el modelo `AuditRun` en la base de datos [docker/db-init/01\_schema.sql54-91](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql#L54-L91)
*   **Flujo de datos**: Creado por `AuditService.process_website`[docker/scraper/service.py110](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L110-L110) poblado por `QualityAuditor.build_report`[compartido/auditor/auditor\_modules/core.py113](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L113-L113) y persistido a través del repositorio scraper.

### Sitio inoperativo (Sitio No Operativo)

Un estado donde una página web es técnicamente accesible pero funcionalmente inútil para un visitante. Esto incluye páginas de error HTTP (404, 500), plantillas de modo mantenimiento, dominios aparcados o marcadores de posición "Próximamente".

*   **Detección**: Gestionado por `QualityAuditor` usando una combinación de códigos de estado HTTP, patrones de regex de título/cuerpo y análisis semántico de IA [compartido/auditor/auditor\_modules/core.py149-210](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L149-L210)
*   **Impacto**: Activa una puntuación fija de `5/100` y bloquea automáticamente el [Release Gate compartido/auditor/scoring.py82-83](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L82-L83)

### Puerta de lanzamiento

Un mecanismo de seguridad que determina si una versión web está "lista para producción".

*   **Lógica**: Definida en `evaluate_release_gate`. Verifica vulnerabilidades críticas de seguridad, enlaces rotos, fallos de formularios y la bandera "Inoperative Site[" shared/auditor/scoring.py95-143](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/scoring.py#L95-L143)
*   **Entidad de código**: `report.release_blocked` (booleana).

* * *

## Jerga técnica y abreviaturas

### BFS Crawler

El rastreador "Breadth-First Search" se utiliza para validar enlaces internos y externos.

*   **Función**: `check_links_recursive`[compartido/auditor/auditor\_modules/core.py24-25](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L24-L25)
*   **Restricciones**: Regido por `AUDIT_MAX_RECURSIVE_LINKS` y `AUDIT_MAX_CRAWL_DEPTH` configuraciones.

### Detección de SPA (Autoclasificación)

El proceso para determinar si un sitio es una aplicación de página única (React, Vue, etc.) para elegir la estrategia correcta de scraping.

*   **Lógica**: `AuditService.classify_and_scrape`[docker/scraper/service.py22-102](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L22-L102)
*   **Indicadores**: Presencia de nodos raíz como `#app` o `#__next` con contenido vacío, o proporciones altas de JS-texto [docker/scraper/service.py54-76](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L54-L76)

### Anclajes semánticos

Cadenas de texto predefinidas usadas por el AI Analyzer para calcular la similitud del coseno frente al contenido extraído.

*   **Categorías**: `ERROR_ANCHORS`, `EDUCATIONAL_ANCHORS` y `MALICIOUS_ANCHORS`[docker/ai-analyzer/analyzer.py19-194](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L19-L194)

* * *

## Mapeo: Lenguaje natural a entidades de código

Los siguientes diagramas asignan los requisitos conceptuales a las clases y funciones específicas que los implementan.

### Mapeo del ciclo de vida de auditoría

Este diagrama muestra cómo una "Solicitud de Auditoría" se mueve desde la interfaz de usuario a través de la lógica del backend hacia la base de datos.

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["Entidades de código"]
        F1["EstrategiaHermosaSopa"]
        F2["Estrategia de Selenio"]
        G1["check_security()"]
        G2["check_seo()"]
        G3["calculate_score()"]
    fin
    subgrafo subGraph1 ["Servicio de Scraper (Python)"]
        C["PostgreSQL: tabla de sitios web"]
        D["AuditScheduler._tick()"]
        E["AuditService.process_website()"]
        F["ScraperContext.execute()"]
        G["QualityAuditor.build_report()"]
        H["db.save_audit_run()"]
    fin
    subgrafo subGraph0 ["Frontend (React)"]
        R["UI: Botón de Auditoría de Activación"]
        B["api.js"]
    fin
    Un -->|" fetch(triggerAudit)"| B
    B -->|" pending_audit = VERDADERO"| C
    D -->|" get_pending_audit_websites()"| C
    D -->|" llama"| E
    E -->|" 1. Raspar"| F
    E -->|" 2. Auditoría"| G
    E -->|" 3. Persistir"| H
    F --> F1
    F --> F2
    G --> G1
    G --> G2
    G --> G3
```

**Fuentes**: [docker/dashboard/frontend/js/audit.js5](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/dashboard/frontend/js/audit.js#L5-L5)[docker/scraper/scheduler.py87-88](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L87-L88)[docker/scraper/service.py104-160](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/service.py#L104-L160)[compartido/auditor/auditor\_modules/core.py113-118](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L113-L118)

### Mapeo de detección inoperativo

Este diagrama ilustra cómo el sistema distingue entre una página de error real y una página educativa sobre errores (por ejemplo, un artículo de Wikipedia sobre "404").

```mermaid
diagrama de flujo LR
    subgrafo subGraph2 ["Espacio de Decisión"]
        IS_ERR["is_inoperative = Verdadero"]
        IS_OK["is_inoperative = Falso"]
    fin
    subgrafo subGraph1 ["Lógica: QualityAuditor.build_report"]
        SC["Código de estado >= 400?"]
        HEU["Patrones Heurísticos (Regex)"]
        EDU["Lista blanca de contexto educativo"]
        IA["AI_ANALYZER_URL/analizar"]
    fin
    subgrafo subGraph0 ["Espacio de entrada"]
        HTML["HTML en bruto + código de estado"]
    fin
    HTML --> SC
    SC -->|" Sí"| IS_ERR
    SC -->|" No (200 OK)"| HEU
    HEU -->|" Coincide con el patrón de error"| EDU
    EDU -->|" Contiene 'RFC' o 'Wikipedia'"| IS_OK
    EDU -->|" Sin coincidencia en la lista blanca"| IA
    IA -->|" Similitud semántica > 0,85"| IS_ERR
```

**Fuentes**: [shared/auditor/auditor\_modules/core.py149-210](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L149-L210)[docker/ai-analyzer/analyzer.py197-220](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L197-L220)[tests/test\_inoperative\_pages.py174-185](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/tests/test_inoperative_pages.py#L174-L185)

* * *

## Diccionario de componentes

| Término | Puntero de archivo / clase | Descripción |
| --- | --- | --- |
| AuditScheduler | docker/scraper/scheduler.py13 | Daemon que consulta la base de datos y gestiona la ejecución basada en crons para sitios activos e inactivos. |
| EstrategiaBellaSopa | scraper/strategies/beautifulsoup\_strategy.py14 | Scraper HTML rápido y estático usando solicitudes. |
| SeleniumStrategy | scraper/strategies/selenium\_strategy.py18 | Scraper de Chrome sin interfaz para sitios con mucho JavaScript. |
| Auditor de Calidad | compartido/auditor/auditor\_modules/core.py101 | El motor principal que ejecuta todos los módulos check\_ y genera el informe. |
| AIContentAnalyzer | docker/ai-analyzer/analyzer.py197 | Servicio de PLN utilizando MiniLM y XLM-RoBERTa para la validación semántica. |
| IssueRow | docker/dashboard/api/main.py33 | Componente Frontend React para mostrar fallos individuales de auditoría. |
| AuditRunSection | docker/db-init/01\_schema.sql103 | Tabla de base de datos que almacena resultados para categorías específicas (SEO, Seguridad, etc.). |

**Fuentes**: [docker/scraper/scheduler.py13](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/scraper/scheduler.py#L13-L13)[scraper/strategies/beautifulsoup\_strategy.py14](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/beautifulsoup_strategy.py#L14-L14)[scraper/strategies/selenium\_strategy.py18](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/scraper/strategies/selenium_strategy.py#L18-L18)[compartido/auditor/auditor\_modules/core.py101](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/shared/auditor/auditor_modules/core.py#L101-L101)[docker/ai-analyzer/analyzer.py197](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/ai-analyzer/analyzer.py#L197-L197)[docker/db-init/01\_schema.sql103](https://github.com/LuisVilRiv/comprobador-de-paginas-web/blob/f18e4242/docker/db-init/01_schema.sql#L103-L103)