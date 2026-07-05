# Temas visuales

El tema se fija en `actividad.yml` (`actividad.tema`) y define la paleta por
defecto. El alumno puede cambiarlo desde el selector de la barra superior; su
preferencia se guarda en su navegador y no afecta a nadie más.

| Tema | Carácter | Fondo |
|---|---|---|
| `oceano` | azules verdosos, sobrio (por defecto) | claro |
| `bosque` | verdes naturales | claro |
| `indigo` | violetas académicos | claro |
| `ambar` | tierras cálidas | claro |
| `grafito` | alto contraste técnico | **oscuro** |
| `coral` | rojizos enérgicos | claro |
| `halloween` | calabaza sobre púrpura nocturno (estacional) | **oscuro** |

## Cómo funcionan

Todo el estilo vive en `styles.css`, que consume exclusivamente *tokens* CSS
(`--c-bg`, `--c-surface`, `--c-text`, `--c-primary`, `--c-accent`,
`--c-border`, estados `--c-success/warning/danger/info`, código
`--c-code-bg/--c-code-text`, y progreso `--c-progress/--c-active/--c-done`).
Cada tema de `themes.css` es solo un bloque `[data-theme="nombre"]` que asigna
esos tokens. Los pares texto/fondo de todos los temas cumplen contraste WCAG AA.

## Crear un tema propio

1. Copia un bloque de `src/aulastep/player/assets/themes.css` y renómbralo,
   p. ej. `[data-theme="instituto"]`.
2. Ajusta los tokens comprobando contraste AA (relación ≥ 4.5:1 para texto).
3. Añade el nombre a `THEMES` en `src/aulastep/branding.py` (validador) y al
   array `THEMES` de `src/aulastep/player/assets/app.js` (selector).
4. `aulastep build` de nuevo: los assets se copian en cada compilación.
