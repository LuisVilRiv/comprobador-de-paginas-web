/**
 * scheduler.js — Hub Central de Programación.
 */
import React from "https://esm.sh/react@18.3.1";
import { useI18n } from "./i18n.js";

// ── UTILIDADES CRON ─────────────────────────────────────────────────────────

export function parseCron(c) {
  const parts = (c && c.split(" ").length === 5 ? c : "0 0 * * *").split(" ");
  return { min: parts[0], hour: parts[1], dom: parts[2], month: parts[3], dow: parts[4] };
}

export function splitCronRules(value) {
  if (!value) return [];
  return value
    .split(/\s*,\s*(?=(?:[^\s]+\s+){4}[^\s]+)/)
    .map(c => c.trim())
    .filter(Boolean);
}

export function detectFrequency(parts) {
  if (parts.dow !== "*") return "weekly";
  if (parts.month.includes("/")) return "monthly_periodic";
  if (parts.dom.includes("/")) return "daily_periodic";
  if (parts.dom !== "*" && parts.month === "*") return "monthly";
  if (parts.dom !== "*" && parts.month !== "*") return "yearly";
  return "daily";
}

export function parseCronRule(cron) {
  const parts = parseCron(cron);
  return {
    min: parts.min,
    hour: parts.hour,
    dom: parts.dom,
    month: parts.month,
    dow: parts.dow,
  };
}

export function serializeCronRule(rule) {
  return `${rule.min} ${rule.hour} ${rule.dom} ${rule.month} ${rule.dow}`;
}

export function isWeeklyRule(rule) {
  return rule.dow !== "*" && rule.dom === "*" && rule.month === "*";
}

export function expandWeeklyRule(rule) {
  if (!isWeeklyRule(rule)) return [rule];
  return rule.dow.split(",").filter(Boolean).map(day => ({ ...rule, dow: day }));
}

export function normalizeWeeklyRules(rules) {
  return rules
    .flatMap(expandWeeklyRule)
    .sort((a, b) => Number(a.dow) - Number(b.dow));
}

export function createWeeklyRule(day) {
  return { min: "0", hour: "0", dom: "*", month: "*", dow: day };
}

// ── COMPONENTES DE UI PREMIUM ───────────────────────────────────────────────

