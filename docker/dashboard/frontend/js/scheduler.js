/**
 * scheduler.js — Hub Central de Programación.
 * Gestiona ciclos globales, clientes y URLs en una interfaz unificada.
 */
import React from "https://esm.sh/react@18.3.1";

// ── UTILIDADES CRON ─────────────────────────────────────────────────────────

function parseCron(c) {
  const parts = (c && c.split(" ").length === 5 ? c : "0 0 * * *").split(" ");
  return { min: parts[0], hour: parts[1], dom: parts[2], month: parts[3], dow: parts[4] };
}

function detectFrequency(parts) {
  if (parts.dow !== "*") return "weekly";
  if (parts.month.includes("/")) return "monthly_periodic";
  if (parts.dom.includes("/")) return "daily_periodic";
  if (parts.dom !== "*" && parts.month === "*") return "monthly";
  if (parts.dom !== "*" && parts.month !== "*") return "yearly";
  return "daily";
}

// ── COMPONENTES DE UI PREMIUM ───────────────────────────────────────────────

function SingleCronEditor({ cronValue, color, onChange, onRemove, showRemove }) {
  const parts = parseCron(cronValue);
  const freq = detectFrequency(parts);

  const updateParts = (newParts) => {
    const p = { ...parts, ...newParts };
    onChange(`${p.min} ${p.hour} ${p.dom} ${p.month} ${p.dow}`);
  };

  const DAYS = [
    { id: "1", n: "L" }, { id: "2", n: "M" }, { id: "3", n: "X" },
    { id: "4", n: "J" }, { id: "5", n: "V" }, { id: "6", n: "S" }, { id: "0", n: "D" },
  ];

  return React.createElement("div", {
    style: {
      background: "rgba(255, 255, 255, 0.03)", border: "1px solid rgba(255, 255, 255, 0.05)",
      padding: "16px", borderRadius: "10px", marginBottom: "12px", position: "relative"
    }
  },
    showRemove && React.createElement("button", {
      type: "button", onClick: onRemove, className: "btn-base btn-small btn-ghost",
      style: { position: "absolute", right: "12px", top: "12px", color: "var(--danger)" }
    }, "Borrar"),

    React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" } },
      React.createElement("div", null,
        React.createElement("label", { style: { fontSize: "11px", opacity: 0.5, display: "block", marginBottom: "8px", textTransform: "uppercase" } }, "Frecuencia"),
        React.createElement("select", {
          value: freq, className: "premium-input", style: { padding: "10px", fontSize: "13px" },
          onChange: (e) => {
            const f = e.target.value;
            if (f === "daily") updateParts({ dom: "*", month: "*", dow: "*" });
            else if (f === "daily_periodic") updateParts({ dom: "*/2", month: "*", dow: "*" });
            else if (f === "weekly") updateParts({ dom: "*", month: "*", dow: "1" });
            else if (f === "monthly") updateParts({ dom: "1", month: "*", dow: "*" });
            else if (f === "monthly_periodic") updateParts({ dom: "1", month: "*/3", dow: "*" });
            else if (f === "yearly") updateParts({ dom: "1", month: "1", dow: "*" });
          }
        },
          React.createElement("option", { value: "daily" }, "Diario"),
          React.createElement("option", { value: "daily_periodic" }, "Cada X días"),
          React.createElement("option", { value: "weekly" }, "Semanal"),
          React.createElement("option", { value: "monthly" }, "Mensual"),
          React.createElement("option", { value: "monthly_periodic" }, "Periódico"),
          React.createElement("option", { value: "yearly" }, "Anual")
        )
      ),
      React.createElement("div", null,
        React.createElement("label", { style: { fontSize: "11px", opacity: 0.5, display: "block", marginBottom: "8px", textTransform: "uppercase" } }, "Hora de Ejecución"),
        React.createElement("input", {
          type: "time", className: "premium-input", style: { padding: "10px", fontSize: "13px" },
          value: `${parts.hour.padStart(2, "0")}:${parts.min.padStart(2, "0")}`,
          onChange: (e) => {
            const [h, m] = e.target.value.split(":");
            updateParts({ hour: parseInt(h).toString(), min: parseInt(m).toString() });
          }
        })
      )
    ),

    freq === "weekly" && React.createElement("div", { style: { marginTop: "15px" } },
      React.createElement("label", { style: { fontSize: "11px", opacity: 0.5, display: "block", marginBottom: "8px", textTransform: "uppercase" } }, "Días de la semana"),
      React.createElement("div", { style: { display: "flex", gap: "6px" } },
        DAYS.map(d => {
          const isSelected = parts.dow.split(",").includes(d.id);
          return React.createElement("button", {
            key: d.id, type: "button",
            onClick: () => {
              let current = parts.dow.split(",");
              current = isSelected ? current.filter(x => x !== d.id) : [...current, d.id];
              updateParts({ dow: current.length === 0 ? "1" : current.sort().join(",") });
            },
            style: {
              background: isSelected ? color : "rgba(255,255,255,0.05)",
              border: `1px solid ${isSelected ? color : "rgba(255,255,255,0.1)"}`,
              color: isSelected ? "#fff" : "var(--text-dim)",
              width: "32px", height: "32px", borderRadius: "8px", fontSize: "11px", fontWeight: "bold",
              cursor: "pointer", transition: "var(--transition)"
            }
          }, d.n);
        })
      )
    )
  );
}

