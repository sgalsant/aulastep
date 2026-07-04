/* AulaStep · navigation.js
   Router por hash (#/paso/<id>), raíl de pasos, cómputo de progreso y
   modos de navegación. Nunca se impide volver a pasos anteriores. */

import { el } from "./ui.js";

const INTERACTIVE = new Set(["task", "question", "evidence", "file", "reflection", "checkpoint"]);

export function interactiveItems(step) {
  return step.segments.filter((s) => INTERACTIVE.has(s.type));
}

export function allInteractiveIds(activity) {
  const ids = new Set();
  for (const step of activity.steps) {
    for (const item of interactiveItems(step)) ids.add(item.id);
  }
  return ids;
}

function itemDone(item, answers, states, files) {
  if (item.type === "task" || item.type === "checkpoint") return !!states.get(item.id)?.done;
  if (item.type === "evidence" || item.type === "file") return !!files.get(item.id);
  const value = answers.get(item.id)?.value;
  if (Array.isArray(value)) return value.length > 0;
  return value !== undefined && value !== null && String(value).trim() !== "";
}

/* Devuelve el estado de progreso completo de la actividad. */
export function computeProgress(activity, answers, states, files) {
  const steps = activity.steps.map((step) => {
    const items = interactiveItems(step).map((item) => ({
      id: item.id,
      type: item.type,
      required: !!item.required,
      done: itemDone(item, answers, states, files),
    }));
    const required = items.filter((i) => i.required);
    const requiredPending = required.filter((i) => !i.done);
    return {
      id: step.id,
      titulo: step.titulo,
      items,
      requiredTotal: required.length,
      requiredDone: required.length - requiredPending.length,
      requiredPending,
      complete: requiredPending.length === 0,
    };
  });
  const totalRequired = steps.reduce((n, s) => n + s.requiredTotal, 0);
  const doneRequired = steps.reduce((n, s) => n + s.requiredDone, 0);
  const totalItems = steps.reduce((n, s) => n + s.items.length, 0);
  const doneItems = steps.reduce((n, s) => n + s.items.filter((i) => i.done).length, 0);
  return {
    steps,
    totalRequired,
    doneRequired,
    totalItems,
    doneItems,
    percent: totalRequired === 0
      ? (totalItems === 0 ? 100 : Math.round((doneItems / totalItems) * 100))
      : Math.round((doneRequired / totalRequired) * 100),
  };
}

/* -------------------------------------------------------------- router */
export class Router extends EventTarget {
  constructor(activity) {
    super();
    this.activity = activity;
    this.index = new Map(activity.steps.map((s, i) => [s.id, i]));
    this._onHashChange = () => this._emit();
    window.addEventListener("hashchange", this._onHashChange);
  }

  /* Retira el listener global. Imprescindible antes de crear otro Router
     (p. ej. al reconstruir el shell tras importar un trabajo). */
  dispose() {
    window.removeEventListener("hashchange", this._onHashChange);
  }

  currentStepId() {
    const match = location.hash.match(/^#\/paso\/([a-z0-9-]+)$/);
    if (match && this.index.has(match[1])) return match[1];
    return this.activity.steps[0]?.id || null;
  }

  go(stepId) {
    if (!this.index.has(stepId)) return;
    if (this.currentStepId() === stepId) this._emit();
    else location.hash = `#/paso/${stepId}`;
  }

  _emit() {
    this.dispatchEvent(new CustomEvent("navigate", { detail: { stepId: this.currentStepId() } }));
  }
}

/* ------------------------------------------------------- política de modos */
export class NavPolicy {
  constructor(navConfig) {
    this.config = navConfig;
    this.maxVisitedIndex = 0;
  }

  visit(index) {
    this.maxVisitedIndex = Math.max(this.maxVisitedIndex, index);
  }

  /* ¿Puede saltarse desde el índice actual a `target` mediante el raíl? */
  canJump(currentIndex, targetIndex, progressSteps) {
    if (targetIndex <= currentIndex) return true; // volver atrás, siempre
    const mode = this.config.modo;
    if (mode === "libre") return true;
    if (mode === "asistente") return this.config.permitir_saltar !== false;
    // secuencial: solo hasta el paso siguiente al más avanzado ya visitado
    if (targetIndex <= this.maxVisitedIndex + 1) {
      return this._forwardAllowed(targetIndex - 1, progressSteps);
    }
    return false;
  }

  /* ¿Puede pulsarse «Siguiente» estando en `currentIndex`? */
  canAdvance(currentIndex, progressSteps) {
    return this._forwardAllowed(currentIndex, progressSteps);
  }

  _forwardAllowed(fromIndex, progressSteps) {
    if (!this.config.exigir_obligatorios_para_avanzar) return true;
    return progressSteps[fromIndex]?.complete !== false;
  }
}

/* ---------------------------------------------------------------- raíl UI */
export function renderRail(activity, currentId, progress, policy, onSelect) {
  const currentIndex = activity.steps.findIndex((s) => s.id === currentId);
  const list = el("ol");
  activity.steps.forEach((step, index) => {
    const stepProgress = progress.steps[index];
    const status = step.id === currentId ? "current" : stepProgress.complete && stepProgress.requiredTotal > 0 ? "done" : "todo";
    const allowed = policy.canJump(currentIndex, index, progress.steps);
    const node = el("span", { class: "rail-node", "aria-hidden": "true", text: status === "done" ? "✓" : String(index + 1) });
    const button = el(
      "button",
      {
        class: "rail-link",
        type: "button",
        disabled: !allowed,
        "aria-current": step.id === currentId ? "step" : undefined,
        title: allowed ? step.titulo : "Completa antes los pasos anteriores",
        onclick: () => onSelect(step.id),
      },
      node,
      el(
        "span",
        { class: "rail-label" },
        document.createTextNode(step.titulo),
        stepProgress.requiredTotal > 0 && !stepProgress.complete
          ? el("span", { class: "rail-req", "aria-label": `${stepProgress.requiredPending.length} obligatorios pendientes`, text: ` (${stepProgress.requiredDone}/${stepProgress.requiredTotal})` })
          : null
      )
    );
    list.append(el("li", { class: "rail-item", dataset: { status } }, button));
  });
  const nav = el("nav", { class: "step-rail", "aria-label": "Índice de pasos" }, el("h2", { text: "Pasos" }), list);
  return nav;
}
