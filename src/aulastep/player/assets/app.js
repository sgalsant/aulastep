/* AulaStep · app.js
   Orquestador del reproductor: carga activity.json, gestiona la pantalla de
   inicio, el shell principal, el renderizado de pasos y la exportación e
   importación del trabajo del alumnado. */

import { renderSegment } from "./directives.js";
import { pickFile } from "./evidence.js";
import {
  ImportError,
  buildAulawork,
  buildExportFilename,
  downloadBlob,
  parseAulawork,
  restoreWork,
} from "./import-export.js";
import {
  NavPolicy,
  Router,
  allInteractiveIds,
  computeProgress,
  renderRail,
} from "./navigation.js";
import { SaveIndicator, Store, autosaveDebounce } from "./storage.js";
import { confirmModal, el, enhanceCodeBlocks, enhanceSolutions, formatDate, openModal, toast } from "./ui.js";

const THEMES = [
  ["oceano", "Océano"],
  ["bosque", "Bosque"],
  ["indigo", "Índigo"],
  ["ambar", "Ámbar"],
  ["grafito", "Grafito"],
  ["coral", "Coral"],
  ["halloween", "Halloween"],
];

const appRoot = document.getElementById("app");
const APP_NAME = appRoot.dataset.appName || "AulaStep";
const LOGO = appRoot.dataset.logo || APP_NAME;

const state = {
  activity: null,
  store: null,
  router: null,
  saveIndicator: null,
  policy: null,
  progress: null,
  knownIds: null,
  debounced: null,
};

/* ------------------------------------------------------------ saneamiento */
function sanitize(html) {
  return DOMPurify.sanitize(html, {
    ADD_ATTR: ["target", "rel", "download", "data-step-link"],
  });
}

function sanitizeActivity(activity) {
  for (const step of activity.steps) {
    for (const segment of step.segments) {
      if (segment.html) segment.html = sanitize(segment.html);
      if (segment.options) {
        for (const option of segment.options) option.html = sanitize(option.html);
      }
    }
  }
  return activity;
}

/* ------------------------------------------------------------------ datos */
async function snapshot() {
  const [answers, states, files, meta] = await Promise.all([
    state.store.allAnswers(),
    state.store.allStates(),
    state.store.allFiles(),
    state.store.getMeta(),
  ]);
  return { answers, states, files, meta };
}

async function refreshProgress() {
  const { answers, states, files } = await snapshot();
  state.progress = computeProgress(state.activity, answers, states, files);
  updateShellProgress();
}

/* ------------------------------------------------------------- exportación */
async function exportWork() {
  const data = await snapshot();
  if (!data.meta?.student) {
    toast("Todavía no hay trabajo que exportar.", "error");
    return;
  }
  try {
    const blob = await buildAulawork({
      activity: state.activity.activity,
      schemaVersion: state.activity.schemaVersion,
      generator: state.activity.generator,
      meta: data.meta,
      answers: data.answers,
      states: data.states,
      files: data.files,
    });
    const maxBytes = state.activity.limites.tamano_maximo_paquete_mb * 1024 * 1024;
    if (blob.size > maxBytes) {
      toast(`El paquete supera ${state.activity.limites.tamano_maximo_paquete_mb} MB; reduce adjuntos o capturas.`, "error");
      return;
    }
    const filename = buildExportFilename(
      state.activity.trabajo.patron_nombre,
      state.activity.activity,
      data.meta.student
    );
    downloadBlob(blob, filename);
    toast("Trabajo exportado. Guarda el archivo y entrégalo.", "success");
  } catch (error) {
    console.error(error);
    toast("No se pudo exportar el trabajo.", "error");
  }
}

async function importWorkFlow(afterImport) {
  const file = await pickFile(`.${state.activity.trabajo.extension},application/zip`);
  if (!file) return;
  try {
    const parsed = await parseAulawork(file, {
      activity: state.activity.activity,
      schemaVersion: state.activity.schemaVersion,
      limits: state.activity.limites,
    });
    if (parsed.warnings.length) {
      const proceed = await openModal({
        title: "Avisos de importación",
        body: el("ul", {}, ...parsed.warnings.map((w) => el("li", { text: w }))),
        actions: [
          { label: "Cancelar", value: false },
          { label: "Importar igualmente", value: true, class: "btn-primary" },
        ],
      });
      if (proceed !== true) return;
    }
    const existing = await state.store.getMeta();
    if (existing?.student) {
      const overwrite = await confirmModal(
        "Sustituir el trabajo local",
        "Ya hay trabajo guardado en este navegador. Importar lo sustituirá por completo.",
        "Sustituir"
      );
      if (!overwrite) return;
    }
    const orphans = await restoreWork(state.store, parsed, state.knownIds);
    if (orphans.length) {
      toast(`Importado con ${orphans.length} respuestas de una versión anterior conservadas aparte.`, "info", 5000);
    } else {
      toast("Trabajo importado correctamente.", "success");
    }
    afterImport();
  } catch (error) {
    if (error instanceof ImportError) {
      openModal({
        title: "No se puede importar",
        body: el("p", { text: error.message }),
        actions: [{ label: "Entendido", value: true, class: "btn-primary" }],
      });
    } else {
      console.error(error);
      toast("Error inesperado al importar el paquete.", "error");
    }
  }
}

