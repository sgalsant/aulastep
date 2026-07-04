/* Pruebas del módulo de persistencia (storage.js) sobre fake-indexeddb. */
import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it } from "vitest";

import { Store, autosaveDebounce } from "../../src/aulastep/player/assets/storage.js";

let store;
let counter = 0;

beforeEach(async () => {
  counter += 1;
  store = await Store.open(`test-${Date.now()}-${counter}`);
});

describe("Store", () => {
  it("guarda y recupera respuestas", async () => {
    await store.setAnswer("q1", "hola", "short-text");
    const record = await store.getAnswer("q1");
    expect(record.value).toBe("hola");
    expect(record.type).toBe("short-text");
    expect(record.updatedAt).toBeTruthy();
  });

  it("guarda estados de tareas y checkpoints", async () => {
    await store.setState("t1", true);
    expect((await store.getState("t1")).done).toBe(true);
    await store.setState("t1", false);
    expect((await store.getState("t1")).done).toBe(false);
  });

  it("fusiona parches de metadatos", async () => {
    await store.setMeta({ student: { nombre: "Ana" } });
    await store.setMeta({ currentStepId: "paso-2" });
    const meta = await store.getMeta();
    expect(meta.student.nombre).toBe("Ana");
    expect(meta.currentStepId).toBe("paso-2");
    expect(meta.updatedAt).toBeTruthy();
  });

  it("guarda blobs de archivos y los lista", async () => {
    const blob = new Blob(["contenido"], { type: "text/plain" });
    await store.setFile("ev1", { kind: "evidence", name: "captura.png", mime: "image/png", size: 9, blob });
    const all = await store.allFiles();
    expect(all.size).toBe(1);
    expect(all.get("ev1").name).toBe("captura.png");
  });

  it("clearAll vacía todos los almacenes", async () => {
    await store.setAnswer("q1", "x", "short-text");
    await store.setState("t1", true);
    await store.setMeta({ student: { nombre: "Ana" } });
    await store.clearAll();
    expect(await store.getAnswer("q1")).toBeUndefined();
    expect(await store.getState("t1")).toBeUndefined();
    expect(await store.getMeta()).toBeUndefined();
  });

  it("emite eventos de guardado", async () => {
    const events = [];
    store.addEventListener("save:start", () => events.push("start"));
    store.addEventListener("save:ok", () => events.push("ok"));
    await store.setAnswer("q1", "x", "short-text");
    expect(events).toEqual(["start", "ok"]);
  });
});

describe("autosaveDebounce", () => {
  it("agrupa escrituras seguidas y garantiza el vaciado", async () => {
    let calls = 0;
    const save = autosaveDebounce(() => { calls += 1; }, 50);
    save(); // primera: inmediata (ha pasado el intervalo desde last=0)
    save();
    save();
    expect(calls).toBe(1);
    await new Promise((r) => setTimeout(r, 700));
    expect(calls).toBe(2); // el vaciado pendiente se ejecutó
  });
});
