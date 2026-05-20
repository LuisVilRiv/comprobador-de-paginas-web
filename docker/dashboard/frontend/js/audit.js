/**
 * audit.js — Componente de detalle de runs y secciones de auditoría.
 */
import React from "https://esm.sh/react@18.3.1";
import { fetchWebsiteRuns, fetchRunSections, fetchRunIssues, triggerAudit } from "./api.js";
import { useI18n } from "./i18n.js";

/**
 * Panel informativo sobre el propósito de cada tipo de prueba.
 */
export function AuditInfoPanel() {
  const { t } = useI18n();
  return React.createElement(
    "div",
    { className: "info-panel" },
    React.createElement("h4", null, t("audit.info_title")),
    React.createElement(
      "ul",
      null,
      React.createElement("li", null, React.createElement("strong", null, t("audit.info_sec")), t("audit.info_sec_desc")),
      React.createElement("li", null, React.createElement("strong", null, t("audit.info_seo")), t("audit.info_seo_desc")),
      React.createElement("li", null, React.createElement("strong", null, t("audit.info_perf")), t("audit.info_perf_desc")),
      React.createElement("li", null, React.createElement("strong", null, t("audit.info_html")), t("audit.info_html_desc")),
      React.createElement("li", null, React.createElement("strong", null, t("audit.info_acc")), t("audit.info_acc_desc")),
      React.createElement("li", null, React.createElement("strong", null, t("audit.info_nav")), t("audit.info_nav_desc"))
    )
  );
}

/**
 * Fila de issue individual dentro de una sección.
 */
function IssueRow({ issue }) {
  const { t } = useI18n();
  const isResolved = issue.diff_status === "resolved";
  const severityColor =
    issue.severity === "critical" ? "var(--danger)" :
    issue.severity === "high"     ? "var(--warning)" : "var(--text-dim)";
  const diffIcon = issue.diff_status === "new" ? "🔴" : issue.diff_status === "resolved" ? "🟢" : "⚪";

  return React.createElement(
    "div",
    { style: { marginBottom: "6px", lineHeight: "1.4" } },
    React.createElement("span", {
      style: { color: severityColor, fontWeight: "bold", marginRight: "8px", fontSize: "11px", display: "inline-flex", alignItems: "center", gap: "8px" }
    }, React.createElement("span", { style: { fontSize: "12px" } }, diffIcon), `[${issue.severity.toUpperCase()}]`),
    React.createElement("span", {
      style: {
        color: isResolved ? "var(--text-dim)" : "var(--text-main)",
        textDecoration: isResolved ? "line-through" : "none",
      }
    }, `${isResolved ? "RESUELTA: " : ""}${issue.message}`),
    issue.line_no && React.createElement(
      "span",
      { style: { color: "var(--text-dim)", marginLeft: "10px", fontSize: "11px", fontStyle: "italic" } },
      `(${t("audit.line")}: ${issue.line_no})`
    )
  );
}

/**
 * Tabla de secciones de un run con sus issues.
 */
function RunSectionsTable({ sections, issues }) {
  const { t } = useI18n();
  // issues can be an array or an object { current: [], resolved: [] }
  const currentIssues = issues && issues.current ? issues.current : (issues || []);
  const resolvedIssues = issues && issues.resolved ? issues.resolved : [];

  return React.createElement(
    "div", { className: "table-container" },
    React.createElement(
      "table", { className: "sections-table" },
      React.createElement(
        "thead", null,
        React.createElement("tr", null,
          [t("audit.col_section"), t("audit.col_execution"), t("audit.issues"), t("audit.col_desc"), t("audit.col_detail")].map(
            (h) => React.createElement("th", { key: h }, h)
          )
        )
      ),
      React.createElement(
        "tbody", null,
        sections.map((s) => {
          const sectionIssues = currentIssues.filter(i => i.category === s.section_key);
          const resolvedForSection = resolvedIssues.filter(i => i.category === s.section_key);
          const isBlocked = s.status === "failed" &&
            (s.result_description.toLowerCase().includes("bloqueado") ||
             s.result_description.toLowerCase().includes("firewall") ||
             s.result_description.toLowerCase().includes("403") ||
             sectionIssues.some(i =>
               i.message.toLowerCase().includes("bloqueada") ||
               i.message.toLowerCase().includes("firewall")
             ));

          return React.createElement(
            React.Fragment, { key: s.section_key },
            React.createElement("tr", { className: "section-row" },
              React.createElement("td", { style: { fontWeight: "bold" } },
                s.section_label,
                !s.passed && React.createElement("span", { style: { color: "var(--danger)", marginLeft: "6px" }, title: t("audit.issues") }, "⚠️")
              ),
              React.createElement("td", null,
                React.createElement("span", {
                  className: `status-badge ${isBlocked ? "blocked" : s.status === "failed" ? "failed" : s.passed ? "passed" : "warn"}`,
                }, isBlocked ? t("audit.status_blocked") : s.status === "failed" ? t("audit.status_failed") : t("audit.status_ok"))
              ),
              React.createElement("td", { style: { color: s.passed ? "var(--success)" : "var(--warning)", fontWeight: "bold" } }, s.issue_count),
              React.createElement("td", { style: { fontSize: "11px", opacity: 0.8 } }, s.check_description),
              React.createElement("td", null, s.result_description)
            ),
            (sectionIssues.length > 0 || resolvedForSection.length > 0) && React.createElement("tr", null,
              React.createElement("td", {
                colSpan: 5,
                style: { padding: "10px 10px 10px 40px", backgroundColor: "var(--bg-accent)", borderBottom: "1px solid rgba(0,0,0,0.06)" }
              },
                React.createElement("div", {
                  style: { borderLeft: "3px solid rgba(59,130,246,0.2)", paddingLeft: "15px", color: "var(--text-main)" }
                },
                  sectionIssues.map((issue, idx) =>
                    React.createElement(IssueRow, { key: `curr-${idx}`, issue })
                  ),
                  resolvedForSection.length > 0 && React.createElement("div", { style: { marginTop: "8px", paddingTop: "8px", borderTop: "1px dashed rgba(255,255,255,0.04)" } },
                    React.createElement("div", { style: { fontSize: "11px", color: "var(--success)", marginBottom: "6px", fontWeight: "bold" } }, "Incidencias resueltas en esta ejecución"),
                    resolvedForSection.map((issue, idx) => React.createElement(IssueRow, { key: `res-${idx}`, issue }))
                  )
                )
              )
            )
          );
        })
      )
    )
  );
}

