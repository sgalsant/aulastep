# Contribuir a AulaStep

¡Gracias por tu interés! Guía rápida para ponerte a trabajar.

## Entorno

Requisitos: Python 3.12+, Node 20+ y [uv](https://docs.astral.sh/uv/).

```bash
git clone <tu-fork>
cd aulastep
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
npm ci
```

## Pruebas y calidad

Antes de abrir un PR, todo esto debe quedar en verde:

```bash
ruff check src tests/python     # estilo y errores comunes
pytest                          # generador (Python)
npm test                        # reproductor (Vitest en Node)
npx playwright install chromium # solo la primera vez
npx playwright test             # E2E + accesibilidad (axe)
```

El CI (`.github/workflows/pages.yml`) ejecuta exactamente lo mismo.

## Convenciones

- **Idioma**: todo lo visible por docentes y alumnado (CLI, errores, web,
  documentación) en español. Los identificadores de código, en inglés.
- **Python**: tipado, sin dependencias nuevas sin justificación; los mensajes
  de error de validación deben decir archivo, problema y cómo arreglarlo.
- **JavaScript**: módulos ES nativos, sin frameworks ni paso de build; nada de
  `localStorage` (IndexedDB) y sin depender de red en el reproductor.
- **Actividades**: sigue las reglas de `AGENTS.md`; aplican igual a humanos.
- **Commits**: mensaje en imperativo y descriptivo («Añade validación de
  enlaces paso:», no «cambios»).

## Dónde tocar qué

| Quiero… | Carpeta |
|---|---|
| Cambiar validación o compilación | `src/aulastep/*.py` + `tests/python/` |
| Cambiar el reproductor | `src/aulastep/player/assets/` + `tests/frontend/` |
| Cambiar la plantilla HTML | `src/aulastep/templates/index.html.j2` |
| Añadir un tema | `themes.css`, `branding.py`, `app.js` (ver `docs/temas.md`) |
| Documentar | `README.md`, `docs/` |

## Publicar cambios en una actividad ya repartida

Sube `actividad.version` y nunca cambies IDs publicados (detalles en
`AGENTS.md` y `docs/aulawork.md`).
