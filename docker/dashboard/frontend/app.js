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
 * @version 2.0.0
 * @author Web Auditor Team
 * @since 2024
 */

import React, { useEffect, useMemo, useState, useCallback } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";

/**
 * Importación de funciones de API
 * Estas funciones se comunican con el backend para operaciones CRUD
 * y ejecución de auditorías
 */
import {
  fetchSummary,        // Obtiene resumen de métricas del dashboard
  fetchClients,        // Obtiene lista de todos los clientes
  fetchWebsites,       // Obtiene websites filtrados por cliente
  fetchSettings,       // Obtiene configuración global de programación
  saveSettings,        // Guarda configuración global
  createClient,        // Crea nuevo cliente
  updateClient,        // Actualiza cliente existente
  deleteClient,        // Elimina cliente (con validación)
  createWebsite,       // Añade nuevo website a monitorear
  updateWebsite,       // Actualiza configuración de website
  deleteWebsite,       // Elimina website del monitoreo
  triggerAudit,        // Inicia auditoría manual para un website
  exportClientReport,  // Genera y descarga reporte PDF de cliente
} from "./js/api.js";

/**
 * Hook personalizado para gestión de detalles de auditoría
 * Maneja el historial, secciones e incidencias de auditorías
 */
import { useAuditDetail } from "./js/audit.js";

/**
 * Componentes de visualización y gestión de websites
 */
import { WebsitesTable, WebsiteDetailModal } from "./js/websites.js";

/**
 * Modal para programación de auditorías (global, por cliente, por website)
 */
import { SchedulerModal } from "./js/scheduler.js";

/**
 * Componentes modales reutilizables para operaciones CRUD
 */
import {
  DeleteConfirmModal,      // Modal de confirmación de eliminación
  AddClientModal,          // Modal para crear cliente
  EditClientModal,         // Modal para editar cliente
  AddWebsiteModal,         // Modal para añadir website
  EditWebsiteModal,        // Modal para editar website
} from "./js/modals.js";

/**
 * Proveedor de internacionalización (i18n)
 * Permite cambiar entre español e inglés en toda la app
 */
import { I18nProvider, useI18n } from "./js/i18n.js";

