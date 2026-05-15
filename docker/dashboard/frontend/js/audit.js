/**
 * audit.js — Componente de detalle de runs y secciones de auditoría.
 * Renderiza el historial de runs de un website y el detalle de cada run.
 */
import React from "https://esm.sh/react@18.3.1";
import { fetchWebsiteRuns, fetchRunSections, fetchRunIssues, triggerAudit } from "./api.js";

/**
 * Panel informativo sobre el propósito de cada tipo de prueba.
 */
export function AuditInfoPanel() {
  return React.createElement(
    "div",
    { className: "info-panel" },
    React.createElement("h4", null, "ℹ️ Pruebas Realizadas y su Propósito"),
    React.createElement(
      "ul",
      null,
      React.createElement("li", null, React.createElement("strong", null, "🛡️ Seguridad:"), " Verifica cabeceras HTTP, exposición de servidor y configuraciones contra ataques comunes."),
      React.createElement("li", null, React.createElement("strong", null, "🔍 SEO:"), " Evalúa metaetiquetas (Title, Description) para asegurar correcta indexación en buscadores."),
      React.createElement("li", null, React.createElement("strong", null, "⚡ Rendimiento:"), " Comprueba tiempos de respuesta y estado del servidor para garantizar velocidad."),
      React.createElement("li", null, React.createElement("strong", null, "🏗️ Estructura HTML:"), " Analiza la jerarquía de encabezados (H1, H2) y el uso correcto de semántica web."),
      React.createElement("li", null, React.createElement("strong", null, "♿ Contenido y Accesibilidad:"), " Revisa atributos 'alt' en imágenes, densidad de texto y contrastes."),
      React.createElement("li", null, React.createElement("strong", null, "🔗 Enlaces y Navegación:"), " Detecta enlaces rotos (404) y verifica que los elementos interactivos funcionen.")
    )
  );
}

/**
 * Fila de issue individual dentro de una sección.
 */
function IssueRow({ issue }) {
  const severityColor =
    issue.severity === "critical" ? "#c0392b" :
    issue.severity === "high"     ? "#d35400" : "#2c3e50";

  return React.createElement(
    "div",
    { style: { marginBottom: "6px", lineHeight: "1.4" } },
    React.createElement("span", {
      style: { color: severityColor, fontWeight: "bold", marginRight: "8px", fontSize: "11px" }
    }, `[${issue.severity.toUpperCase()}]`),
    React.createElement("span", { style: { color: "#2c3e50" } }, issue.message),
    issue.line_no && React.createElement(
      "span",
      { style: { color: "#7f8c8d", marginLeft: "10px", fontSize: "11px", fontStyle: "italic" } },
      `(Fila: ${issue.line_no})`
    )
  );
}

/**
 * Tabla de secciones de un run con sus issues.
 */
function RunSectionsTable({ sections, issues }) {
  return React.createElement(
    "div", { className: "table-container" },
    React.createElement(
      "table", { className: "sections-table" },
      React.createElement(
        "thead", null,
        React.createElement("tr", null,
          ["Sección", "Ejecución", "Issues", "Descripción", "Detalle"].map(
            (h) => React.createElement("th", { key: h }, h)
          )
        )
      ),
      React.createElement(
        "tbody", null,
        sections.map((s) => {
          const sectionIssues = (issues || []).filter(i => i.category === s.section_key);
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
                !s.passed && React.createElement("span", { style: { color: "#e74c3c", marginLeft: "6px" }, title: "Incidencias detectadas" }, "⚠️")
              ),
              React.createElement("td", null,
                React.createElement("span", {
                  className: `status-badge ${isBlocked ? "blocked" : s.status === "failed" ? "failed" : s.passed ? "passed" : "warn"}`,
                }, isBlocked ? "BLOQUEADO" : s.status === "failed" ? "FALLIDO" : "OK")
              ),
              React.createElement("td", { style: { color: s.passed ? "#2ecc71" : "#e67e22", fontWeight: "bold" } }, s.issue_count),
              React.createElement("td", { style: { fontSize: "11px", opacity: 0.8 } }, s.check_description),
              React.createElement("td", null, s.result_description)
            ),
            sectionIssues.length > 0 && React.createElement("tr", null,
              React.createElement("td", {
                colSpan: 5,
                style: { padding: "10px 10px 10px 40px", backgroundColor: "#fff", borderBottom: "1px solid #eee" }
              },
                React.createElement("div", {
                  style: { borderLeft: "3px solid #34495e", paddingLeft: "15px", color: "#2c3e50" }
                },
                  sectionIssues.map((issue, idx) =>
                    React.createElement(IssueRow, { key: idx, issue })
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
  const scoreClass = run.score >= 80 ? "good" : run.score >= 50 ? "warn" : "bad";
  const hasDetail = !!sections;

  return React.createElement(
    "div", { className: "card", style: { marginBottom: "8px" } },
    React.createElement("div", { className: "run-header" },
      React.createElement("span", { className: "run-date" }, `Fecha: ${run.started_at ? new Date(run.started_at).toLocaleString() : run.audit_date || "-"}`),
      React.createElement("span", { className: `run-score ${scoreClass}` }, `Puntuación: ${run.score ?? "-"}/100`),
      React.createElement("span", { className: "run-metrics" },
        `Anterior: ${run.previous_score ?? "-"} | Secciones: ${run.sections_passed ?? 0}/${run.sections_total ?? 10}`
      )
    ),
    React.createElement("div", { style: { display: "flex", gap: "8px", marginTop: "12px" } },
      React.createElement("button", {
        onClick: () => onToggleSections(run.id),
        className: "btn-outline"
      }, hasDetail ? "Ocultar detalles" : "Ver detalle de pruebas"),
      React.createElement("a", {
        href: `/api/runs/${run.id}/export`,
        target: "_blank",
        className: "btn-outline",
        style: { textDecoration: "none", color: "#3498db", borderColor: "#3498db", display: "flex", alignItems: "center" }
      }, "Exportar PDF")
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
      setRunSections(prev => ({ ...prev, [runId]: sections || [] }));
      setRunIssues(prev => ({ ...prev, [runId]: issues || [] }));
    }
  };

  return { runs, runSections, runIssues, loadRuns, toggleSections };
}

/**
 * Lista de runs de un website.
 */
export function RunList({ runs, runSections, runIssues, onToggleSections }) {
  if (!runs.length) return React.createElement("p", { style: { opacity: 0.6 } }, "Sin análisis registrados.");
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
