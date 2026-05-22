/**
 * ============================================================================
 * APP.JS - Componente Principal del Dashboard
 * ============================================================================
 * 
 * DESCRIPCIÓN:
 * Este archivo contiene el componente principal de la aplicación React para el
 * dashboard de auditoría web. Gestiona el estado global, las operaciones CRUD
 * para clientes y sitios web, las auditorías, la programación de tareas, y la
 * interfaz de usuario completa.
 * 
 * ARQUITECTURA:
 * - Patrón: Componentes funcionales con Hooks de React
 * - Gestión de estado: useState para estado local
 * - Efectos secundarios: useEffect para ciclo de vida y polling
 * - Internacionalización: Context API a través de i18n.js
 * - Tours guiados: Driver.js para walkthroughs interactivos
 * 
 * MÓDULOS RELACIONADOS:
 * - api.js: Funciones asíncronas para comunicación con el backend
 * - i18n.js: Sistema de traducción español/inglés
 * - audit.js: Hook personalizado para detalles de auditoría
 * - websites.js: Componentes de tabla y modal de websites
 * - scheduler.js: Modal de programación de auditorías
 * - modals.js: Componentes modales reutilizables
 * 
 * ESTADOS PRINCIPALES:
 * - summary: Resumen de métricas (webs activas, puntuaciones excelentes)
 * - websites: Lista de sitios web monitoreados
 * - clients: Lista de clientes
 * - clientId: Filtro actual por cliente
 * - query: Término de búsqueda actual
 * - settings: Configuración global de programación
 * - theme: Tema claro/oscuro
 * - showTourMenu: Estado del menú desplegable de tours
 * 
 * @version 2.1.0
 * @author Web Auditor Team
 * @since 2024
 */

import React, { useEffect, useMemo, useState, useCallback } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";

// Importaciones de módulos de la aplicación
import {
  fetchSummary, fetchClients, fetchWebsites, fetchSettings, saveSettings,
  createClient, updateClient, deleteClient, createWebsite, updateWebsite,
  deleteWebsite, triggerAudit, exportClientReport,
} from "./js/api.js";
import { useAuditDetail } from "./js/audit.js";
import { WebsitesTable, WebsiteDetailModal } from "./js/websites.js";
import { SchedulerModal } from "./js/scheduler.js";
import {
  DeleteConfirmModal, AddClientModal, EditClientModal,
  AddWebsiteModal, EditWebsiteModal,
} from "./js/modals.js";
import { I18nProvider, useI18n } from "./js/i18n.js";

// ── HELPERS ───────────────────────────────────────────────────────────────────

/**
 * Formatea un timestamp UTC a una cadena de fecha/hora en la zona horaria de España.
 * @param {number} ts - Timestamp de Unix en segundos.
 * @param {string} lang - Idioma actual ('es' o 'en').
 * @returns {string} - La fecha y hora formateada (ej: "(25/07/2024 a las 10:00h)").
 */
function formatTimestampInSpanishTime(ts, lang) {
    if (!ts) return "";
    const date = new Date(ts * 1000);

    const options = {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit',
        hour12: false,
        timeZone: 'Europe/Madrid'
    };

    const formatter = new Intl.DateTimeFormat(lang === 'es' ? 'es-ES' : 'en-GB', options);
    const formattedDate = formatter.format(date);
    
    const parts = formattedDate.split(',');
    const datePart = parts[0] ? parts[0].trim() : "";
    const timePart = parts[1] ? parts[1].trim() : "";

    if (lang === 'es') {
      return `(${datePart} a las ${timePart}h)`;
    }
    return `(${datePart} at ${timePart}h)`;
}

// ── COMPONENTE PRINCIPAL ─────────────────────────────────────────────────────

