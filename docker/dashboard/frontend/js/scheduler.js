/**
 * scheduler.js - Lógica del Frontend para la Programación de Auditorías
 *
 * IMPORTANTE: Este fichero ha sido refactorizado para ELIMINAR CUALQUIER
 * CÁLCULO DE FECHAS en el lado del cliente. Ahora, la única
 * responsabilidad del frontend es MOSTRAR las fechas que la API
 * le proporciona directamente. Esto garantiza que no haya discrepancias.
 */
import React from "https://esm.sh/react@18.3.1";
import { useI18n } from "./i18n.js";

// ── UTILIDADES ───────────────────────────────────────────────────────────────

// Divide una cadena de reglas cron en un array.
export function splitCronRules(value) {
  if (!value) return [];
  // Expresión regular mejorada para separar reglas cron de forma fiable
  return value.split(/\s*,\s*(?=(?:[^\s]+\s+){4}[^\s]+)/).map(c => c.trim()).filter(Boolean);
}

// Serializa un array de reglas en una cadena.
export function serializeCronRules(rules) {
  return rules.map(r => r.trim()).join(", ");
}

// ── COMPONENTES DE UI ────────────────────────────────────────────────────────

/**
 * Componente para editar una o más reglas CRON en modo experto (texto plano).
 * Este componente reemplaza la lógica compleja anterior por una simple
 * caja de texto, ya que el cálculo de fechas no es responsabilidad del frontend.
 */
function CronExpertEditor({ value, onChange }) {
  const { t } = useI18n();
  return React.createElement("div", null,
    React.createElement("textarea", {
      value: value || "",
      className: "premium-input",
      placeholder: t("scheduler.expert_placeholder"),
      onChange: (e) => onChange(e.target.value),
      style: { fontSize: "13px", height: "80px", resize: "vertical" }
    }),
    React.createElement("p", { style: { fontSize: "11px", color: "var(--text-dim)", marginTop: "8px", lineHeight: 1.5 } }, 
      t("scheduler.expert_help")
    )
  );
}

/**
 * Componente principal para gestionar la configuración de CRON, tanto
 * global como a nivel de entidad (cliente/website).
 */
function CronManager({ label, value, onChange, color = "var(--primary)" }) {
  return React.createElement("div", { className: "cron-manager-container", style: { marginBottom: "20px" } },
    label && React.createElement("h5", {
      style: { 
        margin: "0 0 12px 0", 
        color: color, 
        fontSize: "11px", 
        textTransform: "uppercase", 
        letterSpacing: "1px", 
        opacity: 0.9 
      } 
    }, label),
    React.createElement(CronExpertEditor, { value, onChange })
  );
}

// ── HUB CENTRAL DE PROGRAMACIÓN (MODAL) ──────────────────────────────────────

