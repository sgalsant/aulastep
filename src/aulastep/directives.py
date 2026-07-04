"""Parser de directivas ':::tipo{...} ... :::'.

Divide el cuerpo Markdown de un paso en trozos alternos de Markdown normal
y directivas. Las directivas no se anidan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import Report
from .models import DIRECTIVE_KINDS, Directive

OPEN_RE = re.compile(r"^:::([a-zA-Z][a-zA-Z0-9_-]*)(\{[^}]*\})?\s*$")
CLOSE_RE = re.compile(r"^:::\s*$")
ATTR_RE = re.compile(r'([a-zA-Z][a-zA-Z0-9_-]*)\s*=\s*"([^"]*)"')
CHOICE_RE = re.compile(r"^[-*]\s+\[( |x|X)\]\s+(.+)$")


@dataclass
class Chunk:
    """Trozo de Markdown normal (kind='markdown') o directiva (kind='directive')."""

    kind: str
    text: str = ""
    directive: Directive | None = None
    line: int = 0


def parse_attrs(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    return dict(ATTR_RE.findall(raw[1:-1]))


def split_chunks(body: str, report: Report, location: str = "") -> list[Chunk]:
    lines = body.splitlines()
    chunks: list[Chunk] = []
    md_buffer: list[str] = []
    md_start = 1
    i = 0
    in_fence = False
    fence_marker = ""

    def flush_md() -> None:
        nonlocal md_buffer
        text = "\n".join(md_buffer).strip("\n")
        if text.strip():
            chunks.append(Chunk(kind="markdown", text=text, line=md_start))
        md_buffer = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # No interpretar directivas dentro de bloques de código vallados.
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence = False
            md_buffer.append(line)
            i += 1
            continue
        m = OPEN_RE.match(line) if not in_fence else None
        if not m:
            md_buffer.append(line)
            i += 1
            continue

        kind = m.group(1).lower()
        attrs = parse_attrs(m.group(2))
        if kind not in DIRECTIVE_KINDS:
            report.error(
                "DIRECTIVA_DESCONOCIDA",
                f"Directiva ':::{kind}' no reconocida. Tipos válidos: {', '.join(DIRECTIVE_KINDS)}.",
                f"{location}:{i + 1}",
            )
        flush_md()
        opening_line = i + 1
        i += 1
        directive_body: list[str] = []
        closed = False
        while i < len(lines):
            if CLOSE_RE.match(lines[i]):
                closed = True
                i += 1
                break
            directive_body.append(lines[i])
            i += 1
        if not closed:
            report.error(
                "DIRECTIVA_SIN_CIERRE",
                f"La directiva ':::{kind}' abierta en la línea {opening_line} no se cierra con ':::'.",
                f"{location}:{opening_line}",
            )
        if kind in DIRECTIVE_KINDS:
            chunks.append(
                Chunk(
                    kind="directive",
                    line=opening_line,
                    directive=Directive(
                        kind=kind,
                        attrs=attrs,
                        body="\n".join(directive_body).strip("\n"),
                        line=opening_line,
                    ),
                )
            )
        md_start = i + 1
    flush_md()
    return chunks


def parse_choices(body: str) -> tuple[str, list[tuple[str, bool]]]:
    """Separa el enunciado de una pregunta de elección de sus opciones '- [ ]'.

    Devuelve (markdown_del_enunciado, [(texto_opcion, es_correcta), ...]).
    """
    prompt_lines: list[str] = []
    options: list[tuple[str, bool]] = []
    for line in body.splitlines():
        m = CHOICE_RE.match(line.strip())
        if m:
            options.append((m.group(2).strip(), m.group(1).lower() == "x"))
        else:
            prompt_lines.append(line)
    return "\n".join(prompt_lines).strip("\n"), options
