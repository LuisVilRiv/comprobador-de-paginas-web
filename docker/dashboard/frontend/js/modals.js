/**
 * modals.js — Modales de formularios CRUD (clientes, websites, borrado, edición).
 * Contiene todos los modales de la aplicación excepto el del scheduler.
 */
import React from "https://esm.sh/react@18.3.1";

// ── Componente Reutilizable: Switch ───────────────────────────────────────────
function Switch({ label, checked, onChange }) {
  return React.createElement("label", { className: "switch-container" },
    React.createElement("div", { className: "switch" },
      React.createElement("input", { 
        type: "checkbox", 
        checked, 
        onChange: (e) => onChange(e.target.checked) 
      }),
      React.createElement("span", { className: "slider" })
    ),
    React.createElement("span", { style: { fontSize: "14px", fontWeight: "600" } }, label)
  );
}

// ── Modal: Confirmación de borrado ────────────────────────────────────────────

export function DeleteConfirmModal({ confirm, loading, onChange, onConfirm, onCancel }) {
  return React.createElement(
    "div", { className: "modal", onClick: onCancel },
    React.createElement(
      "div", {
        className: "modal-content premium-modal",
        style: { maxWidth: "450px" },
        onClick: (e) => e.stopPropagation()
      },
      React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "25px" } },
        React.createElement("h2", { style: { margin: 0, color: "var(--danger)" } }, "Confirmar Eliminación"),
        React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: onCancel }, "Cerrar")
      ),
      React.createElement("p", { style: { marginBottom: "20px", color: "var(--text-dim)", fontSize: "14px" } },
        `¿Estás seguro de eliminar ${confirm.type === "client" ? "el cliente" : "la URL"}:`
      ),
      React.createElement("div", {
        style: { fontWeight: "bold", fontSize: "16px", background: "rgba(255,255,255,0.05)", padding: "16px", borderRadius: "8px", margin: "0 0 25px 0", textAlign: "center", border: "1px solid rgba(239, 68, 68, 0.2)" }
      }, confirm.name),
      React.createElement("div", { className: "form-group" },
        React.createElement("label", null, `Escribe ELIMINAR para confirmar`),
        React.createElement("input", {
          type: "text", value: confirm.input, className: "premium-input",
          onChange: (e) => onChange(e.target.value),
          placeholder: "ELIMINAR",
          style: { textAlign: "center", textTransform: "uppercase", fontSize: "18px", letterSpacing: "2px" }
        })
      ),
      React.createElement("div", { className: "form-actions" },
        React.createElement("button", {
          className: "btn-base btn-danger", style: { flex: 1 },
          onClick: onConfirm,
          disabled: confirm.input !== "ELIMINAR" || loading,
        }, loading ? "Eliminando..." : "Confirmar"),
        React.createElement("button", { className: "btn-base btn-ghost", onClick: onCancel, style: { flex: 1 } }, "Cancelar")
      )
    )
  );
}

// ── Modal: Agregar cliente ────────────────────────────────────────────────────

export function AddClientModal({ form, error, onChange, onSubmit, onClose }) {
  const field = (label, type, key, placeholder) =>
    React.createElement("div", { className: "form-group" },
      React.createElement("label", null, label),
      React.createElement("input", {
        className: "premium-input",
        type, value: form[key], placeholder,
        onChange: (e) => onChange({ ...form, [key]: e.target.value }),
      })
    );

  return React.createElement(
    "div", { className: "modal", onClick: onClose },
    React.createElement(
      "div", { className: "modal-content premium-modal", style: { maxWidth: "550px" }, onClick: (e) => e.stopPropagation() },
      React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "30px" } },
        React.createElement("h2", { style: { margin: 0 } }, "Nuevo Cliente"),
        React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: onClose }, "Cerrar")
      ),
      React.createElement("form", { onSubmit },
        React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" } },
          field("Nombre *", "text",  "name",    "Nombre comercial"),
          field("Email",    "email", "email",   "contacto@empresa.com"),
        ),
        React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginTop: "10px" } },
          field("Teléfono", "tel",   "phone",   "+34..."),
          field("Empresa",  "text",  "company", "Razón social"),
        ),
        React.createElement("div", { className: "form-group", style: { marginTop: "10px" } },
          React.createElement("label", null, "Notas"),
          React.createElement("textarea", {
            className: "premium-input",
            value: form.notes, rows: 3, placeholder: "Información adicional...",
            onChange: (e) => onChange({ ...form, notes: e.target.value }),
          })
        ),
        React.createElement("div", { className: "form-actions" },
          React.createElement("button", { type: "submit", className: "btn-base btn-success", style: { flex: 1 } }, "Crear Cliente"),
          React.createElement("button", { type: "button", className: "btn-base btn-ghost", style: { flex: 1 }, onClick: onClose }, "Cancelar")
        )
      )
    )
  );
}