/* ----------------------------------------------------------------- licencia */
function licenseIntro(activity) {
  const lic = activity.licencia;
  const autor = activity.autor ? ` por ${activity.autor}` : "";
  return `Esta actividad ha sido creada${autor} y se distribuye bajo la licencia ${lic.nombre_completo} — ${lic.nombre}.`;
}

function licenseBlock(activity) {
  const lic = activity.licencia;
  if (!lic) return null;
  const body = el(
    "div",
    { class: "as-details-body" },
    el("p", { text: licenseIntro(activity) })
  );
  if (lic.condiciones?.length) {
    body.append(
      el("p", { text: "Se permite copiar, distribuir y adaptar este material siempre que:" }),
      el("ul", {}, ...lic.condiciones.map((c) => el("li", { text: c })))
    );
  }
  body.append(
    el(
      "p",
      {},
      document.createTextNode("Más información sobre la licencia: "),
      el("a", { href: lic.url, target: "_blank", rel: "noopener noreferrer license", text: lic.url })
    )
  );
  const details = el(
    "details",
    { class: "as-details license-block" },
    el("summary", { text: `Licencia · ${lic.nombre}` }),
    body
  );
  return details;
}

function licenseFooter(activity) {
  const lic = activity.licencia;
  if (!lic) return null;
  return el(
    "footer",
    { class: "license-footer" },
    document.createTextNode(`${activity.autor ? "© " + activity.autor + " · " : ""}Licencia `),
    el("a", { href: lic.url, target: "_blank", rel: "noopener noreferrer license", text: lic.nombre })
  );
}

/* -------------------------------------------------------- pantalla inicio */
function metaItem(label, value) {
  if (!value) return null;
  return el("div", { class: "meta-item" }, el("dt", { text: label }), el("dd", { text: String(value) }));
}

async function showStart() {
  const activity = state.activity.activity;
  const existing = await state.store.getMeta();
  const actions = el("div", { class: "start-actions" });

  if (existing?.student) {
    const who = Object.values(existing.student).filter(Boolean).join(" · ");
    actions.append(
      el("button", {
        class: "btn btn-primary", type: "button",
        text: "Continuar mi trabajo",
        onclick: () => enterShell(existing.currentStepId),
      }),
      el("p", { class: "resume-hint", text: `Trabajo local de ${who} · último guardado ${formatDate(existing.updatedAt)}` })
    );
  } else {
    actions.append(
      el("button", {
        class: "btn btn-primary", type: "button", text: "Empezar la actividad",
        onclick: showStudentForm,
      })
    );
  }
  if (state.activity.trabajo.permitir_importar) {
    actions.append(
      el("button", {
        class: "btn btn-secondary", type: "button",
        text: `Importar un trabajo (.${state.activity.trabajo.extension})`,
        onclick: () => importWorkFlow(() => enterShell()),
      })
    );
  }
  if (existing?.student) {
    actions.append(
      el("button", {
        class: "btn btn-ghost", type: "button", text: "Vaciar y empezar de cero",
        onclick: async () => {
          const sure = await confirmModal(
            "Vaciar el trabajo local",
            "Se borrarán todas las respuestas, capturas y adjuntos guardados en este navegador. Exporta antes una copia si la necesitas.",
            "Vaciar todo"
          );
          if (sure) {
            await state.store.clearAll();
            toast("Trabajo local eliminado.");
            showStart();
          }
        },
      })
    );
  }

  appRoot.replaceChildren(
    el(
      "div",
      { class: "start-screen" },
      el(
        "main",
        { class: "start-card" },
        el("div", { class: "brand-line" }, el("span", { text: LOGO }), el("span", { text: `v${activity.version}` })),
        el("h1", { text: activity.titulo }),
        activity.subtitulo ? el("p", { class: "start-sub", text: activity.subtitulo }) : null,
        activity.descripcion ? el("p", { class: "start-desc", text: activity.descripcion }) : null,
        el(
          "dl",
          { class: "meta-grid" },
          metaItem("Módulo", activity.modulo),
          metaItem("Curso", activity.curso),
          metaItem("Duración", activity.duracionMinutos ? `${activity.duracionMinutos} min` : ""),
          metaItem("Pasos", state.activity.steps.length),
          metaItem("Autoría", activity.autor),
          metaItem("Licencia", activity.licencia?.nombre)
        ),
        actions,
        licenseBlock(activity)
      )
    )
  );
}

