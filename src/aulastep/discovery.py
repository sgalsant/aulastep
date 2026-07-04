"""Descubrimiento de pasos: la carpeta pasos/ es la única fuente de verdad del orden."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from .errors import Report
from .models import STEP_FILE_PATTERN

STEPS_DIR = "pasos"


@dataclass
class DiscoveredStep:
    path: Path
    number: int
    slug: str


def discover_steps(activity_dir: Path, report: Report) -> list[DiscoveredStep]:
    """Localiza los Markdown de pasos/, exige el patrón NN-nombre.md y los ordena.

    Registra en el informe: carpeta ausente, archivos sin patrón válido,
    prefijos duplicados (error) y saltos de numeración (aviso).
    """
    steps_dir = activity_dir / STEPS_DIR
    if not steps_dir.is_dir():
        report.error("PASOS_AUSENTES", f"No existe la carpeta '{STEPS_DIR}/'.", str(steps_dir))
        return []

    found: list[DiscoveredStep] = []
    for entry in sorted(steps_dir.iterdir()):
        if entry.is_dir() or entry.name.startswith("."):
            continue
        m = STEP_FILE_PATTERN.match(entry.name)
        if not m:
            report.error(
                "PASO_NOMBRE_INVALIDO",
                f"'{entry.name}' no cumple el patrón NN-nombre-del-paso.md "
                f"({STEP_FILE_PATTERN.pattern}).",
                str(entry),
            )
            continue
        found.append(DiscoveredStep(path=entry, number=int(m.group(1)), slug=m.group(2)))

    if not found:
        report.error(
            "SIN_PASOS", "La carpeta 'pasos/' no contiene ningún paso válido.", str(steps_dir)
        )
        return []

    found.sort(key=lambda s: (s.number, s.path.name))

    seen: dict[int, DiscoveredStep] = {}
    for step in found:
        if step.number in seen:
            report.error(
                "PASO_PREFIJO_DUPLICADO",
                f"Prefijo {step.number:02d} duplicado: '{seen[step.number].path.name}' y '{step.path.name}'.",
                str(step.path),
            )
        else:
            seen[step.number] = step

    numbers = sorted(seen)
    for prev, cur in pairwise(numbers):
        if cur - prev > 1:
            report.warning(
                "PASO_SALTO_NUMERACION",
                f"Salto de numeración entre {prev:02d} y {cur:02d}.",
                str(steps_dir),
            )
    return found
