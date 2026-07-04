/* AulaStep · directives.js
   Renderiza los segmentos interactivos de activity.json y los conecta
   con la persistencia local. */

import { compressImage, isImage, makeDropzone, matchesAccept, sanitizeFilename } from "./evidence.js";
import { el, confirmModal, formatSize, openLightbox, toast } from "./ui.js";

const KIND_LABELS = {
  task: "Tarea",
  question: "Pregunta",
  evidence: "Evidencia",
  file: "Adjunto",
  reflection: "Reflexión",
  checkpoint: "Punto de control",
};

function card(segment, ...body) {
  const wrapper = el(
    "section",
    {
      class: `iCard iCard--${segment.type}`,
      id: `item-${segment.id}`,
      "aria-labelledby": `item-${segment.id}-kind`,
      dataset: { itemId: segment.id },
    },
    el(
      "div",
      { class: "iCard-head" },
      el("span", { class: "iCard-kind", id: `item-${segment.id}-kind`, text: KIND_LABELS[segment.type] }),
      segment.required ? el("span", { class: "iCard-req", text: "· obligatorio" }) : null,
      el("span", { class: "iCard-state", "aria-live": "off" })
    ),
    segment.html ? el("div", { class: "iCard-prompt", html: segment.html }) : null,
    ...body
  );
  return wrapper;
}

function setDone(wrapper, done, text = "Completado") {
  wrapper.classList.toggle("is-done", done);
  wrapper.querySelector(".iCard-state").textContent = done ? `✓ ${text}` : "";
}

/* ------------------------------------------------- tareas y checkpoints */
function renderCheck(segment, ctx, label) {
  const wrapper = card(segment);
  const checkbox = el("input", { type: "checkbox", id: `chk-${segment.id}` });
  wrapper.append(
    el("label", { class: "task-check", for: `chk-${segment.id}` }, checkbox, el("span", { text: label }))
  );
  ctx.store.getState(segment.id).then((state) => {
    checkbox.checked = !!state?.done;
    setDone(wrapper, checkbox.checked);
  });
  checkbox.addEventListener("change", async () => {
    await ctx.store.setState(segment.id, checkbox.checked);
    setDone(wrapper, checkbox.checked);
    ctx.onProgress();
  });
  return wrapper;
}

/* -------------------------------------------------------------- preguntas */
function renderTextQuestion(segment, ctx) {
  const wrapper = card(segment);
  const isLong = segment.questionType === "long-text";
  const isNumeric = segment.questionType === "numeric";
  const field = isLong
    ? el("textarea", { class: "input answer", rows: 5 })
    : el("input", { class: "input answer", type: isNumeric ? "number" : "text", step: "any" });
  field.setAttribute("aria-label", "Tu respuesta");
  const hint = isLong ? el("p", { class: "char-hint", text: "0 caracteres" }) : null;
  wrapper.append(field, hint);

  ctx.store.getAnswer(segment.id).then((answer) => {
    if (answer?.value !== undefined && answer?.value !== null) field.value = answer.value;
    update(false);
  });

  const persist = ctx.debounced(async () => {
    await ctx.store.setAnswer(segment.id, field.value, segment.questionType);
    ctx.onProgress();
  });

  function update(save = true) {
    const filled = field.value.trim() !== "";
    setDone(wrapper, filled, "Respondida");
    if (hint) hint.textContent = `${field.value.length} caracteres`;
    if (save) persist();
  }
  field.addEventListener("input", () => update());
  field.addEventListener("blur", () => {
    ctx.store.setAnswer(segment.id, field.value, segment.questionType).then(ctx.onProgress);
  });
  return wrapper;
}