function showStudentForm() {
  const fields = state.activity.alumno.campos;
  const form = el("form", { class: "student-form", novalidate: true });
  const inputs = new Map();
  for (const field of fields) {
    const input = el("input", { class: "input", type: "text", id: `sf-${field.id}`, autocomplete: "off" });
    inputs.set(field.id, input);
    form.append(
      el(
        "div",
        { class: "field" },
        el("label", { for: `sf-${field.id}` },
          document.createTextNode(field.etiqueta),
          field.obligatorio ? el("span", { class: "req", text: " *", "aria-hidden": "true" }) : null),
        input,
        el("p", { class: "field-error", id: `sf-${field.id}-err`, hidden: true })
      )
    );
  }
  const submit = el("button", { class: "btn btn-primary", type: "submit", text: "Comenzar" });
  form.append(el("div", { class: "start-actions" }, submit,
    el("button", { class: "btn btn-ghost", type: "button", text: "Volver", onclick: showStart })));

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    let valid = true;
    const student = {};
    for (const field of fields) {
      const input = inputs.get(field.id);
      const error = document.getElementById(`sf-${field.id}-err`);
      const value = input.value.trim();
      if (field.obligatorio && !value) {
        valid = false;
        input.setAttribute("aria-invalid", "true");
        error.textContent = "Este campo es obligatorio.";
        error.hidden = false;
      } else {
        input.removeAttribute("aria-invalid");
        error.hidden = true;
        student[field.id] = value;
      }
    }
    if (!valid) return;
    await state.store.setMeta({
      student,
      startedAt: new Date().toISOString(),
      currentStepId: state.activity.steps[0].id,
      activityVersion: state.activity.activity.version,
    });
    enterShell(state.activity.steps[0].id);
  });

  appRoot.replaceChildren(
    el(
      "div",
      { class: "start-screen" },
      el(
        "main",
        { class: "start-card" },
        el("div", { class: "brand-line" }, el("span", { text: LOGO })),
        el("h1", { text: "Antes de empezar" }),
        el("p", { class: "start-desc", text: "Identifícate para que tu trabajo quede asociado a tu nombre al exportarlo." }),
        form
      )
    )
  );
  const first = form.querySelector("input");
  if (first) first.focus();
}

/* ------------------------------------------------------------------ shell */
let shellRefs = null;

async function enterShell(startStepId) {
  const meta = await state.store.getMeta();
  const activity = state.activity.activity;

  // Tema: preferencia del alumno > tema de la actividad.
  applyTheme(meta?.theme || activity.tema);

  const saveStatus = el("span", { class: "save-status", role: "status" },
    el("span", { class: "dot", "aria-hidden": "true" }),
    el("span", { class: "save-label", text: "Guardado" }));
  state.saveIndicator?.dispose();
  state.saveIndicator = new SaveIndicator(saveStatus, state.store);

  const themeSelect = el("select", { class: "input theme-select", "aria-label": "Tema visual" },
    ...THEMES.map(([value, label]) => el("option", { value, text: label })));
  themeSelect.value = document.documentElement.dataset.theme;
  themeSelect.addEventListener("change", async () => {
    applyTheme(themeSelect.value);
    await state.store.setMeta({ theme: themeSelect.value });
  });

  const topbarButtons = [];
  if (state.activity.trabajo.permitir_exportar) {
    topbarButtons.push(el("button", { class: "btn btn-secondary btn-sm", type: "button", text: "Guardar copia", onclick: exportWork }));
  }
  if (state.activity.trabajo.permitir_importar) {
    topbarButtons.push(el("button", {
      class: "btn btn-ghost btn-sm", type: "button", text: "Importar",
      onclick: () => importWorkFlow(() => enterShell()),
    }));
  }

  const progressBar = el("div", { class: "progressbar", role: "progressbar", "aria-label": "Progreso de la actividad", "aria-valuemin": "0", "aria-valuemax": "100" }, el("span"));
  const railHost = el("div");
  const main = el("main", { class: "step-main", id: "contenido", tabindex: "-1" });

  appRoot.replaceChildren(
    el(
      "div",
      { class: "shell" },
      el(
        "header",
        { class: "topbar" },
        el("span", { class: "logo", text: LOGO }),
        el("span", { class: "activity-title", text: activity.titulo }),
        el("span", { class: "spacer" }),
        el("span", { class: "student-chip", text: Object.values(meta?.student || {}).filter(Boolean).join(" · ") }),
        saveStatus,
        themeSelect,
        ...topbarButtons
      ),
      progressBar,
      el("div", { class: "layout" }, railHost, main),
      licenseFooter(activity)
    )
  );

  shellRefs = { progressBar, railHost, main };

  state.policy = new NavPolicy(state.activity.navegacion);
  state.router?.dispose();
  state.router = new Router(state.activity);
  state.router.addEventListener("navigate", (event) => renderStep(event.detail.stepId));

  await refreshProgress();
  const target = startStepId || meta?.currentStepId || state.activity.steps[0].id;
  // go() renderiza exactamente una vez: emite en síncrono si el hash ya es el
  // destino, o vía hashchange si lo cambia. No repetir el render aquí.
  state.router.go(target);
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
}

