"""Interfaz de línea de órdenes de AulaStep."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import branding
from .compiler import build as compile_build
from .errors import AulaStepError, Report
from .grading import grade_folder
from .preview import preview as run_preview
from .project import load_project
from .publish import publish as run_publish
from .scaffold import init_activity

app = typer.Typer(
    name=branding.APP_SLUG,
    help=f"{branding.APP_NAME} — {branding.TAGLINE}. Genera actividades web estáticas desde Markdown.",
    no_args_is_help=True,
)
console = Console()

RutaActividad = Annotated[
    Path, typer.Argument(help="Carpeta de la actividad (contiene actividad.yml).")
]


def _print_report(report: Report) -> None:
    for issue in report.issues:
        style = "red" if issue.level.value == "error" else "yellow"
        console.print(f"[{style}]{issue}[/{style}]")


@app.command()
def init(nombre: Annotated[Path, typer.Argument(help="Carpeta de la nueva actividad.")]) -> None:
    """Crea el esqueleto de una actividad nueva."""
    try:
        target = init_activity(nombre)
    except AulaStepError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(f"[green]Actividad creada en[/green] {target}")
    console.print(f"Siguiente paso: [bold]{branding.APP_SLUG} preview {target}[/bold]")


@app.command()
def validate(ruta: RutaActividad) -> None:
    """Valida YAML, estructura, pasos, IDs, directivas, recursos y enlaces."""
    loader = load_project(ruta)
    _print_report(loader.report)
    if loader.report.ok:
        n = len(loader.compiled.steps) if loader.compiled else 0
        console.print(
            f"[green]Validación correcta[/green]: {n} pasos, {len(loader.report.warnings)} avisos."
        )
    else:
        console.print(f"[red]Validación con errores[/red]: {len(loader.report.errors)} errores.")
        raise typer.Exit(1)


@app.command()
def build(
    ruta: RutaActividad,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Carpeta de salida (por defecto dist/).")
    ] = None,
    base_url: Annotated[
        str, typer.Option("--base-url", help="Subruta pública, p. ej. /repositorio/.")
    ] = "",
    clean: Annotated[
        bool, typer.Option("--clean", help="Borra la salida antes de compilar.")
    ] = False,
) -> None:
    """Compila la actividad a una web estática lista para publicar."""
    report, dist = compile_build(ruta, output=output, base_url=base_url, clean=clean)
    _print_report(report)
    if dist is None:
        console.print("[red]Compilación fallida.[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Compilado en[/green] {dist}")


@app.command()
def grade(
    actividad: Annotated[
        Path,
        typer.Argument(help="Carpeta FUENTE de la actividad (con las marcas [x] de corrección)."),
    ],
    entregas: Annotated[
        Path, typer.Argument(help="Carpeta con los .aulawork entregados por el alumnado.")
    ],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Carpeta de salida del informe.")
    ] = Path("informe"),
    title: Annotated[
        str, typer.Option("--title", help="Título del informe.")
    ] = "Informe de corrección",
) -> None:
    """Corrige un lote de entregas .aulawork: verifica integridad, autocorrige
    las preguntas de elección y genera informe HTML + resumen.csv."""
    report, out = grade_folder(actividad, entregas, output=output, title=title)
    _print_report(report)
    if out is None:
        console.print("[red]Corrección fallida.[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Informe generado en[/green] {out / 'index.html'}")
    console.print(f"[green]Resumen CSV en[/green] {out / 'resumen.csv'}")


@app.command()
def publish(
    carpeta: Annotated[
        Path,
        typer.Argument(help="Carpeta que contiene actividades (subcarpetas con actividad.yml)."),
    ],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Carpeta de salida del sitio.")
    ] = Path("_site"),
    clean: Annotated[
        bool, typer.Option("--clean", help="Borra la salida antes de compilar.")
    ] = False,
    title: Annotated[
        str, typer.Option("--title", help="Título del índice de actividades.")
    ] = "Actividades",
) -> None:
    """Compila TODAS las actividades de una carpeta, cada una en su subcarpeta,
    y genera un índice raíz con enlaces. Pensado para GitHub Pages."""
    report, site = run_publish(carpeta, output=output, clean=clean, title=title)
    _print_report(report)
    if site is None:
        console.print("[red]Publicación fallida.[/red]")
        raise typer.Exit(1)
    n = len([p for p in site.iterdir() if p.is_dir()])
    console.print(f"[green]Publicadas {n} actividades en[/green] {site}")


@app.command()
def preview(
    ruta: RutaActividad,
    port: Annotated[int, typer.Option("--port", "-p", help="Puerto local.")] = 8765,
    no_browser: Annotated[
        bool, typer.Option("--no-browser", help="No abrir el navegador.")
    ] = False,
) -> None:
    """Valida, compila y sirve la actividad en local, recompilando al vuelo."""
    run_preview(ruta, port=port, open_browser=not no_browser)


@app.command()
def inspect(ruta: RutaActividad) -> None:
    """Muestra la estructura detectada: pasos, orden y elementos interactivos."""
    loader = load_project(ruta)
    _print_report(loader.report)
    if not loader.report.ok or loader.compiled is None:
        raise typer.Exit(1)
    meta = loader.compiled.activity
    console.print(f"[bold]{meta['titulo']}[/bold] · v{meta['version']} · tema {meta['tema']}")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Orden", justify="right")
    table.add_column("Archivo")
    table.add_column("ID")
    table.add_column("Título")
    table.add_column("Interactivos")
    for step in loader.compiled.steps:
        interactives = (
            ", ".join(f"{s.type}:{s.id}" for s in step.segments if s.type != "html") or "—"
        )
        table.add_row(str(step.orden + 1), step.archivo, step.id, step.titulo, interactives)
    console.print(table)


if __name__ == "__main__":
    app()