function App() {
  const { t, lang, toggleLang } = useI18n();

  // Estados de datos principales
  const [summary, setSummary] = useState({});
  const [websites, setWebsites] = useState([]);
  const [clients, setClients] = useState([]);
  const [settings, setSettings] = useState({ cron_active: "", cron_inactive: "" });

  // Estados de UI y filtros
  const [clientId, setClientId] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [timers, setTimers] = useState({ active: "", inactive: "", active_target: "", inactive_target: "" });
  const [now, setNow] = useState(new Date());
  const [selectedWebsite, setSelectedWebsite] = useState(null);
  const [auditingIds, setAuditingIds] = useState(new Set());
  
  // Estados de modales
  const [deleteConfirm, setDeleteConfirm] = useState({ show: false, type: "", id: "", name: "", input: "" });
  const [showAddClient, setShowAddClient] = useState(false);
  const [showAddWebsite, setShowAddWebsite] = useState(false);
  const [showEditClient, setShowEditClient] = useState(false);
  const [showEditWebsite, setShowEditWebsite] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showTourMenu, setShowTourMenu] = useState(false);

  // Estados de formularios
  const [newClientForm, setNewClientForm] = useState({ name: "", email: "", phone: "", company: "", notes: "" });
  const [newWebsiteForm, setNewWebsiteForm] = useState({ client_id: "", url: "", label: "", strategy: "auto", active: true });
  const [editClientForm, setEditClientForm] = useState(null);
  const [editWebsiteForm, setEditWebsiteForm] = useState(null);

  const { runs, runSections, runIssues, loadRuns, toggleSections } = useAuditDetail();

  const loadAll = async () => {
    setLoading(true);
    try {
      const [s, c, w, cfg] = await Promise.all([
        fetchSummary(),
        fetchClients(),
        fetchWebsites(clientId),
        fetchSettings()
      ]);
      setSummary(s || {});
      setClients(c || []);
      setWebsites(w || []);
      setSettings(cfg || { cron_active: "", cron_inactive: "" });
    } catch (err) { setFormError(err.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadAll(); }, [clientId]);
  
  // Polling para auditorías en curso
  useEffect(() => {
    const hasRunning = websites.some(w => w.run_status === "running" || auditingIds.has(w.website_id));
    if (!hasRunning) return;

    const id = setInterval(loadAll, 3000);
    return () => clearInterval(id);
  }, [websites, auditingIds]);

  // Actualización de cronómetros y fechas de próxima ejecución
  useEffect(() => {
    const formatDiff = (ts) => {
      if (!ts) return "-";
      const diff = new Date(ts * 1000) - new Date();
      if (diff <= 0) return "...";
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff / 3600000) % 24);
      const m = Math.floor((diff / 60000) % 60);
      const s = Math.floor((diff / 1000) % 60);
      return `${d > 0 ? `${d}d ` : ''}${h}h ${m}m ${s}s`;
    };
    
    const tick = () => {
      setNow(new Date());
      setTimers({
        active: formatDiff(settings.next_active),
        inactive: formatDiff(settings.next_inactive),
        active_target: formatTimestampInSpanishTime(settings.next_active, lang),
        inactive_target: formatTimestampInSpanishTime(settings.next_inactive, lang)
      });
    };
    
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [settings, lang]);

  const filtered = useMemo(() => websites.filter(w => {
    const text = `${w.url} ${w.label || ""} ${w.client_name || ""}`.toLowerCase();
    return text.includes(query.toLowerCase());
  }), [websites, query]);

  const notify = (msg) => { setSuccessMessage(msg); setTimeout(() => setSuccessMessage(""), 4000); };

  const handleAuditWebsite = async (website) => {
    const id = website.website_id;
    setAuditingIds(prev => new Set(prev).add(id));
    try {
      await triggerAudit(id);
      notify(`${t("app.audit_scheduled")} ${website.url}`);
      await loadAll();
    } catch (err) { setFormError(err.message); }
    finally { setAuditingIds(prev => { const s = new Set(prev); s.delete(id); return s; }); }
  };

  const handleSaveSettings = async (newSettings) => {
    try {
      await saveSettings(newSettings);
      notify(t("app.schedule_saved"));
      await loadAll();
    } catch (err) { setFormError(err.message); }
  };

  const handleSaveEntityCron = async (newCron, type, entity) => {
    try {
      const normalizedCron = (newCron && newCron.trim()) ? newCron.trim() : null;
      if (type === "client") await updateClient(entity.id, { custom_cron: normalizedCron });
      else await updateWebsite(entity.website_id, { custom_cron: normalizedCron });
      notify(t("app.schedule_saved"));
      await loadAll();
    } catch (err) { setFormError(err.message); }
  };

  // Theme (light/dark)
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "dark");
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme === "light" ? "light" : "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => (t === "light" ? "dark" : "light"));

  // Tour logic
  const createDriver = useCallback((steps, onDestroyCallback) => {
    if (!window.driver || !window.driver.js || !window.driver.js.driver) return null;
    return window.driver.js.driver({ showProgress: true, nextBtnText: t("tour.next"), prevBtnText: t("tour.prev"), doneBtnText: t("tour.done"), steps: steps, onDestroyed: onDestroyCallback });
  }, [t]);

  const fullTourSteps = useCallback(() => ([ { popover: { title: t("tour.step_welcome_title"), description: t("tour.step_welcome_desc") } }, { element: '#tour-toggles', popover: { title: t("tour.step_toggles_title"), description: t("tour.step_toggles_desc"), side: "bottom", align: 'end' } }, { element: '#tour-global-settings', popover: { title: t("tour.step_global_config_title"), description: t("tour.step_global_config_desc"), side: "bottom", align: 'end' } }, { element: '#tour-cron-manager', popover: { title: t("tour.step_cron_title"), description: t("tour.step_cron_desc"), side: "left", align: 'start' }, onHighlightStarted: () => { setShowSettings(true); } }, { element: '#tour-cron-frequency', popover: { title: t("tour.step_cron_frequency_title"), description: t("tour.step_cron_frequency_desc"), side: "top", align: 'start' } }, { element: '#tour-cron-expert-toggle', popover: { title: t("tour.step_cron_expert_title"), description: t("tour.step_cron_expert_desc"), side: "top", align: 'start' }, onDeselected: () => { setShowSettings(false); } }, { element: '#tour-stats', popover: { title: t("tour.step_stats_title"), description: t("tour.step_stats_desc"), side: "bottom", align: 'start' } }, { element: '#tour-new-client', popover: { title: t("tour.step_new_client_title"), description: t("tour.step_new_client_desc"), side: "bottom", align: 'start' } }, { element: '#tour-new-url', popover: { title: t("tour.step_new_url_title"), description: t("tour.step_new_url_desc"), side: "bottom", align: 'start' } }, { element: '#tour-refresh', popover: { title: t("tour.step_refresh_title"), description: t("tour.step_refresh_desc"), side: "bottom", align: 'start' } }, { element: '#tour-client-filter', popover: { title: t("tour.step_filter_title"), description: t("tour.step_filter_desc"), side: "bottom", align: 'start' } }, { element: '#tour-client-actions', popover: { title: t("tour.step_client_actions_title"), description: t("tour.step_client_actions_desc"), side: "bottom", align: 'start' } }, { element: '#tour-search', popover: { title: t("tour.step_filter_title"), description: t("tour.step_filter_desc"), side: "bottom", align: 'start' } }, { element: '#tour-table', popover: { title: t("tour.step_table_title"), description: t("tour.step_table_desc"), side: "top", align: 'start' } }, { element: '#tour-sortable-headers', popover: { title: t("tour.step_headers_title"), description: t("tour.step_headers_desc"), side: "top", align: 'start' } }, { element: '#tour-row-url', popover: { title: t("tour.step_row_url_title"), description: t("tour.step_row_url_desc"), side: "bottom", align: 'start' } }, { element: '#tour-row-actions', popover: { title: t("tour.step_row_actions_title"), description: t("tour.step_row_actions_desc"), side: "bottom", align: 'end' } }, { element: '#tour-pagination', popover: { title: t("tour.step_pagination_title"), description: t("tour.step_pagination_desc"), side: "top", align: 'center' } } ]), [t, setShowSettings]);
  const statsTourSteps = useCallback(() => ([{ element: '#tour-stats', popover: { title: t("tour.step_stats_title"), description: t("tour.step_stats_desc"), side: "bottom", align: 'start' } }]), [t]);
  const clientTourSteps = useCallback(() => ([{ element: '#tour-new-client', popover: { title: t("tour.step_new_client_title"), description: t("tour.step_new_client_desc"), side: "bottom", align: 'start' } }, { element: '#tour-client-filter', popover: { title: t("tour.step_filter_title"), description: t("tour.step_filter_desc"), side: "bottom", align: 'start' } }, { element: '#tour-client-actions', popover: { title: t("tour.step_client_actions_title"), description: t("tour.step_client_actions_desc"), side: "bottom", align: 'start' } }]), [t]);
  const websiteTourSteps = useCallback(() => ([{ element: '#tour-new-url', popover: { title: t("tour.step_new_url_title"), description: t("tour.step_new_url_desc"), side: "bottom", align: 'start' } }, { element: '#tour-refresh', popover: { title: t("tour.step_refresh_title"), description: t("tour.step_refresh_desc"), side: "bottom", align: 'start' } }, { element: '#tour-search', popover: { title: t("tour.step_filter_title"), description: t("tour.step_filter_desc"), side: "bottom", align: 'start' } }]), [t]);
  const tableTourSteps = useCallback(() => ([{ element: '#tour-table', popover: { title: t("tour.step_table_title"), description: t("tour.step_table_desc"), side: "top", align: 'start' } }, { element: '#tour-sortable-headers', popover: { title: t("tour.step_headers_title"), description: t("tour.step_headers_desc"), side: "top", align: 'start' } }, { element: '#tour-row-url', popover: { title: t("tour.step_row_url_title"), description: t("tour.step_row_url_desc"), side: "bottom", align: 'start' } }, { element: '#tour-row-actions', popover: { title: t("tour.step_row_actions_title"), description: t("tour.step_row_actions_desc"), side: "bottom", align: 'end' } }, { element: '#tour-pagination', popover: { title: t("tour.step_pagination_title"), description: t("tour.step_pagination_desc"), side: "top", align: 'center' } }]), [t]);
  const schedulerTourSteps = useCallback(() => ([{ element: '#tour-global-settings', popover: { title: t("tour.step_global_config_title"), description: t("tour.step_global_config_desc"), side: "bottom", align: 'end' } }, { element: '#tour-cron-manager', popover: { title: t("tour.step_cron_title"), description: t("tour.step_cron_desc"), side: "left", align: 'start' }, onHighlightStarted: () => { setShowSettings(true); } }, { element: '#tour-cron-frequency', popover: { title: t("tour.step_cron_frequency_title"), description: t("tour.step_cron_frequency_desc"), side: "top", align: 'start' } }, { element: '#tour-cron-expert-toggle', popover: { title: t("tour.step_cron_expert_title"), description: t("tour.step_cron_expert_desc"), side: "top", align: 'start' }, onDeselected: () => { setShowSettings(false); } }]), [t, setShowSettings]);

  const startModuleTour = useCallback((moduleSteps, tourId) => {
    const driver = createDriver(moduleSteps(), () => localStorage.setItem(`tour_completed_${tourId}`, "true"));
    if (driver) driver.drive();
  }, [createDriver]);

  const startTour = useCallback(() => {
    const driver = createDriver(fullTourSteps(), () => localStorage.setItem("tour_completed", "true"));
    if (driver) driver.drive();
  }, [createDriver, fullTourSteps]);

  useEffect(() => {
    if (!localStorage.getItem("tour_completed")) {
      const timer = setTimeout(startTour, 1000);
      return () => clearTimeout(timer);
    }
  }, [startTour]);

  const handleExportClient = async () => {
    if (!clientId) return;
    try {
      const blob = await exportClientReport(clientId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `client_${clientId}_report.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      notify("Reporte descargado");
    } catch (err) { setFormError(err.message); }
  };

  return React.createElement("div", { className: "app" },
    // Header
    React.createElement("div", { className: "header-area" },
      React.createElement("div", { id: "tour-toggles", style: { display: "flex", alignItems: "center", gap: "15px" } },
        React.createElement("h2", null, t("app.title")),
        React.createElement("button", { className: "tour-btn", onClick: toggleLang, title: t("tour.lang_toggle") }, React.createElement("span", { className: "flag-emoji" }, lang === "es" ? "🇪🇸" : "🇬🇧")),
        React.createElement("button", { className: "tour-btn", onClick: toggleTheme, title: t("tour.theme_toggle") }, theme === "light" ? "☀️" : "🌙")
      ),
      React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "10px" } },
        React.createElement("div", { style: { position: "relative" } },
          React.createElement("div", { style: { display: "flex", gap: "8px" } },
            React.createElement("button", { className: "tour-btn tour-btn-primary", onClick: startTour, title: t("tour.full_tour_title") }, "🎯 " + t("tour.help_btn")),
            React.createElement("button", { className: "tour-btn tour-btn-icon", onClick: () => setShowTourMenu(!showTourMenu), title: t("tour.module_tours") }, "▼")
          ),
          showTourMenu && React.createElement("div", { className: "tour-dropdown" },
            React.createElement("button", { className: "tour-dropdown-item", onClick: () => { startModuleTour(statsTourSteps, "stats"); setShowTourMenu(false); } }, "📊 " + t("tour.module_stats")),
            React.createElement("button", { className: "tour-dropdown-item", onClick: () => { startModuleTour(clientTourSteps, "clients"); setShowTourMenu(false); } }, "👥 " + t("tour.module_clients")),
            React.createElement("button", { className: "tour-dropdown-item", onClick: () => { startModuleTour(websiteTourSteps, "websites"); setShowTourMenu(false); } }, "🌐 " + t("tour.module_websites")),
            React.createElement("button", { className: "tour-dropdown-item", onClick: () => { startModuleTour(tableTourSteps, "table"); setShowTourMenu(false); } }, "📋 " + t("tour.module_table")),
            React.createElement("button", { className: "tour-dropdown-item", onClick: () => { startModuleTour(schedulerTourSteps, "scheduler"); setShowTourMenu(false); } }, "⏰ " + t("tour.module_scheduler"))
          )
        ),
        React.createElement("button", { id: "tour-global-settings", className: "btn-base btn-purple", onClick: () => setShowSettings(true) }, t("app.global_schedule"))
      )
    ),

    // Messages
    successMessage && React.createElement("div", { className: "message success" }, successMessage),
    formError && React.createElement("div", { className: "message error" }, formError),

    // Stats
    React.createElement("div", { className: "grid", id: "tour-stats" },
      React.createElement("div", { className: "card" },
        React.createElement("div", { style: { fontSize: "12px", color: "var(--text-dim)", marginBottom: "8px" } }, t("app.active_webs")),
        React.createElement("div", { style: { fontSize: "24px", fontWeight: "800" } }, summary.active_websites ?? "0")
      ),
      React.createElement("div", { className: "card" },
        React.createElement("div", { style: { fontSize: "12px", color: "var(--text-dim)", marginBottom: "8px" } }, t("app.excellent_score")),
        React.createElement("div", { style: { fontSize: "24px", fontWeight: "800", color: "var(--success)" } }, summary.excellent_count ?? "0")
      ),
      React.createElement("div", { className: "card", style: { borderLeft: "4px solid var(--primary)" } },
        React.createElement("div", { style: { fontSize: "11px", color: "var(--primary)", fontWeight: "700", marginBottom: "8px" } }, t("app.next_active")),
        React.createElement("div", { style: { fontSize: "20px", fontWeight: "800" } }, timers.active),
        React.createElement("div", { style: { fontSize: "12px", color: "var(--text-dim)", marginTop: "4px" } }, timers.active_target)
      ),
      React.createElement("div", { className: "card", style: { borderLeft: "4px solid var(--purple)" } },
        React.createElement("div", { style: { fontSize: "11px", color: "var(--purple)", fontWeight: "700", marginBottom: "8px" } }, t("app.next_inactive")),
        React.createElement("div", { style: { fontSize: "20px", fontWeight: "800" } }, timers.inactive),
        React.createElement("div", { style: { fontSize: "12px", color: "var(--text-dim)", marginTop: "4px" } }, timers.inactive_target)
      )
    ),

    // Toolbar
    React.createElement("div", { className: "topbar" },
      React.createElement("div", { style: { display: "flex", gap: "10px" } },
        React.createElement("button", { id: "tour-new-client", className: "btn-base btn-success", onClick: () => setShowAddClient(true) }, t("app.new_client")),
        React.createElement("button", { id: "tour-new-url", className: "btn-base btn-primary", onClick: () => setShowAddWebsite(true) }, t("app.new_url")),
        React.createElement("button", { id: "tour-refresh", className: "btn-base btn-ghost", onClick: loadAll }, t("app.refresh"))
      ),
      React.createElement("div", { style: { display: "flex", gap: "15px", alignItems: "center", flex: 1 } },
        React.createElement("div", { id: "tour-client-filter", style: { display: "flex", flex: 1, gap: "5px" } },
          React.createElement("select", { className: "premium-input", style: { flex: 1 }, value: clientId, onChange: (e) => setClientId(e.target.value) },
            React.createElement("option", { value: "" }, t("app.all_clients")),
            clients.map(c => React.createElement("option", { key: c.id, value: c.id }, c.name))
          ),
          clientId && React.createElement("div", { id: "tour-client-actions", style: { display: "flex", gap: "5px" } },
            React.createElement("button", { className: "btn-base btn-ghost", style: { padding: "0 12px", border: "1px solid var(--border-main)" }, title: t("app.edit_client"), onClick: () => { const c = clients.find(x => x.id === clientId); if (c) { setEditClientForm(c); setShowEditClient(true); } } }, "✏️"),
            React.createElement("button", { className: "btn-base btn-ghost", style: { padding: "0 12px", color: "var(--danger)", border: "1px solid var(--border-main)" }, title: t("app.delete_client"), onClick: () => { const c = clients.find(x => x.id === clientId); if (c) { setDeleteConfirm({ show: true, type: "client", id: c.id, name: c.name, input: "" }); } } }, "🗑️"),
            React.createElement("button", { className: "btn-base btn-ghost", style: { padding: "0 12px", border: "1px solid var(--border-main)", fontWeight: "700" }, title: t("app.export_client_report") || "Exportar Reporte", onClick: handleExportClient }, "📄 Exportar Reporte")
          )
        ),
        React.createElement("input", { id: "tour-search", className: "premium-input", style: { flex: 1.5 }, value: query, onChange: (e) => setQuery(e.target.value), placeholder: t("app.search_placeholder") })
      )
    ),

    // Table
    React.createElement(WebsitesTable, { websites: filtered, auditingIds, now, onOpen: (w) => { setSelectedWebsite(w); loadRuns(w.website_id); }, onAudit: handleAuditWebsite, onEdit: (w) => { setEditWebsiteForm(w); setShowEditWebsite(true); }, onToggleActive: async (w) => { await updateWebsite(w.website_id, { active: !w.active }); loadAll(); }, onDelete: (w) => setDeleteConfirm({ show: true, type: "website", id: w.website_id, name: w.url, input: "" }) }),

    // Modals
    showSettings && React.createElement(SchedulerModal, { settings, clients, websites, onClose: () => setShowSettings(false), onSaveSettings: handleSaveSettings, onSaveEntityCron: handleSaveEntityCron }),
    showAddClient && React.createElement(AddClientModal, { form: newClientForm, onChange: setNewClientForm, onSubmit: async (e) => { e.preventDefault(); try { await createClient(newClientForm); notify(t("app.client_created")); setShowAddClient(false); loadAll(); } catch (err) { setFormError(err.message); } }, onClose: () => setShowAddClient(false) }),
    showAddWebsite && React.createElement(AddWebsiteModal, { form: newWebsiteForm, clients, onChange: setNewWebsiteForm, onSubmit: async (e) => { e.preventDefault(); const payload = { ...newWebsiteForm, client_id: newWebsiteForm.client_id || null }; try { await createWebsite(payload); notify(t("app.url_added")); setShowAddWebsite(false); setNewWebsiteForm({ client_id: "", url: "", label: "", strategy: "auto", active: true }); loadAll(); } catch (err) { setFormError(err.message); } }, onClose: () => { setShowAddWebsite(false); setNewWebsiteForm({ client_id: "", url: "", label: "", strategy: "auto", active: true }); } }),
    showEditClient && React.createElement(EditClientModal, { form: editClientForm, onChange: setEditClientForm, onSubmit: async (e) => { e.preventDefault(); try { await updateClient(editClientForm.id, editClientForm); notify(t("app.client_updated")); setShowEditClient(false); loadAll(); } catch (err) { setFormError(err.message); } }, onClose: () => setShowEditClient(false) }),
    showEditWebsite && React.createElement(EditWebsiteModal, { form: editWebsiteForm, clients, onChange: setEditWebsiteForm, onSubmit: async (e) => { e.preventDefault(); const payload = { ...editWebsiteForm, client_id: editWebsiteForm.client_id || null }; try { await updateWebsite(editWebsiteForm.website_id, payload); notify(t("app.url_updated")); setShowEditWebsite(false); loadAll(); } catch (err) { setFormError(err.message); } }, onClose: () => setShowEditWebsite(false) }),
    deleteConfirm.show && React.createElement(DeleteConfirmModal, { confirm: deleteConfirm, onChange: (v) => setDeleteConfirm(d => ({ ...d, input: v })), onConfirm: async () => { try { if (deleteConfirm.type === "client") { await deleteClient(deleteConfirm.id); if (clientId === deleteConfirm.id) setClientId(""); } else { await deleteWebsite(deleteConfirm.id); } setDeleteConfirm({ show: false }); notify(t("app.deleted_success")); loadAll(); } catch (err) { setFormError(err.message); } }, onCancel: () => setDeleteConfirm({ show: false }) }),
    selectedWebsite && React.createElement(WebsiteDetailModal, { website: selectedWebsite, auditingIds, runs, runSections, runIssues, onAudit: handleAuditWebsite, onToggleActive: async (w) => { await updateWebsite(w.website_id, { active: !w.active }); loadAll(); }, onDelete: (w) => setDeleteConfirm({ show: true, type: "website", id: w.website_id, name: w.url, input: "" }), onToggleSections: toggleSections, onClose: () => setSelectedWebsite(null) })
  );
}

createRoot(document.getElementById("root")).render(
  React.createElement(I18nProvider, null, React.createElement(App))
);
