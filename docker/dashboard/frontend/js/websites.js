/**
 * websites.js — Componentes relacionados con la tabla de websites
 */
import React from "https://esm.sh/react@18.3.1";
import { AuditInfoPanel, RunList } from "./audit.js";
import { useI18n } from "./i18n.js";

function PendingBadge() {
  return React.createElement("span", {
    style: {
      marginLeft: "8px", fontSize: "10px", backgroundColor: "var(--bg-accent)",
      color: "var(--warning)", borderRadius: "4px", padding: "2px 6px", fontWeight: "bold"
    }
  }, "PENDIENTE");
}

function AuditProgress({ passed, total }) {
  const { t } = useI18n();
  const pct = total > 0 ? Math.round((passed / total) * 100) : 0;
  return React.createElement("div", { style: { minWidth: "100px" } },
    React.createElement("div", { style: { display: "flex", justifyContent: "space-between", fontSize: "10px", marginBottom: "4px", fontWeight: "bold" } },
      React.createElement("span", { style: { color: "var(--primary)" } }, t("table.auditing")),
      React.createElement("span", null, `${pct}%`)
    ),
    React.createElement("div", { className: "progress-container" },
      React.createElement("div", { 
        className: "progress-bar animated", 
        style: { width: `${Math.max(5, pct)}%` } 
      })
    )
  );
}

function WebsiteRow({ w, auditingIds, now, onOpen, onAudit, onEdit, onToggleActive, onDelete }) {
  const { t } = useI18n();
  const isAuditing = auditingIds.has(w.website_id) || w.run_status === "running";
  
  const scoreColor = (s) => {
    if (!s) return "var(--text-dim)";
    if (s >= 90) return "var(--success)";
    if (s >= 50) return "var(--warning)";
    return "var(--danger)";
  };

  const renderNextAudit = () => {
    if (!w.next_audit || !now) return null;
    const diff = new Date(w.next_audit * 1000) - now;
    if (diff <= 0) {
      return React.createElement("div", { style: { marginTop: "4px" } },
        React.createElement("span", { 
          style: { fontSize: "10px", color: "var(--text-dim)", background: "rgba(255,255,255,0.03)", padding: "2px 6px", borderRadius: "4px" } 
        }, `⏱️ ${t("table.running")}`)
      );
    }
    
    const d = Math.floor(diff / 86400000);
    const h = Math.floor((diff / 3600000) % 24);
    const m = Math.floor((diff / 60000) % 60);
    const s = Math.floor((diff / 1000) % 60);
    
    let diffStr = "";
    if (d > 0) diffStr = `${d}d ${h}h ${m}m`;
    else if (h > 0) diffStr = `${h}h ${m}m ${s}s`;
    else diffStr = `${m}m ${s}s`;

    let badgeStyle = {
      fontSize: "9px",
      display: "inline-flex",
      alignItems: "center",
      gap: "4px",
      padding: "2px 6px",
      borderRadius: "4px",
      marginTop: "4px",
    };

    if (w.cron_source === "website") {
      badgeStyle.background = "rgba(59, 130, 246, 0.12)";
      badgeStyle.color = "var(--primary)";
      badgeStyle.border = "1px solid rgba(59, 130, 246, 0.18)";
      badgeStyle.fontWeight = "bold";
      return React.createElement("div", null,
        React.createElement("span", { style: badgeStyle, title: `${t("scheduler.custom_schedule")}: ${w.resolved_cron}` }, `⏱️ ${diffStr} ${t("table.web_specific")}`)
      );
    } else if (w.cron_source === "client") {
      badgeStyle.background = "rgba(16, 185, 129, 0.12)";
      badgeStyle.color = "var(--success)";
      badgeStyle.border = "1px solid rgba(16, 185, 129, 0.18)";
      badgeStyle.fontWeight = "bold";
      return React.createElement("div", null,
        React.createElement("span", { style: badgeStyle, title: `${t("table.client_inherited")}: ${w.resolved_cron}` }, `⏱️ ${diffStr} ${t("table.client_inherited")}`)
      );
    } else {
      badgeStyle.background = "rgba(255, 255, 255, 0.03)";
      badgeStyle.color = "var(--text-dim)";
      badgeStyle.border = "1px solid rgba(255, 255, 255, 0.06)";
      return React.createElement("div", null,
        React.createElement("span", { style: badgeStyle, title: `${t("table.inherited")}: ${w.resolved_cron}` }, `⏱️ ${diffStr}`)
      );
    }
  };

  const renderStatus = () => {
    if (w.run_status === "running") {
      return React.createElement(AuditProgress, { 
        passed: w.sections_passed || 0, 
        total: w.sections_total || 10 
      });
    }
    
    return React.createElement("span", { 
      style: { 
        padding: "4px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: "700",
        background: w.audit_status === "excelente" ? "rgba(16, 185, 129, 0.1)" : "rgba(255,255,255,0.05)",
        color: w.audit_status === "excelente" ? "var(--success)" : "var(--text-dim)"
      } 
    }, (w.audit_status || w.run_status || "nuevo").toUpperCase());
  };

  return React.createElement("tr", null,
    React.createElement("td", { style: { fontWeight: "600", paddingTop: "12px", paddingBottom: "12px" } },
      React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "6px" } },
        React.createElement("span", {
          onClick: () => onOpen(w),
          style: { cursor: "pointer", color: "var(--primary)", textDecoration: "none" }
        }, w.label || w.url),
        w.pending_audit && React.createElement(PendingBadge)
      ),
      renderNextAudit()
    ),
    React.createElement("td", { style: { color: w.client_name ? "var(--text-dim)" : "var(--text-dim)", fontStyle: w.client_name ? "normal" : "italic" } }, w.client_name || "N/A"),
    React.createElement("td", { style: { fontWeight: "800", color: scoreColor(w.score) } }, w.score ?? "-"),
    React.createElement("td", { style: { opacity: 0.6 } }, w.previous_score ?? "-"),
    React.createElement("td", null, `${w.sections_passed ?? 0}/${w.sections_total ?? 10}`),
    React.createElement("td", { style: { fontSize: "12px", color: "var(--text-dim)" } }, w.audit_date || "-"),
    React.createElement("td", null, renderStatus()),
    React.createElement("td", null,
        React.createElement("div", { 
        style: { 
          width: "10px", height: "10px", borderRadius: "50%", 
          background: w.active ? "var(--success)" : "var(--danger)",
          boxShadow: `0 0 8px ${w.active ? "var(--success)" : "var(--danger)"}`
        } 
      })
    ),
    React.createElement("td", null,
      React.createElement("div", { style: { display: "flex", gap: "6px" } },
        React.createElement("button", {
          onClick: () => onAudit(w),
          disabled: isAuditing || w.pending_audit,
          className: "btn-base btn-small btn-ghost",
          title: t("table.audit"),
        }, isAuditing ? "..." : t("table.audit")),
        React.createElement("button", {
          onClick: () => onEdit(w),
          className: "btn-base btn-small btn-ghost",
          title: t("table.edit")
        }, t("table.edit")),
        React.createElement("button", {
          onClick: () => onDelete(w),
          className: "btn-base btn-small btn-ghost",
          style: { color: "var(--danger)" },
          title: t("table.delete")
        }, t("table.delete"))
      )
    )
  );
}