/**
 * Tarjeta de un run individual con su historial de secciones.
 */
function RunCard({ run, sections, issues, onToggleSections }) {
  const { t } = useI18n();
  const scoreClass = run.score >= 80 ? "good" : run.score >= 50 ? "warn" : "bad";
  const hasDetail = !!sections;

  return React.createElement(
    "div", { className: "card", style: { marginBottom: "8px" } },
    React.createElement("div", { className: "run-header" },
      React.createElement("span", { className: "run-date" }, `${t("audit.date")}: ${run.started_at ? new Date(run.started_at).toLocaleString() : run.audit_date || "-"}`),
      React.createElement("span", { className: `run-score ${scoreClass}` }, `${t("audit.score")}: ${run.score ?? "-"}/100`),
      React.createElement("span", { className: "run-metrics" },
        `${t("audit.prev")}: ${run.previous_score ?? "-"} | ${t("audit.col_section")}s: ${run.sections_passed ?? 0}/${run.sections_total ?? 10}`
      )
    ),
    React.createElement("div", { style: { display: "flex", gap: "8px", marginTop: "12px" } },
      React.createElement("button", {
        onClick: () => onToggleSections(run.id),
        className: "btn-outline"
      }, hasDetail ? t("audit.hide_details") : t("audit.show_details")),
        React.createElement("a", {
        href: `/api/runs/${run.id}/export`,
        target: "_blank",
        className: "btn-outline",
        style: { textDecoration: "none", color: "var(--primary)", borderColor: "var(--primary)", display: "flex", alignItems: "center" }
      }, t("audit.export_pdf"))
    ),
    hasDetail && React.createElement(RunSectionsTable, { sections, issues })
  );
}

/**
 * Hook y componente principal de detalle de website.
 * Gestiona la carga de runs y el toggle de secciones.
 */
export function useAuditDetail() {
  const [runs, setRuns] = React.useState([]);
  const [runSections, setRunSections] = React.useState({});
  const [runIssues, setRunIssues] = React.useState({});

  const loadRuns = async (websiteId) => {
    const data = await fetchWebsiteRuns(websiteId);
    setRuns(data.runs || []);
    setRunSections({});
    setRunIssues({});
  };

  const toggleSections = async (runId) => {
    if (runSections[runId]) {
      setRunSections(prev => { const n = { ...prev }; delete n[runId]; return n; });
    } else {
      const [sections, issues] = await Promise.all([
        fetchRunSections(runId),
        fetchRunIssues(runId),
      ]);

      // Intentamos obtener el run anterior para comparar diferencias
      const idx = runs.findIndex(r => r.id === runId);
      let prevIssues = [];
      if (idx >= 0 && idx + 1 < runs.length) {
        try {
          prevIssues = await fetchRunIssues(runs[idx + 1].id);
        } catch (e) { prevIssues = []; }
      }

      // Normalizar claves para diffing
      const keyFor = (i) => `${i.category}||${i.message}||${i.line_no || ""}`;
      const prevSet = new Set((prevIssues || []).map(keyFor));
      const currSet = new Set((issues || []).map(keyFor));

      const currentWithStatus = (issues || []).map(i => ({ ...i, diff_status: prevSet.has(keyFor(i)) ? "persistent" : "new" }));
      const resolved = (prevIssues || []).filter(i => !currSet.has(keyFor(i))).map(i => ({ ...i, diff_status: "resolved" }));

      setRunSections(prev => ({ ...prev, [runId]: sections || [] }));
      setRunIssues(prev => ({ ...prev, [runId]: { current: currentWithStatus, resolved } }));
    }
  };

  return { runs, runSections, runIssues, loadRuns, toggleSections };
}

/**
 * Lista de runs de un website.
 */
export function RunList({ runs, runSections, runIssues, onToggleSections }) {
  const { t } = useI18n();
  if (!runs.length) return React.createElement("p", { style: { opacity: 0.6 } }, t("audit.no_history"));
  return React.createElement(
    React.Fragment, null,
    runs.map(r =>
      React.createElement(RunCard, {
        key: r.id,
        run: r,
        sections: runSections[r.id],
        issues: runIssues[r.id],
        onToggleSections,
      })
    )
  );
}
