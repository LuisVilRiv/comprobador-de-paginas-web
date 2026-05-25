/**
 * ============================================================================
 * I18N.JS - Sistema de Internacionalización (Internacionalización)
 * ============================================================================
 * 
 * DESCRIPCIÓN:
 * Este módulo implementa un sistema de internacionalización (i18n) completo
 * para la aplicación, permitiendo cambiar dinámicamente entre español e inglés.
 * Utiliza React Context API para proveer las funciones de traducción a todos
 * los componentes de la aplicación.
 * 
 * CARACTERÍSTICAS:
 * - Cambio dinámico de idioma sin recargar la página
 * - Persistencia en localStorage (el idioma se mantiene entre sesiones)
 * - Actualización del atributo lang del HTML para accesibilidad
 * - Sistema de diccionarios anidados para organización jerárquica
 * - Función de traducción con fallback a la clave si no existe
 * 
 * ESTRUCTURA DEL DICCIONARIO:
 * Los diccionarios están organizados por categorías:
 * - app: Textos generales de la aplicación (títulos, botones, mensajes)
 * - tour: Textos para los tours guiados (títulos, descripciones, botones)
 * - table: Textos para la tabla de websites (cabeceras, estados, acciones)
 * - modals: Textos para modales (formularios, confirmaciones)
 * - scheduler: Textos para el programador de auditorías
 * - audit: Textos para el detalle de auditorías
 * 
 * USO EN COMPONENTES:
 * ```javascript
 * import { useI18n } from "./js/i18n.js";
 * 
 * function MiComponente() {
 *   const { t, lang, toggleLang } = useI18n();
 *   
 *   return (
 *     <div>
 *       <h1>{t("app.title")}</h1>
 *       <button onClick={toggleLang}>
 *         {lang === "es" ? "English" : "Español"}
 *       </button>
 *     </div>
 *   );
 * }
 * ```
 * 
 * CLAVES DE TRADUCCIÓN:
 * - Formato: "categoria.clave" (ej: "app.title", "tour.next")
 * - Separador: punto (.) para jerarquía
 * - Fallback: si no existe, devuelve la clave completa
 * 
 * @version 2.0.0
 * @author Web Auditor Team
 * @since 2024
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from "https://esm.sh/react@18.3.1";

const dictionaries = {
  es: {
    app: {
      title: "Web Auditor Dashboard",
      global_schedule: "Programación Global",
      active_webs: "WEBS ACTIVAS",
      excellent_score: "PUNTUACIÓN EXCELENTE",
      next_active: "PRÓXIMO CICLO: ACTIVOS",
      next_inactive: "PRÓXIMO CICLO: INACTIVOS",
      new_client: "Nuevo Cliente",
      new_url: "Nueva URL",
      refresh: "Actualizar",
      all_clients: "Todos los clientes",
      search_placeholder: "Buscar por URL o etiqueta...",
      edit_client: "Editar cliente seleccionado",
      delete_client: "Eliminar cliente seleccionado",
      deleted_success: "✓ Eliminado correctamente",
      client_updated: "✓ Cliente actualizado",
      url_updated: "✓ URL actualizada",
      client_created: "✓ Cliente creado",
      url_added: "✓ URL añadida",
      schedule_saved: "✓ Programación guardada",
      audit_scheduled: "✓ Auditoría programada para",
    },
    tour: {
      help_btn: "Tour",
      step_welcome_title: "¡Bienvenido al Dashboard!",
      step_welcome_desc: "Vamos a dar un rápido paseo por las funcionalidades principales para que le saques el máximo partido al auditor.",
      step_toggles_title: "Apariencia e Idioma",
      step_toggles_desc: "Aquí puedes cambiar el idioma de la interfaz y alternar entre el modo claro y oscuro.",
      step_global_config_title: "Configuración Global",
      step_global_config_desc: "Define los ciclos de escaneo por defecto para todas las webs activas e inactivas. Pulsa 'Siguiente' para ver cómo funciona.",
      step_cron_title: "Programador Visual",
      step_cron_desc: "Aquí puedes configurar la frecuencia con un constructor visual fácil de usar.",
      step_cron_frequency_title: "Frecuencia Básica",
      step_cron_frequency_desc: "Selecciona si quieres que las auditorías se ejecuten cada día, semana, mes, etc. y a qué hora exacta.",
      step_cron_expert_title: "Modo Experto",
      step_cron_expert_desc: "Si necesitas una programación muy específica (ej. 'cada martes a las 14:30'), puedes activar el modo experto y escribir tu propia expresión CRON.",
      step_stats_title: "Métricas Generales",
      step_stats_desc: "Aquí puedes ver un resumen rápido de las webs activas, las puntuaciones excelentes y el tiempo restante para los próximos ciclos de auditoría.",
      step_new_client_title: "Gestión de Clientes",
      step_new_client_desc: "Agrupa tus webs creando clientes. Cada cliente puede tener su propia programación de auditorías.",
      step_new_url_title: "Añadir URLs",
      step_new_url_desc: "Añade nuevas páginas web para ser monitorizadas por el auditor.",
      step_refresh_title: "Actualización Manual",
      step_refresh_desc: "El panel se actualiza periódicamente, pero puedes forzar la recarga de datos con este botón.",
      step_filter_title: "Filtros y Búsqueda",
      step_filter_desc: "Filtra la vista por cliente o busca una URL específica rápidamente.",
      step_client_actions_title: "Acciones de Cliente",
      step_client_actions_desc: "Si seleccionas un cliente en el filtro, aparecerán opciones para editarlo, borrarlo o exportar un reporte en PDF de todas sus webs.",
      step_table_title: "Tabla de Resultados",
      step_table_desc: "Aquí verás el estado de todas las webs, sus puntuaciones y próximos escaneos. Haz clic en el título de la web para ver su historial detallado.",
      step_headers_title: "Ordenación",
      step_headers_desc: "Puedes hacer clic en cualquier cabecera de la columna (URL, Cliente, Score, Estado, etc.) para ordenar la tabla ascendente o descendentemente.",
      step_pagination_title: "Paginación",
      step_pagination_desc: "Utiliza estos controles para navegar entre las distintas páginas de resultados si tienes muchas URLs configuradas.",
      step_row_url_title: "Detalles de Auditoría",
      step_row_url_desc: "Haz clic en el nombre de cualquier web para abrir una ventana con el historial detallado de todas sus auditorías pasadas.",
      step_row_actions_title: "Acciones Individuales",
      step_row_actions_desc: "En cada fila tienes botones rápidos para forzar una auditoría en este momento, editar su configuración o eliminarla.",
      done: "Terminar",
      next: "Siguiente",
      prev: "Atrás",
      // New modular tour labels
      lang_toggle: "Cambiar idioma",
      theme_toggle: "Cambiar tema",
      full_tour_title: "Iniciar tour completo",
      module_tours: "Tours por módulo",
      module_stats: "Estadísticas",
      module_clients: "Clientes",
      module_websites: "Webs y Búsqueda",
      module_table: "Tabla de Resultados",
      module_scheduler: "Programador"
    },
    table: {
      url: "Sitio Web",
      client: "Cliente",
      next_audit: "Próxima Auditoría",
      status: "Estado",
      score: "Score",
      issues: "Incidencias",
      last_audit: "Última",
      actions: "Acciones",
      active: "Act.",
      inactive: "Inactiva",
      inherited: "Global",
      client_inherited: "(Cliente)",
      web_specific: "(Web)",
      edit: "Editar",
      delete: "Borrar",
      audit: "Auditar",
      auditing: "Auditoría en curso...",
      running: "Procesando...",
      no_runs: "Sin datos",
      score_suffix: "pts",
      pending: "PENDIENTE"
    },
    modals: {
      close: "Cerrar",
      cancel: "Cancelar",
      save: "Guardar Cambios",
      create_client: "Crear Cliente",
      create_url: "Añadir URL",
      delete_title: "Confirmar Eliminación",
      delete_prompt: "¿Estás seguro de eliminar",
      delete_type_client: "el cliente:",
      delete_type_url: "la URL:",
      delete_confirm_text: "Escribe ELIMINAR para confirmar",
      delete_placeholder: "ELIMINAR",
      add_client: "Añadir Cliente",
      edit_client: "Editar Cliente",
      name: "Nombre *",
      email: "Email",
      phone: "Teléfono",
      company: "Empresa",
      notes: "Notas",
      add_website: "Añadir URL",
      edit_website: "Editar URL",
      no_client: "— Sin cliente —",
      url_label: "URL *",
      alias_label: "Etiqueta / Alias",
      strategy: "Estrategia de renderizado",
      strategy_auto: "Automática (Recomendada)",
      strategy_selenium: "Forzar Selenium (JS render)",
      strategy_bs4: "Forzar BS4 (Páginas estáticas)",
      is_active: "Sitio Web Activo (monitoreado)",
      reset: "Restablecer",
      client: "Cliente asociado"
    },
    scheduler: {
      title: "Programación de Auditorías",
      tab_global: "Global",
      tab_clients: "Clientes",
      tab_urls: "URLs",
      save_global: "Guardar Configuración Global",
      active_cycles: "Ciclo (Webs Activas)",
      inactive_cycles: "Ciclo (Webs Inactivas)",
      expert_mode: "Modo Experto",
      simple_mode: "Modo Simple",
      add_rule: "+ Añadir regla de programación",
      expert_placeholder: "Ej: 0 0 * * *, 0 12 * * 0",
      expert_help: "Formato CRON de 5 campos (minuto hora día mes día_semana)",
      freq: "Frecuencia",
      time: "Hora",
      daily: "Diario",
      daily_x: "Cada X días",
      weekly: "Semanal",
      monthly: "Mensual",
      monthly_x: "Periódico",
      yearly: "Anual",
      week_days: "Días de la semana",
      weekly_note: "En esta tarjeta semanal puedes definir varias entradas de día de la semana/hora juntas.",
      weekly_entry_time_help: "Establece una hora para esta fila.",
      weekly_entry_days_help: "Selecciona uno o más días de la semana para esa hora.",
      add_weekly_entry: "Añadir entrada de día/hora",
      every_x_days: "Intervalo en días",
      days: "días",
      every_x_months: "Intervalo en meses",
      months: "meses",
      month_year: "Mes del año",
      day_month: "Día del mes",
      m_1: "Enero", m_2: "Febrero", m_3: "Marzo", m_4: "Abril", m_5: "Mayo", m_6: "Junio",
      m_7: "Julio", m_8: "Agosto", m_9: "Septiembre", m_10: "Octubre", m_11: "Noviembre", m_12: "Diciembre",
      day_l: "L", day_m: "M", day_x: "X", day_j: "J", day_v: "V", day_s: "S", day_d: "D",
      day_l_full: "Lunes", day_m_full: "Martes", day_x_full: "Miércoles", day_j_full: "Jueves", day_v_full: "Viernes", day_s_full: "Sábado", day_d_full: "Domingo",
      hour_of: "Hora de",
      weekly_select_day_message: "Selecciona uno o más días de la semana para añadir horarios.",
      search_client: "Buscar por nombre...",
      search_url: "Buscar por URL...",
      show_custom: "Mostrar solo modificados",
      custom_schedule: "Programación Custom",
      configure: "Configurar",
      no_results: "No se encontraron resultados"
    },
    audit: {
      detail_title: "Detalle de la URL",
      history: "Historial de Análisis",
      issues: "Incidencias",
      no_history: "Sin análisis registrados.",
      no_sections: "No hay datos de secciones para este informe.",
      scan_failed: "Error en Auditoría",
      failed_reason: "Motivo del fallo",
      general_issues: "Incidencias Generales",
      no_issues: "¡Excelente! No se encontraron incidencias.",
      file: "Archivo / Recurso",
      line: "Fila",
      action: "Acción Sugerida",
      time_day: "d", time_hour: "h", time_min: "m", time_sec: "s",
      time_now: "...",
      info_title: "ℹ️ Pruebas Realizadas y su Propósito",
      info_sec: "🛡️ Seguridad:",
      info_sec_desc: " Verifica cabeceras HTTP, exposición de servidor y configuraciones contra ataques comunes.",
      info_seo: "🔍 SEO:",
      info_seo_desc: " Evalúa metaetiquetas (Title, Description) para asegurar correcta indexación en buscadores.",
      info_perf: "⚡ Rendimiento:",
      info_perf_desc: " Comprueba tiempos de respuesta y estado del servidor para garantizar velocidad.",
      info_html: "🏗️ Estructura HTML:",
      info_html_desc: " Analiza la jerarquía de encabezados (H1, H2) y el uso correcto de semántica web.",
      info_acc: "♿ Contenido y Accesibilidad:",
      info_acc_desc: " Revisa atributos 'alt' en imágenes, densidad de texto y contrastes.",
      info_nav: "🔗 Enlaces y Navegación:",
      info_nav_desc: " Detecta enlaces rotos (404) y verifica que los elementos interactivos funcionen.",
      col_section: "Sección",
      col_execution: "Ejecución",
      col_desc: "Descripción",
      col_detail: "Detalle",
      status_blocked: "BLOQUEADO",
      status_failed: "FALLIDO",
      status_ok: "OK",
      date: "Fecha",
      score: "Puntuación",
      prev: "Anterior",
      hide_details: "Ocultar detalles",
      show_details: "Ver detalle de pruebas",
      export_pdf: "Exportar PDF"
    }
  },
  en: {
    app: {
      title: "Web Auditor Dashboard",
      global_schedule: "Global Schedule",
      active_webs: "ACTIVE WEBSITES",
      excellent_score: "EXCELLENT SCORE",
      next_active: "NEXT CYCLE: ACTIVE",
      next_inactive: "NEXT CYCLE: INACTIVE",
      new_client: "New Client",
      new_url: "New URL",
      refresh: "Refresh",
      all_clients: "All clients",
      search_placeholder: "Search by URL or label...",
      edit_client: "Edit selected client",
      delete_client: "Delete selected client",
      deleted_success: "✓ Deleted successfully",
      client_updated: "✓ Client updated",
      url_updated: "✓ URL updated",
      client_created: "✓ Client created",
      url_added: "✓ URL added",
      schedule_saved: "✓ Schedule saved",
      audit_scheduled: "✓ Audit scheduled for",
    },
    tour: {
      help_btn: "ℹ️ Tour",
      step_welcome_title: "Welcome to the Dashboard!",
      step_welcome_desc: "Let's take a quick tour of the main features so you can get the most out of the auditor.",
      step_toggles_title: "Appearance and Language",
      step_toggles_desc: "Here you can change the interface language and toggle between light and dark mode.",
      step_global_config_title: "Global Configuration",
      step_global_config_desc: "Define the default scan cycles for all active and inactive websites. Click 'Next' to see how it works.",
      step_cron_title: "Visual Scheduler",
      step_cron_desc: "Here you can set the frequency using an easy-to-use visual builder.",
      step_cron_frequency_title: "Basic Frequency",
      step_cron_frequency_desc: "Select whether you want audits to run daily, weekly, monthly, etc., and at what exact time.",
      step_cron_expert_title: "Expert Mode",
      step_cron_expert_desc: "If you need a very specific schedule (e.g. 'every Tuesday at 14:30'), you can activate expert mode and write your own CRON expression.",
      step_stats_title: "General Metrics",
      step_stats_desc: "Here you can see a quick summary of active websites, excellent scores, and the remaining time for the next audit cycles.",
      step_new_client_title: "Client Management",
      step_new_client_desc: "Group your websites by creating clients. Each client can have its own specific audit schedule.",
      step_new_url_title: "Add URLs",
      step_new_url_desc: "Add new websites to be monitored by the auditor system.",
      step_refresh_title: "Manual Refresh",
      step_refresh_desc: "The dashboard updates periodically, but you can force a data reload with this button.",
      step_filter_title: "Filters and Search",
      step_filter_desc: "Filter the view by client or search for a specific URL quickly.",
      step_client_actions_title: "Client Actions",
      step_client_actions_desc: "If you select a client in the filter, options will appear to edit it, delete it, or export a PDF report of all its websites.",
      step_table_title: "Results Table",
      step_table_desc: "Here you will see the status of all websites, their scores, and upcoming scans. Click on a website's title to see its detailed history.",
      step_headers_title: "Sorting",
      step_headers_desc: "You can click on any column header (URL, Client, Score, Status, etc.) to sort the table ascending or descending.",
      step_pagination_title: "Pagination",
      step_pagination_desc: "Use these controls to navigate between different pages of results if you have many URLs configured.",
      step_row_url_title: "Audit Details",
      step_row_url_desc: "Click on the name of any website to open a modal with the detailed history of all its past audits.",
      step_row_actions_title: "Individual Actions",
      step_row_actions_desc: "On each row you have quick buttons to manually force an audit right now, edit its settings, or delete it.",
      done: "Done",
      next: "Next",
      prev: "Previous",
      // New modular tour labels
      lang_toggle: "Change language",
      theme_toggle: "Change theme",
      full_tour_title: "Start full tour",
      module_tours: "Module tours",
      module_stats: "Statistics",
      module_clients: "Clients",
      module_websites: "Websites & Search",
      module_table: "Results Table",
      module_scheduler: "Scheduler"
    },
    table: {
      url: "Website",
      client: "Client",
      next_audit: "Next Audit",
      status: "Status",
      score: "Score",
      issues: "Issues",
      last_audit: "Last Audit",
      actions: "Actions",
      active: "Act.",
      inactive: "Inactive",
      inherited: "Global",
      client_inherited: "(Client)",
      web_specific: "(Web)",
      edit: "Edit",
      delete: "Delete",
      audit: "Audit",
      auditing: "Auditing in progress...",
      running: "Processing...",
      no_runs: "No data",
      score_suffix: "pts",
      pending: "PENDING"
    },
    modals: {
      close: "Close",
      cancel: "Cancel",
      save: "Save Changes",
      create_client: "Create Client",
      create_url: "Add URL",
      delete_title: "Confirm Deletion",
      delete_prompt: "Are you sure you want to delete",
      delete_type_client: "the client:",
      delete_type_url: "the URL:",
      delete_confirm_text: "Type DELETE to confirm",
      delete_placeholder: "DELETE",
      add_client: "Add Client",
      edit_client: "Edit Client",
      name: "Name *",
      email: "Email",
      phone: "Phone",
      company: "Company",
      notes: "Notes",
      add_website: "Add URL",
      edit_website: "Edit URL",
      no_client: "— No client —",
      url_label: "URL *",
      alias_label: "Label / Alias",
      strategy: "Render Strategy",
      strategy_auto: "Automatic (Recommended)",
      strategy_selenium: "Force Selenium (JS render)",
      strategy_bs4: "Force BS4 (Static pages)",
      is_active: "Active Website (monitored)",
      reset: "Reset",
      client: "Associated Client"
    },
    scheduler: {
      title: "Audit Schedule",
      tab_global: "Global",
      tab_clients: "Clients",
      tab_urls: "URLs",
      save_global: "Save Global Config",
      active_cycles: "Cycle (Active Webs)",
      inactive_cycles: "Cycle (Inactive Webs)",
      expert_mode: "Expert Mode",
      simple_mode: "Simple Mode",
      add_rule: "+ Add schedule rule",
      expert_placeholder: "Ex: 0 0 * * *, 0 12 * * 0",
      expert_help: "5-field CRON format (minute hour day month day_of_week)",
      freq: "Frequency",
      time: "Time",
      daily: "Daily",
      daily_x: "Every X days",
      weekly: "Weekly",
      monthly: "Monthly",
      monthly_x: "Periodic",
      yearly: "Yearly",
      week_days: "Days of the week",
      weekly_note: "In this weekly card you can define several weekday/time entries together.",
      weekly_entry_time_help: "Set a time for this row.",
      weekly_entry_days_help: "Select one or more weekdays for that time.",
      add_weekly_entry: "Add weekday/time entry",
      every_x_days: "Interval in days",
      days: "days",
      every_x_months: "Interval in months",
      months: "months",
      month_year: "Month of the year",
      day_month: "Day of the month",
      m_1: "January", m_2: "February", m_3: "March", m_4: "April", m_5: "May", m_6: "June",
      m_7: "July", m_8: "August", m_9: "September", m_10: "October", m_11: "November", m_12: "December",
      day_l: "M", day_m: "T", day_x: "W", day_j: "T", day_v: "F", day_s: "S", day_d: "S",
      day_l_full: "Monday", day_m_full: "Tuesday", day_x_full: "Wednesday", day_j_full: "Thursday", day_v_full: "Friday", day_s_full: "Saturday", day_d_full: "Sunday",
      hour_of: "Hour of",
      weekly_select_day_message: "Select one or more days of the week to add schedule entries.",
      search_client: "Search by name...",
      search_url: "Search by URL...",
      show_custom: "Show only modified",
      custom_schedule: "Custom Schedule",
      configure: "Configure",
      no_results: "No results found"
    },
    audit: {
      detail_title: "URL Details",
      history: "Analysis History",
      issues: "Issues",
      no_history: "No recorded analysis.",
      no_sections: "No section data available for this report.",
      scan_failed: "Audit Error",
      failed_reason: "Reason for failure",
      general_issues: "General Issues",
      no_issues: "Excellent! No issues found.",
      file: "File / Resource",
      line: "Row",
      action: "Suggested Action",
      time_day: "d", time_hour: "h", time_min: "m", time_sec: "s",
      time_now: "...",
      info_title: "ℹ️ Tests Performed and their Purpose",
      info_sec: "🛡️ Security:",
      info_sec_desc: " Checks HTTP headers, server exposure, and configs against common attacks.",
      info_seo: "🔍 SEO:",
      info_seo_desc: " Evaluates meta tags (Title, Description) to ensure proper search engine indexing.",
      info_perf: "⚡ Performance:",
      info_perf_desc: " Checks response times and server status to guarantee speed.",
      info_html: "🏗️ HTML Structure:",
      info_html_desc: " Analyzes heading hierarchy (H1, H2) and correct semantic web usage.",
      info_acc: "♿ Content and Accessibility:",
      info_acc_desc: " Reviews 'alt' attributes on images, text density, and contrasts.",
      info_nav: "🔗 Links and Navigation:",
      info_nav_desc: " Detects broken links (404) and verifies interactive elements work.",
      col_section: "Section",
      col_execution: "Execution",
      col_desc: "Description",
      col_detail: "Details",
      status_blocked: "BLOCKED",
      status_failed: "FAILED",
      status_ok: "OK",
      date: "Date",
      score: "Score",
      prev: "Previous",
      hide_details: "Hide details",
      show_details: "View test details",
      export_pdf: "Export PDF"
    }
  }
};

export const I18nContext = createContext();

export function I18nProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem("app_lang") || "es");

  useEffect(() => {
    localStorage.setItem("app_lang", lang);
    document.documentElement.lang = lang;
  }, [lang]);

  const toggleLang = useCallback(() => {
    setLang(prev => prev === "es" ? "en" : "es");
  }, []);

  const t = useCallback((key) => {
    const keys = key.split(".");
    let val = dictionaries[lang];
    for (const k of keys) {
      if (val) val = val[k];
    }
    return val !== undefined ? val : key;
  }, [lang]);

  return React.createElement(
    I18nContext.Provider,
    { value: { lang, toggleLang, t } },
    children
  );
}

export const useI18n = () => useContext(I18nContext);
