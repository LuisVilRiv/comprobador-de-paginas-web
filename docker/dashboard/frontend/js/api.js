/**
 * api.js — Capa de comunicación con el backend.
 * Centraliza todas las llamadas fetch a la API REST.
 */

/**
 * Wrapper genérico de fetch hacia la API.
 * @param {string} path - Ruta relativa (ej. "/clients")
 * @param {string} method - Método HTTP
 * @param {object|null} body - Cuerpo de la petición
 * @returns {Promise<any>} - Respuesta JSON
 */
export const apiFetch = async (path, method = "GET", body = null) => {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`/api${path}`, opts);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
};

// ── Clientes ──────────────────────────────────────────────────────────────────

export const fetchClients = () => apiFetch("/clients");
export const createClient = (data) => apiFetch("/clients", "POST", data);
export const updateClient = (id, data) => apiFetch(`/clients/${id}`, "PUT", data);
export const deleteClient = (id) => apiFetch(`/clients/${id}`, "DELETE");

// ── Websites ──────────────────────────────────────────────────────────────────

export const fetchWebsites = (clientId = "") =>
  apiFetch(clientId ? `/websites?client_id=${clientId}` : "/websites");
export const createWebsite = (data) => apiFetch("/websites", "POST", data);
export const updateWebsite = (id, data) => apiFetch(`/websites/${id}`, "PUT", data);
export const deleteWebsite = (id) => apiFetch(`/websites/${id}`, "DELETE");
export const triggerAudit = (id) => apiFetch(`/websites/${id}/audit`, "POST");
export const fetchWebsiteRuns = (id, limit = 5) =>
  apiFetch(`/websites/${id}/runs?limit=${limit}`);

// ── Runs / auditorías ─────────────────────────────────────────────────────────

export const fetchRunDetail = (runId) => apiFetch(`/runs/${runId}`);
export const fetchRunSections = (runId) => apiFetch(`/runs/${runId}/sections`);
export const fetchRunIssues = (runId, category = null, severity = null) => {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (severity) params.set("severity", severity);
  const qs = params.toString();
  return apiFetch(`/runs/${runId}/issues${qs ? "?" + qs : ""}`);
};

// ── Resumen global ────────────────────────────────────────────────────────────

export const fetchSummary = () => apiFetch("/summary");

// ── Configuración (scheduler) ─────────────────────────────────────────────────

export const fetchSettings = () => apiFetch("/settings");
export const saveSettings = (data) => apiFetch("/settings", "PUT", data);