export function CronManager({ label, value, onChange, color = "#3498db" }) {
  const [internalMode, setInternalMode] = React.useState("simple");
  const crons = (value || "").split(",").map(c => c.trim()).filter(c => c);
  if (crons.length === 0 && internalMode === "simple") crons.push("0 0 * * *");

  const handleUpdate = (idx, val) => {
    const next = [...crons];
    next[idx] = val;
    onChange(next.join(", "));
  };

  const handleAdd = () => onChange([...crons, "0 0 * * *"].join(", "));
  const handleRemove = (idx) => onChange(crons.filter((_, i) => i !== idx).join(", "));

  return React.createElement("div", { className: "cron-manager-container", style: { marginBottom: "20px" } },
    React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" } },
      label && React.createElement("h5", { style: { margin: 0, color: `${color}cc`, fontSize: "11px", textTransform: "uppercase", letterSpacing: "1px" } }, label),
      React.createElement("button", {
        type: "button",
        onClick: () => setInternalMode(internalMode === "simple" ? "expert" : "simple"),
        style: { background: "transparent", border: "none", color: "var(--text-dim)", fontSize: "10px", cursor: "pointer", textDecoration: "underline" }
      }, internalMode === "simple" ? "Cambiar a Modo Experto" : "Volver a Modo Simple")
    ),
    
    internalMode === "simple" ? React.createElement("div", null,
      crons.map((c, i) => React.createElement(SingleCronEditor, {
        key: i, cronValue: c, color,
        onChange: (v) => handleUpdate(i, v),
        onRemove: () => handleRemove(i),
        showRemove: crons.length > 1
      })),
      React.createElement("button", {
        type: "button", onClick: handleAdd,
        className: "btn-base btn-ghost",
        style: { width: "100%", border: `1px dashed ${color}66`, color, fontSize: "12px" }
      }, "+ Añadir regla de programación")
    ) : React.createElement("div", null,
      React.createElement("input", {
        type: "text", value: value || "", className: "premium-input",
        placeholder: "Ej: 0 0 * * *, 0 12 * * 0",
        onChange: (e) => onChange(e.target.value),
        style: { fontSize: "14px" }
      }),
      React.createElement("p", { style: { fontSize: "11px", color: "var(--text-dim)", marginTop: "8px" } }, "Formato estándar de 5 campos (minuto hora día mes día_semana)")
    )
  );
}

// ── HUB CENTRAL DE PROGRAMACIÓN ──────────────────────────────────────────────

