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

    const badgeStyle = {
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
      badgeStyle.background = "var(--bg-accent)";
      badgeStyle.color = "var(--text-dim)";
      badgeStyle.border = "1px solid var(--border-main)";
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
        background: w.audit_status === "excelente" ? "rgba(16, 185, 129, 0.1)" : "var(--bg-accent)",
        border: `1px solid ${w.audit_status === "excelente" ? "rgba(16, 185, 129, 0.2)" : "var(--border-main)"}`,
        color: w.audit_status === "excelente" ? "var(--success)" : "var(--text-dim)"
      } 
    }, (w.audit_status || w.run_status || "nuevo").toUpperCase());
  };

  return React.createElement("tr", null,
    React.createElement("td", { style: { fontWeight: "600", paddingTop: "12px", paddingBottom: "12px" } },
      React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "6px" } },
        React.createElement("span", {
          id: "tour-row-url",
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
      React.createElement("div", { id: "tour-row-actions", style: { display: "flex", gap: "6px" } },
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

function sortValue(web, key) {
  switch (key) {
    case "url": return (web.label || web.url || "").toString().toLowerCase();
    case "client": return (web.client_name || "").toString().toLowerCase();
    case "score": return Number(web.score ?? Number.NEGATIVE_INFINITY);
    case "prev": return Number(web.previous_score ?? Number.NEGATIVE_INFINITY);
    case "sections": return Number(web.sections_passed ?? 0);
    case "last_audit": return new Date(web.audit_date).getTime() || 0;
    case "status": return (web.audit_status || web.run_status || "").toString().toLowerCase();
    case "active": return web.active ? 1 : 0;
    default: return "";
  }
}

function stableSort(websites, key, direction) {
  return [...websites].sort((a, b) => {
    const aVal = sortValue(a, key);
    const bVal = sortValue(b, key);
    if (aVal < bVal) return direction === "asc" ? -1 : 1;
    if (aVal > bVal) return direction === "asc" ? 1 : -1;
    return 0;
  });
}

export function WebsitesTable({ websites, auditingIds, now, onOpen, onAudit, onEdit, onToggleActive, onDelete }) {
  const { t, lang } = useI18n();
  const [sortConfig, setSortConfig] = React.useState({ key: "url", direction: "asc" });
  
  // Pagination State
  const [currentPage, setCurrentPage] = React.useState(1);
  const itemsPerPage = 8;

  // Reset to page 1 when the filtered list changes
  React.useEffect(() => {
    setCurrentPage(1);
  }, [websites.length]);

  const handleHeaderClick = (key) => {
    setSortConfig(prev => {
      if (prev.key === key) {
        return { key, direction: prev.direction === "asc" ? "desc" : "asc" };
      }
      return { key, direction: "asc" };
    });
  };

  const sortedWebsites = stableSort(websites || [], sortConfig.key, sortConfig.direction);
  
  // Pagination calculation
  const totalPages = Math.ceil(sortedWebsites.length / itemsPerPage) || 1;
  const activePage = Math.min(currentPage, totalPages);
  const startIndex = (activePage - 1) * itemsPerPage;
  const paginatedWebsites = sortedWebsites.slice(startIndex, startIndex + itemsPerPage);

  const headers = [
    { key: "url", label: t("table.url") },
    { key: "client", label: t("table.client") },
    { key: "score", label: t("table.score") },
    { key: "prev", label: "Prev." },
    { key: "sections", label: "Sect." },
    { key: "last_audit", label: t("table.last_audit") },
    { key: "status", label: t("table.status") },
    { key: "active", label: "Act." },
    { key: "actions", label: t("table.actions"), sortable: false }
  ];

  return React.createElement("div", { className: "table-container", id: "tour-table" },
    React.createElement("table", null,
      React.createElement("thead", { id: "tour-sortable-headers" },
        React.createElement("tr", null,
          headers.map((header) => {
            const isSortable = header.sortable !== false;
            const active = sortConfig.key === header.key;
            const arrow = active ? (sortConfig.direction === "asc" ? " ▲" : " ▼") : "";
            return React.createElement("th", {
              key: header.key,
              onClick: isSortable ? () => handleHeaderClick(header.key) : undefined,
              style: isSortable ? { cursor: "pointer", userSelect: "none" } : undefined
            }, header.label + arrow);
          })
        )
      ),
      React.createElement("tbody", null,
        paginatedWebsites.length > 0 ? paginatedWebsites.map((w) =>
          React.createElement(WebsiteRow, {
            key: w.website_id, w, auditingIds, now,
            onOpen, onAudit, onEdit, onToggleActive, onDelete,
          })
        ) : React.createElement("tr", null, React.createElement("td", { colSpan: 9, style: { textAlign: "center", padding: "40px", color: "var(--text-dim)" } }, t("scheduler.no_results")))
      )
    ),
    sortedWebsites.length > itemsPerPage && React.createElement("div", {
      id: "tour-pagination",
      style: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "12px 20px",
        borderTop: "1px solid var(--border-main)",
        background: "var(--bg-accent)",
        gap: "15px",
        flexWrap: "wrap"
      }
    },
      React.createElement("span", { style: { fontSize: "13px", color: "var(--text-dim)", fontWeight: "500" } },
        lang === "es" 
          ? `Mostrando ${startIndex + 1}-${Math.min(startIndex + itemsPerPage, sortedWebsites.length)} de ${sortedWebsites.length}`
          : `Showing ${startIndex + 1}-${Math.min(startIndex + itemsPerPage, sortedWebsites.length)} of ${sortedWebsites.length}`
      ),
      React.createElement("div", { style: { display: "flex", gap: "6px", alignItems: "center" } },
        React.createElement("button", {
          disabled: activePage === 1,
          onClick: () => setCurrentPage(prev => Math.max(prev - 1, 1)),
          className: "btn-base btn-small btn-ghost",
          style: { cursor: activePage === 1 ? "not-allowed" : "pointer", opacity: activePage === 1 ? 0.5 : 1 }
        }, lang === "es" ? "Anterior" : "Previous"),
        
        (function() {
          const pages = [];
          if (totalPages <= 1) {
            pages.push(1);
          } else {
            pages.push(1);
            if (activePage > 2) pages.push('...-left');
            if (activePage > 1 && activePage < totalPages) pages.push(activePage);
            if (activePage < totalPages - 1) pages.push('...-right');
            pages.push(totalPages);
          }
          return pages.map((pageNum) => {
            if (typeof pageNum === 'string' && pageNum.startsWith('...')) {
              return React.createElement("span", { key: pageNum, style: { padding: "0 4px", color: "var(--text-dim)" } }, "...");
            }
            const isActive = pageNum === activePage;
            return React.createElement("button", {
              key: pageNum,
              onClick: () => setCurrentPage(pageNum),
              className: `btn-base btn-small ${isActive ? "btn-primary" : "btn-ghost"}`,
              style: {
                minWidth: "28px",
                height: "28px",
                padding: 0,
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                fontWeight: "bold",
                fontSize: "12px"
              }
            }, pageNum);
          });
        })(),

        React.createElement("button", {
          disabled: activePage === totalPages,
          onClick: () => setCurrentPage(prev => Math.min(prev + 1, totalPages)),
          className: "btn-base btn-small btn-ghost",
          style: { cursor: activePage === totalPages ? "not-allowed" : "pointer", opacity: activePage === totalPages ? 0.5 : 1 }
        }, lang === "es" ? "Siguiente" : "Next")
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