function updateShellProgress() {
  if (!shellRefs || !state.progress) return;
  const percent = state.progress.percent;
  shellRefs.progressBar.querySelector("span").style.width = `${percent}%`;
  shellRefs.progressBar.setAttribute("aria-valuenow", String(percent));
  if (!state.activity.navegacion.mostrar_progreso) shellRefs.progressBar.hidden = true;
  renderRailNow();
  const pill = shellRefs.main.querySelector(".pending-pill");
  if (pill) paintPendingPill(pill);
  const summary = shellRefs.main.querySelector(".summary-card");
  if (summary) renderSummaryInto(summary);
}

function renderRailNow() {
  if (!state.activity.navegacion.mostrar_indice) {
    shellRefs.railHost.replaceChildren();
    return;
  }
  const currentId = state.router.currentStepId();
  const rail = renderRail(state.activity, currentId, state.progress, state.policy, (stepId) => {
    state.router.go(stepId);
  });
  shellRefs.railHost.replaceChildren(rail);
}

/* ------------------------------------------------------------- paso actual */
async function renderStep(stepId) {
  const index = state.activity.steps.findIndex((s) => s.id === stepId);
  const step = state.activity.steps[index];
  if (!step) return;
  state.policy.visit(index);
  await state.store.setMeta({ currentStepId: stepId });
  await refreshProgress();

  const ctx = {
    store: state.store,
    limits: state.activity.limites,
    debounced: (fn) => autosaveDebounce(fn, state.activity.trabajo.intervalo_autoguardado_segundos * 1000),
    onProgress: refreshProgress,
  };

  const head = el(
    "header",
    { class: "step-head" },
    el("p", { class: "step-eyebrow", text: `Paso ${index + 1} de ${state.activity.steps.length}` }),
    el("h1", { tabindex: "-1", text: step.titulo }),
    step.descripcion ? el("p", { class: "step-desc", text: step.descripcion }) : null,
    step.duracionMinutos ? el("p", { class: "step-duration", text: `Duración estimada: ${step.duracionMinutos} min` }) : null
  );

  const body = el("div");
  for (const segment of step.segments) {
    body.append(renderSegment(segment, ctx));
  }

  const isLast = index === state.activity.steps.length - 1;
  if (isLast) {
    const summary = el("section", { class: "summary-card", "aria-label": "Resumen del trabajo" });
    renderSummaryInto(summary);
    body.append(summary);
  }

  shellRefs.main.replaceChildren(head, body, renderStepNav(index));
  enhanceCodeBlocks(shellRefs.main);
  enhanceSolutions(shellRefs.main);
  bindStepLinks(shellRefs.main);
  shellRefs.main.querySelector("h1").focus({ preventScroll: true });
  window.scrollTo({ top: 0 });
  renderRailNow();
}

function bindStepLinks(root) {
  for (const link of root.querySelectorAll("a[data-step-link]")) {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const target = link.dataset.stepLink;
      const currentIndex = state.activity.steps.findIndex((s) => s.id === state.router.currentStepId());
      const targetIndex = state.activity.steps.findIndex((s) => s.id === target);
      if (targetIndex === -1) return;
      if (state.policy.canJump(currentIndex, targetIndex, state.progress.steps)) {
        state.router.go(target);
      } else {
        toast("Completa antes los pasos anteriores.", "error");
      }
    });
  }
}