function SingleCronEditor({ cronValue, color, onChange, onRemove, showRemove }) {
  const { t } = useI18n();
  const parts = parseCron(cronValue);
  const freq = detectFrequency(parts);

  const updateParts = (newParts) => {
    const p = { ...parts, ...newParts };
    onChange(`${p.min} ${p.hour} ${p.dom} ${p.month} ${p.dow}`);
  };

  const DAYS = [
    { id: "1", n: t("scheduler.day_l") }, { id: "2", n: t("scheduler.day_m") }, { id: "3", n: t("scheduler.day_x") },
    { id: "4", n: t("scheduler.day_j") }, { id: "5", n: t("scheduler.day_v") }, { id: "6", n: t("scheduler.day_s") }, { id: "0", n: t("scheduler.day_d") },
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
    }, t("table.delete")),

    React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" } },
      React.createElement("div", { id: "tour-cron-frequency" },
        React.createElement("label", { style: { fontSize: "11px", opacity: 0.5, display: "block", marginBottom: "8px", textTransform: "uppercase" } }, t("scheduler.freq")),
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
          React.createElement("option", { value: "daily" }, t("scheduler.daily")),
          React.createElement("option", { value: "daily_periodic" }, t("scheduler.daily_x")),
          React.createElement("option", { value: "weekly" }, t("scheduler.weekly")),
          React.createElement("option", { value: "monthly" }, t("scheduler.monthly")),
          React.createElement("option", { value: "monthly_periodic" }, t("scheduler.monthly_x")),
          React.createElement("option", { value: "yearly" }, t("scheduler.yearly"))
        )
      ),
      React.createElement("div", null,
        React.createElement("label", { style: { fontSize: "11px", opacity: 0.5, display: "block", marginBottom: "8px", textTransform: "uppercase" } }, t("scheduler.time")),
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
      React.createElement("label", { style: { fontSize: "11px", opacity: 0.5, display: "block", marginBottom: "8px", textTransform: "uppercase" } }, t("scheduler.week_days")),
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
              color: isSelected ? "var(--text-main)" : "var(--text-dim)",
              width: "32px", height: "32px", borderRadius: "8px", fontSize: "11px", fontWeight: "bold",
              cursor: "pointer", transition: "var(--transition)"
            }
          }, d.n);
        })
      ),
      React.createElement("p", { style: { marginTop: "12px", fontSize: "12px", color: "var(--text-dim)", lineHeight: 1.5 } }, t("scheduler.weekly_note"))
    ),

    freq === "daily_periodic" && React.createElement("div", { style: { marginTop: "15px" } },
      React.createElement("label", { style: { fontSize: "11px", opacity: 0.5, display: "block", marginBottom: "8px", textTransform: "uppercase" } }, t("scheduler.every_x_days")),
      React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "10px" } },
        React.createElement("input", {
          type: "number", min: 2, max: 31, className: "premium-input",
          style: { width: "100px", padding: "10px", fontSize: "13px" },
          value: parts.dom.includes("/") ? parseInt(parts.dom.split("/")[1]) || 2 : 2,
          onChange: (e) => {
            const val = Math.max(2, Math.min(31, parseInt(e.target.value) || 2));
            updateParts({ dom: `*/${val}` });
          }
        }),
        React.createElement("span", { style: { fontSize: "13px", color: "var(--text-dim)" } }, t("scheduler.days"))
      )
    ),

    freq === "monthly_periodic" && React.createElement("div", { style: { marginTop: "15px" } },
      React.createElement("label", { style: { fontSize: "11px", opacity: 0.5, display: "block", marginBottom: "8px", textTransform: "uppercase" } }, t("scheduler.every_x_months")),
      React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "10px" } },
        React.createElement("input", {
          type: "number", min: 2, max: 12, className: "premium-input",
          style: { width: "100px", padding: "10px", fontSize: "13px" },
          value: parts.month.includes("/") ? parseInt(parts.month.split("/")[1]) || 3 : 3,
          onChange: (e) => {
            const val = Math.max(2, Math.min(12, parseInt(e.target.value) || 2));
            updateParts({ month: `*/${val}` });
          }
        }),
        React.createElement("span", { style: { fontSize: "13px", color: "var(--text-dim)" } }, t("scheduler.months"))
      )
    ),

    freq === "yearly" && React.createElement("div", { style: { marginTop: "15px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" } },
      React.createElement("div", null,
        React.createElement("label", { style: { fontSize: "11px", opacity: 0.5, display: "block", marginBottom: "8px", textTransform: "uppercase" } }, t("scheduler.month_year")),
        React.createElement("select", {
          value: parts.month !== "*" ? parts.month : "1",
          className: "premium-input", style: { padding: "10px", fontSize: "13px" },
          onChange: (e) => updateParts({ month: e.target.value })
        },
          React.createElement("option", { value: "1" }, t("scheduler.m_1")),
          React.createElement("option", { value: "2" }, t("scheduler.m_2")),
          React.createElement("option", { value: "3" }, t("scheduler.m_3")),
          React.createElement("option", { value: "4" }, t("scheduler.m_4")),
          React.createElement("option", { value: "5" }, t("scheduler.m_5")),
          React.createElement("option", { value: "6" }, t("scheduler.m_6")),
          React.createElement("option", { value: "7" }, t("scheduler.m_7")),
          React.createElement("option", { value: "8" }, t("scheduler.m_8")),
          React.createElement("option", { value: "9" }, t("scheduler.m_9")),
          React.createElement("option", { value: "10" }, t("scheduler.m_10")),
          React.createElement("option", { value: "11" }, t("scheduler.m_11")),
          React.createElement("option", { value: "12" }, t("scheduler.m_12"))
        )
      ),
      React.createElement("div", null,
        React.createElement("label", { style: { fontSize: "11px", opacity: 0.5, display: "block", marginBottom: "8px", textTransform: "uppercase" } }, t("scheduler.day_month")),
        React.createElement("input", {
          type: "number", min: 1, max: 31, className: "premium-input",
          style: { padding: "10px", fontSize: "13px" },
          value: parts.dom !== "*" ? parseInt(parts.dom) || 1 : 1,
          onChange: (e) => {
            const val = Math.max(1, Math.min(31, parseInt(e.target.value) || 1));
            updateParts({ dom: val.toString() });
          }
        })
      )
    )
  );
}

