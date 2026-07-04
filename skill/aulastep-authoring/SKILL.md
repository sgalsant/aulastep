---
name: aulastep-authoring
description: Crea actividades educativas guiadas en formato AulaStep (Markdown con directivas) y las compila a una web estática HTML lista para distribuir al alumnado. Usa esta skill siempre que el usuario pida crear, editar o publicar una "actividad", "práctica guiada", "guion de práctica", "ficha de trabajo" o "actividad AulaStep" para estudiantes (especialmente de FP informática), convertir apuntes o una práctica a formato interactivo/web, generar un paquete HTML para entregar a alumnos, o mencione archivos actividad.yml, pasos numerados en Markdown, directivas :::task/:::question, o el formato .aulawork. Aplica también si solo pide "una práctica de <tema> para mis alumnos" sin nombrar AulaStep.
---

# Autoría de actividades AulaStep

AulaStep convierte una carpeta con `actividad.yml` + `pasos/*.md` + `recursos/`
en una web estática (HTML5/CSS/JS) donde el alumnado sigue la práctica paso a
paso, responde preguntas, sube capturas y exporta su trabajo en un archivo
`.aulawork`. Esta skill cubre el ciclo completo: **crear → validar → compilar**.

## 0. Preparación (una vez por entorno)

Comprueba si la CLI está disponible; si no, instala el wheel incluido en la skill
(las dependencias se descargan de PyPI):

```bash
aulastep --help >/dev/null 2>&1 || pip install --quiet <ruta-de-esta-skill>/assets/aulastep-*.whl
```

Si el proyecto del usuario ya contiene el repositorio de AulaStep, usa su
versión en su lugar: `pip install -e <repo>` (o `uv run aulastep ...`).

## 1. Crear la actividad

Reúne (o deduce del contexto) tema, módulo/curso, duración aproximada y qué
debe evidenciar el alumno. Después:

```bash
aulastep init <carpeta-actividad>
```

Edita `actividad.yml` (título, autor, módulo, curso, duración, tema visual;
la licencia CC BY-NC-SA 4.0 va por defecto y se puede sustituir) y escribe los
pasos. **Antes de escribir el primer paso, lee `references/formato.md` y
`references/directivas.md` de esta skill**: contienen el contrato exacto del
formato y ejemplos de cada directiva.

## 2. Reglas de autoría innegociables

1. **Un paso = un archivo** `pasos/NN-nombre.md` (prefijo de 2-3 dígitos,
   minúsculas y guiones). El orden lo marca SOLO el nombre; los pasos jamás se
   listan en el YAML.
2. **IDs estables y semánticos** en pasos y directivas interactivas
   (`captura-servicio`, no `q1`). En una actividad ya repartida, **nunca**
   cambies un id existente: destruiría el trabajo guardado del alumnado.
   Si la modificas, sube `actividad.version`.
3. **Las soluciones evaluables no se publican**: la marca `- [x]` de las
   preguntas de elección vive solo en el fuente. No escribas la respuesta en
   el enunciado. Para soluciones didácticas visibles usa `:::solution` (y
   pistas con `:::hint`), sabiendo que su contenido sí viaja en la web.
4. Toda directiva se cierra con `:::`; atributos entre comillas dobles; sin
   anidar; los `:::` dentro de bloques de código vallados se ignoran.
5. Recursos (imágenes, configs) en `recursos/` con ruta relativa; enlaces
   entre pasos con `[texto](paso:id-del-paso)`.
6. Contenido en español, dirigido al alumno de tú, comandos reales (no
   inventes flags), y el último paso siempre con `:::reflection`, la entrega
   de adjuntos si procede y el recordatorio de exportar el `.aulawork`.

## 3. Validar (bucle obligatorio)

```bash
aulastep validate <carpeta-actividad>
```

No des la actividad por terminada con errores o avisos sin revisar. Los
mensajes indican archivo y causa; corrige y repite hasta
`Validación correcta`.

## 4. Compilar a HTML para distribuir

Una actividad:

```bash
aulastep build <carpeta-actividad> --clean
```

Genera `<carpeta>/dist/`: web autosuficiente (rutas relativas) que funciona en
GitHub Pages, en cualquier servidor estático o servida en LAN con
`python3 -m http.server --directory dist`. Abrir `index.html` con doble clic
NO funciona (necesita servidor).

Varias actividades con índice raíz (cada una en su subcarpeta):

```bash
aulastep publish <carpeta-con-actividades> --output _site --clean --title "Mis actividades"
```

Si el usuario quiere "un archivo para enviar", comprime `dist/` en un ZIP.

## 5. Verificación final antes de entregar

- `aulastep validate` limpio y `aulastep inspect <carpeta>` muestra los pasos
  esperados en orden.
- `grep -c '"correct"' dist/activity.json` debe dar 0 (sin fugas de
  soluciones).
- La portada muestra autoría y licencia (van en `activity.json`
  automáticamente).

## Errores frecuentes

| Síntoma | Causa |
|---|---|
| `DIRECTIVA_SIN_CIERRE` | Falta la línea `:::` de cierre |
| `PASO_NOMBRE_INVALIDO` | Archivo sin prefijo `NN-` o con mayúsculas |
| `RECURSO_AUSENTE` | Enlace a `recursos/x` que no existe |
| `PREGUNTA_MARCADO_UNICO` (aviso) | single-choice sin exactamente una `[x]` |
| Página en blanco al abrir dist | Se abrió con file:// en vez de un servidor |
