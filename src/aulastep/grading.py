"""Corrección de entregas .aulawork.

Lee un lote de archivos `.aulawork`, verifica su integridad (SHA-256, mismo
esquema y misma actividad), autocorrige las preguntas de elección contra las
marcas `[x]` del fuente (que nunca se publican) y genera:

- `index.html`: informe navegable e imprimible (tabla resumen + detalle por alumno).
- `resumen.csv`: una fila por entrega, para la hoja de calificaciones.
- `evidencias/<alumno>/…`: capturas y adjuntos extraídos, enlazados desde el informe.

Las respuestas de texto NO se puntúan: se presentan para corrección manual.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from . import branding
from .errors import Report
from .project import ProjectLoader, load_project

_env = Environment(
    loader=PackageLoader("aulastep", "templates"),
    autoescape=select_autoescape(["html", "j2"]),
)

_INTERACTIVE = {"task", "question", "evidence", "file", "reflection", "checkpoint"}
# El manifiesto no puede contener su propio hash; el resto sí debe declararse.
_REQUIRED_ENTRIES = ("student.json", "answers.json", "progress.json")


# --------------------------------------------------------------- lectura ZIP
@dataclass
class Work:
    """Una entrega leída (válida o no)."""

    filename: str
    ok: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    student: dict[str, str] = field(default_factory=dict)
    answers: dict[str, dict[str, Any]] = field(default_factory=dict)
    states: dict[str, dict[str, Any]] = field(default_factory=dict)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    started_at: str | None = None
    updated_at: str | None = None
    exported_at: str | None = None
    activity_version: str | None = None
    _zip_path: Path | None = None


def _major(version: str) -> str:
    return str(version).split(".")[0]


def read_aulawork(path: Path, expected_id: str, schema_version: str) -> Work:
    """Lee y verifica un .aulawork. Nunca lanza: los problemas van en Work.errors."""
    work = Work(filename=path.name, _zip_path=path)
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        work.errors.append("No es un archivo ZIP válido.")
        return work

    with zf:
        try:
            return _read_verified(zf, work, expected_id, schema_version)
        except (zipfile.BadZipFile, OSError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
            # Corrupción por debajo de nuestra verificación (p. ej. CRC del ZIP):
            # la entrega se marca inválida sin tumbar el resto del lote.
            work.errors.append("Paquete corrupto o alterado: contenido ilegible.")
            work.ok = False
            return work


def _read_verified(zf: zipfile.ZipFile, work: Work, expected_id: str, schema_version: str) -> Work:
    names = set(zf.namelist())
    if "manifest.json" not in names:
        work.errors.append("Falta manifest.json: no es un paquete .aulawork.")
        return work
    try:
        manifest = json.loads(zf.read("manifest.json"))
    except json.JSONDecodeError:
        work.errors.append("manifest.json ilegible.")
        return work

    if manifest.get("format") != "aulawork":
        work.errors.append("El paquete no declara el formato aulawork.")
        return work
    pkg_schema = str(manifest.get("schemaVersion", ""))
    if _major(pkg_schema) != _major(schema_version):
        work.errors.append(
            f"Esquema incompatible: paquete {pkg_schema}, actividad {schema_version}."
        )
        return work
    activity = manifest.get("activity", {})
    if activity.get("id") != expected_id:
        work.errors.append(
            f"Es un trabajo de otra actividad ('{activity.get('id')}', "
            f"se esperaba '{expected_id}')."
        )
        return work
    work.activity_version = activity.get("version")
    work.exported_at = manifest.get("exportedAt")

    integrity = manifest.get("integrity", {})
    if integrity.get("algorithm") != "SHA-256":
        work.errors.append("El manifiesto no declara integridad SHA-256.")
        return work
    declared: dict[str, str] = integrity.get("files", {})
    for entry, expected_hash in declared.items():
        if entry.startswith("/") or ".." in entry:
            work.errors.append(f"Ruta insegura en el paquete: '{entry}'.")
            return work
        if entry not in names:
            work.errors.append(f"Falta la entrada declarada '{entry}'.")
            return work
        digest = hashlib.sha256(zf.read(entry)).hexdigest()
        if digest != expected_hash:
            work.errors.append(
                f"Integridad violada en '{entry}': el paquete fue alterado o está corrupto."
            )
            return work
    for required in _REQUIRED_ENTRIES:
        if required not in declared:
            work.errors.append(f"'{required}' no está protegido por integridad.")
            return work

    work.student = json.loads(zf.read("student.json"))
    work.answers = json.loads(zf.read("answers.json"))
    progress = json.loads(zf.read("progress.json"))
    work.states = progress.get("states", {})
    work.started_at = progress.get("startedAt")
    work.updated_at = progress.get("updatedAt")
    if "attachments.json" in names:
        work.attachments = json.loads(zf.read("attachments.json"))

    if work.activity_version and work.activity_version != _ACTIVITY_VERSION_SENTINEL.get(
        expected_id, work.activity_version
    ):
        work.warnings.append(f"Exportado con la versión {work.activity_version} de la actividad.")
    work.ok = True
    return work


# La versión actual de la actividad se registra aquí antes de leer los trabajos,
# para poder avisar (sin bloquear) de entregas de versiones anteriores.
_ACTIVITY_VERSION_SENTINEL: dict[str, str] = {}


# ------------------------------------------------------------- calificación
def inventory(loader: ProjectLoader) -> list[dict[str, Any]]:
    """Elementos interactivos de la actividad, en orden, con su contexto de paso."""
    items: list[dict[str, Any]] = []
    assert loader.compiled is not None
    for step in loader.compiled.steps:
        for segment in step.segments:
            if segment.type in _INTERACTIVE:
                items.append(
                    {
                        "step_id": step.id,
                        "step_titulo": step.titulo,
                        "id": segment.id,
                        "type": segment.type,
                        "required": bool(segment.required),
                        "question_type": segment.question_type,
                        "prompt_html": segment.html or "",
                    }
                )
    return items


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _item_done(item: dict[str, Any], work: Work, attachment_ids: set[str]) -> bool:
    kind = item["type"]
    iid = item["id"]
    if kind in ("task", "checkpoint"):
        return bool(work.states.get(iid, {}).get("done"))
    if kind in ("evidence", "file"):
        return iid in attachment_ids
    value = work.answers.get(iid, {}).get("value")
    if isinstance(value, list):
        return len(value) > 0
    return value is not None and str(value).strip() != ""


def grade_work(
    work: Work, items: list[dict[str, Any]], answer_key: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Califica una entrega válida contra el inventario y la clave."""
    attachment_ids = {str(a["id"]) for a in work.attachments if a.get("id")}
    graded_items: list[dict[str, Any]] = []
    required_total = required_done = 0
    choice_total = choice_hits = 0
    timestamps: list[datetime] = []

    for item in items:
        done = _item_done(item, work, attachment_ids)
        if item["required"]:
            required_total += 1
            required_done += int(done)
        record = dict(item, done=done)

        answer = work.answers.get(item["id"], {})
        if ts := _parse_iso(answer.get("updatedAt")):
            timestamps.append(ts)
        if ts := _parse_iso(work.states.get(item["id"], {}).get("updatedAt")):
            timestamps.append(ts)

        key = answer_key.get(item["id"])
        if key:  # pregunta de elección: autocorrección
            choice_total += 1
            raw = answer.get("value")
            given = raw if isinstance(raw, list) else ([raw] if raw else [])
            correct = sorted(given) == sorted(key["correct"])
            choice_hits += int(correct)
            record.update(
                answered=bool(given),
                given=given,
                correct=correct,
                expected=key["correct"],
                options=key["options"],
            )
        elif item["type"] in ("question", "reflection"):
            record["text_value"] = answer.get("value", "")
        elif item["type"] in ("evidence", "file"):
            record["attachments"] = [a for a in work.attachments if a.get("id") == item["id"]]
        graded_items.append(record)

    started = _parse_iso(work.started_at)
    if ts := _parse_iso(work.updated_at):
        timestamps.append(ts)  # último guardado global: la señal más reciente
    last = max(timestamps) if timestamps else None
    duration_min: int | None = None
    if started and last and last >= started:
        duration_min = round((last - started).total_seconds() / 60)

    return {
        "items": graded_items,
        "required_done": required_done,
        "required_total": required_total,
        "required_pct": round(required_done / required_total * 100) if required_total else 100,
        "choice_hits": choice_hits,
        "choice_total": choice_total,
        "started": started,
        "last": last,
        "duration_min": duration_min,
    }