function WeeklyCronEditor({ rules, color, onChange, t, onFrequencyChange }) {
  const DAYS = [
    { id: "1", n: t("scheduler.day_l"), full: t("scheduler.day_l_full") },
    { id: "2", n: t("scheduler.day_m"), full: t("scheduler.day_m_full") },
    { id: "3", n: t("scheduler.day_x"), full: t("scheduler.day_x_full") },
    { id: "4", n: t("scheduler.day_j"), full: t("scheduler.day_j_full") },
    { id: "5", n: t("scheduler.day_v"), full: t("scheduler.day_v_full") },
    { id: "6", n: t("scheduler.day_s"), full: t("scheduler.day_s_full") },
    { id: "0", n: t("scheduler.day_d"), full: t("scheduler.day_d_full") },
  ];

  const selectedDays = rules.map(r => r.dow);

  const updateRule = (index, updated) => {
    const next = [...rules];
    next[index] = updated;
    onChange(next);
  };

  const removeRule = (index) => {
    const next = rules.filter((_, i) => i !== index);
    onChange(next);
  };

  const toggleDay = (dayId) => {
    if (selectedDays.includes(dayId)) {
      onChange(rules.filter(r => r.dow !== dayId));
      return;
    }
    onChange([...rules, createWeeklyRule(dayId)].sort((a, b) => Number(a.dow) - Number(b.dow)));
  };

  // Get a representative time from the first rule (all rules should typically have the same time)
  const representativeTime = rules.length > 0 ? rules[0] : { hour: "0", min: "0" };

  return React.createElement("div", {
    style: {
      background: "var(--bg-accent)",
      border: "1px solid var(--border-main)",
      borderRadius: "14px",
      padding: "18px",
      marginBottom: "12px"
    }
  },
    // Frequency selector to allow switching away from weekly mode
    React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "18px" } },
      React.createElement("div", null,
        React.createElement("label", { style: { fontSize: "11px", opacity: 0.5, display: "block", marginBottom: "8px", textTransform: "uppercase" } }, t("scheduler.freq")),
        React.createElement("select", {
          value: "weekly", className: "premium-input", style: { padding: "10px", fontSize: "13px" },
          onChange: (e) => {
            const f = e.target.value;
            if (onFrequencyChange) onFrequencyChange(f, representativeTime);
          }
        },
          React.createElement("option", { value: "daily" }, t("scheduler.daily")),
          React.createElement("option", { value: "daily_periodic" }, t("scheduler.daily_x")),
          React.createElement("option", { value: "weekly", selected: true }, t("scheduler.weekly")),
          React.createElement("option", { value: "monthly" }, t("scheduler.monthly")),
          React.createElement("option", { value: "monthly_periodic" }, t("scheduler.monthly_x")),
          React.createElement("option", { value: "yearly" }, t("scheduler.yearly"))
        )
      ),
      React.createElement("div", null,
        React.createElement("strong", { style: { display: "block", marginBottom: "8px", color: "var(--text-main)" } }, t("scheduler.time")),
        React.createElement("span", { style: { fontSize: "12px", color: "var(--text-dim)" } }, t("scheduler.weekly_entry_time_help"))
      )
    ),
    React.createElement("div", { style: { display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "18px" } },
      DAYS.map(d => {
        const isSelected = selectedDays.includes(d.id);
        return React.createElement("button", {
          key: d.id, type: "button",
          onClick: () => toggleDay(d.id),
          style: {
            background: isSelected ? color : "var(--btn-ghost-bg)",
            border: `1px solid ${isSelected ? color : "var(--border-main)"}`,
            color: isSelected ? "var(--text-main)" : "var(--text-dim)",
            width: "32px", height: "32px", borderRadius: "8px", fontSize: "11px", fontWeight: "bold",
            cursor: "pointer", transition: "var(--transition)"
          }
        }, d.n);
      })
    ),
    rules.length === 0 && React.createElement("p", { style: { fontSize: "12px", color: "var(--text-dim)", marginBottom: "12px" } }, t("scheduler.weekly_select_day_message")),
    rules.map((rule, idx) => {
      const day = DAYS.find(d => d.id === rule.dow);
      return React.createElement("div", {
        key: idx,
        style: {
          display: "grid",
          gridTemplateColumns: "1fr auto",
          gap: "14px",
          alignItems: "center",
          padding: "12px 0",
          borderTop: idx > 0 ? "1px solid rgba(255,255,255,0.08)" : "none"
        }
      },
        React.createElement("div", null,
          React.createElement("strong", { style: { display: "block", marginBottom: "6px", color: "var(--text-main)" } }, `${t("scheduler.hour_of")} ${day ? day.full : rule.dow}`),
          React.createElement("input", {
            type: "time", className: "premium-input",
            style: { padding: "10px", fontSize: "13px", width: "100%" },
            value: `${rule.hour.padStart(2, "0")}:${rule.min.padStart(2, "0")}`,
            onChange: (e) => {
              const [h, m] = e.target.value.split(":");
              updateRule(idx, { ...rule, hour: parseInt(h).toString(), min: parseInt(m).toString() });
            }
          })
        ),
        React.createElement("button", {
          type: "button",
          onClick: () => removeRule(idx),
          className: "btn-base btn-small btn-ghost",
          style: { color: "var(--danger)", minWidth: "fit-content" }
        }, t("table.delete"))
      );
    })
  );
}