function renderChoiceQuestion(segment, ctx) {
  const wrapper = card(segment);
  const multiple = segment.questionType === "multi-choice";
  const list = el("div", { class: "choice-list", role: "group", "aria-label": "Opciones" });
  const inputs = new Map();

  for (const option of segment.options) {
    const input = el("input", {
      type: multiple ? "checkbox" : "radio",
      name: `q-${segment.id}`,
      value: option.id,
      id: `opt-${option.id}`,
    });
    inputs.set(option.id, input);
    const label = el("label", { class: "choice", for: `opt-${option.id}` }, input, el("div", { html: option.html }));
    list.append(label);
  }
  wrapper.append(list);

  const readValue = () => {
    const selected = [...inputs.entries()].filter(([, i]) => i.checked).map(([id]) => id);
    return multiple ? selected : selected[0] || "";
  };
  const paint = () => {
    for (const [, input] of inputs) input.closest(".choice").classList.toggle("is-selected", input.checked);
    const value = readValue();
    setDone(wrapper, multiple ? value.length > 0 : !!value, "Respondida");
  };

  ctx.store.getAnswer(segment.id).then((answer) => {
    const value = answer?.value;
    if (value) {
      for (const id of Array.isArray(value) ? value : [value]) inputs.get(id) && (inputs.get(id).checked = true);
    }
    paint();
  });

  list.addEventListener("change", async () => {
    paint();
    await ctx.store.setAnswer(segment.id, readValue(), segment.questionType);
    ctx.onProgress();
  });
  return wrapper;
}

/* ------------------------------------------------------------- evidencias */
function renderEvidence(segment, ctx) {
  const wrapper = card(segment);
  const holder = el("div");
  wrapper.append(holder);
  const maxBytes = ctx.limits.tamano_maximo_captura_mb * 1024 * 1024;

  async function accept(file) {
    if (!file) return;
    if (!isImage(file)) {
      toast("La evidencia debe ser una imagen (PNG, JPG, WebP o GIF).", "error");
      return;
    }
    let final = file;
    if (file.size > maxBytes) {
      toast("Imagen grande: comprimiendo…");
      final = await compressImage(file, maxBytes);
      if (!final) {
        toast(`No se pudo dejar la imagen por debajo de ${ctx.limits.tamano_maximo_captura_mb} MB.`, "error");
        return;
      }
    }
    const previous = await ctx.store.getFile(segment.id);
    await ctx.store.setFile(segment.id, {
      kind: "evidence",
      name: sanitizeFilename(final.name),
      mime: final.type,
      size: final.size,
      description: previous?.description || "",
      blob: final,
    });
    toast("Captura guardada.", "success");
    render();
    ctx.onProgress();
  }

  async function render() {
    holder.replaceChildren();
    const record = await ctx.store.getFile(segment.id);
    setDone(wrapper, !!record, "Aportada");
    if (!record) {
      holder.append(
        makeDropzone({
          label: "Arrastra una captura, pégala o haz clic para elegirla",
          hint: `Imagen de hasta ${ctx.limits.tamano_maximo_captura_mb} MB. También puedes pegar con Ctrl+V.`,
          accept: "image/*",
          onFile: accept,
        })
      );
      return;
    }
    const url = URL.createObjectURL(record.blob);
    const description = el("textarea", {
      class: "input", rows: 2, placeholder: "Describe qué se ve en la captura (opcional)",
      "aria-label": "Descripción de la captura",
    });
    description.value = record.description || "";
    description.addEventListener(
      "input",
      ctx.debounced(async () => {
        const current = await ctx.store.getFile(segment.id);
        if (current) await ctx.store.setFile(segment.id, { ...current, description: description.value });
      })
    );
    holder.append(
      el(
        "div",
        { class: "evidence-preview" },
        el(
          "button",
          { class: "evidence-thumb", type: "button", "aria-label": "Ampliar la captura", onclick: () => openLightbox(url, record.description) },
          el("img", { src: url, alt: record.description || "Captura aportada" })
        ),
        el(
          "div",
          { class: "evidence-meta" },
          el("span", { class: "fileline", text: `${record.name} · ${formatSize(record.size)}` }),
          description,
          el(
            "div",
            { class: "evidence-actions" },
            el("button", {
              class: "btn btn-secondary btn-sm", type: "button", text: "Sustituir",
              onclick: async () => {
                const { pickFile } = await import("./evidence.js");
                accept(await pickFile("image/*"));
              },
            }),
            el("button", {
              class: "btn btn-danger btn-sm", type: "button", text: "Eliminar",
              onclick: async () => {
                if (await confirmModal("Eliminar captura", "¿Seguro que quieres eliminar esta captura?", "Eliminar")) {
                  await ctx.store.deleteFile(segment.id);
                  render();
                  ctx.onProgress();
                }
              },
            })
          )
        )
      )
    );
  }
  render();

  // Pegado global mientras la tarjeta tiene el foco dentro.
  wrapper.addEventListener("paste", (e) => {
    const item = [...(e.clipboardData?.items || [])].find((i) => i.kind === "file");
    if (item) { e.preventDefault(); accept(item.getAsFile()); }
  });
  return wrapper;
}

