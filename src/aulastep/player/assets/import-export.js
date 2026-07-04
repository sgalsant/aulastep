/* AulaStep · import-export.js
   Formato .aulawork: ZIP con manifest.json, student.json, answers.json,
   progress.json, attachments.json, evidence/ y files/.
   Integridad: SHA-256 de cada entrada, registrado en manifest.integrity. */

import { sanitizeFilename } from "./evidence.js";

export const AULAWORK_FORMAT = "aulawork";

async function sha256Hex(data) {
  let buffer;
  if (typeof data === "string") buffer = new TextEncoder().encode(data);
  else if (data instanceof ArrayBuffer || ArrayBuffer.isView(data)) buffer = data;
  else buffer = await data.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function majorOf(version) {
  return String(version || "").split(".")[0];
}

function textEntry(obj) {
  return JSON.stringify(obj, null, 2);
}


export function buildExportFilename(pattern, activity, student) {
  const date = new Date().toISOString().slice(0, 10);
  const alumno = sanitizeFilename(student?.nombre || student?.[Object.keys(student || {})[0]] || "alumno")
    .replace(/\.[^.]*$/, "");
  return pattern
    .replaceAll("{actividad}", activity.id)
    .replaceAll("{alumno}", alumno || "alumno")
    .replaceAll("{fecha}", date);
}

/* ---------------------------------------------------------------- exportar */
export async function buildAulawork({ activity, schemaVersion, generator, meta, answers, states, files }) {
  const zip = new JSZip();
  const integrity = {};
  const attachmentsIndex = [];

  const add = async (path, data) => {
    zip.file(path, data, { binary: typeof data !== "string" });
    integrity[path] = await sha256Hex(data);
  };

  const student = meta?.student || {};
  await add("student.json", textEntry(student));

  const answersObj = {};
  for (const [id, record] of answers) answersObj[id] = record;
  await add("answers.json", textEntry(answersObj));

  const statesObj = {};
  for (const [id, record] of states) statesObj[id] = record;
  await add(
    "progress.json",
    textEntry({
      currentStepId: meta?.currentStepId || null,
      startedAt: meta?.startedAt || null,
      updatedAt: meta?.updatedAt || null,
      states: statesObj,
    })
  );

  for (const [id, record] of files) {
    const folder = record.kind === "evidence" ? "evidence" : "files";
    const path = `${folder}/${id}__${sanitizeFilename(record.name)}`;
    attachmentsIndex.push({
      id,
      kind: record.kind,
      name: record.name,
      mime: record.mime,
      size: record.size,
      description: record.description || "",
      path,
    });
    await add(path, await record.blob.arrayBuffer());
  }
  await add("attachments.json", textEntry(attachmentsIndex));

  const manifest = {
    format: AULAWORK_FORMAT,
    schemaVersion,
    generator,
    activity: { id: activity.id, version: activity.version, titulo: activity.titulo },
    exportedAt: new Date().toISOString(),
    integrity: { algorithm: "SHA-256", files: integrity },
  };
  zip.file("manifest.json", JSON.stringify(manifest, null, 2));
  return zip.generateAsync({ type: "blob", compression: "DEFLATE" });
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

/* ---------------------------------------------------------------- importar */
export class ImportError extends Error {}

function safeEntryName(name) {
  return !name.startsWith("/") && !name.includes("..") && !name.includes("\\");
}

export async function parseAulawork(fileOrBlob, { activity, schemaVersion, limits }) {
  let zip;
  try {
    const data = typeof fileOrBlob?.arrayBuffer === "function"
      ? await fileOrBlob.arrayBuffer()
      : fileOrBlob;
    zip = await JSZip.loadAsync(data);
  } catch {
    throw new ImportError("El archivo no es un paquete .aulawork válido (ZIP corrupto o ilegible).");
  }
  const manifestEntry = zip.file("manifest.json");
  if (!manifestEntry) throw new ImportError("El paquete no contiene manifest.json.");
  let manifest;
  try {
    manifest = JSON.parse(await manifestEntry.async("string"));
  } catch {
    throw new ImportError("El manifest.json del paquete está dañado.");
  }
  if (manifest.format !== AULAWORK_FORMAT) {
    throw new ImportError("El paquete no tiene formato aulawork.");
  }
  if (majorOf(manifest.schemaVersion) !== majorOf(schemaVersion)) {
    throw new ImportError(
      `Esquema incompatible: el trabajo usa ${manifest.schemaVersion} y la actividad ${schemaVersion}.`
    );
  }
  if (manifest.activity?.id !== activity.id) {
    throw new ImportError(
      `El trabajo pertenece a otra actividad ('${manifest.activity?.id}'), no a '${activity.id}'.`
    );
  }

  const warnings = [];
  if (manifest.activity?.version !== activity.version) {
    warnings.push(
      `El trabajo se creó con la versión ${manifest.activity?.version} de la actividad ` +
      `(actual: ${activity.version}). Se importará; revisa que no falte nada.`
    );
  }

  const readJson = async (path, fallback) => {
    const entry = zip.file(path);
    if (!entry) return fallback;
    try {
      return JSON.parse(await entry.async("string"));
    } catch {
      throw new ImportError(`La entrada ${path} del paquete está dañada.`);
    }
  };

  // Verificación de integridad de todas las entradas declaradas.
  const declared = manifest.integrity?.files || {};
  for (const [path, expected] of Object.entries(declared)) {
    if (!safeEntryName(path)) throw new ImportError(`Ruta insegura en el paquete: ${path}`);
    const entry = zip.file(path);
    if (!entry) throw new ImportError(`Falta la entrada declarada ${path}: paquete incompleto.`);
    const actual = await sha256Hex(await entry.async("arraybuffer"));
    if (actual !== expected) {
      throw new ImportError(`La entrada ${path} no supera la comprobación de integridad (paquete alterado o corrupto).`);
    }
  }

  const student = await readJson("student.json", {});
  const answers = await readJson("answers.json", {});
  const progress = await readJson("progress.json", { states: {} });
  const attachmentsIndex = await readJson("attachments.json", []);

  const maxEvidence = (limits?.tamano_maximo_captura_mb || 8) * 1024 * 1024;
  const maxAttachment = (limits?.tamano_maximo_adjunto_mb || 20) * 1024 * 1024;
  const files = [];
  for (const item of attachmentsIndex) {
    if (!item?.id || !item?.path || !safeEntryName(item.path)) {
      warnings.push(`Se ha ignorado un adjunto con ruta no válida (${item?.path || "?"}).`);
      continue;
    }
    const entry = zip.file(item.path);
    if (!entry) {
      warnings.push(`Falta el archivo ${item.path}; se omite.`);
      continue;
    }
    const buffer = await entry.async("arraybuffer");
    const limit = item.kind === "evidence" ? maxEvidence : maxAttachment;
    if (buffer.byteLength > limit) {
      warnings.push(`'${item.name}' supera el tamaño permitido y se ha omitido.`);
      continue;
    }
    if (item.kind === "evidence" && !(item.mime || "").startsWith("image/")) {
      warnings.push(`La evidencia '${item.name}' no es una imagen y se ha omitido.`);
      continue;
    }
    files.push({
      id: item.id,
      record: {
        kind: item.kind === "evidence" ? "evidence" : "file",
        name: sanitizeFilename(item.name),
        mime: item.mime || "application/octet-stream",
        size: buffer.byteLength,
        description: item.description || "",
        blob: new Blob([buffer], { type: item.mime || "application/octet-stream" }),
      },
    });
  }

  return { manifest, student, answers, progress, files, warnings };
}

/* Vuelca en el almacén un paquete ya validado. Marca como huérfanas las
   respuestas cuyo ID ya no exista en la actividad actual. */
export async function restoreWork(store, parsed, knownIds) {
  await store.clearAll();
  const orphanIds = [];
  for (const [id, record] of Object.entries(parsed.answers)) {
    const isOrphan = !knownIds.has(id);
    if (isOrphan) orphanIds.push(id);
    await store.putAnswerRaw(id, { ...record, orphan: isOrphan || undefined });
  }
  for (const [id, record] of Object.entries(parsed.progress.states || {})) {
    await store.setState(id, !!record.done);
  }
  for (const { id, record } of parsed.files) {
    await store.setFile(id, record);
  }
  await store.setMeta({
    student: parsed.student,
    currentStepId: parsed.progress.currentStepId || null,
    startedAt: parsed.progress.startedAt || new Date().toISOString(),
    importedAt: new Date().toISOString(),
  });
  return orphanIds;
}
