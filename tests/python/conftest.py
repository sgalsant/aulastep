"""Fixtures compartidas: fábrica de actividades mínimas en carpetas temporales."""

from __future__ import annotations

from pathlib import Path

import pytest

MINIMAL_YML = """schema_version: "1.0"
actividad:
  id: demo
  titulo: Demo
  version: 1.0.0
  tema: oceano
alumno:
  campos:
    - id: nombre
      etiqueta: Nombre
      obligatorio: true
"""

STEP_TEMPLATE = """---
id: {sid}
titulo: {titulo}
obligatorio: true
---

{body}
"""


@pytest.fixture
def make_activity(tmp_path: Path):
    """Crea una actividad mínima y devuelve su ruta. Admite pasos extra."""

    def _make(steps: dict[str, str] | None = None, yml: str = MINIMAL_YML) -> Path:
        root = tmp_path / "actividad"
        (root / "pasos").mkdir(parents=True)
        (root / "recursos").mkdir()
        (root / "actividad.yml").write_text(yml, encoding="utf-8")
        default = {
            "01-inicio.md": STEP_TEMPLATE.format(
                sid="inicio", titulo="Inicio", body="Hola **mundo**."
            ),
        }
        for name, content in (steps or default).items():
            (root / "pasos" / name).write_text(content, encoding="utf-8")
        return root

    return _make
