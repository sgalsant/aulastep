/* AulaStep · ui.js — utilidades de interfaz accesibles. */

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key === "html") node.innerHTML = value; // solo HTML ya saneado
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2), value);
    } else if (key === "dataset") Object.assign(node.dataset, value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  node.append(...children.filter(Boolean));
  return node;
}

export function toast(message, kind = "info", ms = 3200) {
  const host = document.getElementById("toasts");
  const item = el("div", { class: `toast toast--${kind}`, role: "status", text: message });
  host.append(item);
  setTimeout(() => item.remove(), ms);
}

export function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} kB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-ES", { dateStyle: "medium", timeStyle: "short" });
}

/* Modal accesible sobre <dialog>: foco atrapado por el propio elemento,
   cierre con Escape, devuelve una promesa con el resultado. */
export function openModal({ title, body, actions }) {
  return new Promise((resolve) => {
    const dialog = el("dialog", { class: "modal", "aria-labelledby": "modal-title" });
    const heading = el("h2", { id: "modal-title", text: title });
    const content = typeof body === "string" ? el("div", { text: body }) : body;
    const buttonRow = el("div", { class: "modal-actions" });
    for (const action of actions) {
      buttonRow.append(
        el("button", {
          class: `btn ${action.class || "btn-secondary"}`,
          type: "button",
          text: action.label,
          onclick: () => { dialog.close(); resolve(action.value); },
        })
      );
    }
    dialog.append(heading, content, buttonRow);
    dialog.addEventListener("close", () => { dialog.remove(); resolve(undefined); });
    document.body.append(dialog);
    dialog.showModal();
  });
}

export function confirmModal(title, message, confirmLabel = "Confirmar") {
  return openModal({
    title,
    body: el("p", { text: message }),
    actions: [
      { label: "Cancelar", value: false },
      { label: confirmLabel, value: true, class: "btn-danger" },
    ],
  }).then((v) => v === true);
}

export function openLightbox(url, alt) {
  const dialog = el("dialog", { class: "lightbox" });
  dialog.append(
    el("img", { src: url, alt: alt || "Vista ampliada" }),
    el("button", { class: "btn btn-secondary", type: "button", text: "Cerrar", onclick: () => dialog.close() })
  );
  dialog.addEventListener("close", () => dialog.remove());
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });
  document.body.append(dialog);
  dialog.showModal();
}

/* Envuelve cada <pre><code> en una tarjeta de terminal con botón de copiar. */
export function enhanceCodeBlocks(root) {
  for (const pre of root.querySelectorAll("pre")) {
    if (pre.closest(".codeblock")) continue;
    const code = pre.querySelector("code");
    const langClass = code ? [...code.classList].find((c) => c.startsWith("language-")) : null;
    const lang = langClass ? langClass.replace("language-", "") : "código";
    const wrapper = el("div", { class: "codeblock" });
    const copyButton = el("button", {
      class: "copy-btn", type: "button", text: "Copiar",
      "aria-label": "Copiar el bloque de código",
    });
    copyButton.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(code ? code.textContent : pre.textContent);
        copyButton.textContent = "Copiado";
        copyButton.classList.add("copied");
        setTimeout(() => { copyButton.textContent = "Copiar"; copyButton.classList.remove("copied"); }, 1800);
      } catch {
        toast("No se pudo copiar al portapapeles.", "error");
      }
    });
    const bar = el("div", { class: "codeblock-bar" }, el("span", { class: "lang", text: lang }), copyButton);
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.append(bar, pre);
  }
}

/* Desvelado en dos pasos para las soluciones (:::solution):
   al abrir el <details>, el contenido queda oculto tras un botón de
   confirmación. Fricción deliberada: invita a intentarlo antes de mirar. */
export function enhanceSolutions(root) {
  for (const details of root.querySelectorAll('details.as-details--solution[data-guarded="true"]')) {
    const body = details.querySelector(".as-details-body");
    if (!body) continue;
    body.hidden = true;
    const guard = el(
      "div",
      { class: "solution-guard" },
      el("p", { text: "¿Seguro? Intenta resolverlo antes de mirar la solución." }),
      el("button", {
        class: "btn btn-secondary btn-sm",
        type: "button",
        text: "Mostrar la solución",
        onclick: () => {
          body.hidden = false;
          guard.remove();
          details.classList.add("is-revealed");
          details.removeAttribute("data-guarded");
        },
      })
    );
    body.parentNode.insertBefore(guard, body);
  }
}
