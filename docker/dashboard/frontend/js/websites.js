/**
 * websites.js — Componentes relacionados con la tabla de websites
 */
import React from "https://esm.sh/react@18.3.1";
import { AuditInfoPanel, RunList } from "./audit.js";

function PendingBadge() {
  return React.createElement("span", {
    style: {
      marginLeft: "8px", fontSize: "10px", backgroundColor: "rgba(245, 158, 11, 0.2)",
      color: "#f59e0b", borderRadius: "4px", padding: "2px 6px", fontWeight: "bold"
    }
  }, "PENDIENTE");
}

function AuditProgress({ passed, total }) {
  const pct = total > 0 ? Math.round((passed / total) * 100) : 0;
  return React.createElement("div", { style: { minWidth: "100px" } },
    React.createElement("div", { style: { display: "flex", justifyContent: "space-between", fontSize: "10px", marginBottom: "4px", fontWeight: "bold" } },
      React.createElement("span", { style: { color: "var(--primary)" } }, "AUDITANDO..."),
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

function WebsiteRow({ w, auditingIds, onOpen, onAudit, onEdit, onToggleActive, onDelete }) {
  const isAuditing = auditingIds.has(w.website_id) || w.run_status === "running";
  
  const scoreColor = (s) => {
    if (!s) return "var(--text-dim)";
    if (s >= 90) return "var(--success)";
    if (s >= 50) return "var(--warning)";
    return "var(--danger)";
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
    React.createElement("td", { style: { fontWeight: "600" } },
      React.createElement("span", {
        onClick: () => onOpen(w),
        style: { cursor: "pointer", color: "var(--primary)", textDecoration: "none" }
      }, w.label || w.url),
      w.pending_audit && React.createElement(PendingBadge)
    ),
    React.createElement("td", { style: { color: "var(--text-dim)" } }, w.client_name || "-"),
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
          boxShadow: `0 0 8px ${w.active ? "var(--success)" : "var(--danger)"}44`
        } 
      })
    ),
    React.createElement("td", null,
      React.createElement("div", { style: { display: "flex", gap: "6px" } },
        React.createElement("button", {
          onClick: () => onAudit(w),
          disabled: isAuditing || w.pending_audit,
          className: "btn-base btn-small btn-ghost",
          title: "Auditar ahora",
        }, isAuditing ? "..." : "Auditar"),
        React.createElement("button", {
          onClick: () => onEdit(w),
          className: "btn-base btn-small btn-ghost",
          title: "Editar"
        }, "Editar"),
        React.createElement("button", {
          onClick: () => onDelete(w),
          className: "btn-base btn-small btn-ghost",
          style: { color: "var(--danger)" },
          title: "Eliminar"
        }, "Borrar")
      )
    )
  );
}

export function WebsitesTable({ websites, auditingIds, onOpen, onAudit, onEdit, onToggleActive, onDelete }) {
  return React.createElement("div", { className: "table-container" },
    React.createElement("table", null,
      React.createElement("thead", null,
        React.createElement("tr", null,
          ["Sitio Web", "Cliente", "Score", "Prev.", "Sect.", "Última", "Estado", "Act.", "Acciones"].map(
            (h) => React.createElement("th", { key: h }, h)
          )
        )
      ),
      React.createElement("tbody", null,
        websites.length > 0 ? websites.map((w) =>
          React.createElement(WebsiteRow, {
            key: w.website_id, w, auditingIds,
            onOpen, onAudit, onEdit, onToggleActive, onDelete,
          })
        ) : React.createElement("tr", null, React.createElement("td", { colSpan: 9, style: { textAlign: "center", padding: "40px", color: "var(--text-dim)" } }, "No se encontraron resultados"))
      )
    )
  );
}

export function WebsiteDetailModal({
  website, auditingIds,
  runs, runSections, runIssues,
  onAudit, onToggleActive, onDelete, onToggleSections, onClose,
}) {
  const isAuditing = auditingIds.has(website.website_id) || website.run_status === "running";

  return React.createElement("div", { className: "modal", onClick: onClose },
    React.createElement("div", { className: "modal-content premium-modal", style: { maxWidth: "1000px", width: "100%" }, onClick: (e) => e.stopPropagation() },
      React.createElement("div", { style: { padding: "30px" } },
        React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "30px" } },
          React.createElement("div", null,
            React.createElement("h2", { style: { margin: 0, fontSize: "24px", background: "none", webkitTextFillColor: "initial", color: "#fff" } }, website.url),
            React.createElement("p", { style: { margin: "5px 0 0", color: "var(--text-dim)" } }, `Cliente: ${website.client_name}`)
          ),
          React.createElement("button", { className: "btn-base btn-ghost", onClick: onClose }, "Cerrar")
        ),

        React.createElement("div", { style: { marginBottom: "30px", display: "flex", gap: "12px" } },
          React.createElement("button", {
            onClick: () => onAudit(website),
            disabled: isAuditing || website.pending_audit,
            className: "btn-base btn-primary",
          }, isAuditing ? "Auditoría en curso..." : "Lanzar Auditoría Ahora"),
          React.createElement("button", {
            onClick: () => onToggleActive(website),
            className: `btn-base ${website.active ? "btn-danger" : "btn-success"}`,
          }, website.active ? "Desactivar Sitio" : "Activar Sitio"),
          React.createElement("button", {
            onClick: () => onDelete(website),
            className: "btn-base btn-ghost",
            style: { color: "var(--danger)" }
          }, "Borrar")
        ),

        React.createElement(AuditInfoPanel),

        React.createElement("h3", { style: { marginTop: "40px", borderBottom: "1px solid rgba(255,255,255,0.05)", paddingBottom: "15px" } }, "Historial de Análisis"),
        React.createElement(RunList, { runs, runSections, runIssues, onToggleSections })
      )
    )
  );
}
