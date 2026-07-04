"""Publicación de un conjunto de actividades.

Compila todas las actividades encontradas en una carpeta (subcarpetas con
`actividad.yml`), cada una en su propia subcarpeta de salida, y genera un
`index.html` raíz con el listado. Pensado para GitHub Pages:

    _site/
    ├── index.html          ← índice con enlaces
    ├── dhcp-kea-ubuntu/    ← una actividad por subcarpeta
    └── ftp-vsftpd/
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from . import branding
from .compiler import build
from .errors import Report
from .project import load_project

_env = Environment(
    loader=PackageLoader("aulastep", "templates"),
    autoescape=select_autoescape(["html", "j2"]),
)


def discover_activities(source_dir: Path) -> list[Path]:
    """Subcarpetas directas de source_dir que contienen actividad.yml, ordenadas."""
    if not source_dir.is_dir():
        return []
    return sorted(
        (p for p in source_dir.iterdir() if p.is_dir() and (p / "actividad.yml").is_file()),
        key=lambda p: p.name,
    )


def publish(
    source_dir: Path,
    output: Path,
    clean: bool = False,
    title: str = "Actividades",
) -> tuple[Report, Path | None]:
    """Compila cada actividad en output/<id>/ y escribe el índice raíz.

    Devuelve (informe, ruta de salida | None si hubo errores).
    """
    report = Report()
    activities = discover_activities(source_dir)
    if not activities:
        report.error(
            "PUBLICACION_SIN_ACTIVIDADES",
            f"No hay actividades en '{source_dir}': se esperan subcarpetas con actividad.yml.",
        )
        return report, None

    if clean and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    seen_ids: dict[str, Path] = {}
    for activity_dir in activities:
        loader = load_project(activity_dir)
        if not loader.report.ok or loader.compiled is None:
            for issue in loader.report.issues:
                report.issues.append(issue)
            report.error(
                "PUBLICACION_ACTIVIDAD_INVALIDA",
                f"La actividad '{activity_dir.name}' no valida; corrige sus errores.",
            )
            continue
        meta = loader.compiled.activity
        aid = str(meta["id"])
        if aid in seen_ids:
            report.error(
                "PUBLICACION_ID_DUPLICADO",
                f"ID de actividad '{aid}' repetido en '{activity_dir.name}' "
                f"y '{seen_ids[aid].name}': cada actividad publicada necesita un id único.",
            )
            continue
        seen_ids[aid] = activity_dir

        sub_report, dist = build(activity_dir, output=output / aid, clean=True)
        for issue in sub_report.issues:
            report.issues.append(issue)
        if dist is None:
            continue
        entries.append(
            {
                "id": aid,
                "titulo": meta["titulo"],
                "subtitulo": meta.get("subtitulo", ""),
                "descripcion": meta.get("descripcion", ""),
                "modulo": meta.get("modulo", ""),
                "curso": meta.get("curso", ""),
                "duracion": meta.get("duracionMinutos"),
                "version": meta.get("version", ""),
                "autor": meta.get("autor", ""),
                "licencia": meta.get("licencia", {}),
                "pasos": len(loader.compiled.steps),
            }
        )

    if not report.ok:
        return report, None

    template = _env.get_template("publish-index.html.j2")
    html = template.render(
        title=title,
        entries=entries,
        app_name=branding.APP_NAME,
        app_version=branding.APP_VERSION,
    )
    (output / "index.html").write_text(html, encoding="utf-8")
    return report, output