export function WebsitesTable({ websites, auditingIds, now, onOpen, onAudit, onEdit, onToggleActive, onDelete }) {
  const { t } = useI18n();
  return React.createElement("div", { className: "table-container" },
    React.createElement("table", null,
      React.createElement("thead", null,
        React.createElement("tr", null,
          [t("table.url"), t("table.client"), t("table.score"), "Prev.", "Sect.", t("table.last_audit"), t("table.status"), "Act.", t("table.actions")].map(
            (h) => React.createElement("th", { key: h }, h)
          )
        )
      ),
      React.createElement("tbody", null,
        websites.length > 0 ? websites.map((w) =>
          React.createElement(WebsiteRow, {
            key: w.website_id, w, auditingIds, now,
            onOpen, onAudit, onEdit, onToggleActive, onDelete,
          })
        ) : React.createElement("tr", null, React.createElement("td", { colSpan: 9, style: { textAlign: "center", padding: "40px", color: "var(--text-dim)" } }, t("scheduler.no_results")))
      )
    )
  );
}

export function WebsiteDetailModal({
  website, auditingIds,
  runs, runSections, runIssues,
  onAudit, onToggleActive, onDelete, onToggleSections, onClose,
}) {
  const { t } = useI18n();
  const isAuditing = auditingIds.has(website.website_id) || website.run_status === "running";

  return React.createElement("div", { className: "modal", onClick: onClose },
    React.createElement("div", { className: "modal-content premium-modal", style: { maxWidth: "1000px", width: "100%" }, onClick: (e) => e.stopPropagation() },
      React.createElement("div", { style: { padding: "30px" } },
        React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "30px" } },
          React.createElement("div", null,
            React.createElement("h2", { style: { margin: 0, fontSize: "24px", background: "none", webkitTextFillColor: "initial", color: "var(--text-main)" } }, website.url),
            React.createElement("p", { style: { margin: "5px 0 0", color: "var(--text-dim)" } }, `${t("table.client")}: ${website.client_name || "N/A"}`)
          ),
          React.createElement("button", { className: "btn-base btn-ghost", onClick: onClose }, t("modals.close"))
        ),

        React.createElement("div", { style: { marginBottom: "30px", display: "flex", gap: "12px" } },
          React.createElement("button", {
            onClick: () => onAudit(website),
            disabled: isAuditing || website.pending_audit,
            className: "btn-base btn-primary",
          }, isAuditing ? t("table.auditing") : t("table.audit")),
          React.createElement("button", {
            onClick: () => onToggleActive(website),
            className: `btn-base ${website.active ? "btn-danger" : "btn-success"}`,
          }, website.active ? t("table.inactive") : t("table.active")),
          React.createElement("button", {
            onClick: () => onDelete(website),
            className: "btn-base btn-ghost",
            style: { color: "var(--danger)" }
          }, t("table.delete"))
        ),

        React.createElement(AuditInfoPanel),

        React.createElement("h3", { style: { marginTop: "40px", borderBottom: "1px solid rgba(255,255,255,0.05)", paddingBottom: "15px" } }, t("audit.history")),
        React.createElement(RunList, { runs, runSections, runIssues, onToggleSections })
      )
    )
  );
}
