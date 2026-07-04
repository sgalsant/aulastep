"""Carga completa del proyecto fuente y construcción del modelo compilado.

Es el corazón compartido por `validate`, `build`, `preview` e `inspect`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, cast

from . import branding
from .directives import Chunk, parse_choices, split_chunks
from .discovery import discover_steps
from .errors import Report
from .frontmatter import load_activity_config, parse_step_front_matter
from .markdown import extract_local_refs, extract_step_links, render_markdown
from .models import (
    ID_PATTERN,
    ActivityConfig,
    CompiledActivity,
    CompiledStep,
    Directive,
    QuestionType,
    Segment,
)

RESOURCES_DIR = "recursos"
CALLOUT_KINDS = ("note", "tip", "warning", "danger")
CALLOUT_LABELS = {"note": "Nota", "tip": "Consejo", "warning": "Atención", "danger": "Peligro"}
QUESTION_TYPES = ("short-text", "long-text", "single-choice", "multi-choice", "numeric")
CHOICE_TYPES = ("single-choice", "multi-choice")
INTERACTIVE_KINDS = ("task", "question", "evidence", "file", "reflection", "checkpoint")
STEP_LINK_RE = re.compile(r'href="paso:([a-z0-9-]+)"')
MAX_RESOURCE_MB = 20


def _rewrite_step_links(html: str) -> str:
    return STEP_LINK_RE.sub(r'href="#/paso/\1" class="as-step-link" data-step-link="\1"', html)


DISCLOSURE_KINDS = ("details", "hint", "solution")
DISCLOSURE_DEFAULTS = {
    "details": "Más información",
    "hint": "Pista",
    "solution": "Solución",
}


def _callout_html(kind: str, directive: Directive) -> str:
    if kind in DISCLOSURE_KINDS:
        summary = directive.attrs.get("summary", DISCLOSURE_DEFAULTS[kind])
        guarded = ' data-guarded="true"' if kind == "solution" else ""
        return (
            f'<details class="as-details as-details--{kind}"{guarded}>'
            f"<summary>{summary}</summary>"
            f'<div class="as-details-body">{render_markdown(directive.body)}</div></details>'
        )
    label = CALLOUT_LABELS[kind]
    return (
        f'<aside class="as-callout as-callout--{kind}" role="note">'
        f'<span class="as-callout-label">{label}</span>'
        f'<div class="as-callout-body">{render_markdown(directive.body)}</div></aside>'
    )


class ProjectLoader:
    def __init__(self, activity_dir: Path) -> None:
        self.dir = activity_dir.resolve()
        self.report = Report()
        self.config: ActivityConfig | None = None
        self.compiled: CompiledActivity | None = None
        # Clave de corrección: {id_pregunta: {"type", "correct": [ids], "options": {id: html}}}
        # Vive SOLO aquí; jamás viaja a activity.json ni a dist/.
        self.answer_key: dict[str, dict[str, Any]] = {}
        self._interactive_ids: dict[str, str] = {}  # id -> ubicación
        self._step_ids: dict[str, str] = {}
        self._resource_refs: list[tuple[str, str]] = []  # (ref, ubicación)
        self._step_links: list[tuple[str, str]] = []

    # ------------------------------------------------------------------ carga
    def load(self) -> ProjectLoader:
        self.config = load_activity_config(self.dir, self.report)
        if self.config is None:
            return self
        self._validate_config(self.config)
        steps = self._load_steps()
        if self.config and self.report.ok:
            self.compiled = self._assemble(self.config, steps)
        self._validate_step_links()
        return self

    def _validate_config(self, config: ActivityConfig) -> None:
        major = config.schema_version.split(".")[0]
        if major != branding.SCHEMA_VERSION.split(".")[0]:
            self.report.error(
                "SCHEMA_INCOMPATIBLE",
                f"schema_version '{config.schema_version}' incompatible con la herramienta "
                f"({branding.SCHEMA_VERSION}).",
                "actividad.yml",
            )
        if config.actividad.tema not in branding.THEMES:
            self.report.error(
                "TEMA_DESCONOCIDO",
                f"Tema '{config.actividad.tema}' no existe. Disponibles: {', '.join(branding.THEMES)}.",
                "actividad.yml",
            )
        seen: set[str] = set()
        for field in config.alumno.campos:
            if field.id in seen:
                self.report.error(
                    "CAMPO_ALUMNO_DUPLICADO",
                    f"Campo de alumno duplicado: '{field.id}'.",
                    "actividad.yml",
                )
            seen.add(field.id)

    def _load_steps(self) -> list[CompiledStep]:
        compiled_steps: list[CompiledStep] = []
        for order, found in enumerate(discover_steps(self.dir, self.report)):
            fm, body = parse_step_front_matter(found.path, self.report)
            if fm is None:
                continue
            rel = found.path.relative_to(self.dir).as_posix()
            if fm.id in self._step_ids:
                self.report.error(
                    "PASO_ID_DUPLICADO",
                    f"El ID de paso '{fm.id}' ya se usa en {self._step_ids[fm.id]}.",
                    rel,
                )
            self._step_ids[fm.id] = rel
            for ref in extract_local_refs(body):
                self._resource_refs.append((ref, rel))
            for target in extract_step_links(body):
                self._step_links.append((target, rel))
            segments = self._compile_chunks(split_chunks(body, self.report, rel), rel)
            compiled_steps.append(
                CompiledStep(
                    id=fm.id,
                    titulo=fm.titulo,
                    descripcion=fm.descripcion,
                    duracion_minutos=fm.duracion_minutos,
                    obligatorio=fm.obligatorio,
                    orden=order,
                    archivo=rel,
                    segments=segments,
                )
            )
        self._validate_resources()
        return compiled_steps

    # ------------------------------------------------------------- directivas
    def _compile_chunks(self, chunks: list[Chunk], location: str) -> list[Segment]:
        segments: list[Segment] = []
        for chunk in chunks:
            if chunk.kind == "markdown":
                segments.append(
                    Segment(type="html", html=_rewrite_step_links(render_markdown(chunk.text)))
                )
                continue
            directive = chunk.directive
            assert directive is not None
            where = f"{location}:{directive.line}"
            if directive.kind in CALLOUT_KINDS or directive.kind in DISCLOSURE_KINDS:
                segments.append(Segment(type="html", html=_callout_html(directive.kind, directive)))
                continue
            segment = self._compile_interactive(directive, where)
            if segment is not None:
                segments.append(segment)
        return segments

    def _register_id(self, directive: Directive, where: str) -> bool:
        did = directive.id
        if not did:
            self.report.error(
                "DIRECTIVA_SIN_ID",
                f"La directiva ':::{directive.kind}' no tiene atributo id.",
                where,
            )
            return False
        if not ID_PATTERN.match(did):
            self.report.error(
                "DIRECTIVA_ID_INVALIDO",
                f"ID '{did}' no válido (minúsculas, dígitos y guiones).",
                where,
            )
            return False
        if did in self._interactive_ids:
            self.report.error(
                "DIRECTIVA_ID_DUPLICADO",
                f"El ID '{did}' ya se usa en {self._interactive_ids[did]}.",
                where,
            )
            return False
        self._interactive_ids[did] = where
        return True

    def _compile_interactive(self, directive: Directive, where: str) -> Segment | None:
        if not self._register_id(directive, where):
            return None
        kind = directive.kind
        did = directive.id
        assert did is not None  # garantizado por _register_id
        required = directive.required

        if kind == "question":
            qtype_raw = directive.attrs.get("type", "short-text")
            if qtype_raw not in QUESTION_TYPES:
                self.report.error(
                    "PREGUNTA_TIPO_INVALIDO",
                    f"Tipo de pregunta '{qtype_raw}' no válido. Tipos: {', '.join(QUESTION_TYPES)}.",
                    where,
                )
                return None
            qtype = cast(QuestionType, qtype_raw)  # validado justo arriba
            if qtype in CHOICE_TYPES:
                prompt, options = parse_choices(directive.body)
                if len(options) < 2:
                    self.report.error(
                        "PREGUNTA_SIN_OPCIONES",
                        f"La pregunta '{did}' de tipo {qtype} necesita al menos dos opciones '- [ ]'.",
                        where,
                    )
                    return None
                marked = sum(1 for _, c in options if c)
                if qtype == "single-choice" and marked != 1:
                    self.report.warning(
                        "PREGUNTA_MARCADO_UNICO",
                        f"La pregunta '{did}' debería marcar exactamente una opción '[x]' "
                        f"(marcadas: {marked}). Las marcas no se publican al alumnado.",
                        where,
                    )
                # Las respuestas correctas NO se incluyen en la salida pública,
                # pero sí en la clave de corrección en memoria (aulastep grade).
                option_dicts: list[dict[str, Any]] = [
                    {"id": f"{did}-op{i + 1}", "html": render_markdown(text)}
                    for i, (text, _c) in enumerate(options)
                ]
                self.answer_key[did] = {
                    "type": qtype,
                    "correct": [
                        f"{did}-op{i + 1}" for i, (_t, correct) in enumerate(options) if correct
                    ],
                    "options": {o["id"]: o["html"] for o in option_dicts},
                }
                return Segment(
                    type=kind,
                    id=did,
                    required=required,
                    question_type=qtype,
                    html=render_markdown(prompt),
                    options=option_dicts,
                )
            return Segment(
                type=kind,
                id=did,
                required=required,
                question_type=qtype,
                html=render_markdown(directive.body),
            )

        if kind == "reflection":
            return Segment(
                type=kind,
                id=did,
                required=required,
                question_type="long-text",
                html=render_markdown(directive.body),
            )

        if kind == "file":
            return Segment(
                type=kind,
                id=did,
                required=required,
                html=render_markdown(directive.body),
                accept=directive.attrs.get("accept", ""),
            )

        if kind == "evidence":
            ev_type = directive.attrs.get("type", "screenshot")
            return Segment(
                type=kind,
                id=did,
                required=required,
                html=render_markdown(directive.body),
                label=ev_type,
            )

        # task y checkpoint
        return Segment(type=kind, id=did, required=required, html=render_markdown(directive.body))

    # ------------------------------------------------------------ validaciones
    def _validate_resources(self) -> None:
        for ref, where in self._resource_refs:
            if ref.startswith("/") or ".." in ref.split("/"):
                self.report.error(
                    "RECURSO_RUTA_INSEGURA",
                    f"Referencia '{ref}' fuera del proyecto: usa rutas relativas dentro de la actividad.",
                    where,
                )
                continue
            target = self.dir / ref
            if not target.is_file():
                self.report.error("RECURSO_AUSENTE", f"El recurso '{ref}' no existe.", where)
            elif target.stat().st_size > MAX_RESOURCE_MB * 1024 * 1024:
                self.report.warning(
                    "RECURSO_GRANDE",
                    f"'{ref}' supera {MAX_RESOURCE_MB} MB; encarecerá la publicación.",
                    where,
                )

    def _validate_step_links(self) -> None:
        for target, where in self._step_links:
            if target not in self._step_ids:
                self.report.error(
                    "ENLACE_PASO_ROTO",
                    f"El enlace interno 'paso:{target}' no apunta a ningún paso.",
                    where,
                )

    # -------------------------------------------------------------- ensamblado
    def _assemble(self, config: ActivityConfig, steps: list[CompiledStep]) -> CompiledActivity:
        meta = config.actividad
        return CompiledActivity(
            schema_version=config.schema_version,
            generator={"name": branding.APP_NAME, "version": branding.APP_VERSION},
            activity={
                "id": meta.id,
                "titulo": meta.titulo,
                "subtitulo": meta.subtitulo,
                "version": meta.version,
                "descripcion": meta.descripcion.strip(),
                "autor": meta.autor,
                "modulo": meta.modulo,
                "curso": meta.curso,
                "duracionMinutos": meta.duracion_minutos,
                "tema": meta.tema,
                "licencia": meta.licencia.model_dump(),
            },
            navegacion=config.navegacion.model_dump(),
            alumno=config.alumno.model_dump(),
            trabajo=config.trabajo.model_dump(),
            limites=config.limites.model_dump(),
            steps=steps,
        )


def load_project(activity_dir: Path) -> ProjectLoader:
    return ProjectLoader(activity_dir).load()
