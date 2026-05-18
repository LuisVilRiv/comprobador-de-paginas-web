/**
 * modals.js — Modales de formularios CRUD (clientes, websites, borrado, edición).
 */
import React from "https://esm.sh/react@18.3.1";
import { useI18n } from "./i18n.js";

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
  const { t } = useI18n();
  return React.createElement(
    "div", { className: "modal", onClick: onCancel },
    React.createElement(
      "div", {
        className: "modal-content premium-modal",
        style: { maxWidth: "450px" },
        onClick: (e) => e.stopPropagation()
      },
      React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "25px" } },
        React.createElement("h2", { style: { margin: 0, color: "var(--danger)" } }, t("modals.delete_title")),
        React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: onCancel }, t("modals.close"))
      ),
      React.createElement("p", { style: { marginBottom: "20px", color: "var(--text-dim)", fontSize: "14px" } },
        `${t("modals.delete_prompt")} ${confirm.type === "client" ? t("modals.delete_type_client") : t("modals.delete_type_url")}`
      ),
      React.createElement("div", {
        style: { fontWeight: "bold", fontSize: "16px", background: "rgba(255,255,255,0.05)", padding: "16px", borderRadius: "8px", margin: "0 0 25px 0", textAlign: "center", border: "1px solid rgba(239, 68, 68, 0.2)" }
      }, confirm.name),
      React.createElement("div", { className: "form-group" },
        React.createElement("label", null, t("modals.delete_confirm_text")),
        React.createElement("input", {
          type: "text", value: confirm.input, className: "premium-input",
          onChange: (e) => onChange(e.target.value),
          placeholder: t("modals.delete_placeholder"),
          style: { textAlign: "center", textTransform: "uppercase", fontSize: "18px", letterSpacing: "2px" }
        })
      ),
      React.createElement("div", { className: "form-actions" },
        React.createElement("button", {
          className: "btn-base btn-danger", style: { flex: 1 },
          onClick: onConfirm,
          disabled: confirm.input !== "ELIMINAR" || loading,
        }, loading ? "..." : t("table.delete")),
        React.createElement("button", { className: "btn-base btn-ghost", onClick: onCancel, style: { flex: 1 } }, t("modals.cancel"))
      )
    )
  );
}

// ── Modal: Agregar cliente ────────────────────────────────────────────────────

export function AddClientModal({ form, error, onChange, onSubmit, onClose }) {
  const { t } = useI18n();
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
        React.createElement("h2", { style: { margin: 0 } }, t("modals.create_client")),
        React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: onClose }, t("modals.close"))
      ),
      React.createElement("form", { onSubmit },
        React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" } },
          field(t("modals.name"), "text",  "name",    ""),
          field(t("modals.email"),    "email", "email",   ""),
        ),
        React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginTop: "10px" } },
          field(t("modals.phone"), "tel",   "phone",   ""),
          field(t("modals.company"),  "text",  "company", ""),
        ),
        React.createElement("div", { className: "form-group", style: { marginTop: "10px" } },
          React.createElement("label", null, t("modals.notes")),
          React.createElement("textarea", {
            className: "premium-input",
            value: form.notes, rows: 3, placeholder: "",
            onChange: (e) => onChange({ ...form, notes: e.target.value }),
          })
        ),
        React.createElement("div", { className: "form-actions" },
          React.createElement("button", { type: "submit", className: "btn-base btn-success", style: { flex: 1 } }, t("modals.create_client")),
          React.createElement("button", { type: "button", className: "btn-base btn-ghost", style: { flex: 1 }, onClick: onClose }, t("modals.cancel"))
        )
      )
    )
  );
}

// ── Modal: Editar cliente ─────────────────────────────────────────────────────

export function EditClientModal({ form, onSubmit, onChange, onClose }) {
  const { t } = useI18n();
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
        React.createElement("h2", { style: { margin: 0 } }, t("modals.edit_client")),
        React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: onClose }, t("modals.close"))
      ),
      React.createElement("form", { onSubmit },
        React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" } },
          field(t("modals.name"), "text",  "name"),
          field(t("modals.email"),    "email", "email"),
        ),
        React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginTop: "10px" } },
          field(t("modals.phone"), "tel",   "phone"),
          field(t("modals.company"),  "text",  "company"),
        ),
        React.createElement("div", { className: "form-group", style: { marginTop: "10px" } },
          React.createElement("label", null, t("modals.notes")),
          React.createElement("textarea", {
            className: "premium-input",
            value: form.notes || "", rows: 3,
            onChange: (e) => onChange({ ...form, notes: e.target.value }),
          })
        ),
        React.createElement("div", { className: "form-actions" },
          React.createElement("button", { type: "submit", className: "btn-base btn-warning", style: { flex: 1 } }, t("modals.save")),
          React.createElement("button", { type: "button", className: "btn-base btn-ghost", style: { flex: 1 }, onClick: onClose }, t("modals.cancel"))
        )
      )
    )
  );
}

// ── Modal: Agregar website ────────────────────────────────────────────────────