// ── Modal: Editar cliente ─────────────────────────────────────────────────────

export function EditClientModal({ form, onSubmit, onChange, onClose }) {
  const field = (label, type, key) =>
    React.createElement("div", { className: "form-group" },
      React.createElement("label", null, label),
      React.createElement("input", {
        className: "premium-input",
        type, value: form[key] || "", required: key === "name",
        onChange: (e) => onChange({ ...form, [key]: e.target.value }),
      })
    );

  return React.createElement(
    "div", { className: "modal", onClick: onClose },
    React.createElement(
      "div", { className: "modal-content premium-modal", style: { maxWidth: "550px" }, onClick: (e) => e.stopPropagation() },
      React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "30px" } },
        React.createElement("h2", { style: { margin: 0 } }, "Editar Cliente"),
        React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: onClose }, "Cerrar")
      ),
      React.createElement("form", { onSubmit },
        React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" } },
          field("Nombre *", "text",  "name"),
          field("Email",    "email", "email"),
        ),
        React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginTop: "10px" } },
          field("Teléfono", "tel",   "phone"),
          field("Empresa",  "text",  "company"),
        ),
        React.createElement("div", { className: "form-group", style: { marginTop: "10px" } },
          React.createElement("label", null, "Notas"),
          React.createElement("textarea", {
            className: "premium-input",
            value: form.notes || "", rows: 3,
            onChange: (e) => onChange({ ...form, notes: e.target.value }),
          })
        ),
        React.createElement("div", { className: "form-actions" },
          React.createElement("button", { type: "submit", className: "btn-base btn-warning", style: { flex: 1 } }, "Guardar Cambios"),
          React.createElement("button", { type: "button", className: "btn-base btn-ghost", style: { flex: 1 }, onClick: onClose }, "Cancelar")
        )
      )
    )
  );
}

// ── Modal: Agregar website ────────────────────────────────────────────────────

