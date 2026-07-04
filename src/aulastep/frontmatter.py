"""Carga de YAML: actividad.yml y front matter de los pasos."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .errors import Report
from .models import ActivityConfig, StepFrontMatter

_yaml = YAML(typ="safe")
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
CONFIG_FILE = "actividad.yml"


def _format_pydantic_errors(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "(raíz)"
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


def load_activity_config(activity_dir: Path, report: Report) -> ActivityConfig | None:
    path = activity_dir / CONFIG_FILE
    if not path.is_file():
        report.error("CONFIG_AUSENTE", f"No existe '{CONFIG_FILE}'.", str(path))
        return None
    try:
        data: Any = _yaml.load(path.read_text(encoding="utf-8"))
    except YAMLError as exc:
        report.error("CONFIG_YAML", f"YAML no válido: {exc}", str(path))
        return None
    if not isinstance(data, dict):
        report.error("CONFIG_YAML", "El YAML raíz debe ser un mapa de claves.", str(path))
        return None
    try:
        return ActivityConfig.model_validate(data)
    except ValidationError as exc:
        report.error("CONFIG_ESQUEMA", _format_pydantic_errors(exc), str(path))
        return None


def split_front_matter(text: str) -> tuple[dict[str, Any] | None, str, str | None]:
    """Devuelve (front_matter, cuerpo, error)."""
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return None, text, "El paso no comienza con front matter '---'."
    try:
        data = _yaml.load(m.group(1)) or {}
    except YAMLError as exc:
        return None, text[m.end() :], f"Front matter YAML no válido: {exc}"
    if not isinstance(data, dict):
        return None, text[m.end() :], "El front matter debe ser un mapa de claves."
    return data, text[m.end() :], None


def parse_step_front_matter(path: Path, report: Report) -> tuple[StepFrontMatter | None, str]:
    text = path.read_text(encoding="utf-8")
    data, body, err = split_front_matter(text)
    if err:
        report.error("PASO_FRONT_MATTER", err, str(path))
        return None, body
    try:
        return StepFrontMatter.model_validate(data), body
    except ValidationError as exc:
        report.error("PASO_FRONT_MATTER", _format_pydantic_errors(exc), str(path))
        return None, body