/* --------------------------------------------------------------- adjuntos */
function renderFile(segment, ctx) {
  const wrapper = card(segment);
  const holder = el("div");
  wrapper.append(holder);
  const maxBytes = ctx.limits.tamano_maximo_adjunto_mb * 1024 * 1024;

  async function accept(file) {
    if (!file) return;
    if (segment.accept && !matchesAccept(file, segment.accept)) {
      toast(`Tipo de archivo no admitido. Se espera: ${segment.accept}`, "error");
      return;
    }
    if (file.size > maxBytes) {
      toast(`El adjunto supera el máximo de ${ctx.limits.tamano_maximo_adjunto_mb} MB.`, "error");
      return;
    }
    await ctx.store.setFile(segment.id, {
      kind: "file",
      name: sanitizeFilename(file.name),
      mime: file.type || "application/octet-stream",
      size: file.size,
      blob: file,
    });
    toast("Adjunto guardado.", "success");
    render();
    ctx.onProgress();
  }

  async function render() {
    holder.replaceChildren();
    const record = await ctx.store.getFile(segment.id);
    setDone(wrapper, !!record, "Adjuntado");
    if (!record) {
      holder.append(
        makeDropzone({
          label: "Arrastra el archivo o haz clic para elegirlo",
          hint: `${segment.accept ? `Tipos admitidos: ${segment.accept}. ` : ""}Máximo ${ctx.limits.tamano_maximo_adjunto_mb} MB.`,
          accept: segment.accept,
          onFile: accept,
        })
      );
      return;
    }
    holder.append(
      el(
        "div",
        { class: "file-chip" },
        el("span", { class: "fname", text: record.name }),
        el("span", { class: "fsize", text: formatSize(record.size) }),
        el("span", { class: "spacer", style: "flex:1" }),
        el("button", {
          class: "btn btn-ghost btn-sm", type: "button", text: "Descargar",
          onclick: () => {
            const url = URL.createObjectURL(record.blob);
            const a = el("a", { href: url, download: record.name });
            document.body.append(a); a.click(); a.remove();
            setTimeout(() => URL.revokeObjectURL(url), 4000);
          },
        }),
        el("button", {
          class: "btn btn-secondary btn-sm", type: "button", text: "Sustituir",
          onclick: async () => {
            const { pickFile } = await import("./evidence.js");
            accept(await pickFile(segment.accept));
          },
        }),
        el("button", {
          class: "btn btn-danger btn-sm", type: "button", text: "Eliminar",
          onclick: async () => {
            if (await confirmModal("Eliminar adjunto", "¿Seguro que quieres eliminar este adjunto?", "Eliminar")) {
              await ctx.store.deleteFile(segment.id);
              render();
              ctx.onProgress();
            }
          },
        })
      )
    );
  }
  render();
  return wrapper;
}

/* --------------------------------------------------------------- registro */
export function renderSegment(segment, ctx) {
  switch (segment.type) {
    case "html": {
      return el("div", { class: "segment", html: segment.html });
    }
    case "task":
      return renderCheck(segment, ctx, "Marcar la tarea como realizada");
    case "checkpoint":
      return renderCheck(segment, ctx, "Confirmo este punto de control");
    case "question":
      return segment.options ? renderChoiceQuestion(segment, ctx) : renderTextQuestion(segment, ctx);
    case "reflection":
      return renderTextQuestion(segment, ctx);
    case "evidence":
      return renderEvidence(segment, ctx);
    case "file":
      return renderFile(segment, ctx);
    default:
      return el("div", { class: "segment", text: "" });
  }
}
