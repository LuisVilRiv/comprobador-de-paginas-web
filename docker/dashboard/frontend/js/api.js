/**
 * ============================================================================
 * API.JS - Capa de Comunicación con el Backend
 * ============================================================================
 * 
 * DESCRIPCIÓN:
 * Este módulo centraliza todas las llamadas HTTP a la API REST del backend.
 * Proporciona una interfaz consistente y tipada para todas las operaciones
 * CRUD y de consulta de datos del dashboard de auditoría web.
 * 
 * ARQUITECTURA:
 * - Wrapper genérico (apiFetch) para manejar peticiones fetch
 * - Funciones específicas organizadas por entidad (clientes, websites, runs)
 * - Manejo centralizado de errores y respuestas
 * - Serialización/deserialización automática de JSON
 * 
 * ENDPOINTS DEL BACKEND:
 * - /api/clients - Gestión de clientes
 * - /api/websites - Gestión de sitios web
 * - /api/runs - Historial de auditorías
 * - /api/summary - Resumen de métricas
 * - /api/settings - Configuración del scheduler
 * 
 * MANEJO DE ERRORES:
 * Todas las funciones lanzan errores con formato:
 * "API {statusCode}: {mensajeDeError}"
 * 
 * EJEMPLO DE USO:
 * ```javascript
 * import { fetchClients, createClient } from "./js/api.js";
 * 
 * // Obtener lista de clientes
 * const clients = await fetchClients();
 * 
 * // Crear nuevo cliente
 * try {
 *   const newClient = await createClient({ name: "Nuevo Cliente" });
 *   console.log("Cliente creado:", newClient);
 * } catch (error) {
 *   console.error("Error:", error.message);
 * }
 * ```
 * 
 * @version 2.0.0
 * @author Web Auditor Team
 * @since 2024
 */

/**
 * ═══════════════════════════════════════════════════════════════════════════
 * WRAPPER GENÉRICO DE FETCH
 * ═══════════════════════════════════════════════════════════════════════════
 * Función de bajo nivel que maneja todas las peticiones HTTP al backend.
 * Centraliza la lógica de:
 * - Construcción de URL (/api + path)
 * - Configuración de headers (Content-Type: application/json)
 * - Serialización de cuerpo de petición
 * - Manejo de errores HTTP
 * - Parseo de respuesta JSON
 * 
 * @param {string} path - Ruta relativa del endpoint (ej: "/clients", "/websites/123")
 * @param {string} [method="GET"] - Método HTTP (GET, POST, PUT, DELETE)
 * @param {object|null} [body=null] - Cuerpo de la petición (se serializa a JSON)
 * @returns {Promise<any>} Respuesta parseada como JSON
 * @throws {Error} Si la respuesta HTTP no es exitosa (status >= 400)
 * 
 * @example
 * // GET request
 * const data = await apiFetch("/clients");
 * 
 * // POST request with body
 * const newClient = await apiFetch("/clients", "POST", { name: "John" });
 * 
 * // PUT request
 * await apiFetch("/clients/123", "PUT", { name: "Jane" });
 */
export const apiFetch = async (path, method = "GET", body = null) => {
  // Configurar opciones de fetch
  const opts = { 
    method, 
    headers: { "Content-Type": "application/json" } 
  };
  
  // Añadir cuerpo si existe (serializado a JSON)
  if (body) opts.body = JSON.stringify(body);
  
  // Realizar petición al endpoint (/api + path)
  const res = await fetch(`/api${path}`, opts);
  
  // Manejar errores HTTP (4xx, 5xx)
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  
  // Retornar respuesta parseada como JSON
  return res.json();
};

/**
 * ═══════════════════════════════════════════════════════════════════════════
 * GESTIÓN DE CLIENTES (CRUD)
 * ═══════════════════════════════════════════════════════════════════════════
 * Funciones para operaciones CRUD sobre la entidad "Cliente".
 * Un cliente representa una entidad que posee uno o más sitios web para auditar.
 * 
 * Estructura de un cliente:
 * {
 *   id: string,           // UUID del cliente
 *   name: string,         // Nombre del cliente
 *   email?: string,       // Email de contacto
 *   phone?: string,       // Teléfono de contacto
 *   company?: string,     // Empresa
 *   notes?: string,       // Notas adicionales
 *   custom_cron?: string  // Programación CRON personalizada
 * }
 */