# ------------------------------------------------------------------ informe
def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return text or "alumno"


def _extract_attachments(work: Work, out_dir: Path) -> dict[str, str]:
    """Extrae evidencias/adjuntos de una entrega. Devuelve {ruta_zip: ruta_relativa}."""
    if not work._zip_path or not work.attachments:
        return {}
    student_name = " ".join(v for v in work.student.values() if v) or work.filename
    target = out_dir / "evidencias" / _slug(student_name)
    mapping: dict[str, str] = {}
    with zipfile.ZipFile(work._zip_path) as zf:
        names = set(zf.namelist())
        for att in work.attachments:
            path = att.get("path", "")
            if not path or path.startswith("/") or ".." in path or path not in names:
                continue
            target.mkdir(parents=True, exist_ok=True)
            dest = target / Path(path).name
            dest.write_bytes(zf.read(path))
            mapping[path] = str(dest.relative_to(out_dir))
    return mapping


def grade_folder(
    activity_dir: Path,
    works_dir: Path,
    output: Path,
    title: str = "Informe de corrección",
) -> tuple[Report, Path | None]:
    """Corrige todos los .aulawork de una carpeta y escribe el informe."""
    report = Report()
    loader = load_project(activity_dir)
    if not loader.report.ok or loader.compiled is None or loader.config is None:
        for issue in loader.report.issues:
            report.issues.append(issue)
        report.error(
            "CORRECCION_ACTIVIDAD_INVALIDA",
            f"La actividad '{activity_dir}' no valida: corrígela antes de corregir entregas.",
        )
        return report, None

    meta = loader.compiled.activity
    extension = loader.config.trabajo.extension
    files = sorted(works_dir.glob(f"*.{extension}")) if works_dir.is_dir() else []
    if not files:
        report.error(
            "CORRECCION_SIN_ENTREGAS",
            f"No hay archivos .{extension} en '{works_dir}'.",
        )
        return report, None

    _ACTIVITY_VERSION_SENTINEL[str(meta["id"])] = str(meta["version"])
    items = inventory(loader)
    output.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for path in files:
        work = read_aulawork(path, str(meta["id"]), str(loader.compiled.schema_version))
        entry: dict[str, Any] = {"work": work, "grade": None, "paths": {}}
        if work.ok:
            entry["grade"] = grade_work(work, items, loader.answer_key)
            entry["paths"] = _extract_attachments(work, output)
        else:
            report.warning(
                "CORRECCION_ENTREGA_INVALIDA",
                f"'{path.name}' descartada: {' '.join(work.errors)}",
            )
        rows.append(entry)

    rows.sort(key=lambda r: " ".join(r["work"].student.values()).lower() or r["work"].filename)

    student_fields = [c.id for c in (loader.config.alumno.campos or [])]
    field_labels = {c.id: c.etiqueta for c in (loader.config.alumno.campos or [])}

    template = _env.get_template("grade-report.html.j2")
    html = template.render(
        title=title,
        activity=meta,
        rows=rows,
        student_fields=student_fields,
        field_labels=field_labels,
        generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
        app_name=branding.APP_NAME,
        app_version=branding.APP_VERSION,
    )
    (output / "index.html").write_text(html, encoding="utf-8")

    with (output / "resumen.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(
            ["archivo"]
            + [field_labels[f] for f in student_fields]
            + [
                "obligatorios_hechos",
                "obligatorios_total",
                "obligatorios_pct",
                "eleccion_aciertos",
                "eleccion_total",
                "inicio",
                "ultima_actividad",
                "duracion_min",
                "estado",
            ]
        )
        for entry in rows:
            work, grade = entry["work"], entry["grade"]
            base = [work.filename] + [work.student.get(f, "") for f in student_fields]
            if grade is None:
                writer.writerow(base + [""] * 7 + ["INVÁLIDA: " + " ".join(work.errors)])
            else:
                writer.writerow(
                    [
                        *base,
                        grade["required_done"],
                        grade["required_total"],
                        grade["required_pct"],
                        grade["choice_hits"],
                        grade["choice_total"],
                        grade["started"].strftime("%d/%m %H:%M") if grade["started"] else "",
                        grade["last"].strftime("%d/%m %H:%M") if grade["last"] else "",
                        grade["duration_min"] if grade["duration_min"] is not None else "",
                        "; ".join(work.warnings) or "OK",
                    ]
                )
    return report, output
