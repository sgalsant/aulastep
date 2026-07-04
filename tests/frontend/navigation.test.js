/* Pruebas puras de navigation.js: progreso y política de modos. */
import { describe, expect, it } from "vitest";

import { NavPolicy, computeProgress } from "../../src/aulastep/player/assets/navigation.js";

const ACTIVITY = {
  steps: [
    {
      id: "uno", titulo: "Uno",
      segments: [
        { type: "html", html: "<p>hola</p>" },
        { type: "task", id: "t1", required: true },
        { type: "question", id: "q1", required: true, questionType: "short-text" },
        { type: "question", id: "q-opcional", required: false, questionType: "long-text" },
      ],
    },
    {
      id: "dos", titulo: "Dos",
      segments: [
        { type: "evidence", id: "ev1", required: true },
        { type: "checkpoint", id: "c1", required: true },
      ],
    },
    { id: "tres", titulo: "Tres", segments: [{ type: "html", html: "<p>fin</p>" }] },
  ],
};

const maps = ({ answers = {}, states = {}, files = {} } = {}) => [
  new Map(Object.entries(answers)),
  new Map(Object.entries(states)),
  new Map(Object.entries(files)),
];

describe("computeProgress", () => {
  it("con todo vacío no hay nada completado", () => {
    const progress = computeProgress(ACTIVITY, ...maps());
    expect(progress.totalRequired).toBe(4);
    expect(progress.doneRequired).toBe(0);
    expect(progress.percent).toBe(0);
    expect(progress.steps[0].requiredPending.map((i) => i.id)).toEqual(["t1", "q1"]);
  });

  it("las respuestas en blanco no cuentan", () => {
    const progress = computeProgress(ACTIVITY, ...maps({ answers: { q1: { value: "   " } } }));
    expect(progress.steps[0].requiredDone).toBe(0);
  });

  it("suma tareas, respuestas, evidencias y checkpoints", () => {
    const progress = computeProgress(ACTIVITY, ...maps({
      answers: { q1: { value: "UDP 67" } },
      states: { t1: { done: true }, c1: { done: true } },
      files: { ev1: { name: "x.png" } },
    }));
    expect(progress.doneRequired).toBe(4);
    expect(progress.percent).toBe(100);
    expect(progress.steps[0].complete).toBe(true);
    expect(progress.steps[1].complete).toBe(true);
  });

  it("las opciones múltiples vacías no cuentan", () => {
    const withMulti = {
      steps: [{ id: "s", titulo: "S", segments: [{ type: "question", id: "m", required: true, questionType: "multi-choice" }] }],
    };
    expect(computeProgress(withMulti, ...maps({ answers: { m: { value: [] } } })).doneRequired).toBe(0);
    expect(computeProgress(withMulti, ...maps({ answers: { m: { value: ["a"] } } })).doneRequired).toBe(1);
  });
});

describe("NavPolicy", () => {
  const progressAllPending = computeProgress(ACTIVITY, ...maps()).steps;
  const progressAllDone = computeProgress(ACTIVITY, ...maps({
    answers: { q1: { value: "x" } },
    states: { t1: { done: true }, c1: { done: true } },
    files: { ev1: { name: "x.png" } },
  })).steps;

  it("siempre permite volver atrás en cualquier modo", () => {
    for (const modo of ["libre", "asistente", "secuencial"]) {
      const policy = new NavPolicy({ modo, exigir_obligatorios_para_avanzar: true });
      expect(policy.canJump(2, 0, progressAllPending)).toBe(true);
    }
  });

  it("modo libre permite saltar a cualquier paso", () => {
    const policy = new NavPolicy({ modo: "libre" });
    expect(policy.canJump(0, 2, progressAllPending)).toBe(true);
  });

  it("modo secuencial limita los saltos hacia delante", () => {
    const policy = new NavPolicy({ modo: "secuencial" });
    policy.visit(0);
    expect(policy.canJump(0, 1, progressAllPending)).toBe(true);
    expect(policy.canJump(0, 2, progressAllPending)).toBe(false);
    policy.visit(1);
    expect(policy.canJump(1, 2, progressAllPending)).toBe(true);
  });

  it("exigir obligatorios bloquea Siguiente hasta completar", () => {
    const policy = new NavPolicy({ modo: "asistente", exigir_obligatorios_para_avanzar: true });
    expect(policy.canAdvance(0, progressAllPending)).toBe(false);
    expect(policy.canAdvance(0, progressAllDone)).toBe(true);
  });
});

describe("Router (ciclo de vida)", () => {
  async function withDomStubs(fn) {
    const prevWindow = globalThis.window;
    const prevLocation = globalThis.location;
    globalThis.window = new EventTarget();
    globalThis.location = { hash: "" };
    try {
      return await fn();
    } finally {
      globalThis.window = prevWindow;
      globalThis.location = prevLocation;
    }
  }

  it("dispose retira el listener de hashchange", async () => {
    await withDomStubs(async () => {
      const { Router } = await import("../../src/aulastep/player/assets/navigation.js");
      const router = new Router(ACTIVITY);
      let emitted = 0;
      router.addEventListener("navigate", () => { emitted += 1; });
      globalThis.location.hash = "#/paso/dos";
      globalThis.window.dispatchEvent(new Event("hashchange"));
      expect(emitted).toBe(1);
      router.dispose();
      globalThis.window.dispatchEvent(new Event("hashchange"));
      expect(emitted).toBe(1); // sin dispose seguiría contando
    });
  });

  it("reconstruir el shell no duplica renders si se desmonta el router anterior", async () => {
    await withDomStubs(async () => {
      const { Router } = await import("../../src/aulastep/player/assets/navigation.js");
      let renders = 0;
      const onNavigate = () => { renders += 1; };
      // Simula el patrón de enterShell(): desmontar antes de recrear.
      let router = new Router(ACTIVITY);
      router.addEventListener("navigate", onNavigate);
      router.dispose();
      router = new Router(ACTIVITY);
      router.addEventListener("navigate", onNavigate);
      globalThis.window.dispatchEvent(new Event("hashchange"));
      expect(renders).toBe(1); // con el bug de acumulación serían 2
    });
  });
});