function App() {
  const { t, lang, toggleLang } = useI18n();

  const [summary, setSummary] = useState({});
  const [websites, setWebsites] = useState([]);
  const [clients, setClients] = useState([]);
  const [clientId, setClientId] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [settings, setSettings] = useState({ cron_active: "", cron_inactive: "" });
  const [timers, setTimers] = useState({ active: "", inactive: "" });
  const [now, setNow] = useState(new Date());
  const [selectedWebsite, setSelectedWebsite] = useState(null);
  const [auditingIds, setAuditingIds] = useState(new Set());
  const [deleteConfirm, setDeleteConfirm] = useState({ show: false, type: "", id: "", name: "", input: "" });

  const [showAddClient, setShowAddClient] = useState(false);
  const [showAddWebsite, setShowAddWebsite] = useState(false);
  const [showEditClient, setShowEditClient] = useState(false);
  const [showEditWebsite, setShowEditWebsite] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showTourMenu, setShowTourMenu] = useState(false);

  const [newClientForm, setNewClientForm] = useState({ name: "", email: "", phone: "", company: "", notes: "" });
  const [newWebsiteForm, setNewWebsiteForm] = useState({ client_id: "", url: "", label: "", strategy: "auto", active: true });
  const [editClientForm, setEditClientForm] = useState(null);
  const [editWebsiteForm, setEditWebsiteForm] = useState(null);

  const { runs, runSections, runIssues, loadRuns, toggleSections } = useAuditDetail();

  const loadAll = async () => {
    setLoading(true);
    try {
      const [s, c, w] = await Promise.all([fetchSummary(), fetchClients(), fetchWebsites(clientId)]);
      setSummary(s || {});
      setClients(c || []);
      setWebsites(w || []);
    } catch (err) { setFormError(err.message); }
    finally { setLoading(false); }
  };

  const loadSettingsData = async () => {
    try { setSettings(await fetchSettings()); }
    catch (err) { console.error(err); }
  };

  useEffect(() => { loadAll(); loadSettingsData(); }, [clientId]);

  // Polling para auditorías en curso
  useEffect(() => {
    const hasRunning = websites.some(w => w.run_status === "running" || auditingIds.has(w.website_id));
    if (!hasRunning) return;

    const id = setInterval(loadAll, 3000);
    return () => clearInterval(id);
  }, [websites, auditingIds]);

  useEffect(() => {
    const formatDiff = (ts) => {
      if (!ts) return "-";
      const diff = new Date(ts * 1000) - new Date();
      if (diff <= 0) return "...";
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff / 3600000) % 24);
      const m = Math.floor((diff / 60000) % 60);
      const s = Math.floor((diff / 1000) % 60);
      return `${d}d ${h}h ${m}m ${s}s`;
    };
    const tick = () => {
      setNow(new Date());
      setTimers({ active: formatDiff(settings.next_active), inactive: formatDiff(settings.next_inactive) });
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [settings]);

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
      await loadSettingsData();
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

  // Tour logic - Modular tours
  const createDriver = useCallback((steps, onDestroyCallback) => {
    if (!window.driver || !window.driver.js || !window.driver.js.driver) {
      console.warn("Driver.js is not loaded yet.");
      return null;
    }
    return window.driver.js.driver({
      showProgress: true,
      nextBtnText: t("tour.next"),
      prevBtnText: t("tour.prev"),
      doneBtnText: t("tour.done"),
      steps: steps,
      onDestroyed: onDestroyCallback
    });
  }, [t]);

  // Full tour steps
  const fullTourSteps = useCallback(() => ([
    { popover: { title: t("tour.step_welcome_title"), description: t("tour.step_welcome_desc") } },
    { element: '#tour-toggles', popover: { title: t("tour.step_toggles_title"), description: t("tour.step_toggles_desc"), side: "bottom", align: 'end' } },
    { element: '#tour-global-settings', popover: { title: t("tour.step_global_config_title"), description: t("tour.step_global_config_desc"), side: "bottom", align: 'end' } },
    { 
      element: '#tour-cron-manager', 
      popover: { title: t("tour.step_cron_title"), description: t("tour.step_cron_desc"), side: "left", align: 'start' },
      onHighlightStarted: () => {
        setShowSettings(true);
      }
    },
    { element: '#tour-cron-frequency', popover: { title: t("tour.step_cron_frequency_title"), description: t("tour.step_cron_frequency_desc"), side: "top", align: 'start' } },
    { 
      element: '#tour-cron-expert-toggle', 
      popover: { title: t("tour.step_cron_expert_title"), description: t("tour.step_cron_expert_desc"), side: "top", align: 'start' },
      onDeselected: () => {
        setShowSettings(false);
      }
    },
    { element: '#tour-stats', popover: { title: t("tour.step_stats_title"), description: t("tour.step_stats_desc"), side: "bottom", align: 'start' } },
    { element: '#tour-new-client', popover: { title: t("tour.step_new_client_title"), description: t("tour.step_new_client_desc"), side: "bottom", align: 'start' } },
    { element: '#tour-new-url', popover: { title: t("tour.step_new_url_title"), description: t("tour.step_new_url_desc"), side: "bottom", align: 'start' } },
    { element: '#tour-refresh', popover: { title: t("tour.step_refresh_title"), description: t("tour.step_refresh_desc"), side: "bottom", align: 'start' } },
    { element: '#tour-client-filter', popover: { title: t("tour.step_filter_title"), description: t("tour.step_filter_desc"), side: "bottom", align: 'start' } },
    { element: '#tour-client-actions', popover: { title: t("tour.step_client_actions_title"), description: t("tour.step_client_actions_desc"), side: "bottom", align: 'start' } },
    { element: '#tour-search', popover: { title: t("tour.step_filter_title"), description: t("tour.step_filter_desc"), side: "bottom", align: 'start' } },
    { element: '#tour-table', popover: { title: t("tour.step_table_title"), description: t("tour.step_table_desc"), side: "top", align: 'start' } },
    { element: '#tour-sortable-headers', popover: { title: t("tour.step_headers_title"), description: t("tour.step_headers_desc"), side: "top", align: 'start' } },
    { element: '#tour-row-url', popover: { title: t("tour.step_row_url_title"), description: t("tour.step_row_url_desc"), side: "bottom", align: 'start' } },
    { element: '#tour-row-actions', popover: { title: t("tour.step_row_actions_title"), description: t("tour.step_row_actions_desc"), side: "bottom", align: 'end' } },
    { element: '#tour-pagination', popover: { title: t("tour.step_pagination_title"), description: t("tour.step_pagination_desc"), side: "top", align: 'center' } }
  ]), [t]);

  // Stats module tour steps
  const statsTourSteps = useCallback(() => ([
    { element: '#tour-stats', popover: { title: t("tour.step_stats_title"), description: t("tour.step_stats_desc"), side: "bottom", align: 'start' } }
  ]), [t]);

  // Client management module tour steps
  const clientTourSteps = useCallback(() => ([
    { element: '#tour-new-client', popover: { title: t("tour.step_new_client_title"), description: t("tour.step_new_client_desc"), side: "bottom", align: 'start' } },
    { element: '#tour-client-filter', popover: { title: t("tour.step_filter_title"), description: t("tour.step_filter_desc"), side: "bottom", align: 'start' } },
    { element: '#tour-client-actions', popover: { title: t("tour.step_client_actions_title"), description: t("tour.step_client_actions_desc"), side: "bottom", align: 'start' } }
  ]), [t]);

  // Website management module tour steps
  const websiteTourSteps = useCallback(() => ([
    { element: '#tour-new-url', popover: { title: t("tour.step_new_url_title"), description: t("tour.step_new_url_desc"), side: "bottom", align: 'start' } },
    { element: '#tour-refresh', popover: { title: t("tour.step_refresh_title"), description: t("tour.step_refresh_desc"), side: "bottom", align: 'start' } },
    { element: '#tour-search', popover: { title: t("tour.step_filter_title"), description: t("tour.step_filter_desc"), side: "bottom", align: 'start' } }
  ]), [t]);

  // Table module tour steps
  const tableTourSteps = useCallback(() => ([
    { element: '#tour-table', popover: { title: t("tour.step_table_title"), description: t("tour.step_table_desc"), side: "top", align: 'start' } },
    { element: '#tour-sortable-headers', popover: { title: t("tour.step_headers_title"), description: t("tour.step_headers_desc"), side: "top", align: 'start' } },
    { element: '#tour-row-url', popover: { title: t("tour.step_row_url_title"), description: t("tour.step_row_url_desc"), side: "bottom", align: 'start' } },
    { element: '#tour-row-actions', popover: { title: t("tour.step_row_actions_title"), description: t("tour.step_row_actions_desc"), side: "bottom", align: 'end' } },
    { element: '#tour-pagination', popover: { title: t("tour.step_pagination_title"), description: t("tour.step_pagination_desc"), side: "top", align: 'center' } }
  ]), [t]);

  // Scheduler module tour steps
  const schedulerTourSteps = useCallback(() => ([
    { element: '#tour-global-settings', popover: { title: t("tour.step_global_config_title"), description: t("tour.step_global_config_desc"), side: "bottom", align: 'end' } },
    { 
      element: '#tour-cron-manager', 
      popover: { title: t("tour.step_cron_title"), description: t("tour.step_cron_desc"), side: "left", align: 'start' },
      onHighlightStarted: () => {
        setShowSettings(true);
      }
    },
    { element: '#tour-cron-frequency', popover: { title: t("tour.step_cron_frequency_title"), description: t("tour.step_cron_frequency_desc"), side: "top", align: 'start' } },
    { 
      element: '#tour-cron-expert-toggle', 
      popover: { title: t("tour.step_cron_expert_title"), description: t("tour.step_cron_expert_desc"), side: "top", align: 'start' },
      onDeselected: () => {
        setShowSettings(false);
      }
    }
  ]), [t]);

  // Start specific tour module
  const startModuleTour = useCallback((moduleSteps, tourId) => {
    const driver = createDriver(moduleSteps(), () => {
      localStorage.setItem(`tour_completed_${tourId}`, "true");
    });
    if (driver) driver.drive();
  }, [createDriver]);

  // Start full tour
  const startTour = useCallback(() => {
    const driver = createDriver(fullTourSteps(), () => {
      localStorage.setItem("tour_completed", "true");
    });
    if (driver) driver.drive();
  }, [createDriver, fullTourSteps]);

  useEffect(() => {
    const hasCompletedTour = localStorage.getItem("tour_completed");
    if (!hasCompletedTour) {
      // Give UI a moment to render before starting tour
      const timer = setTimeout(() => {
        startTour();
      }, 1000);
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
    React.createElement("div", { className: "header-area", style: { display: "flex", justifyContent: "space-between", alignItems: "center" } },
      React.createElement("div", { id: "tour-toggles", style: { display: "flex", alignItems: "center", gap: "15px" } },
        React.createElement("h2", null, t("app.title")),
        React.createElement("button", {
          className: "tour-btn",
          onClick: toggleLang,
          title: t("tour.lang_toggle")
        }, React.createElement("span", { className: "flag-emoji" }, lang === "es" ? "🇪🇸" : "🇬🇧")),
        React.createElement("button", {
          className: "tour-btn",
          onClick: toggleTheme,
          title: t("tour.theme_toggle")
        }, theme === "light" ? "☀️" : "🌙")
      ),
      // Tour button with dropdown menu
      React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "10px", position: "relative" } },
        React.createElement("div", { style: { display: "flex", gap: "8px" } },
          React.createElement("button", {
            className: "tour-btn tour-btn-primary",
            onClick: startTour,
            title: t("tour.full_tour_title")
          }, "🎯 " + t("tour.help_btn")),
          React.createElement("button", {
            className: "tour-btn tour-btn-icon",
            onClick: () => setShowTourMenu(!showTourMenu),
            title: t("tour.module_tours")
          }, "▼")
        ),
        // Dropdown menu for module tours
        showTourMenu && React.createElement("div", { className: "tour-dropdown" },
          React.createElement("button", {
            className: "tour-dropdown-item",
            onClick: () => { startModuleTour(statsTourSteps, "stats"); setShowTourMenu(false); }
          }, "📊 " + t("tour.module_stats")),
          React.createElement("button", {
            className: "tour-dropdown-item",
            onClick: () => { startModuleTour(clientTourSteps, "clients"); setShowTourMenu(false); }
          }, "👥 " + t("tour.module_clients")),
          React.createElement("button", {
            className: "tour-dropdown-item",
            onClick: () => { startModuleTour(websiteTourSteps, "websites"); setShowTourMenu(false); }
          }, "🌐 " + t("tour.module_websites")),
          React.createElement("button", {
            className: "tour-dropdown-item",
            onClick: () => { startModuleTour(tableTourSteps, "table"); setShowTourMenu(false); }
          }, "📋 " + t("tour.module_table")),
          React.createElement("button", {
            className: "tour-dropdown-item",
            onClick: () => { startModuleTour(schedulerTourSteps, "scheduler"); setShowTourMenu(false); }
          }, "⏰ " + t("tour.module_scheduler"))
        )
      ),
      React.createElement("button", {
        id: "tour-global-settings",
        className: "btn-base btn-purple",
        onClick: () => setShowSettings(true)
      }, t("app.global_schedule"))
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
        React.createElement("div", { style: { fontSize: "20px", fontWeight: "800" } }, timers.active)
      ),
      React.createElement("div", { className: "card", style: { borderLeft: "4px solid var(--purple)" } },
        React.createElement("div", { style: { fontSize: "11px", color: "var(--purple)", fontWeight: "700", marginBottom: "8px" } }, t("app.next_inactive")),
        React.createElement("div", { style: { fontSize: "20px", fontWeight: "800" } }, timers.inactive)
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
          React.createElement("select", {
            className: "premium-input",
            style: { flex: 1 },
            value: clientId,
            onChange: (e) => setClientId(e.target.value)
          },
            React.createElement("option", { value: "" }, t("app.all_clients")),
            clients.map(c => React.createElement("option", { key: c.id, value: c.id }, c.name))
          ),
          clientId && React.createElement("div", { id: "tour-client-actions", style: { display: "flex", gap: "5px" } },
            React.createElement("button", {
              className: "btn-base btn-ghost",
              style: { padding: "0 12px", border: "1px solid var(--border-main)" },
              title: t("app.edit_client"),
              onClick: () => {
                const c = clients.find(x => x.id === clientId);
                if (c) { setEditClientForm(c); setShowEditClient(true); }
              }
            }, "✏️"),
            React.createElement("button", {
              className: "btn-base btn-ghost",
              style: { padding: "0 12px", color: "var(--danger)", border: "1px solid var(--border-main)" },
              title: t("app.delete_client"),
              onClick: () => {
                const c = clients.find(x => x.id === clientId);
                if (c) { setDeleteConfirm({ show: true, type: "client", id: c.id, name: c.name, input: "" }); }
              }
            }, "🗑️"),
            React.createElement("button", {
              className: "btn-base btn-ghost",
              style: { padding: "0 12px", border: "1px solid var(--border-main)", fontWeight: "700" },
              title: t("app.export_client_report") || "Exportar Reporte",
              onClick: handleExportClient
            }, "📄 Exportar Reporte")
          )
        ),
        React.createElement("input", {
          id: "tour-search",
          className: "premium-input",
          style: { flex: 1.5 },
          value: query,
          onChange: (e) => setQuery(e.target.value),
          placeholder: t("app.search_placeholder")
        })
      )
    ),

    // Table
    React.createElement(WebsitesTable, {
      websites: filtered, auditingIds, now,
      onOpen: (w) => { setSelectedWebsite(w); loadRuns(w.website_id); },
      onAudit: handleAuditWebsite,
      onEdit: (w) => { setEditWebsiteForm(w); setShowEditWebsite(true); },
      onToggleActive: async (w) => { await updateWebsite(w.website_id, { active: !w.active }); loadAll(); },
      onDelete: (w) => setDeleteConfirm({ show: true, type: "website", id: w.website_id, name: w.url, input: "" }),
    }),

    // Modals
    showSettings && React.createElement(SchedulerModal, {
      settings, clients, websites,
      onClose: () => setShowSettings(false),
      onSaveSettings: handleSaveSettings,
      onSaveEntityCron: handleSaveEntityCron
    }),

    showAddClient && React.createElement(AddClientModal, { form: newClientForm, onChange: setNewClientForm, onSubmit: (e) => { e.preventDefault(); createClient(newClientForm).then(() => { notify(t("app.client_created")); setShowAddClient(false); loadAll(); }).catch(err => setFormError(err.message)); }, onClose: () => setShowAddClient(false) }),
    showAddWebsite && React.createElement(AddWebsiteModal, { form: newWebsiteForm, clients, onChange: setNewWebsiteForm, onSubmit: (e) => { e.preventDefault(); const payload = { ...newWebsiteForm, client_id: newWebsiteForm.client_id || null }; createWebsite(payload).then(() => { notify(t("app.url_added")); setShowAddWebsite(false); setNewWebsiteForm({ client_id: "", url: "", label: "", strategy: "auto", active: true }); loadAll(); }).catch(err => setFormError(err.message)); }, onClose: () => { setShowAddWebsite(false); setNewWebsiteForm({ client_id: "", url: "", label: "", strategy: "auto", active: true }); } }),
    showEditClient && React.createElement(EditClientModal, { form: editClientForm, onChange: setEditClientForm, onSubmit: (e) => { e.preventDefault(); updateClient(editClientForm.id, editClientForm).then(() => { notify(t("app.client_updated")); setShowEditClient(false); loadAll(); }).catch(err => setFormError(err.message)); }, onClose: () => setShowEditClient(false) }),
    showEditWebsite && React.createElement(EditWebsiteModal, { form: editWebsiteForm, clients, onChange: setEditWebsiteForm, onSubmit: (e) => { e.preventDefault(); const payload = { ...editWebsiteForm, client_id: editWebsiteForm.client_id || null }; updateWebsite(editWebsiteForm.website_id, payload).then(() => { notify(t("app.url_updated")); setShowEditWebsite(false); loadAll(); }).catch(err => setFormError(err.message)); }, onClose: () => setShowEditWebsite(false) }),
    deleteConfirm.show && React.createElement(DeleteConfirmModal, {
      confirm: deleteConfirm, onChange: (v) => setDeleteConfirm(d => ({ ...d, input: v })), onConfirm: async () => {
        if (deleteConfirm.type === "client") {
          await deleteClient(deleteConfirm.id);
          if (clientId === deleteConfirm.id) setClientId("");
        } else {
          await deleteWebsite(deleteConfirm.id);
        }
        setDeleteConfirm({ show: false });
        notify(t("app.deleted_success"));
        loadAll();
      }, onCancel: () => setDeleteConfirm({ show: false })
    }),
    selectedWebsite && React.createElement(WebsiteDetailModal, {
      website: selectedWebsite, auditingIds, runs, runSections, runIssues,
      onAudit: handleAuditWebsite, onToggleActive: async (w) => { await updateWebsite(w.website_id, { active: !w.active }); loadAll(); },
      onDelete: (w) => setDeleteConfirm({ show: true, type: "website", id: w.website_id, name: w.url, input: "" }),
      onToggleSections: toggleSections, onClose: () => setSelectedWebsite(null)
    })
  );
}

createRoot(document.getElementById("root")).render(
  React.createElement(I18nProvider, null,
    React.createElement(App)
  )
);