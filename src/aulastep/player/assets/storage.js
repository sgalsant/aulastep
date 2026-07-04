/* AulaStep · storage.js
   Persistencia local en IndexedDB. Sin dependencias externas.
   Una base de datos por actividad: "aulastep-<idActividad>".
   Emite eventos: save:start, save:ok, save:error, data:changed. */

const DB_VERSION = 1;
const STORES = ["meta", "answers", "states", "files"];

function req(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export class Store extends EventTarget {
  constructor(db, activityId) {
    super();
    this.db = db;
    this.activityId = activityId;
    this._pending = 0;
  }

  static async open(activityId) {
    const request = indexedDB.open(`aulastep-${activityId}`, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      for (const name of STORES) {
        if (!db.objectStoreNames.contains(name)) db.createObjectStore(name);
      }
    };
    const db = await req(request);
    return new Store(db, activityId);
  }

  _tx(name, mode = "readonly") {
    return this.db.transaction(name, mode).objectStore(name);
  }

  async _write(storeName, key, value) {
    this._pending += 1;
    this.dispatchEvent(new CustomEvent("save:start"));
    try {
      if (value === undefined) {
        await req(this._tx(storeName, "readwrite").delete(key));
      } else {
        await req(this._tx(storeName, "readwrite").put(value, key));
      }
      this.dispatchEvent(new CustomEvent("data:changed", { detail: { store: storeName, key } }));
      this.dispatchEvent(new CustomEvent("save:ok"));
    } catch (error) {
      this.dispatchEvent(new CustomEvent("save:error", { detail: { error } }));
      throw error;
    } finally {
      this._pending -= 1;
    }
  }

  async _read(storeName, key) {
    return req(this._tx(storeName).get(key));
  }

  async _readAll(storeName) {
    const store = this._tx(storeName);
    const [keys, values] = await Promise.all([req(store.getAllKeys()), req(store.getAll())]);
    const out = new Map();
    keys.forEach((k, i) => out.set(k, values[i]));
    return out;
  }

  /* ---- metadatos del trabajo (alumno, paso actual, fechas, tema) ---- */
  getMeta() { return this._read("meta", "meta"); }
  async setMeta(patch) {
    const current = (await this.getMeta()) || {};
    const next = { ...current, ...patch, updatedAt: new Date().toISOString() };
    await this._write("meta", "meta", next);
    return next;
  }

  /* ---- respuestas (preguntas y reflexiones) ---- */
  getAnswer(id) { return this._read("answers", id); }
  setAnswer(id, value, type) {
    return this._write("answers", id, { value, type, updatedAt: new Date().toISOString() });
  }
  putAnswerRaw(id, record) { return this._write("answers", id, record); }
  deleteAnswer(id) { return this._write("answers", id, undefined); }
  allAnswers() { return this._readAll("answers"); }

  /* ---- estados de tareas y checkpoints ---- */
  getState(id) { return this._read("states", id); }
  setState(id, done) {
    return this._write("states", id, { done: !!done, updatedAt: new Date().toISOString() });
  }
  allStates() { return this._readAll("states"); }

  /* ---- evidencias y adjuntos (blobs) ---- */
  getFile(id) { return this._read("files", id); }
  setFile(id, record) {
    return this._write("files", id, { ...record, updatedAt: new Date().toISOString() });
  }
  deleteFile(id) { return this._write("files", id, undefined); }
  allFiles() { return this._readAll("files"); }

  async clearAll() {
    for (const name of STORES) {
      await req(this._tx(name, "readwrite").clear());
    }
    this.dispatchEvent(new CustomEvent("data:changed", { detail: { store: "*", key: "*" } }));
  }
}

/* Indicador de guardado: Guardando… / Guardado / Error, con aria-live. */
export class SaveIndicator {
  constructor(element, store) {
    this.el = element;
    this.label = element.querySelector(".save-label");
    this._store = store;
    this._timer = null;
    this._onStart = () => this._set("saving", "Guardando…");
    this._onOk = () => {
      clearTimeout(this._timer);
      this._timer = setTimeout(() => this._set("saved", "Guardado"), 350);
    };
    this._onError = () => {
      clearTimeout(this._timer);
      this._set("error", "Error al guardar");
    };
    store.addEventListener("save:start", this._onStart);
    store.addEventListener("save:ok", this._onOk);
    store.addEventListener("save:error", this._onError);
  }

  /* Retira los listeners del store. Imprescindible antes de crear otro
     indicador sobre el mismo store (reconstrucción del shell). */
  dispose() {
    clearTimeout(this._timer);
    this._store.removeEventListener("save:start", this._onStart);
    this._store.removeEventListener("save:ok", this._onOk);
    this._store.removeEventListener("save:error", this._onError);
  }

  _set(state, text) {
    this.el.dataset.state = state;
    this.label.textContent = text;
  }
}

/* Debounce con intervalo máximo: escribe mientras se teclea sin saturar,
   garantizando un guardado al menos cada `intervalMs` (autoguardado). */
export function autosaveDebounce(fn, intervalMs) {
  let timer = null;
  let last = 0;
  const flush = (...args) => {
    last = Date.now();
    timer = null;
    fn(...args);
  };
  return (...args) => {
    clearTimeout(timer);
    if (Date.now() - last >= intervalMs) {
      flush(...args);
    } else {
      timer = setTimeout(() => flush(...args), 600);
    }
  };
}
