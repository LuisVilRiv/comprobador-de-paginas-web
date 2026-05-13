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

  // ── Modal de formularios ──────────────────────────────────────────────────
  const [showAddClient, setShowAddClient] = useState(false);
  const [showAddWebsite, setShowAddWebsite] = useState(false);
  const [newClientForm, setNewClientForm] = useState({
    name: "",
    email: "",
    phone: "",
    company: "",
    notes: "",
  });
  const [newWebsiteForm, setNewWebsiteForm] = useState({
    client_id: "",
    url: "",
    label: "",
    strategy: "auto",
    active: true,
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

  useEffect(() => {
    loadAll();
  }, [clientId]);

  const filtered = useMemo(
    () =>
      websites.filter((w) => {
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
    const data = await api(`/runs/${runId}/sections`);
    setRunSections((prev) => ({ ...prev, [runId]: data || [] }));
  };

  // ── CRUD Functions ───────────────────────────────────────────────────────

  const handleCreateClient = async (e) => {
    e.preventDefault();
    setFormError("");
    try {
      if (!newClientForm.name.trim()) {
        setFormError("El nombre del cliente es obligatorio");
        return;
      }
      await api("/clients", "POST", newClientForm);
      setSuccessMessage("✓ Cliente creado exitosamente");
      setNewClientForm({
        name: "",
        email: "",
        phone: "",
        company: "",
        notes: "",
      });
      setShowAddClient(false);
      await loadAll();
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (err) {
      setFormError(err.message);
    }
  };

  const handleCreateWebsite = async (e) => {
    e.preventDefault();
    setFormError("");
    try {
      if (!newWebsiteForm.client_id) {
        setFormError("Debes seleccionar un cliente");
        return;
      }
      if (!newWebsiteForm.url.trim()) {
        setFormError("La URL es obligatoria");
        return;
      }
      await api("/websites", "POST", newWebsiteForm);
      setSuccessMessage("✓ URL agregada exitosamente");
      setNewWebsiteForm({
        client_id: "",
        url: "",
        label: "",
        strategy: "auto",
        active: true,
      });
      setShowAddWebsite(false);
      await loadAll();
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (err) {
      setFormError(err.message);
    }
  };

  const handleToggleActive = async (website) => {
    try {
      setLoading(true);
      await api(`/websites/${website.website_id}`, "PUT", {
        active: !website.active,
      });
      setSuccessMessage(
        `✓ URL marcada como ${!website.active ? "activa" : "inactiva"}`
      );
      await loadAll();
      setSelectedWebsite(null);
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (err) {
      setFormError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteWebsite = async (website_id) => {
    if (!confirm("¿Estás seguro de que quieres eliminar esta URL?")) return;
    try {
      setLoading(true);
      await api(`/websites/${website_id}`, "DELETE");
      setSuccessMessage("✓ URL eliminada exitosamente");
      await loadAll();
      setSelectedWebsite(null);
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (err) {
      setFormError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClient = async (client_id) => {
    if (!confirm("¿Estás seguro? Esto eliminará el cliente y todas sus URLs."))
      return;
    try {
      setLoading(true);
      await api(`/clients/${client_id}`, "DELETE");
      setSuccessMessage("✓ Cliente eliminado exitosamente");
      setClientId("");
      await loadAll();
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (err) {
      setFormError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return React.createElement(
    "div",
    { className: "app" },

    // ── Encabezado ────────────────────────────────────────────────────────
    React.createElement("h2", null, "Web Auditor Dashboard"),

    // ── Mensajes de éxito/error ──────────────────────────────────────────
    successMessage &&
      React.createElement(
        "div",
        { className: "message success" },
        successMessage
      ),
    formError &&
      React.createElement("div", { className: "message error" }, formError),

    // ── Tarjetas de resumen ──────────────────────────────────────────────
    React.createElement(
      "div",
      { className: "grid" },
      React.createElement("div", { className: "card" }, `Webs activas: ${summary.active_websites ?? "-"}`),
      React.createElement("div", { className: "card" }, `Excelentes: ${summary.excellent_count ?? "-"}`),
      React.createElement("div", { className: "card" }, `Críticas: ${summary.critical_count ?? "-"}`),
      React.createElement("div", { className: "card" }, `Bloqueadas: ${summary.blocked_count ?? "-"}`)
    ),

    // ── Barra de herramientas ────────────────────────────────────────────
    React.createElement(
      "div",
      { className: "topbar" },
      React.createElement(
        "div",
        { className: "topbar-left" },
        React.createElement("button", {
          onClick: loadAll,
          disabled: loading,
        }, loading ? "Actualizando..." : "Actualizar"),
        React.createElement("button", {
          onClick: () => {
            setShowAddClient(true);
            setFormError("");
          },
          style: { backgroundColor: "#2ecc71" },
        }, "+ Cliente"),
        React.createElement("button", {
          onClick: () => {
            setShowAddWebsite(true);
            setFormError("");
          },
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

    // ── Tabla de websites ────────────────────────────────────────────────
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
        filtered.map((w) =>
          React.createElement(
            "tr",
            { key: w.website_id },
            React.createElement("td", {
              onClick: () => openWebsite(w),
              style: { cursor: "pointer", textDecoration: "underline" },
            }, w.label ? `${w.label}` : w.url),
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
              { style: { fontSize: "12px" } },
              React.createElement("button", {
                onClick: () => handleToggleActive(w),
                style: {
                  backgroundColor: w.active ? "#e74c3c" : "#27ae60",
                  padding: "4px 8px",
                  marginRight: "4px",
                },
              }, w.active ? "Desactivar" : "Activar"),
              React.createElement("button", {
                onClick: () => handleDeleteWebsite(w.website_id),
                style: { backgroundColor: "#c0392b", padding: "4px 8px" },
              }, "Eliminar")
            )
          )
        )
      )
    ),

    // ── Modal: Detalle de website ────────────────────────────────────────
    selectedWebsite &&
      React.createElement(
        "div",
        { className: "modal", onClick: () => setSelectedWebsite(null) },
        React.createElement(
          "div",
          { className: "modal-content", onClick: (e) => e.stopPropagation() },
          React.createElement("h3", null, selectedWebsite.url),
          React.createElement("p", null, `Cliente: ${selectedWebsite.client_name}`),
          React.createElement(
            "div",
            { style: { marginBottom: "12px" } },
            React.createElement("button", {
              onClick: () => handleToggleActive(selectedWebsite),
              style: {
                backgroundColor: selectedWebsite.active ? "#e74c3c" : "#27ae60",
              },
            }, selectedWebsite.active ? "Desactivar" : "Activar"),
            React.createElement("button", {
              onClick: () => handleDeleteWebsite(selectedWebsite.website_id),
              style: { backgroundColor: "#c0392b", marginLeft: "8px" },
            }, "Eliminar"),
            React.createElement("button", {
              onClick: () => setSelectedWebsite(null),
              style: { backgroundColor: "#95a5a6", marginLeft: "8px" },
            }, "Cerrar")
          ),
          React.createElement("h4", null, "Histórico de análisis"),
          runs.map((r) =>
            React.createElement(
              "div",
              { key: r.id, className: "card", style: { marginBottom: "8px" } },
              React.createElement(
                "div",
                null,
                `Fecha: ${r.audit_date || "-"} | Score: ${r.score ?? "-"} | Score anterior: ${r.previous_score ?? "-"} | Secciones: ${r.sections_passed ?? 0}/${r.sections_total ?? 10}`
              ),
              React.createElement(
                "button",
                { onClick: () => loadSections(r.id), style: { marginTop: "6px" } },
                "Ver tabla de secciones"
              ),
              runSections[r.id] &&
                React.createElement(
                  "table",
                  { style: { marginTop: "8px" } },
                  React.createElement(
                    "thead",
                    null,
                    React.createElement(
                      "tr",
                      null,
                      ["Sección", "Resultado", "Issues", "Descripción", "Detalle"].map(
                        (h) => React.createElement("th", { key: h }, h)
                      )
                    )
                  ),
                  React.createElement(
                    "tbody",
                    null,
                    runSections[r.id].map((s) =>
                      React.createElement(
                        "tr",
                        { key: s.section_key },
                        React.createElement("td", null, s.section_label),
                        React.createElement(
                          "td",
                          {
                            className:
                              s.status === "ok" ? "ok" : s.status === "failed" ? "fail" : "warn",
                          },
                          s.passed ? "OK" : "FALLO"
                        ),
                        React.createElement("td", null, s.issue_count),
                        React.createElement("td", null, s.check_description),
                        React.createElement("td", null, s.result_description)
                      )
                    )
                  )
                )
            )
          )
        )
      ),

    // ── Modal: Agregar cliente ───────────────────────────────────────────
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
            React.createElement(
              "div",
              { className: "form-group" },
              React.createElement("label", null, "Nombre *"),
              React.createElement("input", {
                type: "text",
                value: newClientForm.name,
                onChange: (e) =>
                  setNewClientForm({ ...newClientForm, name: e.target.value }),
                placeholder: "Nombre del cliente",
                required: true,
              })
            ),
            React.createElement(
              "div",
              { className: "form-group" },
              React.createElement("label", null, "Email"),
              React.createElement("input", {
                type: "email",
                value: newClientForm.email,
                onChange: (e) =>
                  setNewClientForm({ ...newClientForm, email: e.target.value }),
                placeholder: "email@ejemplo.com",
              })
            ),
            React.createElement(
              "div",
              { className: "form-group" },
              React.createElement("label", null, "Teléfono"),
              React.createElement("input", {
                type: "tel",
                value: newClientForm.phone,
                onChange: (e) =>
                  setNewClientForm({ ...newClientForm, phone: e.target.value }),
                placeholder: "+34 666 123 456",
              })
            ),
            React.createElement(
              "div",
              { className: "form-group" },
              React.createElement("label", null, "Empresa"),
              React.createElement("input", {
                type: "text",
                value: newClientForm.company,
                onChange: (e) =>
                  setNewClientForm({ ...newClientForm, company: e.target.value }),
                placeholder: "Nombre de la empresa",
              })
            ),
            React.createElement(
              "div",
              { className: "form-group" },
              React.createElement("label", null, "Notas"),
              React.createElement("textarea", {
                value: newClientForm.notes,
                onChange: (e) =>
                  setNewClientForm({ ...newClientForm, notes: e.target.value }),
                placeholder: "Notas adicionales",
                rows: 3,
              })
            ),
            React.createElement(
              "div",
              { className: "form-actions" },
              React.createElement("button", { type: "submit", style: { backgroundColor: "#2ecc71" } }, "Crear cliente"),
              React.createElement("button", {
                type: "button",
                onClick: () => setShowAddClient(false),
                style: { backgroundColor: "#95a5a6" },
              }, "Cancelar")
            )
          )
        )
      ),

    // ── Modal: Agregar website ───────────────────────────────────────────
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
            React.createElement(
              "div",
              { className: "form-group" },
              React.createElement("label", null, "Cliente *"),
              React.createElement(
                "select",
                {
                  value: newWebsiteForm.client_id,
                  onChange: (e) =>
                    setNewWebsiteForm({
                      ...newWebsiteForm,
                      client_id: e.target.value,
                    }),
                  required: true,
                },
                React.createElement("option", { value: "" }, "Selecciona un cliente"),
                clients.map((c) =>
                  React.createElement("option", { key: c.id, value: c.id }, c.name)
                )
              )
            ),
            React.createElement(
              "div",
              { className: "form-group" },
              React.createElement("label", null, "URL *"),
              React.createElement("input", {
                type: "url",
                value: newWebsiteForm.url,
                onChange: (e) =>
                  setNewWebsiteForm({ ...newWebsiteForm, url: e.target.value }),
                placeholder: "https://ejemplo.com",
                required: true,
              })
            ),
            React.createElement(
              "div",
              { className: "form-group" },
              React.createElement("label", null, "Etiqueta (nombre descriptivo)"),
              React.createElement("input", {
                type: "text",
                value: newWebsiteForm.label,
                onChange: (e) =>
                  setNewWebsiteForm({ ...newWebsiteForm, label: e.target.value }),
                placeholder: "Mi Sitio Web",
              })
            ),
            React.createElement(
              "div",
              { className: "form-group" },
              React.createElement("label", null, "Estrategia de scraping"),
              React.createElement(
                "select",
                {
                  value: newWebsiteForm.strategy,
                  onChange: (e) =>
                    setNewWebsiteForm({
                      ...newWebsiteForm,
                      strategy: e.target.value,
                    }),
                },
                React.createElement("option", { value: "auto" }, "Auto (detecta automáticamente)"),
                React.createElement("option", { value: "beautifulsoup" }, "BeautifulSoup (estático)"),
                React.createElement("option", { value: "selenium" }, "Selenium (JavaScript)")
              )
            ),
            React.createElement(
              "div",
              { className: "form-group" },
              React.createElement("label", null),
              React.createElement("input", {
                type: "checkbox",
                checked: newWebsiteForm.active,
                onChange: (e) =>
                  setNewWebsiteForm({ ...newWebsiteForm, active: e.target.checked }),
              }),
              React.createElement("span", { style: { marginLeft: "8px" } }, "Activa (auditará 2 veces/semana)")
            ),
            React.createElement(
              "div",
              { className: "form-actions" },
              React.createElement("button", { type: "submit", style: { backgroundColor: "#3498db" } }, "Agregar URL"),
              React.createElement("button", {
                type: "button",
                onClick: () => setShowAddWebsite(false),
                style: { backgroundColor: "#95a5a6" },
              }, "Cancelar")
            )
          )
        )
      )
  );
}

createRoot(document.getElementById("root")).render(React.createElement(App));
