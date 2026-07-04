/* Pruebas del formato .aulawork (import-export.js): integridad y compatibilidad. */
import "fake-indexeddb/auto";
import JSZip from "jszip";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";

import {
  ImportError,
  buildAulawork,
  buildExportFilename,
  parseAulawork,
  restoreWork,
} from "../../src/aulastep/player/assets/import-export.js";
import { Store } from "../../src/aulastep/player/assets/storage.js";

beforeAll(() => {
  globalThis.JSZip = JSZip; // en el navegador lo aporta el vendor
});

const ACTIVITY = { id: "dhcp-kea-ubuntu", version: "1.0.0", titulo: "DHCP con Kea" };
const LIMITS = { tamano_maximo_captura_mb: 8, tamano_maximo_adjunto_mb: 20, tamano_maximo_paquete_mb: 100 };
const CTX = { activity: ACTIVITY, schemaVersion: "1.0", limits: LIMITS };

function sampleData() {
  const answers = new Map([
    ["q1", { value: "UDP 67", type: "short-text", updatedAt: "2026-07-02T10:00:00Z" }],
    ["q2", { value: ["a", "b"], type: "multi-choice", updatedAt: "2026-07-02T10:01:00Z" }],
  ]);
  const states = new Map([["t1", { done: true, updatedAt: "2026-07-02T10:02:00Z" }]]);
  const files = new Map([
    ["ev1", {
      kind: "evidence", name: "captura.png", mime: "image/png", size: 4,
      description: "IP del servidor", blob: new Blob([new Uint8Array([1, 2, 3, 4])], { type: "image/png" }),
    }],
    ["adj1", {
      kind: "file", name: "kea.conf", mime: "text/plain", size: 5,
      blob: new Blob(["hola!"], { type: "text/plain" }),
    }],
  ]);
  const meta = {
    student: { nombre: "Ana Pérez", grupo: "2A" },
    currentStepId: "prueba-cliente",
    startedAt: "2026-07-02T09:00:00Z",
    updatedAt: "2026-07-02T10:05:00Z",
  };
  return { meta, answers, states, files };
}

async function buildSample() {
  const data = sampleData();
  return buildAulawork({
    activity: ACTIVITY,
    schemaVersion: "1.0",
    generator: { name: "AulaStep", version: "0.1.0" },
    ...data,
  });
}

describe("exportación", () => {
  it("genera un ZIP con manifiesto e integridad SHA-256", async () => {
    const blob = await buildSample();
    const zip = await JSZip.loadAsync(await blob.arrayBuffer());
    const manifest = JSON.parse(await zip.file("manifest.json").async("string"));
    expect(manifest.format).toBe("aulawork");
    expect(manifest.activity.id).toBe(ACTIVITY.id);
    expect(manifest.integrity.algorithm).toBe("SHA-256");
    expect(Object.keys(manifest.integrity.files)).toContain("answers.json");
    expect(Object.keys(manifest.integrity.files).some((k) => k.startsWith("evidence/ev1__"))).toBe(true);
    expect(zip.file("student.json")).toBeTruthy();
    expect(zip.file("progress.json")).toBeTruthy();
  });

  it("construye el nombre de archivo con el patrón", () => {
    const name = buildExportFilename("{actividad}_{alumno}_{fecha}.aulawork", ACTIVITY, { nombre: "Ana Pérez" });
    expect(name).toMatch(/^dhcp-kea-ubuntu_Ana-P.*_\d{4}-\d{2}-\d{2}\.aulawork$/);
  });
});

describe("importación", () => {
  it("acepta un paquete válido (ida y vuelta)", async () => {
    const parsed = await parseAulawork(await buildSample(), CTX);
    expect(parsed.warnings).toEqual([]);
    expect(parsed.answers.q1.value).toBe("UDP 67");
    expect(parsed.progress.states.t1.done).toBe(true);
    expect(parsed.files).toHaveLength(2);
    expect(parsed.student.nombre).toBe("Ana Pérez");
  });

  it("rechaza paquetes alterados (integridad)", async () => {
    const zip = await JSZip.loadAsync(await (await buildSample()).arrayBuffer());
    zip.file("answers.json", JSON.stringify({ q1: { value: "MANIPULADA" } }));
    const tampered = await zip.generateAsync({ type: "blob" });
    await expect(parseAulawork(tampered, CTX)).rejects.toThrow(/integridad/);
  });

  it("rechaza trabajos de otra actividad", async () => {
    const parsedPromise = parseAulawork(await buildSample(), {
      ...CTX, activity: { id: "otra-actividad", version: "1.0.0" },
    });
    await expect(parsedPromise).rejects.toThrow(ImportError);
    await expect(parseAulawork(await buildSample(), { ...CTX, activity: { id: "otra", version: "1.0.0" } }))
      .rejects.toThrow(/otra actividad/);
  });

  it("rechaza esquemas incompatibles", async () => {
    await expect(parseAulawork(await buildSample(), { ...CTX, schemaVersion: "2.0" }))
      .rejects.toThrow(/incompatible/i);
  });

  it("avisa (sin bloquear) si cambia la versión de la actividad", async () => {
    const parsed = await parseAulawork(await buildSample(), {
      ...CTX, activity: { ...ACTIVITY, version: "1.1.0" },
    });
    expect(parsed.warnings.some((w) => w.includes("1.0.0"))).toBe(true);
  });

  it("rechaza archivos que no son aulawork", async () => {
    await expect(parseAulawork(new Blob(["no soy un zip"]), CTX)).rejects.toThrow(ImportError);
    const empty = await new JSZip().generateAsync({ type: "blob" });
    await expect(parseAulawork(empty, CTX)).rejects.toThrow(/manifest/);
  });
});

describe("restauración", () => {
  let store;
  beforeEach(async () => {
    store = await Store.open(`restore-${Date.now()}-${Math.random()}`);
  });

  it("restaura el trabajo y marca huérfanas las respuestas desconocidas", async () => {
    const parsed = await parseAulawork(await buildSample(), CTX);
    const knownIds = new Set(["q1", "t1", "ev1", "adj1"]); // q2 ya no existe
    const orphans = await restoreWork(store, parsed, knownIds);
    expect(orphans).toEqual(["q2"]);
    expect((await store.getAnswer("q1")).orphan).toBeUndefined();
    expect((await store.getAnswer("q2")).orphan).toBe(true);
    expect((await store.getState("t1")).done).toBe(true);
    expect((await store.getFile("ev1")).description).toBe("IP del servidor");
    const meta = await store.getMeta();
    expect(meta.student.grupo).toBe("2A");
    expect(meta.currentStepId).toBe("prueba-cliente");
  });
});