export function SchedulerModal({ settings, clients, websites, onClose, onSaveSettings, onSaveEntityCron }) {
  const [activeTab, setActiveTab] = React.useState("global");
  const [localSettings, setLocalSettings] = React.useState(settings);
  const [editingEntity, setEditingEntity] = React.useState(null);

  React.useEffect(() => { setLocalSettings(settings); }, [settings]);

  const renderGlobal = () => React.createElement("div", { style: { animation: "modalFadeIn 0.3s ease" } },
    React.createElement(CronManager, {
      label: "Ciclos para Webs Activas", color: "#3b82f6",
      value: localSettings.cron_active,
      onChange: (v) => setLocalSettings(s => ({ ...s, cron_active: v }))
    }),
    React.createElement("div", { style: { height: "10px" } }),
    React.createElement(CronManager, {
      label: "Ciclos para Webs Inactivas", color: "#8b5cf6",
      value: localSettings.cron_inactive,
      onChange: (v) => setLocalSettings(s => ({ ...s, cron_inactive: v }))
    }),
    React.createElement("div", { className: "form-actions", style: { marginTop: "30px" } },
      React.createElement("button", { 
        className: "btn-base btn-primary", 
        style: { width: "100%" },
        onClick: () => onSaveSettings(localSettings) 
      }, "Guardar Configuración Global")
    )
  );

  const renderEntities = (type) => {
    const list = type === "client" ? clients : websites;
    return React.createElement("div", { style: { animation: "modalFadeIn 0.3s ease" } },
      editingEntity ? React.createElement("div", null,
        React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "15px", marginBottom: "25px" } },
          React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: () => setEditingEntity(null) }, "Volver"),
          React.createElement("h4", { style: { margin: 0 } }, type === "client" ? editingEntity.name : editingEntity.url)
        ),
        React.createElement(CronManager, {
          label: "Programación Personalizada",
          value: editingEntity.custom_cron || "",
          color: type === "client" ? "#10b981" : "#3b82f6",
          onChange: (v) => setEditingEntity(e => ({ ...e, custom_cron: v }))
        }),
        React.createElement("div", { className: "form-actions", style: { marginTop: "30px" } },
          React.createElement("button", { 
            className: "btn-base btn-success", style: { flex: 1 },
            onClick: () => { onSaveEntityCron(editingEntity.custom_cron, type, editingEntity); setEditingEntity(null); }
          }, "Guardar Cambios"),
          React.createElement("button", { 
            className: "btn-base btn-ghost", style: { flex: 1 },
            onClick: () => setEditingEntity(null) 
          }, "Cancelar")
        )
      ) : React.createElement("div", null,
        React.createElement("div", { className: "table-container", style: { maxHeight: "400px", overflowY: "auto" } },
          React.createElement("table", null,
            React.createElement("thead", null, 
              React.createElement("tr", null, 
                React.createElement("th", null, type === "client" ? "Cliente" : "Sitio Web"),
                React.createElement("th", null, "Programación"),
                React.createElement("th", null, "Acción")
              )
            ),
            React.createElement("tbody", null,
              list.map(item => React.createElement("tr", { key: type === "client" ? item.id : item.website_id },
                React.createElement("td", { style: { fontWeight: "600" } }, type === "client" ? item.name : (item.label || item.url)),
                React.createElement("td", { style: { fontSize: "12px", opacity: 0.6 } }, item.custom_cron || "(Heredado del global)"),
                React.createElement("td", null, 
                  React.createElement("button", { 
                    className: "btn-base btn-ghost btn-small",
                    onClick: () => setEditingEntity(item)
                  }, "Configurar")
                )
              ))
            )
          )
        )
      )
    );
  };

  return React.createElement("div", { className: "modal", onClick: onClose },
    React.createElement("div", {
      className: "modal-content premium-modal",
      style: { maxWidth: "850px" },
      onClick: (e) => e.stopPropagation()
    },
      React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "30px" } },
        React.createElement("h2", { style: { margin: 0 } }, "Programación Global y Específica"),
        React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: onClose }, "Cerrar")
      ),

      React.createElement("div", { className: "tabs-header" },
        React.createElement("button", { 
          className: activeTab === "global" ? "tab-btn active" : "tab-btn",
          onClick: () => { setActiveTab("global"); setEditingEntity(null); }
        }, "Global"),
        React.createElement("button", { 
          className: activeTab === "clients" ? "tab-btn active" : "tab-btn",
          onClick: () => { setActiveTab("clients"); setEditingEntity(null); }
        }, "Clientes"),
        React.createElement("button", { 
          className: activeTab === "urls" ? "tab-btn active" : "tab-btn",
          onClick: () => { setActiveTab("urls"); setEditingEntity(null); }
        }, "URLs Específicas")
      ),

      activeTab === "global" && renderGlobal(),
      activeTab === "clients" && renderEntities("client"),
      activeTab === "urls" && renderEntities("website")
    )
  );
}
