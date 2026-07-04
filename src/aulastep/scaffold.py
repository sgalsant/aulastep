"""`aulastep init`: crea el esqueleto de una actividad nueva."""

from __future__ import annotations

from pathlib import Path

from . import branding
from .errors import AulaStepError

_ACTIVIDAD_YML = """schema_version: "{schema}"

actividad:
  id: {aid}
  titulo: Título de la actividad
  subtitulo: Subtítulo opcional
  version: 1.0.0
  descripcion: >
    Describe brevemente qué va a aprender y hacer el alumnado.
  autor: Tu nombre
  modulo: Nombre del módulo
  curso: 1º SMR
  duracion_minutos: 60
  tema: {theme}
  # Referencia de licencia: se muestra siempre en la portada y en el pie.
  # Si se omite este bloque, se aplica CC BY-NC-SA 4.0 por defecto.
  licencia:
    nombre: CC BY-NC-SA 4.0
    nombre_completo: Creative Commons Atribución-NoComercial-CompartirIgual 4.0 Internacional
    url: https://creativecommons.org/licenses/by-nc-sa/4.0/deed.es

navegacion:
  modo: asistente
  permitir_anterior: true
  permitir_saltar: true
  mostrar_indice: true
  mostrar_progreso: true
  exigir_obligatorios_para_avanzar: false

alumno:
  campos:
    - id: nombre
      etiqueta: Nombre y apellidos
      tipo: texto
      obligatorio: true
    - id: grupo
      etiqueta: Grupo
      tipo: texto
      obligatorio: true

trabajo:
  autoguardado: true
  intervalo_autoguardado_segundos: 5
  permitir_exportar: true
  permitir_importar: true
  extension: {ext}
  patron_nombre: "{{actividad}}_{{alumno}}_{{fecha}}.{ext}"

limites:
  tamano_maximo_captura_mb: 8
  tamano_maximo_adjunto_mb: 20
  tamano_maximo_paquete_mb: 100
"""

_PASO_01 = """---
id: presentacion
titulo: Presentación
descripcion: Objetivos y contexto de la actividad
duracion_minutos: 10
obligatorio: true
---

## Objetivos

Explica aquí qué va a conseguir el alumnado.

:::note{id="nota-bienvenida"}
Este paso es un ejemplo generado por `aulastep init`. Edítalo libremente.
:::

:::question{id="pregunta-ejemplo" type="short-text" required="true"}
¿Con qué equipo vas a trabajar hoy?
:::
"""

_PASO_02 = """---
id: entrega
titulo: Entrega
descripcion: Resumen y exportación del trabajo
duracion_minutos: 5
obligatorio: true
---

## Entrega del trabajo

Revisa el resumen de pendientes y exporta tu trabajo con el botón
**Exportar trabajo para entregar**.

:::checkpoint{id="comprobacion-final" required="true"}
He revisado todas mis respuestas y capturas antes de exportar.
:::
"""


def init_activity(target: Path) -> Path:
    if target.exists() and any(target.iterdir()):
        raise AulaStepError(f"La carpeta '{target}' ya existe y no está vacía.")
    aid = target.name.lower().replace("_", "-")
    (target / "pasos").mkdir(parents=True)
    (target / "recursos").mkdir()
    (target / "actividad.yml").write_text(
        _ACTIVIDAD_YML.format(
            schema=branding.SCHEMA_VERSION,
            aid=aid,
            theme=branding.DEFAULT_THEME,
            ext=branding.WORK_EXTENSION,
        ),
        encoding="utf-8",
    )
    (target / "pasos" / "01-presentacion.md").write_text(_PASO_01, encoding="utf-8")
    (target / "pasos" / "02-entrega.md").write_text(_PASO_02, encoding="utf-8")
    (target / "recursos" / "README.md").write_text(
        "Coloca aquí imágenes, archivos de configuración y otros recursos de la actividad.\n",
        encoding="utf-8",
    )
    return target
