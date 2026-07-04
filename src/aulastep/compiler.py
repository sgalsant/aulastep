"""Compilador: proyecto fuente → aplicación web estática en dist/."""

from __future__ import annotations

import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import branding
from .errors import AulaStepError, Report
from .project import RESOURCES_DIR, ProjectLoader, load_project

PLAYER_DIR = Path(__file__).parent / "player"
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def build(
    activity_dir: Path,
    output: Path | None = None,
    base_url: str = "",
    clean: bool = False,
) -> tuple[Report, Path | None]:
    """Valida y compila. Devuelve (informe, ruta_dist | None si hubo errores)."""
    loader: ProjectLoader = load_project(activity_dir)
    report = loader.report
    if not report.ok or loader.compiled is None or loader.config is None:
        return report, None

    dist = (output or (activity_dir / "dist")).resolve()
    if clean and dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True, exist_ok=True)

    # 1. activity.json — el navegador nunca interpreta Markdown.
    (dist / "activity.json").write_text(loader.compiled.to_json() + "\n", encoding="utf-8")

    # 2. Reproductor común (assets).
    assets_src = PLAYER_DIR / "assets"
    assets_dst = dist / "assets"
    if assets_dst.exists():
        shutil.rmtree(assets_dst)
    shutil.copytree(assets_src, assets_dst)

    # 3. Recursos de la actividad.
    resources_src = activity_dir / RESOURCES_DIR
    resources_dst = dist / RESOURCES_DIR
    if resources_dst.exists():
        shutil.rmtree(resources_dst)
    if resources_src.is_dir():
        shutil.copytree(resources_src, resources_dst)

    # 4. index.html desde plantilla. Las rutas son relativas, por lo que la
    #    salida funciona bajo cualquier subruta (GitHub Pages incluido).
    meta = loader.config.actividad
    if base_url and not base_url.endswith("/"):
        base_url += "/"
    html = (
        _jinja_env()
        .get_template("index.html.j2")
        .render(
            app_name=branding.APP_NAME,
            logo_text=branding.LOGO_TEXT,
            app_version=branding.APP_VERSION,
            titulo=meta.titulo,
            subtitulo=meta.subtitulo,
            descripcion=meta.descripcion.strip(),
            tema=meta.tema,
            base_url=base_url,
        )
    )
    (dist / "index.html").write_text(html, encoding="utf-8")
    return report, dist


def build_or_raise(
    activity_dir: Path,
    output: Path | None = None,
    base_url: str = "",
    clean: bool = False,
) -> Path:
    report, dist = build(activity_dir, output=output, base_url=base_url, clean=clean)
    if dist is None:
        raise AulaStepError("La actividad no compila: corrige los errores de validación.", report)
    return dist
