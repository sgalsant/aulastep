/* AulaStep · evidence.js — utilidades para capturas y adjuntos. */

import { el } from "./ui.js";

export const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];

export function isImage(file) {
  return IMAGE_TYPES.includes(file.type);
}

export function sanitizeFilename(name) {
  const base = (name || "archivo").split(/[\\/]/).pop();
  return base.replace(/[^a-zA-Z0-9._ -]/g, "_").replace(/\s+/g, "-").slice(0, 120) || "archivo";
}

export function pickFile(accept) {
  return new Promise((resolve) => {
    const input = el("input", { type: "file", accept: accept || undefined, hidden: true });
    input.addEventListener("change", () => { resolve(input.files[0] || null); input.remove(); });
    input.addEventListener("cancel", () => { resolve(null); input.remove(); });
    document.body.append(input);
    input.click();
  });
}

export function matchesAccept(file, accept) {
  if (!accept) return true;
  const name = file.name.toLowerCase();
  return accept.split(",").map((s) => s.trim().toLowerCase()).some((rule) => {
    if (!rule) return false;
    if (rule.startsWith(".")) return name.endsWith(rule);
    if (rule.endsWith("/*")) return file.type.startsWith(rule.slice(0, -1));
    return file.type === rule;
  });
}

/* Comprime una imagen si supera el límite: reduce dimensiones y recodifica
   a JPEG progresivamente hasta cumplir maxBytes (o agotar intentos). */
export async function compressImage(file, maxBytes) {
  if (file.size <= maxBytes) return file;
  const bitmap = await createImageBitmap(file);
  let width = bitmap.width;
  let height = bitmap.height;
  let quality = 0.88;
  for (let attempt = 0; attempt < 6; attempt += 1) {
    const scale = Math.min(1, 1920 / Math.max(width, height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
    if (blob && blob.size <= maxBytes) {
      bitmap.close();
      return new File([blob], file.name.replace(/\.[^.]+$/, "") + ".jpg", { type: "image/jpeg" });
    }
    width = Math.round(width * 0.8);
    height = Math.round(height * 0.8);
    quality = Math.max(0.55, quality - 0.08);
  }
  bitmap.close();
  return null; // imposible dejarla bajo el límite
}

/* Zona de arrastre reutilizable. onFile recibe el File elegido. */
export function makeDropzone({ label, hint, accept, onFile }) {
  const zone = el(
    "div",
    { class: "dropzone", role: "button", tabindex: "0", "aria-label": label },
    el("div", { html: `<strong>${label}</strong>` }),
    el("span", { class: "hint", text: hint })
  );
  const choose = async () => {
    const file = await pickFile(accept);
    if (file) onFile(file);
  };
  zone.addEventListener("click", choose);
  zone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choose(); }
  });
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("is-over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("is-over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("is-over");
    const file = e.dataTransfer.files[0];
    if (file) onFile(file);
  });
  zone.addEventListener("paste", (e) => {
    const item = [...(e.clipboardData?.items || [])].find((i) => i.kind === "file");
    if (item) { e.preventDefault(); onFile(item.getAsFile()); }
  });
  return zone;
}