export function CronManager({ label, value, onChange, color = "var(--primary)" }) {
  const { t } = useI18n();
  const [internalMode, setInternalMode] = React.useState("simple");
  const rawCrons = splitCronRules(value || "").map(c => c.trim()).filter(c => c);
  const crons = rawCrons.length === 0 && internalMode === "simple" ? ["0 0 * * *"] : rawCrons;
  const cronRules = crons.map(parseCronRule);
  const expandedWeeklyRules = normalizeWeeklyRules(cronRules.filter(isWeeklyRule));
  const weeklyRules = expandedWeeklyRules;
  const otherRules = cronRules.filter(r => !isWeeklyRule(r));
  const isWeeklyOnly = weeklyRules.length > 0 && otherRules.length === 0;

  const updateCronRules = (nextRules) => onChange(nextRules.map(serializeCronRule).join(", "));
  const handleUpdate = (idx, val) => {
    const next = [...crons];
    next[idx] = val;
    onChange(next.join(", "));
  };

  const handleAdd = () => onChange([...crons, "0 0 * * *"].join(", "));
  const handleRemove = (idx) => onChange(crons.filter((_, i) => i !== idx).join(", "));

  return React.createElement("div", { className: "cron-manager-container", style: { marginBottom: "20px" } },
    React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" } },
      label && React.createElement("h5", { style: { margin: 0, color: color, fontSize: "11px", textTransform: "uppercase", letterSpacing: "1px", opacity: 0.9 } }, label),
      React.createElement("button", {
        id: "tour-cron-expert-toggle",
        type: "button",
        onClick: () => setInternalMode(internalMode === "simple" ? "expert" : "simple"),
        style: { background: "transparent", border: "none", color: "var(--text-dim)", fontSize: "10px", cursor: "pointer", textDecoration: "underline" }
      }, internalMode === "simple" ? t("scheduler.expert_mode") : t("scheduler.simple_mode"))
    ),
    
    internalMode === "simple" ? React.createElement("div", null,
      isWeeklyOnly ? React.createElement(WeeklyCronEditor, {
        rules: weeklyRules,
        color,
        onChange: updateCronRules,
        t,
        onFrequencyChange: (newFreq, time) => {
          // Convert from weekly mode to the new frequency
          let newRule;
          if (newFreq === "daily") {
            newRule = { min: time.min, hour: time.hour, dom: "*", month: "*", dow: "*" };
          } else if (newFreq === "daily_periodic") {
            newRule = { min: time.min, hour: time.hour, dom: "*/2", month: "*", dow: "*" };
          } else if (newFreq === "monthly") {
            newRule = { min: time.min, hour: time.hour, dom: "1", month: "*", dow: "*" };
          } else if (newFreq === "monthly_periodic") {
            newRule = { min: time.min, hour: time.hour, dom: "1", month: "*/3", dow: "*" };
          } else if (newFreq === "yearly") {
            newRule = { min: time.min, hour: time.hour, dom: "1", month: "1", dow: "*" };
          } else {
            // Stay in weekly mode (shouldn't happen, but fallback)
            return;
          }
          onChange(serializeCronRule(newRule));
        }
      }) : React.createElement(React.Fragment, null,
        crons.map((c, i) => React.createElement(SingleCronEditor, {
          key: i, cronValue: c, color,
          onChange: (v) => handleUpdate(i, v),
          onRemove: () => handleRemove(i),
          showRemove: crons.length > 1
        })),
        React.createElement("button", {
          type: "button", onClick: handleAdd,
          className: "btn-base btn-ghost",
          style: { width: "100%", border: `1px dashed rgba(59,130,246,0.18)`, color, fontSize: "12px" }
        }, t("scheduler.add_rule"))
      )
    ) : React.createElement("div", null,
      React.createElement("input", {
        type: "text", value: value || "", className: "premium-input",
        placeholder: t("scheduler.expert_placeholder"),
        onChange: (e) => onChange(e.target.value),
        style: { fontSize: "14px" }
      }),
      React.createElement("p", { style: { fontSize: "11px", color: "var(--text-dim)", marginTop: "8px" } }, t("scheduler.expert_help"))
    )
  );
}

