"""Renderizado Markdown → HTML.

Se realiza íntegramente en Python durante la compilación. El navegador nunca
interpreta Markdown. El HTML embebido está desactivado: se escapa como texto.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import cast

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict
from mdit_py_plugins.footnote import footnote_plugin

_ATTACHMENT_LINK_RE = re.compile(r'href="(recursos/[^"]+)"')


def _build_renderer() -> MarkdownIt:
    md = (
        MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
        .enable("table")
        .enable("strikethrough")
        .use(footnote_plugin)
    )
    renderer = md.renderer
    assert isinstance(renderer, RendererHTML)  # preset "commonmark" → RendererHTML

    # Los enlaces externos se abren en pestaña nueva con protecciones.
    LinkRule = Callable[[Sequence[Token], int, OptionsDict, EnvType], str]
    default_link = cast("LinkRule | None", renderer.rules.get("link_open"))

    def link_open(
        self: RendererHTML,
        tokens: Sequence[Token],
        idx: int,
        options: OptionsDict,
        env: EnvType,
    ) -> str:
        token = tokens[idx]
        href = token.attrGet("href") or ""
        if isinstance(href, str) and href.startswith(("http://", "https://")):
            token.attrSet("target", "_blank")
            token.attrSet("rel", "noopener noreferrer")
        if default_link:
            return default_link(tokens, idx, options, env)
        return self.renderToken(tokens, idx, options, env)

    md.add_render_rule("link_open", link_open)

    # Las tablas se envuelven para poder desplazarse en horizontal en móvil
    # sin desbordar la página (los datos de red suelen ser anchos).
    def table_open(
        self: RendererHTML,
        tokens: Sequence[Token],
        idx: int,
        options: OptionsDict,
        env: EnvType,
    ) -> str:
        return '<div class="table-scroll">' + self.renderToken(tokens, idx, options, env)

    def table_close(
        self: RendererHTML,
        tokens: Sequence[Token],
        idx: int,
        options: OptionsDict,
        env: EnvType,
    ) -> str:
        return self.renderToken(tokens, idx, options, env) + "</div>"

    md.add_render_rule("table_open", table_open)
    md.add_render_rule("table_close", table_close)
    return md


_md = _build_renderer()


def render_markdown(text: str) -> str:
    """Convierte Markdown en HTML seguro (sin HTML embebido, sin scripts)."""
    html = _md.render(text)
    # Los enlaces a recursos locales se marcan como descargables.
    html = _ATTACHMENT_LINK_RE.sub(r'href="\1" download class="as-resource-link"', html)
    return html.strip()


def render_inline(text: str) -> str:
    """Renderiza una línea de Markdown sin envolver en <p>."""
    html: str = _md.renderInline(text)
    return html.strip()


def extract_local_refs(text: str) -> list[str]:
    """Extrae referencias locales (imágenes y enlaces a recursos/) para validarlas."""
    refs: list[str] = []
    for m in re.finditer(r"!\[[^\]]*\]\(([^)\s]+)[^)]*\)", text):
        refs.append(m.group(1))
    for m in re.finditer(r"(?<!!)\[[^\]]*\]\(([^)\s]+)[^)]*\)", text):
        refs.append(m.group(1))
    return [r for r in refs if not r.startswith(("http://", "https://", "mailto:", "#", "paso:"))]


def extract_step_links(text: str) -> list[str]:
    """Enlaces internos entre pasos con el esquema 'paso:id-del-paso'."""
    return re.findall(r"\]\(paso:([a-z0-9-]+)\)", text)