export function AddWebsiteModal({ form, clients, onSubmit, onChange, onClose }) {
  return React.createElement(
    "div", { className: "modal", onClick: onClose },
    React.createElement(
      "div", { className: "modal-content premium-modal", style: { maxWidth: "600px" }, onClick: (e) => e.stopPropagation() },
      React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "30px" } },
        React.createElement("h2", { style: { margin: 0 } }, "Añadir Nueva URL"),
        React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: onClose }, "Cerrar")
      ),
      React.createElement("form", { onSubmit },
        React.createElement("div", { className: "form-group" },
          React.createElement("label", null, "Cliente *"),
          React.createElement("select", {
            className: "premium-input",
            value: form.client_id, required: true,
            onChange: (e) => onChange({ ...form, client_id: e.target.value }),
          },
            React.createElement("option", { value: "" }, "Selecciona cliente..."),
            clients.map((c) => React.createElement("option", { key: c.id, value: c.id }, c.name))
          )
        ),
        React.createElement("div", { className: "form-group" },
          React.createElement("label", null, "URL *"),
          React.createElement("input", {
            className: "premium-input",
            type: "url", value: form.url, required: true, placeholder: "https://ejemplo.com",
            onChange: (e) => onChange({ ...form, url: e.target.value }),
          })
        ),
        React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" } },
          React.createElement("div", { className: "form-group" },
            React.createElement("label", null, "Etiqueta"),
            React.createElement("input", {
              className: "premium-input",
              type: "text", value: form.label, placeholder: "Nombre interno",
              onChange: (e) => onChange({ ...form, label: e.target.value }),
            })
          ),
          React.createElement("div", { className: "form-group" },
            React.createElement("label", null, "Estrategia"),
            React.createElement("select", {
              className: "premium-input",
              value: form.strategy,
              onChange: (e) => onChange({ ...form, strategy: e.target.value }),
            },
              React.createElement("option", { value: "auto" }, "Automática"),
              React.createElement("option", { value: "beautifulsoup" }, "Estática (Rápida)"),
              React.createElement("option", { value: "selenium" }, "Dinámica (JS)")
            )
          )
        ),
        React.createElement("div", { className: "form-group", style: { marginTop: "10px" } },
          React.createElement(Switch, {
            label: "Inicializar como activa",
            checked: form.active,
            onChange: (val) => onChange({ ...form, active: val })
          })
        ),
        React.createElement("div", { className: "form-actions", style: { marginTop: "30px" } },
          React.createElement("button", { type: "submit", className: "btn-base btn-primary", style: { flex: 1 } }, "Confirmar Alta"),
          React.createElement("button", { type: "button", className: "btn-base btn-ghost", style: { flex: 1 }, onClick: onClose }, "Cancelar")
        )
      )
    )
  );
}

// ── Modal: Editar website ─────────────────────────────────────────────────────

export function EditWebsiteModal({ form, onSubmit, onChange, onClose }) {
  return React.createElement(
    "div", { className: "modal", onClick: onClose },
    React.createElement(
      "div", { className: "modal-content premium-modal", style: { maxWidth: "600px" }, onClick: (e) => e.stopPropagation() },
      React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "30px" } },
        React.createElement("h2", { style: { margin: 0 } }, "Editar URL"),
        React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: onClose }, "Cerrar")
      ),
      React.createElement("form", { onSubmit },
        React.createElement("div", { className: "form-group" },
          React.createElement("label", null, "URL *"),
          React.createElement("input", {
            className: "premium-input",
            type: "url", value: form.url, required: true,
            onChange: (e) => onChange({ ...form, url: e.target.value }),
          })
        ),
        React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" } },
          React.createElement("div", { className: "form-group" },
            React.createElement("label", null, "Etiqueta"),
            React.createElement("input", {
              className: "premium-input",
              type: "text", value: form.label || "",
              onChange: (e) => onChange({ ...form, label: e.target.value }),
            })
          ),
          React.createElement("div", { className: "form-group" },
            React.createElement("label", null, "Estrategia"),
            React.createElement("select", {
              className: "premium-input",
              value: form.strategy,
              onChange: (e) => onChange({ ...form, strategy: e.target.value }),
            },
              React.createElement("option", { value: "auto" }, "Automática"),
              React.createElement("option", { value: "beautifulsoup" }, "Estática"),
              React.createElement("option", { value: "selenium" }, "Dinámica")
            )
          )
        ),
        React.createElement("div", { className: "form-group", style: { marginTop: "10px" } },
          React.createElement(Switch, {
            label: "Sitio activo",
            checked: form.active,
            onChange: (val) => onChange({ ...form, active: val })
          })
        ),
        React.createElement("div", { className: "form-actions", style: { marginTop: "30px" } },
          React.createElement("button", { type: "submit", className: "btn-base btn-warning", style: { flex: 1 } }, "Guardar Cambios"),
          React.createElement("button", { type: "button", className: "btn-base btn-ghost", style: { flex: 1 }, onClick: onClose }, "Cerrar")
        )
      )
    )
  );
}