/**
 * Obtiene la lista completa de todos los clientes
 * @returns {Promise<Array>} Array de objetos cliente
 */
export const fetchClients = () => apiFetch("/clients");

/**
 * Crea un nuevo cliente
 * @param {object} data - Datos del cliente a crear
 * @returns {Promise<object>} Cliente creado con ID generado
 */
export const createClient = (data) => apiFetch("/clients", "POST", data);

/**
 * Actualiza los datos de un cliente existente
 * @param {string} id - ID del cliente a actualizar
 * @param {object} data - Nuevos datos del cliente
 * @returns {Promise<object>} Cliente actualizado
 */
export const updateClient = (id, data) => apiFetch(`/clients/${id}`, "PUT", data);

/**
 * Elimina un cliente (y todos sus websites asociados)
 * @param {string} id - ID del cliente a eliminar
 * @returns {Promise<void>}
 */
export const deleteClient = (id) => apiFetch(`/clients/${id}`, "DELETE");

/**
 * ═══════════════════════════════════════════════════════════════════════════
 * GESTIÓN DE WEBSITES (CRUD + AUDITORÍAS)
 * ═══════════════════════════════════════════════════════════════════════════
 * Funciones para operaciones CRUD sobre la entidad "Website".
 * Un website representa una URL específica que será auditada periódicamente.
 * 
 * Estructura de un website:
 * {
 *   website_id: string,    // UUID del website
 *   client_id?: string,    // ID del cliente propietario (opcional)
 *   url: string,           // URL completa a auditar
 *   label?: string,        // Alias/etiqueta para identificar el website
 *   strategy: string,      // Estrategia de scraping: "auto", "selenium", "bs4"
 *   active: boolean,       // Si está activo para auditorías automáticas
 *   custom_cron?: string   // Programación CRON personalizada
 * }
 */

/**
 * Obtiene la lista de websites, opcionalmente filtrada por cliente
 * @param {string} [clientId=""] - ID del cliente para filtrar (vacío = todos)
 * @returns {Promise<Array>} Array de objetos website con datos de cliente
 */
export const fetchWebsites = (clientId = "") =>
  apiFetch(clientId ? `/websites?client_id=${clientId}` : "/websites");

/**
 * Crea un nuevo website para auditoría
 * @param {object} data - Datos del website (url, client_id, strategy, etc.)
 * @returns {Promise<object>} Website creado con ID generado
 */
export const createWebsite = (data) => apiFetch("/websites", "POST", data);

/**
 * Actualiza la configuración de un website existente
 * @param {string} id - ID del website a actualizar
 * @param {object} data - Nuevos datos del website
 * @returns {Promise<object>} Website actualizado
 */
export const updateWebsite = (id, data) => apiFetch(`/websites/${id}`, "PUT", data);

/**
 * Elimina un website del sistema de auditoría
 * @param {string} id - ID del website a eliminar
 * @returns {Promise<void>}
 */
export const deleteWebsite = (id) => apiFetch(`/websites/${id}`, "DELETE");

/**
 * Inicia una auditoría manual e inmediata para un website específico
 * @param {string} id - ID del website a auditar
 * @returns {Promise<object>} Información de la auditoría iniciada
 */
export const triggerAudit = (id) => apiFetch(`/websites/${id}/audit`, "POST");

/**
 * Obtiene el historial de ejecuciones (runs) de un website
 * @param {string} id - ID del website
 * @param {number} [limit=5] - Número máximo de ejecuciones a retornar
 * @returns {Promise<Array>} Array de objetos run (ejecuciones de auditoría)
 */
export const fetchWebsiteRuns = (id, limit = 5) =>
  apiFetch(`/websites/${id}/runs?limit=${limit}`);

/**
 * ═══════════════════════════════════════════════════════════════════════════
 * GESTIÓN DE EJECUCIONES / AUDITORÍAS (LECTURA)
 * ═══════════════════════════════════════════════════════════════════════════
 * Funciones para obtener detalles de ejecuciones de auditoría individuales.
 * Cada "run" representa una auditoría completada o en progreso.
 * 
 * Estructura de un run:
 * {
 *   run_id: string,        // UUID de la ejecución
 *   website_id: string,    // ID del website auditado
 *   status: string,        // "running", "completed", "failed", "blocked"
 *   score: number,         // Puntuación total (0-100)
 *   started_at: number,    // Timestamp de inicio
 *   completed_at?: number  // Timestamp de finalización
 * }
 */