export function AddWebsiteModal({ form, clients, onSubmit, onChange, onClose }) {
  const { t } = useI18n();
  return React.createElement(
    "div", { className: "modal", onClick: onClose },
    React.createElement(
      "div", { className: "modal-content premium-modal", style: { maxWidth: "600px" }, onClick: (e) => e.stopPropagation() },
      React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "30px" } },
        React.createElement("h2", { style: { margin: 0 } }, t("modals.create_url")),
        React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: onClose }, t("modals.close"))
      ),
      React.createElement("form", { onSubmit },
        React.createElement("div", { className: "form-group" },
          React.createElement("label", null, t("modals.client")),
          React.createElement("select", {
            className: "premium-input",
            value: form.client_id,
            onChange: (e) => onChange({ ...form, client_id: e.target.value }),
          },
            React.createElement("option", { value: "" }, t("modals.no_client")),
            clients.map((c) => React.createElement("option", { key: c.id, value: c.id }, c.name))
          )
        ),
        React.createElement("div", { className: "form-group" },
          React.createElement("label", null, t("modals.url_label")),
          React.createElement("input", {
            className: "premium-input",
            type: "url", value: form.url, required: true, placeholder: "https://ejemplo.com",
            onChange: (e) => onChange({ ...form, url: e.target.value }),
          })
        ),
        React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" } },
          React.createElement("div", { className: "form-group" },
            React.createElement("label", null, t("modals.alias_label")),
            React.createElement("input", {
              className: "premium-input",
              type: "text", value: form.label, placeholder: "",
              onChange: (e) => onChange({ ...form, label: e.target.value }),
            })
          ),
          React.createElement("div", { className: "form-group" },
            React.createElement("label", null, t("modals.strategy")),
            React.createElement("select", {
              className: "premium-input",
              value: form.strategy,
              onChange: (e) => onChange({ ...form, strategy: e.target.value }),
            },
              React.createElement("option", { value: "auto" }, t("modals.strategy_auto")),
              React.createElement("option", { value: "beautifulsoup" }, t("modals.strategy_bs4")),
              React.createElement("option", { value: "selenium" }, t("modals.strategy_selenium"))
            )
          )
        ),
        React.createElement("div", { className: "form-group", style: { marginTop: "10px" } },
          React.createElement(Switch, {
            label: t("modals.is_active"),
            checked: form.active,
            onChange: (val) => onChange({ ...form, active: val })
          })
        ),
        React.createElement("div", { className: "form-actions", style: { marginTop: "30px" } },
          React.createElement("button", { type: "submit", className: "btn-base btn-primary", style: { flex: 1 } }, t("modals.create_url")),
          React.createElement("button", { type: "button", className: "btn-base btn-ghost", style: { flex: 1 }, onClick: onClose }, t("modals.cancel"))
        )
      )
    )
  );
}

// ── Modal: Editar website ─────────────────────────────────────────────────────

export function EditWebsiteModal({ form, clients = [], onSubmit, onChange, onClose }) {
  const { t } = useI18n();
  return React.createElement(
    "div", { className: "modal", onClick: onClose },
    React.createElement(
      "div", { className: "modal-content premium-modal", style: { maxWidth: "600px" }, onClick: (e) => e.stopPropagation() },
      React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "30px" } },
        React.createElement("h2", { style: { margin: 0 } }, t("modals.edit_website")),
        React.createElement("button", { className: "btn-base btn-ghost btn-small", onClick: onClose }, t("modals.close"))
      ),
      React.createElement("form", { onSubmit },
        React.createElement("div", { className: "form-group" },
          React.createElement("label", null, t("modals.client")),
          React.createElement("select", {
            className: "premium-input",
            value: form.client_id || "",
            onChange: (e) => onChange({ ...form, client_id: e.target.value || null }),
          },
            React.createElement("option", { value: "" }, t("modals.no_client")),
            clients.map((c) => React.createElement("option", { key: c.id, value: c.id }, c.name))
          )
        ),
        React.createElement("div", { className: "form-group" },
          React.createElement("label", null, t("modals.url_label")),
          React.createElement("input", {
            className: "premium-input",
            type: "url", value: form.url, required: true,
            onChange: (e) => onChange({ ...form, url: e.target.value }),
          })
        ),
        React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" } },
          React.createElement("div", { className: "form-group" },
            React.createElement("label", null, t("modals.alias_label")),
            React.createElement("input", {
              className: "premium-input",
              type: "text", value: form.label || "",
              onChange: (e) => onChange({ ...form, label: e.target.value }),
            })
          ),
          React.createElement("div", { className: "form-group" },
            React.createElement("label", null, t("modals.strategy")),
            React.createElement("select", {
              className: "premium-input",
              value: form.strategy,
              onChange: (e) => onChange({ ...form, strategy: e.target.value }),
            },
              React.createElement("option", { value: "auto" }, t("modals.strategy_auto")),
              React.createElement("option", { value: "beautifulsoup" }, t("modals.strategy_bs4")),
              React.createElement("option", { value: "selenium" }, t("modals.strategy_selenium"))
            )
          )
        ),
        React.createElement("div", { className: "form-group", style: { marginTop: "10px" } },
          React.createElement(Switch, {
            label: t("modals.is_active"),
            checked: form.active,
            onChange: (val) => onChange({ ...form, active: val })
          })
        ),
        React.createElement("div", { className: "form-actions", style: { marginTop: "30px" } },
          React.createElement("button", { type: "submit", className: "btn-base btn-warning", style: { flex: 1 } }, t("modals.save")),
          React.createElement("button", { type: "button", className: "btn-base btn-ghost", style: { flex: 1 }, onClick: onClose }, t("modals.close"))
        )
      )
    )
  );
}