export function SchedulerModal({ settings, clients, websites, onClose, onSaveSettings, onSaveEntityCron }) {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = React.useState("global");
  const [localSettings, setLocalSettings] = React.useState(settings);
  const [editingEntity, setEditingEntity] = React.useState(null);

  // Estados para búsqueda y filtrado
  const [filterQuery, setFilterQuery] = React.useState("");
  const [showOnlyCustom, setShowOnlyCustom] = React.useState(false);

  // Sincronizar estado local cuando las props de settings cambian.
  React.useEffect(() => { setLocalSettings(settings); }, [settings]);

  const resetFilters = () => {
    setEditingEntity(null);
    setFilterQuery("");
    setShowOnlyCustom(false);
  };

  // Renderiza la pestaña de configuración global.
  const renderGlobal = () => React.createElement("div", { style: { animation: "modalFadeIn 0.3s ease" } },
    React.createElement(CronManager, {
      label: t("scheduler.active_cycles"),
      color: "var(--primary)",
      value: localSettings.cron_active,
      onChange: (v) => setLocalSettings(s => ({ ...s, cron_active: v }))
    }),
    React.createElement("div", { style: { height: "10px" } }),
    React.createElement(CronManager, {
      label: t("scheduler.inactive_cycles"),
      color: "var(--purple)",
      value: localSettings.cron_inactive,
      onChange: (v) => setLocalSettings(s => ({ ...s, cron_inactive: v }))
    }),
    React.createElement("div", { className: "form-actions", style: { marginTop: "30px" } },
      React.createElement("button", { 
        className: "btn-base btn-primary", 
        style: { width: "100%" },
        onClick: () => onSaveSettings(localSettings) 
      }, t("scheduler.save_global"))
    )
  );

  // Renderiza la lista y el editor para entidades (clientes o websites).
  const renderEntities = (type) => {
    const rawList = type === "client" 
      ? clients.map(c => ({ ...c, custom_cron: c.client_cron })) // Normalizar a custom_cron
      : websites.map(w => ({ ...w, custom_cron: w.website_cron }));
    
    const filteredList = rawList.filter(item => {
      const name = (type === "client" ? item.name : (item.label || item.url || "")).toLowerCase();
      if (filterQuery && !name.includes(filterQuery.toLowerCase())) return false;
      if (showOnlyCustom && !item.custom_cron) return false;
      return true;
    });

    return React.createElement("div", { style: { animation: "modalFadeIn 0.3s ease" } },
      editingEntity ? React.createElement("div", null,
        React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "15px", marginBottom: "25px" } },
          React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: () => setEditingEntity(null) }, t("modals.back")),
          React.createElement("h4", { style: { margin: 0 } }, type === "client" ? editingEntity.name : (editingEntity.label || editingEntity.url))
        ),
        React.createElement(CronManager, {
          label: t("scheduler.custom_schedule"),
          value: editingEntity.custom_cron || "",
          color: type === "client" ? "var(--success)" : "var(--primary)",
          onChange: (v) => setEditingEntity(e => ({ ...e, custom_cron: v }))
        }),
        React.createElement("div", { className: "form-actions", style: { marginTop: "30px", display: "flex", gap: "10px" } },
          React.createElement("button", { 
            className: "btn-base btn-success", style: { flex: 1.5 },
            onClick: () => { onSaveEntityCron(editingEntity.custom_cron, type, editingEntity); setEditingEntity(null); }
          }, t("modals.save")),
          editingEntity.custom_cron && React.createElement("button", { 
            className: "btn-base btn-danger btn-ghost", style: { flex: 1 },
            onClick: () => { onSaveEntityCron(null, type, editingEntity); setEditingEntity(null); }
          }, t("modals.reset")),
          React.createElement("button", { 
            className: "btn-base btn-ghost", style: { flex: 1 },
            onClick: () => setEditingEntity(null) 
          }, t("modals.cancel"))
        )
      ) : React.createElement("div", null,
        React.createElement("div", { style: { display: "flex", gap: "15px", alignItems: "center", marginBottom: "20px" } },
          React.createElement("input", {
            type: "text",
            className: "premium-input",
            placeholder: type === "client" ? t("scheduler.search_client") : t("scheduler.search_url"),
            value: filterQuery,
            onChange: (e) => setFilterQuery(e.target.value),
            style: { flex: 1, padding: "10px 14px", fontSize: "13px" }
          }),
          React.createElement("label", { style: { display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "var(--text-dim)", cursor: "pointer", userSelect: "none" } },
            React.createElement("input", {
              type: "checkbox",
              checked: showOnlyCustom,
              onChange: (e) => setShowOnlyCustom(e.target.checked),
              style: { cursor: "pointer", width: "16px", height: "16px", accentColor: "var(--primary)" }
            }),
            t("scheduler.show_custom")
          )
        ),
        React.createElement("div", { className: "table-container", style: { maxHeight: "400px", overflowY: "auto" } },
          React.createElement("table", null,
            React.createElement("thead", null, React.createElement("tr", null, 
              React.createElement("th", null, type === "client" ? t("table.client") : t("table.url")),
              React.createElement("th", null, t("table.status")),
              React.createElement("th", { style: { textAlign: "right" } }, t("table.actions"))
            )),
            React.createElement("tbody", null,
              filteredList.length > 0 ? filteredList.map(item => {
                const isCustom = !!item.custom_cron;
                const badgeStyle = {
                  background: isCustom ? (type === "client" ? "rgba(16, 185, 129, 0.12)" : "rgba(59, 130, 246, 0.12)") : "rgba(255, 255, 255, 0.03)",
                  color: isCustom ? (type === "client" ? "var(--success)" : "var(--primary)") : "var(--text-dim)",
                  border: `1px solid ${isCustom ? (type === "client" ? "rgba(16,185,145,0.18)" : "rgba(59,130,246,0.18)") : "rgba(255,255,255,0.05)"}`,
                  padding: "4px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: "bold",
                  display: "inline-flex", alignItems: "center", gap: "4px", whiteSpace: "nowrap", maxWidth: "250px", overflow: "hidden", textOverflow: "ellipsis"
                };

                return React.createElement("tr", { key: type === "client" ? item.id : item.website_id },
                  React.createElement("td", { style: { fontWeight: "600", maxWidth: "300px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, type === "client" ? item.name : (item.label || item.url)),
                  React.createElement("td", null, 
                    React.createElement("span", { style: badgeStyle, title: item.custom_cron }, 
                      isCustom ? `📅 ${item.custom_cron}` : `🌐 ${t("table.inherited")}`
                    )
                  ),
                  React.createElement("td", { style: { textAlign: "right" } }, 
                    React.createElement("button", { 
                      className: "btn-base btn-ghost btn-small",
                      onClick: () => setEditingEntity(item)
                    }, t("scheduler.configure"))
                  )
                );
              }) : React.createElement("tr", null, 
                React.createElement("td", { colSpan: 3, style: { textAlign: "center", padding: "30px", color: "var(--text-dim)", fontSize: "13px" } }, t("scheduler.no_results"))
              )
            )
          )
        )
      )
    );
  };

  // Renderiza el modal completo.
  return React.createElement("div", { className: "modal", onClick: onClose },
    React.createElement("div", {
      className: "modal-content premium-modal",
      style: { maxWidth: "850px" },
      onClick: (e) => e.stopPropagation()
    },
      React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "30px" } },
        React.createElement("h2", { style: { margin: 0 } }, t("scheduler.title")),
        React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: onClose }, t("modals.close"))
      ),
      React.createElement("div", { className: "tabs-header" },
        React.createElement("button", { 
          className: `tab-btn ${activeTab === "global" ? "active" : ""}`,
          onClick: () => { setActiveTab("global"); resetFilters(); }
        }, t("scheduler.tab_global")),
        React.createElement("button", { 
          className: `tab-btn ${activeTab === "clients" ? "active" : ""}`,
          onClick: () => { setActiveTab("clients"); resetFilters(); }
        }, t("scheduler.tab_clients")),
        React.createElement("button", { 
          className: `tab-btn ${activeTab === "urls" ? "active" : ""}`,
          onClick: () => { setActiveTab("urls"); resetFilters(); }
        }, t("scheduler.tab_urls"))
      ),
      activeTab === "global" && renderGlobal(),
      activeTab === "clients" && renderEntities("client"),
      activeTab === "urls" && renderEntities("website")
    )
  );
}