/**
 * Obtiene los detalles completos de una ejecución de auditoría
 * @param {string} runId - ID de la ejecución (run)
 * @returns {Promise<object>} Detalles del run con métricas y estado
 */
export const fetchRunDetail = (runId) => apiFetch(`/runs/${runId}`);

/**
 * Obtiene el desglose por secciones de una auditoría
 * Cada sección representa un área de evaluación (SEO, Seguridad, etc.)
 * @param {string} runId - ID de la ejecución
 * @returns {Promise<Array>} Array de secciones con su estado individual
 */
export const fetchRunSections = (runId) => apiFetch(`/runs/${runId}/sections`);

/**
 * Obtiene las incidencias/problemas detectados en una auditoría
 * Permite filtrar por categoría y severidad para análisis específicos
 * @param {string} runId - ID de la ejecución
 * @param {string|null} [category=null] - Filtrar por categoría (ej: "security", "seo")
 * @param {string|null} [severity=null] - Filtrar por severidad (ej: "high", "medium", "low")
 * @returns {Promise<Array>} Array de incidencias con detalles y sugerencias
 */
export const fetchRunIssues = (runId, category = null, severity = null) => {
  // Construir query string con parámetros opcionales
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (severity) params.set("severity", severity);
  const qs = params.toString();
  return apiFetch(`/runs/${runId}/issues${qs ? "?" + qs : ""}`);
};

/**
 * ═══════════════════════════════════════════════════════════════════════════
 * RESUMEN GLOBAL DEL DASHBOARD
 * ═══════════════════════════════════════════════════════════════════════════
 * Obtiene métricas agregadas para mostrar en el dashboard principal.
 * 
 * Estructura del resumen:
 * {
 *   active_websites: number,      // Total de websites activos
 *   excellent_count: number,      // Websites con score >= 90
 *   next_active: number,          // Timestamp próximo ciclo activos
 *   next_inactive: number         // Timestamp próximo ciclo inactivos
 * }
 */

/**
 * Obtiene el resumen de métricas globales del sistema
 * @returns {Promise<object>} Objeto con métricas agregadas
 */
export const fetchSummary = () => apiFetch("/summary");

/**
 * ═══════════════════════════════════════════════════════════════════════════
 * CONFIGURACIÓN DEL SCHEDULER (PROGRAMADOR)
 * ═══════════════════════════════════════════════════════════════════════════
 * Funciones para gestionar la programación de auditorías automáticas.
 * Permite configurar ciclos de escaneo globales, por cliente o por website.
 * 
 * Estructura de configuración:
 * {
 *   cron_active: string,      // Expresión CRON para websites activos
 *   cron_inactive: string,    // Expresión CRON para websites inactivos
 *   next_active: number,      // Próxima ejecución para activos (timestamp)
 *   next_inactive: number     // Próxima ejecución para inactivos (timestamp)
 * }
 */

/**
 * Obtiene la configuración actual del programador de auditorías
 * @returns {Promise<object>} Configuración global de programación
 */
export const fetchSettings = () => apiFetch("/settings");

/**
 * Guarda/actualiza la configuración del programador
 * @param {object} data - Nueva configuración (cron expressions)
 * @returns {Promise<object>} Configuración guardada
 */
export const saveSettings = (data) => apiFetch("/settings", "PUT", data);

/**
 * ═══════════════════════════════════════════════════════════════════════════
 * EXPORTACIÓN DE REPORTES
 * ═══════════════════════════════════════════════════════════════════════════
 * Funciones para generar y descargar reportes en formato PDF.
 */

/**
 * Genera y descarga un reporte PDF completo de un cliente
 * Incluye todas las auditorías de sus websites asociados
 * @param {string} clientId - ID del cliente para el reporte
 * @returns {Promise<Blob>} Blob del archivo PDF para descarga
 * @throws {Error} Si falla la generación del reporte
 */
export const exportClientReport = async (clientId) => {
  // Fetch directo sin wrapper apiFetch porque esperamos un Blob (no JSON)
  const res = await fetch(`/api/clients/${clientId}/export`);
  
  // Manejar errores HTTP
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  
  // Retornar como Blob para descarga
  return await res.blob();
};
