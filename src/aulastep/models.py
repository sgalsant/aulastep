"""Modelos de datos (Pydantic) del proyecto fuente y de la actividad compilada."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import branding

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
STEP_FILE_PATTERN = re.compile(r"^(\d{2,3})-([a-z0-9][a-z0-9-]*)\.md$")

InteractiveKind = Literal["task", "question", "evidence", "file", "reflection", "checkpoint"]
CalloutKind = Literal["note", "tip", "warning", "danger", "details"]
QuestionType = Literal["short-text", "long-text", "single-choice", "multi-choice", "numeric"]

DIRECTIVE_KINDS: tuple[str, ...] = (
    "note",
    "tip",
    "warning",
    "danger",
    "details",
    "hint",
    "solution",
    "task",
    "question",
    "evidence",
    "file",
    "reflection",
    "checkpoint",
)


def _check_id(value: str) -> str:
    if not ID_PATTERN.match(value):
        raise ValueError(
            f"ID no válido: '{value}'. Usa minúsculas, dígitos y guiones (patrón {ID_PATTERN.pattern})."
        )
    return value


class StudentField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    etiqueta: str
    tipo: Literal["texto"] = "texto"
    obligatorio: bool = False

    _vid = field_validator("id")(_check_id)


class LicenseConfig(BaseModel):
    """Licencia de la actividad. Por defecto, CC BY-NC-SA 4.0.

    La referencia se muestra siempre en la portada y en el pie del reproductor.
    """

    model_config = ConfigDict(extra="forbid")
    nombre: str = "CC BY-NC-SA 4.0"
    nombre_completo: str = (
        "Creative Commons Atribución-NoComercial-CompartirIgual 4.0 Internacional"
    )
    url: str = "https://creativecommons.org/licenses/by-nc-sa/4.0/deed.es"
    condiciones: list[str] = Field(
        default_factory=lambda: [
            "se reconozca adecuadamente la autoría;",
            "no se utilice con fines comerciales;",
            "cualquier obra derivada se distribuya bajo esta misma licencia;",
            "se indiquen claramente los cambios realizados sobre el material original.",
        ]
    )


class ActivityMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    titulo: str
    subtitulo: str = ""
    version: str = "1.0.0"
    descripcion: str = ""
    autor: str = ""
    modulo: str = ""
    curso: str = ""
    duracion_minutos: int | None = Field(default=None, ge=0)
    tema: str = branding.DEFAULT_THEME
    licencia: LicenseConfig = Field(default_factory=LicenseConfig)

    _vid = field_validator("id")(_check_id)

    @field_validator("version")
    @classmethod
    def _semver(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"La versión debe ser semántica (x.y.z), no '{v}'.")
        return v


class NavigationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    modo: Literal["asistente", "libre", "secuencial"] = "asistente"
    permitir_anterior: bool = True
    permitir_saltar: bool = True
    mostrar_indice: bool = True
    mostrar_progreso: bool = True
    exigir_obligatorios_para_avanzar: bool = False


class StudentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campos: list[StudentField] = Field(default_factory=list)


class WorkConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    autoguardado: bool = True
    intervalo_autoguardado_segundos: int = Field(default=5, ge=1)
    permitir_exportar: bool = True
    permitir_importar: bool = True
    extension: str = branding.WORK_EXTENSION
    patron_nombre: str = "{actividad}_{alumno}_{fecha}." + branding.WORK_EXTENSION


class LimitsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tamano_maximo_captura_mb: int = Field(default=8, ge=1)
    tamano_maximo_adjunto_mb: int = Field(default=20, ge=1)
    tamano_maximo_paquete_mb: int = Field(default=100, ge=1)


class ActivityConfig(BaseModel):
    """Contenido validado de actividad.yml."""

    model_config = ConfigDict(extra="forbid")
    schema_version: str = branding.SCHEMA_VERSION
    actividad: ActivityMeta
    navegacion: NavigationConfig = Field(default_factory=NavigationConfig)
    alumno: StudentConfig = Field(default_factory=StudentConfig)
    trabajo: WorkConfig = Field(default_factory=WorkConfig)
    limites: LimitsConfig = Field(default_factory=LimitsConfig)


class StepFrontMatter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    titulo: str
    descripcion: str = ""
    duracion_minutos: int | None = Field(default=None, ge=0)
    obligatorio: bool = True

    _vid = field_validator("id")(_check_id)


class ChoiceOption(BaseModel):
    id: str
    html: str
    correct: bool = False


class Directive(BaseModel):
    """Directiva ':::tipo{...}' extraída de un paso."""

    kind: str
    attrs: dict[str, str] = Field(default_factory=dict)
    body: str = ""
    line: int = 0

    @property
    def id(self) -> str:
        return self.attrs.get("id", "")

    @property
    def required(self) -> bool:
        return self.attrs.get("required", "false").lower() == "true"


class Segment(BaseModel):
    """Segmento compilado de un paso: HTML estático o componente interactivo."""

    type: str  # "html" | InteractiveKind
    html: str = ""
    id: str = ""
    required: bool = False
    question_type: QuestionType | None = Field(default=None, serialization_alias="questionType")
    options: list[dict[str, Any]] | None = None
    accept: str | None = None
    label: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class CompiledStep(BaseModel):
    id: str
    titulo: str
    descripcion: str = ""
    duracion_minutos: int | None = Field(default=None, serialization_alias="duracionMinutos")
    obligatorio: bool = True
    orden: int = 0
    archivo: str = ""
    segments: list[Segment] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class CompiledActivity(BaseModel):
    """Estructura serializada en activity.json para el reproductor."""

    schema_version: str = Field(serialization_alias="schemaVersion")
    generator: dict[str, str]
    activity: dict[str, Any]
    navegacion: dict[str, Any]
    alumno: dict[str, Any]
    trabajo: dict[str, Any]
    limites: dict[str, Any]
    steps: list[CompiledStep]

    model_config = ConfigDict(populate_by_name=True)

    def to_json(self) -> str:
        return self.model_dump_json(by_alias=True, indent=2)