function paintPendingPill(pill) {
  const stepId = state.router.currentStepId();
  const stepProgress = state.progress.steps.find((s) => s.id === stepId);
  if (!stepProgress || stepProgress.requiredTotal === 0) {
    pill.hidden = true;
    return;
  }
  pill.hidden = false;
  const pending = stepProgress.requiredPending.length;
  pill.classList.toggle("all-done", pending === 0);
  pill.textContent = pending === 0
    ? "✓ Paso completado"
    : `${pending} obligatorio${pending > 1 ? "s" : ""} pendiente${pending > 1 ? "s" : ""}`;
}

function renderStepNav(index) {
  const steps = state.activity.steps;
  const nav = el("nav", { class: "step-nav", "aria-label": "Navegación entre pasos" });

  const previous = el("button", {
    class: "btn btn-secondary", type: "button", text: "← Anterior",
    disabled: index === 0 || state.activity.navegacion.permitir_anterior === false,
    onclick: () => state.router.go(steps[index - 1].id),
  });

  const pill = el("button", {
    class: "pending-pill", type: "button", hidden: true,
    onclick: () => {
      const stepProgress = state.progress.steps[index];
      const first = stepProgress?.requiredPending[0];
      if (first) {
        const target = document.getElementById(`item-${first.id}`);
        if (target) { target.scrollIntoView({ behavior: "smooth", block: "center" }); target.querySelector("input, textarea, [tabindex]")?.focus(); }
      }
    },
  });
  paintPendingPill(pill);

  nav.append(previous, pill, el("span", { class: "spacer" }));

  if (index < steps.length - 1) {
    const next = el("button", {
      class: "btn btn-primary", type: "button", text: "Siguiente →",
      onclick: () => {
        if (!state.policy.canAdvance(index, state.progress.steps)) {
          toast("Completa los elementos obligatorios de este paso para avanzar.", "error");
          return;
        }
        state.router.go(steps[index + 1].id);
      },
    });
    nav.append(next);
  }
  return nav;
}

/* ---------------------------------------------------------------- resumen */
function renderSummaryInto(container) {
  const progress = state.progress;
  if (!progress) return;
  container.replaceChildren(
    el("h2", { text: "Resumen de tu trabajo" }),
    el(
      "div",
      { class: "summary-grid" },
      summaryStat(`${progress.percent}%`, "obligatorio completado"),
      summaryStat(`${progress.doneItems}/${progress.totalItems}`, "elementos realizados"),
      summaryStat(String(progress.steps.filter((s) => s.complete && s.requiredTotal > 0).length), "pasos completos")
    )
  );
  const pendingSteps = progress.steps.filter((s) => s.requiredPending.length > 0);
  if (pendingSteps.length) {
    container.append(el("h3", { text: "Pendiente antes de entregar" }));
    const list = el("ul", { class: "pending-list" });
    for (const step of pendingSteps) {
      list.append(
        el(
          "li",
          {},
          el("button", { type: "button", text: step.titulo, onclick: () => state.router.go(step.id) }),
          document.createTextNode(` — ${step.requiredPending.length} obligatorio${step.requiredPending.length > 1 ? "s" : ""}`)
        )
      );
    }
    container.append(list);
  } else {
    container.append(el("p", { text: "No queda nada obligatorio pendiente. Ya puedes entregar tu trabajo." }));
  }
  if (state.activity.trabajo.permitir_exportar) {
    container.append(
      el(
        "div",
        { class: "summary-export" },
        el("button", { class: "btn btn-primary", type: "button", text: "Exportar trabajo para entregar", onclick: exportWork }),
        el("span", { class: "step-duration", text: `Se descargará un archivo .${state.activity.trabajo.extension} con todas tus respuestas y capturas.` })
      )
    );
  }
}

function summaryStat(number, label) {
  return el("div", { class: "summary-stat" }, el("div", { class: "num", text: number }), el("div", { class: "lbl", text: label }));
}

/* ------------------------------------------------------------------- boot */
async function boot() {
  try {
    const response = await fetch("activity.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.activity = sanitizeActivity(await response.json());
  } catch (error) {
    console.error(error);
    appRoot.replaceChildren(
      el("div", { class: "boot" }, el("p", { text: "No se pudo cargar la actividad (activity.json). Si abres el archivo directamente, usa un servidor local o publícalo en GitHub Pages." }))
    );
    return;
  }
  state.knownIds = allInteractiveIds(state.activity);
  state.store = await Store.open(state.activity.activity.id);
  const meta = await state.store.getMeta();
  applyTheme(meta?.theme || state.activity.activity.tema);
  showStart();
}

boot();