// ── HUB CENTRAL DE PROGRAMACIÓN ──────────────────────────────────────────────

export function SchedulerModal({ settings, clients, websites, onClose, onSaveSettings, onSaveEntityCron }) {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = React.useState("global");
  const [localSettings, setLocalSettings] = React.useState(settings);
  const [editingEntity, setEditingEntity] = React.useState(null);

  // Estados para búsqueda y filtrado integrado
  const [filterQuery, setFilterQuery] = React.useState("");
  const [showOnlyCustom, setShowOnlyCustom] = React.useState(false);

  React.useEffect(() => { setLocalSettings(settings); }, [settings]);

  const resetFilters = () => {
    setEditingEntity(null);
    setFilterQuery("");
    setShowOnlyCustom(false);
  };

  const renderGlobal = () => React.createElement("div", { id: "tour-cron-manager", style: { animation: "modalFadeIn 0.3s ease" } },
    React.createElement(CronManager, {
      label: t("scheduler.active_cycles"), color: "var(--primary)",
      value: localSettings.cron_active,
      onChange: (v) => setLocalSettings(s => ({ ...s, cron_active: v }))
    }),
    React.createElement("div", { style: { height: "10px" } }),
    React.createElement(CronManager, {
      label: t("scheduler.inactive_cycles"), color: "var(--purple)",
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

  const renderEntities = (type) => {
    const rawList = type === "client" 
      ? clients 
      : websites.map(w => ({ ...w, custom_cron: w.website_cron }));
    
    // Filtrado inteligente
    const filteredList = rawList.filter(item => {
      const name = (type === "client" ? item.name : (item.label || item.url || "")).toLowerCase();
      if (filterQuery && !name.includes(filterQuery.toLowerCase())) return false;
      if (showOnlyCustom && !item.custom_cron) return false;
      return true;
    });

    return React.createElement("div", { style: { animation: "modalFadeIn 0.3s ease" } },
      editingEntity ? React.createElement("div", null,
        React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "15px", marginBottom: "25px" } },
          React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: () => setEditingEntity(null) }, "Volver"),
          React.createElement("h4", { style: { margin: 0 } }, type === "client" ? editingEntity.name : editingEntity.url)
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
        // Barra de búsqueda e interruptor de filtro
        React.createElement("div", { style: { display: "flex", gap: "15px", alignItems: "center", marginBottom: "20px" } },
          React.createElement("input", {
            type: "text",
            className: "premium-input",
            placeholder: type === "client" ? t("scheduler.search_client") : t("scheduler.search_url"),
            value: filterQuery,
            onChange: (e) => setFilterQuery(e.target.value),
            style: { flex: 1, padding: "10px 14px", fontSize: "13px" }
          }),
          React.createElement("label", { 
            style: { display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "var(--text-dim)", cursor: "pointer", userSelect: "none" } 
          },
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
            React.createElement("thead", null, 
              React.createElement("tr", null, 
                React.createElement("th", null, type === "client" ? t("table.client") : t("table.url")),
                React.createElement("th", null, t("table.status")),
                React.createElement("th", { style: { textAlign: "right" } }, t("table.actions"))
              )
            ),
            React.createElement("tbody", null,
              filteredList.length > 0 ? filteredList.map(item => {
                        const isCustom = !!item.custom_cron;
                        const badgeStyle = isCustom ? {
                          background: type === "client" ? "rgba(16, 185, 129, 0.12)" : "rgba(59, 130, 246, 0.12)",
                          color: type === "client" ? "var(--success)" : "var(--primary)",
                          border: `1px solid ${type === "client" ? "rgba(16,185,145,0.18)" : "rgba(59,130,246,0.18)"}`,
                  padding: "4px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: "bold",
                  display: "inline-flex", alignItems: "center", gap: "4px"
                } : {
                          background: "rgba(255, 255, 255, 0.03)",
                  color: "var(--text-dim)",
                  padding: "4px 8px", borderRadius: "6px", fontSize: "11px",
                  display: "inline-flex", alignItems: "center", gap: "4px"
                };

                return React.createElement("tr", { key: type === "client" ? item.id : item.website_id },
                  React.createElement("td", { style: { fontWeight: "600" } }, type === "client" ? item.name : (item.label || item.url)),
                  React.createElement("td", null, 
                    React.createElement("span", { style: badgeStyle }, 
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
          className: activeTab === "global" ? "tab-btn active" : "tab-btn",
          onClick: () => { setActiveTab("global"); resetFilters(); }
        }, t("scheduler.tab_global")),
        React.createElement("button", { 
          className: activeTab === "clients" ? "tab-btn active" : "tab-btn",
          onClick: () => { setActiveTab("clients"); resetFilters(); }
        }, t("scheduler.tab_clients")),
        React.createElement("button", { 
          className: activeTab === "urls" ? "tab-btn active" : "tab-btn",
          onClick: () => { setActiveTab("urls"); resetFilters(); }
        }, t("scheduler.tab_urls"))
      ),

      activeTab === "global" && renderGlobal(),
      activeTab === "clients" && renderEntities("client"),
      activeTab === "urls" && renderEntities("website")
    )
  );
}
