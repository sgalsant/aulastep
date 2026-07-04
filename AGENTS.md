# AGENTS.md — Reglas para editar este repositorio con agentes de IA

Este archivo define cómo debe comportarse cualquier agente de IA (opencode,
Claude Code, Copilot…) al crear o modificar **actividades AulaStep**. Las
actividades las siguen alumnos reales que guardan trabajo asociado a los IDs:
una edición descuidada destruye su progreso.

## Reglas de oro (no negociables)

1. **Nunca cambies un `id` ya publicado**: ni el `id` de la actividad, ni el
   `id` de un paso, ni el `id` de una directiva interactiva (`task`,
   `question`, `evidence`, `file`, `reflection`, `checkpoint`). El trabajo del
   alumnado se guarda con esas claves. Para retirar algo, elimina la directiva;
   para añadir algo, crea un `id` nuevo. No reutilices IDs retirados con otro
   significado.
2. **Un paso = un archivo Markdown** en `pasos/`. No fusiones varios pasos en
   un archivo ni declares pasos en `actividad.yml`: los pasos **no** se listan
   en el YAML.
3. **El orden lo marca solo el nombre de archivo** (`01-…`, `02-…`). Para
   reordenar, renombra archivos; no inventes campos de orden.
4. **IDs semánticos**: en minúsculas con guiones, descriptivos del contenido
   (`captura-servicio`, `pregunta-dora`), nunca genéricos (`q1`, `paso2`).
5. **No publiques soluciones evaluables**: la marca `- [x]` de las preguntas de
   elección documenta la respuesta esperada en el fuente y jamás debe aparecer
   en texto visible para el alumno. La única excepción son los bloques
   `:::solution`, pensados para soluciones **didácticas** (no evaluables):
   su contenido sí se publica en `activity.json` tras una confirmación en la
   interfaz, y un alumno con conocimientos puede leerlo. Nunca pongas dentro
   de `:::solution` la respuesta de una `:::question`.
6. **Tras cualquier cambio, ejecuta `aulastep validate <carpeta>`** y no des el
   trabajo por terminado hasta que salga sin errores. Si tocaste algo visual,
   ejecuta también `aulastep build` y revisa `dist/`.
7. **Sube la versión** (`actividad.version`, semántica) en cada modificación de
   una actividad ya repartida: el reproductor avisa al alumno importar trabajo
   de una versión anterior y conserva sus respuestas huérfanas.
8. **No introduzcas JSX, JavaScript ni HTML en los Markdown**: el HTML embebido
   se escapa y los scripts no se ejecutan jamás. Todo lo interactivo se expresa
   con directivas.
9. **Modifica solo lo necesario**: no reformatees ni reescribas pasos que no
   forman parte de la petición; los diffs pequeños se revisan mejor.
10. **No elimines preguntas, evidencias o adjuntos sin advertirlo
    expresamente**: cada eliminación destruye las respuestas asociadas del
    alumnado; señálalo siempre en tu respuesta o en el PR.
11. **Mantén la accesibilidad**: texto alternativo en todas las imágenes,
    enlaces con texto descriptivo (no «pincha aquí») y sin transmitir
    información solo mediante color.

## Convenciones del contenido

- Todo el texto visible en **español**, tono directo dirigido al alumno («tú»).
- Directivas: cuerpo en Markdown; atributos siempre entre comillas dobles
  (`id="…" required="true"`); cierre `:::` obligatorio; sin anidar.
- Recursos en `recursos/` y referenciados con ruta relativa
  (`recursos/imagen.png`); nada de rutas absolutas ni `..`.
- Enlaces entre pasos con `paso:` (`[texto](paso:id-del-paso)`), nunca con
  rutas de archivo ni anclas manuales.
- Preguntas de elección: mínimo 2 opciones; `single-choice` con exactamente
  una `- [x]`.

## Al crear una actividad nueva

1. `aulastep init <carpeta>` como punto de partida.
2. Rellena `actividad.yml` (el esquema formal está en
   `schemas/actividad.schema.json`).
3. Escribe los pasos con numeración `01-`, `02-`… dejando huecos (`10-`, `20-`)
   si prevés insertar pasos después.
4. Termina siempre con un paso de entrega que incluya `:::reflection` y el
   recordatorio de exportar el `.aulawork`.

## Sobre el código del generador y el reproductor

- Python: `ruff check src tests/python` y `pytest` deben quedar en verde.
- JavaScript: `npm test` (Vitest) debe quedar en verde; los módulos del
  reproductor no usan frameworks ni herramientas de build.
- No añadas dependencias nuevas sin justificarlo en el PR.
