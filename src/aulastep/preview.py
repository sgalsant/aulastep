"""`aulastep preview`: servidor local de desarrollo con recompilación automática.

Solo es una herramienta de desarrollo; el producto final no necesita servidor.
"""

from __future__ import annotations

import contextlib
import functools
import http.server
import tempfile
import threading
import webbrowser
from pathlib import Path

from rich.console import Console

from .compiler import build

console = Console()


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        pass

    def end_headers(self) -> None:  # sin caché durante el desarrollo
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def preview(
    activity_dir: Path, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True
) -> None:
    activity_dir = activity_dir.resolve()
    with tempfile.TemporaryDirectory(prefix="aulastep-preview-") as tmp:
        dist = Path(tmp) / "dist"

        def rebuild() -> bool:
            report, out = build(activity_dir, output=dist, clean=False)
            for issue in report.issues:
                style = "red" if issue.level.value == "error" else "yellow"
                console.print(f"[{style}]{issue}[/{style}]")
            if out is None:
                console.print(
                    "[red]La actividad no compila; se mantiene la última versión válida.[/red]"
                )
                return False
            console.print(f"[green]Compilado[/green] → {out}")
            return True

        if not rebuild():
            console.print("[red]Corrige los errores para poder previsualizar.[/red]")
            return

        handler = functools.partial(_QuietHandler, directory=str(dist))
        server = http.server.ThreadingHTTPServer((host, port), handler)
        url = f"http://{host}:{port}/"
        console.print(f"[bold]Previsualización[/bold] en {url}  (Ctrl+C para salir)")
        threading.Thread(target=server.serve_forever, daemon=True).start()
        if open_browser:
            with contextlib.suppress(Exception):
                webbrowser.open(url)

        try:
            from watchfiles import watch

            for _changes in watch(activity_dir, recursive=True):
                console.print("[dim]Cambios detectados; recompilando…[/dim]")
                rebuild()
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            console.print("Previsualización detenida.")
