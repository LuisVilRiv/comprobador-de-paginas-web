import React, { useEffect, useMemo, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";

const api = async (path, method = "GET", body = null) => {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`/api${path}`, opts);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
};

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true };
  }
  componentDidCatch(error, info) {
    this.setState({ error, info });
    console.error("ErrorBoundary caught an error", error, info);
  }
  render() {
    if (this.state.hasError) {
      return React.createElement("div", { style: { padding: "20px", color: "red", background: "#fff" } },
        React.createElement("h1", null, "Algo salió mal."),
        React.createElement("pre", null, this.state.error && this.state.error.toString()),
        React.createElement("pre", null, this.state.info && this.state.info.componentStack)
      );
    }
    return this.props.children;
  }
}

function App() {
  const [summary, setSummary] = useState({});
  const [websites, setWebsites] = useState([]);
  const [clients, setClients] = useState([]);
  const [clientId, setClientId] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedWebsite, setSelectedWebsite] = useState(null);
  const [runs, setRuns] = useState([]);
  const [runSections, setRunSections] = useState({});
  const [runIssues, setRunIssues] = useState({});

  // Estado para doble verificación de borrado
  const [deleteConfirm, setDeleteConfirm] = useState({ show: false, type: "", id: "", name: "", input: "" });

  // Cronómetros
  const [timers, setTimers] = useState({ active: "", inactive: "" });

  // Estado de "auditando" por website_id para feedback inmediato del botón
  const [auditingIds, setAuditingIds] = useState(new Set());

  // ── Modal de formularios ──────────────────────────────────────────────────
  const [showAddClient, setShowAddClient] = useState(false);
  const [showAddWebsite, setShowAddWebsite] = useState(false);
  const [newClientForm, setNewClientForm] = useState({
    name: "", email: "", phone: "", company: "", notes: "",
  });
  const [newWebsiteForm, setNewWebsiteForm] = useState({
    client_id: "", url: "", label: "", strategy: "auto", active: true,
  });
  const [formError, setFormError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const loadAll = async () => {
    setLoading(true);
    try {
      const [s, c, w] = await Promise.all([
        api("/summary"),
        api("/clients"),
        api(clientId ? `/websites?client_id=${clientId}` : "/websites"),
      ]);
      setSummary(s || {});
      setClients(c || []);
      setWebsites(w || []);
      setFormError("");
    } catch (err) {
      setFormError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, [clientId]);

  useEffect(() => {
    const updateTimers = () => {
      const now = new Date();
      
      // Activos (Miércoles y Domingo a las 00:00)
      let nextActive = new Date(now);
      nextActive.setHours(0, 0, 0, 0);
      let daysToAddActive = 0;
      if (now.getDay() === 0) daysToAddActive = (now.getHours() > 0 || now.getMinutes() > 0 || now.getSeconds() > 0) ? 3 : 0;
      else if (now.getDay() < 3) daysToAddActive = 3 - now.getDay();
      else if (now.getDay() === 3) daysToAddActive = (now.getHours() > 0 || now.getMinutes() > 0 || now.getSeconds() > 0) ? 4 : 0;
      else daysToAddActive = 7 - now.getDay();
      if (daysToAddActive > 0) nextActive.setDate(now.getDate() + daysToAddActive);
      
      // Inactivos (Día 1 meses pares: Feb, Abr, Jun, Ago, Oct, Dic)
      let nextInactive = new Date(now);
      nextInactive.setHours(0, 0, 0, 0);
      nextInactive.setDate(1);
      let currentMonth = now.getMonth();
      let targetMonth = currentMonth + (currentMonth % 2 === 0 ? 1 : 2);
      if (now.getMonth() % 2 !== 0 && now.getDate() === 1 && now.getHours() === 0 && now.getMinutes() === 0 && now.getSeconds() === 0) {
        targetMonth = currentMonth; 
      }
      nextInactive.setMonth(targetMonth);

      const formatDiff = (target) => {
        const diff = target - new Date();
        if (diff <= 0) return "¡En ejecución!";
        const d = Math.floor(diff / (1000 * 60 * 60 * 24));
        const h = Math.floor((diff / (1000 * 60 * 60)) % 24);
        const m = Math.floor((diff / 1000 / 60) % 60);
        const s = Math.floor((diff / 1000) % 60);
        return `${d}d ${h}h ${m}m ${s}s`;
      };

      setTimers({ active: formatDiff(nextActive), inactive: formatDiff(nextInactive) });
    };

    updateTimers();
    const interval = setInterval(updateTimers, 1000);
    return () => clearInterval(interval);
  }, []);

  const filtered = useMemo(
    () => websites.filter((w) => {
      const text = `${w.url} ${w.label || ""} ${w.client_name || ""}`.toLowerCase();
      return text.includes(query.toLowerCase());
    }),
    [websites, query]
  );

  const openWebsite = async (website) => {
    setSelectedWebsite(website);
    const data = await api(`/websites/${website.website_id}/runs?limit=20`);
    setRuns(data.runs || []);
    setRunSections({});
  };

  const loadSections = async (runId) => {
    if (runSections[runId]) return;
    const [sections, issues] = await Promise.all([
      api(`/runs/${runId}/sections`),
      api(`/runs/${runId}/issues`)
    ]);
    setRunSections((prev) => ({ ...prev, [runId]: sections || [] }));
    setRunIssues((prev) => ({ ...prev, [runId]: issues || [] }));
  };

  // ── CRUD ──────────────────────────────────────────────────────────────────

  const handleCreateClient = async (e) => {
    e.preventDefault();
    setFormError("");
    try {
      if (!newClientForm.name.trim()) { setFormError("El nombre del cliente es obligatorio"); return; }
      await api("/clients", "POST", newClientForm);
      setSuccessMessage("✓ Cliente creado exitosamente");
      setNewClientForm({ name: "", email: "", phone: "", company: "", notes: "" });
      setShowAddClient(false);
      await loadAll();
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (err) { setFormError(err.message); }
  };

  const handleCreateWebsite = async (e) => {
    e.preventDefault();
    setFormError("");
    try {
      if (!newWebsiteForm.client_id) { setFormError("Debes seleccionar un cliente"); return; }
      if (!newWebsiteForm.url.trim()) { setFormError("La URL es obligatoria"); return; }
      await api("/websites", "POST", newWebsiteForm);
      setSuccessMessage("✓ URL agregada exitosamente");
      setNewWebsiteForm({ client_id: "", url: "", label: "", strategy: "auto", active: true });
      setShowAddWebsite(false);
      await loadAll();
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (err) { setFormError(err.message); }
  };

  const handleToggleActive = async (website) => {
    try {
      setLoading(true);
      await api(`/websites/${website.website_id}`, "PUT", { active: !website.active });
      setSuccessMessage(`✓ URL marcada como ${!website.active ? "activa" : "inactiva"}`);
      await loadAll();
      setSelectedWebsite(null);
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (err) { setFormError(err.message); }
    finally { setLoading(false); }
  };

  const triggerDeleteWebsite = (website) => {
    setDeleteConfirm({ show: true, type: "website", id: website.website_id, name: website.label || website.url, input: "" });
  };

  const triggerDeleteClient = (client_id, client_name) => {
    setDeleteConfirm({ show: true, type: "client", id: client_id, name: client_name || "Este cliente", input: "" });
  };

  const executeDelete = async () => {
    if (deleteConfirm.input !== "ELIMINAR") return;
    try {
      setLoading(true);
      if (deleteConfirm.type === "client") {
        await api(`/clients/${deleteConfirm.id}`, "DELETE");
        setClientId("");
        setSuccessMessage("✓ Cliente eliminado exitosamente");
      } else {
        await api(`/websites/${deleteConfirm.id}`, "DELETE");
        setSelectedWebsite(null);
        setSuccessMessage("✓ URL eliminada exitosamente");
      }
      setDeleteConfirm({ show: false, type: "", id: "", name: "", input: "" });
      await loadAll();
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (err) {
      setFormError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Auditoría manual ──────────────────────────────────────────────────────

  const handleAuditWebsite = async (website) => {
    const id = website.website_id;
    setAuditingIds((prev) => new Set(prev).add(id));
    setFormError("");
    try {
      const res = await api(`/websites/${id}/audit`, "POST");
      const label = website.label || website.url;
      setSuccessMessage(
        `⏳ Auditoría iniciada para "${label}". El scraper la procesará de inmediato.`
      );
      // Refrescar tabla para que el badge "Pendiente" aparezca
      await loadAll();
      // Si el modal estaba abierto, actualizar selectedWebsite con los datos frescos
      if (selectedWebsite?.website_id === id) {
        setSelectedWebsite((prev) => ({ ...prev, pending_audit: true }));
      }
      setTimeout(() => setSuccessMessage(""), 6000);
    } catch (err) {
      setFormError(err.message);
    } finally {
      setAuditingIds((prev) => { const s = new Set(prev); s.delete(id); return s; });
    }
  };

  return React.createElement(
    "div",
    { className: "app" },

    // ── Encabezado ────────────────────────────────────────────────────────
    React.createElement("h2", null, "Web Auditor Dashboard"),

    // ── Mensajes ─────────────────────────────────────────────────────────
    successMessage && React.createElement("div", { className: "message success" }, successMessage),
    formError      && React.createElement("div", { className: "message error" }, formError),

    // ── Tarjetas de resumen ───────────────────────────────────────────────
    React.createElement(
      "div",
      { className: "grid" },
      React.createElement("div", { className: "card" }, `Webs activas: ${summary.active_websites ?? "-"}`),
      React.createElement("div", { className: "card" }, `Excelentes: ${summary.excellent_count ?? "-"}`),
      React.createElement("div", { className: "card" }, `Críticas: ${summary.critical_count ?? "-"}`),
      React.createElement("div", { className: "card" }, `Bloqueadas: ${summary.blocked_count ?? "-"}`),
      React.createElement(
        "div",
        { className: "card", style: { backgroundColor: "#1e2b3c", borderColor: "#3498db" } },
        React.createElement("div", { style: { fontSize: "11px", color: "#85c1e9", marginBottom: "4px" } }, "⏱️ Próximo ciclo Activos"),
        React.createElement("div", { style: { fontSize: "15px", fontWeight: "bold" } }, timers.active)
      ),
      React.createElement(
        "div",
        { className: "card", style: { backgroundColor: "#2c223a", borderColor: "#9b59b6" } },
        React.createElement("div", { style: { fontSize: "11px", color: "#d2b4de", marginBottom: "4px" } }, "⏱️ Próximo ciclo Inactivos"),
        React.createElement("div", { style: { fontSize: "15px", fontWeight: "bold" } }, timers.inactive)
      ),
      summary.pending_audit_count > 0 &&
        React.createElement(
          "div",
          { className: "card", style: { borderColor: "#f39c12", color: "#f39c12" } },
          `⏳ Auditorías pendientes: ${summary.pending_audit_count}`
        )
    ),

    // ── Barra de herramientas ─────────────────────────────────────────────
    React.createElement(
      "div",
      { className: "topbar" },
      React.createElement(
        "div",
        { className: "topbar-left" },
        React.createElement("button", { onClick: loadAll, disabled: loading },
          loading ? "Actualizando..." : "Actualizar"
        ),
        React.createElement("button", {
          onClick: () => { setShowAddClient(true); setFormError(""); },
          style: { backgroundColor: "#2ecc71" },
        }, "+ Cliente"),
        React.createElement("button", {
          onClick: () => { setShowAddWebsite(true); setFormError(""); },
          style: { backgroundColor: "#3498db" },
        }, "+ URL")
      ),
      React.createElement(
        "div",
        { className: "topbar-center" },
        React.createElement(
          "select",
          { value: clientId, onChange: (e) => setClientId(e.target.value) },
          React.createElement("option", { value: "" }, "Todos los clientes"),
          clients.map((c) =>
            React.createElement("option", { key: c.id, value: c.id }, c.name)
          )
        ),
        clientId && React.createElement(
          "button",
          {
            onClick: () => triggerDeleteClient(clientId, clients.find(c => c.id === clientId)?.name),
            style: { backgroundColor: "#c0392b" },
            title: "Eliminar Cliente Seleccionado"
          },
          "🗑️ Eliminar Cliente"
        )
      ),
      React.createElement(
        "div",
        { className: "topbar-right" },
        React.createElement("input", {
          value: query,
          onChange: (e) => setQuery(e.target.value),
          placeholder: "Buscar...",
        })
      )
    ),

    // ── Tabla de websites ─────────────────────────────────────────────────
    React.createElement(
      "table",
      null,
      React.createElement(
        "thead",
        null,
        React.createElement(
          "tr",
          null,
          ["URL", "Cliente", "Score", "Prev.", "Secciones", "Fecha", "Estado", "Activa", "Acciones"].map(
            (h) => React.createElement("th", { key: h }, h)
          )
        )
      ),
      React.createElement(
        "tbody",
        null,
        filtered.map((w) => {
          const isAuditing = auditingIds.has(w.website_id);
          return React.createElement(
            "tr",
            { key: w.website_id },
            React.createElement("td", {
              onClick: () => openWebsite(w),
              style: { cursor: "pointer", textDecoration: "underline" },
            },
              w.label ? w.label : w.url,
              // Badge "Pendiente" cuando hay auditoría programada
              w.pending_audit && React.createElement(
                "span",
                {
                  style: {
                    marginLeft: "6px",
                    fontSize: "10px",
                    backgroundColor: "#f39c12",
                    color: "#fff",
                    borderRadius: "3px",
                    padding: "1px 5px",
                    verticalAlign: "middle",
                  },
                },
                "⏳ pendiente"
              )
            ),
            React.createElement("td", null, w.client_name || "-"),
            React.createElement("td", null, w.score ?? "-"),
            React.createElement("td", null, w.previous_score ?? "-"),
            React.createElement("td", null, `${w.sections_passed ?? 0}/${w.sections_total ?? 10}`),
            React.createElement("td", null, w.audit_date || "-"),
            React.createElement("td", null, w.audit_status || w.run_status || "-"),
            React.createElement(
              "td",
              { style: { fontWeight: "bold", color: w.active ? "#27ae60" : "#e74c3c" } },
              w.active ? "✓ SÍ" : "✗ NO"
            ),
            React.createElement(
              "td",
              { style: { fontSize: "12px", whiteSpace: "nowrap" } },
              // ── Botón Auditar ─────────────────────────────────────────
              React.createElement("button", {
                onClick: () => handleAuditWebsite(w),
                disabled: isAuditing || w.pending_audit,
                title: w.pending_audit
                  ? "Ya hay una auditoría pendiente para esta URL"
                  : "Ejecutar auditoría inmediata",
                style: {
                  backgroundColor: w.pending_audit ? "#7f6c1f" : "#f39c12",
                  padding: "4px 8px",
                  marginRight: "4px",
                  opacity: (isAuditing || w.pending_audit) ? 0.6 : 1,
                },
              }, isAuditing ? "..." : w.pending_audit ? "⏳" : "Auditar"),
              // ── Botón Desactivar / Activar ────────────────────────────
              React.createElement("button", {
                onClick: () => handleToggleActive(w),
                style: {
                  backgroundColor: w.active ? "#e74c3c" : "#27ae60",
                  padding: "4px 8px",
                  marginRight: "4px",
                },
              }, w.active ? "Desactivar" : "Activar"),
              // ── Botón Eliminar ────────────────────────────────────────
              React.createElement("button", {
                onClick: () => triggerDeleteWebsite(w),
                style: { backgroundColor: "#c0392b", padding: "4px 8px" },
              }, "Eliminar")
            )
          );
        })
      )
    ),

    // ── Modal: Detalle de website ─────────────────────────────────────────
    selectedWebsite &&
      React.createElement(
        "div",
        { className: "modal", onClick: () => setSelectedWebsite(null) },
        React.createElement(
          "div",
          { className: "modal-content", onClick: (e) => e.stopPropagation() },
          React.createElement("h3", null,
            selectedWebsite.url,
            selectedWebsite.pending_audit && React.createElement(
              "span",
              {
                style: {
                  marginLeft: "8px",
                  fontSize: "12px",
                  backgroundColor: "#f39c12",
                  color: "#fff",
                  borderRadius: "4px",
                  padding: "2px 7px",
                },
              },
              "⏳ auditoría pendiente"
            )
          ),
          React.createElement("p", null, `Cliente: ${selectedWebsite.client_name}`),
          React.createElement(
            "div",
            { style: { marginBottom: "12px", display: "flex", gap: "8px", flexWrap: "wrap" } },
            // ── Botón Auditar en modal ────────────────────────────────
            React.createElement("button", {
              onClick: () => handleAuditWebsite(selectedWebsite),
              disabled: auditingIds.has(selectedWebsite.website_id) || selectedWebsite.pending_audit,
              title: selectedWebsite.pending_audit
                ? "Ya hay una auditoría pendiente"
                : "Ejecutar auditoría inmediata",
              style: {
                backgroundColor: selectedWebsite.pending_audit ? "#7f6c1f" : "#f39c12",
                opacity: (auditingIds.has(selectedWebsite.website_id) || selectedWebsite.pending_audit) ? 0.6 : 1,
              },
            },
              auditingIds.has(selectedWebsite.website_id)
                ? "Programando..."
                : selectedWebsite.pending_audit
                  ? "⏳ Auditoría pendiente"
                  : "🔍 Auditar ahora"
            ),
            React.createElement("button", {
              onClick: () => handleToggleActive(selectedWebsite),
              style: { backgroundColor: selectedWebsite.active ? "#e74c3c" : "#27ae60" },
            }, selectedWebsite.active ? "Desactivar" : "Activar"),
            React.createElement("button", {
              onClick: () => triggerDeleteWebsite(selectedWebsite),
              style: { backgroundColor: "#c0392b" },
            }, "Eliminar"),
            React.createElement("button", {
              onClick: () => setSelectedWebsite(null),
              style: { backgroundColor: "#95a5a6" },
            }, "Cerrar")
          ),

          // ── Panel de información de pruebas ──────────────────────────────────
          React.createElement(
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
          ),

          React.createElement("h4", { style: { marginTop: "24px", borderBottom: "1px solid #2c2f39", paddingBottom: "8px" } }, "Histórico de análisis"),
          runs.map((r) =>
            React.createElement(
              "div",
              { key: r.id, className: "card", style: { marginBottom: "8px" } },
              React.createElement("div", { className: "run-header" },
                React.createElement("span", { className: "run-date" }, `📅 ${r.audit_date || "-"}`),
                React.createElement("span", { className: `run-score ${r.score >= 80 ? "good" : r.score >= 50 ? "warn" : "bad"}` }, `Puntuación: ${r.score ?? "-"}/100`),
                React.createElement("span", { className: "run-metrics" }, `Anterior: ${r.previous_score ?? "-"} | Secciones: ${r.sections_passed ?? 0}/${r.sections_total ?? 10}`)
              ),
              React.createElement(
                "button",
                { 
                  onClick: () => {
                    if (runSections[r.id]) {
                      const newSections = { ...runSections };
                      delete newSections[r.id];
                      setRunSections(newSections);
                    } else {
                      loadSections(r.id);
                    }
                  },
                  className: "btn-outline", style: { marginTop: "12px" } 
                },
                runSections[r.id] ? "Ocultar detalles" : "Ver detalle de pruebas"
              ),
              runSections[r.id] &&
                React.createElement(
                  "div", { className: "table-container" },
                  React.createElement(
                    "table",
                    { className: "sections-table" },
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
                    runSections[r.id].map((s) => {
                      const sectionIssues = (runIssues[r.id] || []).filter(i => i.category === s.section_key);
                      // Determinar si fue bloqueado por firewall o error de red
                      const isBlocked = s.status === "failed" && 
                        (s.result_description.toLowerCase().includes("bloqueado") || 
                         s.result_description.toLowerCase().includes("firewall") ||
                         s.result_description.toLowerCase().includes("403") ||
                         sectionIssues.some(i => i.message.toLowerCase().includes("bloqueada") || i.message.toLowerCase().includes("firewall")));

                      return React.createElement(React.Fragment, { key: s.section_key },
                        React.createElement("tr", { className: "section-row" },
                          React.createElement("td", { style: { fontWeight: "bold" } }, s.section_label),
                          React.createElement("td", null, 
                            React.createElement("span", {
                              className: `status-badge ${isBlocked ? "blocked" : s.status === "failed" ? "failed" : "passed"}`,
                            }, isBlocked ? "BLOQUEADO" : s.status === "failed" ? "FALLIDO" : "OK")
                          ),
                          React.createElement("td", null, s.issue_count),
                          React.createElement("td", null, s.check_description),
                          React.createElement("td", null, s.result_description)
                        ),
                        sectionIssues.length > 0 && React.createElement("tr", null,
                          React.createElement("td", { colSpan: 5, style: { padding: "10px 10px 10px 40px", backgroundColor: "#fff", borderBottom: "1px solid #eee" } },
                            React.createElement("div", { style: { borderLeft: "3px solid #34495e", paddingLeft: "15px", color: "#2c3e50" } },
                              sectionIssues.map((issue, idx) => 
                                React.createElement("div", { key: idx, style: { marginBottom: "6px", lineHeight: "1.4" } },
                                  React.createElement("span", { 
                                    style: { 
                                      color: issue.severity === "critical" ? "#c0392b" : (issue.severity === "high" ? "#d35400" : "#2c3e50"),
                                      fontWeight: "bold",
                                      marginRight: "8px",
                                      fontSize: "11px"
                                    } 
                                  }, `[${issue.severity.toUpperCase()}]`),
                                  React.createElement("span", { style: { color: "#2c3e50" } }, issue.message),
                                  issue.line_no && React.createElement("span", { style: { color: "#7f8c8d", marginLeft: "10px", fontSize: "11px", fontStyle: "italic" } }, `(Fila: ${issue.line_no})`)
                                )
                              )
                            )
                          )
                        )
                      );
                    })
                  )
                )
              )
            )
          )
        )
      ),

    // ── Modal: Agregar cliente ────────────────────────────────────────────
    showAddClient &&
      React.createElement(
        "div",
        { className: "modal", onClick: () => setShowAddClient(false) },
        React.createElement(
          "div",
          { className: "modal-content", onClick: (e) => e.stopPropagation() },
          React.createElement("h3", null, "Agregar nuevo cliente"),
          React.createElement(
            "form",
            { onSubmit: handleCreateClient },
            React.createElement("div", { className: "form-group" },
              React.createElement("label", null, "Nombre *"),
              React.createElement("input", {
                type: "text", value: newClientForm.name, required: true,
                placeholder: "Nombre del cliente",
                onChange: (e) => setNewClientForm({ ...newClientForm, name: e.target.value }),
              })
            ),
            React.createElement("div", { className: "form-group" },
              React.createElement("label", null, "Email"),
              React.createElement("input", {
                type: "email", value: newClientForm.email, placeholder: "email@ejemplo.com",
                onChange: (e) => setNewClientForm({ ...newClientForm, email: e.target.value }),
              })
            ),
            React.createElement("div", { className: "form-group" },
              React.createElement("label", null, "Teléfono"),
              React.createElement("input", {
                type: "tel", value: newClientForm.phone, placeholder: "+34 666 123 456",
                onChange: (e) => setNewClientForm({ ...newClientForm, phone: e.target.value }),
              })
            ),
            React.createElement("div", { className: "form-group" },
              React.createElement("label", null, "Empresa"),
              React.createElement("input", {
                type: "text", value: newClientForm.company, placeholder: "Nombre de la empresa",
                onChange: (e) => setNewClientForm({ ...newClientForm, company: e.target.value }),
              })
            ),
            React.createElement("div", { className: "form-group" },
              React.createElement("label", null, "Notas"),
              React.createElement("textarea", {
                value: newClientForm.notes, rows: 3, placeholder: "Notas adicionales",
                onChange: (e) => setNewClientForm({ ...newClientForm, notes: e.target.value }),
              })
            ),
            React.createElement("div", { className: "form-actions" },
              React.createElement("button", { type: "submit", style: { backgroundColor: "#2ecc71" } }, "Crear cliente"),
              React.createElement("button", {
                type: "button", style: { backgroundColor: "#95a5a6" },
                onClick: () => setShowAddClient(false),
              }, "Cancelar")
            )
          )
        )
      ),

    // ── Modal: Agregar website ────────────────────────────────────────────
    showAddWebsite &&
      React.createElement(
        "div",
        { className: "modal", onClick: () => setShowAddWebsite(false) },
        React.createElement(
          "div",
          { className: "modal-content", onClick: (e) => e.stopPropagation() },
          React.createElement("h3", null, "Agregar nueva URL"),
          React.createElement(
            "form",
            { onSubmit: handleCreateWebsite },
            React.createElement("div", { className: "form-group" },
              React.createElement("label", null, "Cliente *"),
              React.createElement(
                "select",
                {
                  value: newWebsiteForm.client_id, required: true,
                  onChange: (e) => setNewWebsiteForm({ ...newWebsiteForm, client_id: e.target.value }),
                },
                React.createElement("option", { value: "" }, "Selecciona un cliente"),
                clients.map((c) =>
                  React.createElement("option", { key: c.id, value: c.id }, c.name)
                )
              )
            ),
            React.createElement("div", { className: "form-group" },
              React.createElement("label", null, "URL *"),
              React.createElement("input", {
                type: "url", value: newWebsiteForm.url, required: true,
                placeholder: "https://ejemplo.com",
                onChange: (e) => setNewWebsiteForm({ ...newWebsiteForm, url: e.target.value }),
              })
            ),
            React.createElement("div", { className: "form-group" },
              React.createElement("label", null, "Etiqueta (nombre descriptivo)"),
              React.createElement("input", {
                type: "text", value: newWebsiteForm.label, placeholder: "Mi Sitio Web",
                onChange: (e) => setNewWebsiteForm({ ...newWebsiteForm, label: e.target.value }),
              })
            ),
            React.createElement("div", { className: "form-group" },
              React.createElement("label", null, "Estrategia de scraping"),
              React.createElement(
                "select",
                {
                  value: newWebsiteForm.strategy,
                  onChange: (e) => setNewWebsiteForm({ ...newWebsiteForm, strategy: e.target.value }),
                },
                React.createElement("option", { value: "auto" }, "Auto (detecta automáticamente)"),
                React.createElement("option", { value: "beautifulsoup" }, "BeautifulSoup (estático)"),
                React.createElement("option", { value: "selenium" }, "Selenium (JavaScript)")
              )
            ),
            React.createElement("div", { className: "form-group" },
              React.createElement("label", null),
              React.createElement("input", {
                type: "checkbox", checked: newWebsiteForm.active,
                onChange: (e) => setNewWebsiteForm({ ...newWebsiteForm, active: e.target.checked }),
              }),
              React.createElement("span", { style: { marginLeft: "8px" } }, "Activa (auditará 2 veces/semana)")
            ),
            React.createElement("div", { className: "form-actions" },
              React.createElement("button", { type: "submit", style: { backgroundColor: "#3498db" } }, "Agregar URL"),
              React.createElement("button", {
                type: "button", style: { backgroundColor: "#95a5a6" },
                onClick: () => setShowAddWebsite(false),
              }, "Cancelar")
            )
          )
        )
      ),

    // ── Modal: Confirmación de Borrado ────────────────────────────────────
    deleteConfirm.show &&
      React.createElement(
        "div",
        { className: "modal", onClick: () => setDeleteConfirm({ ...deleteConfirm, show: false }) },
        React.createElement(
          "div",
          { className: "modal-content", style: { maxWidth: "400px", borderColor: "#e74c3c" }, onClick: (e) => e.stopPropagation() },
          React.createElement("h3", { style: { color: "#e74c3c", marginTop: 0 } }, "⚠️ Doble Verificación Requerida"),
          React.createElement("p", { style: { lineHeight: "1.5", fontSize: "14px" } },
            `Estás a punto de eliminar de forma irreversible ${deleteConfirm.type === "client" ? "el cliente" : "la URL"}: `
          ),
          React.createElement("p", { style: { fontWeight: "bold", fontSize: "16px", background: "#171922", padding: "8px", borderRadius: "4px", textAlign: "center" } }, deleteConfirm.name),
          deleteConfirm.type === "client" && React.createElement("p", { style: { color: "#e74c3c", fontSize: "13px" } }, "También se eliminarán TODAS las URLs y los reportes asociados a este cliente."),
          React.createElement("p", { style: { fontSize: "13px", marginTop: "16px" } }, "Para confirmar, escribe ", React.createElement("strong", null, "ELIMINAR"), " en el cuadro de abajo:"),
          React.createElement("input", {
            type: "text",
            value: deleteConfirm.input,
            onChange: (e) => setDeleteConfirm({ ...deleteConfirm, input: e.target.value }),
            placeholder: "ELIMINAR",
            style: { width: "100%", padding: "10px", marginTop: "8px", boxSizing: "border-box", fontSize: "16px", textAlign: "center", textTransform: "uppercase" }
          }),
          React.createElement("div", { className: "form-actions", style: { marginTop: "24px" } },
            React.createElement("button", {
              onClick: executeDelete,
              disabled: deleteConfirm.input !== "ELIMINAR" || loading,
              style: { backgroundColor: deleteConfirm.input === "ELIMINAR" ? "#c0392b" : "#7f8c8d", transition: "all 0.3s", opacity: deleteConfirm.input === "ELIMINAR" ? 1 : 0.6 }
            }, loading ? "Eliminando..." : "Eliminar Definitivamente"),
            React.createElement("button", {
              onClick: () => setDeleteConfirm({ ...deleteConfirm, show: false }),
              style: { backgroundColor: "#95a5a6" }
            }, "Cancelar")
          )
        )
      )
  );
}

createRoot(document.getElementById("root")).render(React.createElement(ErrorBoundary, null, React.createElement(App)));