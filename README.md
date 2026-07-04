# AulaStep

**Actividades guiadas para el aula**: escribe tu práctica en Markdown y AulaStep
la convierte en una aplicación web estática (HTML5/CSS/JS) que puedes publicar
en GitHub Pages o servir desde cualquier carpeta. El alumnado la sigue paso a
paso, responde preguntas, aporta capturas y adjuntos, y **exporta su trabajo en
un único archivo `.aulawork`** que te entrega. Solo necesita un navegador: sin
cuentas, sin servidor, sin base de datos.

Pensado para Formación Profesional de informática (SMR, ASIR, DAW…), aunque
sirve para cualquier práctica guiada.

## Características

- **Markdown como fuente**: un archivo por paso, orden por nombre de archivo.
- **Directivas interactivas** (`:::task`, `:::question`, `:::evidence`,
  `:::file`, `:::reflection`, `:::checkpoint`) y avisos estáticos
  (`:::note`, `:::tip`, `:::warning`, `:::danger`, `:::details`).
- **Reproductor web accesible**: asistente por pasos con índice, progreso,
  bloques de código con botón de copiar y seis temas visuales.
- **Trabajo del alumno local**: autoguardado en IndexedDB; sobrevive a recargas
  y cortes. Exportación e importación en `.aulawork` (ZIP con manifiesto e
  integridad SHA-256).
- **Validación estricta** antes de compilar: IDs, recursos, enlaces internos,
  tipos de pregunta… con errores claros y accionables.
- **IDs estables** pensados para que un agente de IA pueda editar pasos sin
  romper el trabajo ya realizado por el alumnado (ver `AGENTS.md`).

## Instalación

Requiere Python 3.12+. Con [uv](https://docs.astral.sh/uv/):

```bash
uv venv
uv pip install -e ".[dev]"
```

o con pip clásico: `pip install -e ".[dev]"`.

## Uso en 60 segundos

```bash
# 1. Crea una actividad nueva
aulastep init mi-practica

# 2. Edita actividad.yml y los Markdown de mi-practica/pasos/

# 3. Previsualiza en local con recarga automática
aulastep preview mi-practica

# 4. Valida y compila la web estática
aulastep validate mi-practica
aulastep build mi-practica            # genera mi-practica/dist/

# 5. Consulta la estructura detectada
aulastep inspect mi-practica

# 6. Corrige un lote de entregas .aulawork (informe HTML + CSV)
aulastep grade mi-practica entregas/ --output informe
```

La carpeta `dist/` resultante es autosuficiente: súbela a GitHub Pages, a un
Moodle como recurso HTML o compártela por USB. Las rutas son relativas, así que
funciona igualmente bajo una subruta (`https://usuario.github.io/repo/`).

## Estructura de una actividad

```
mi-practica/
├── actividad.yml        # metadatos, navegación, campos del alumno, límites
├── pasos/
│   ├── 01-presentacion.md
│   ├── 02-instalacion.md
│   └── 03-entrega.md    # el orden lo marca SIEMPRE el nombre de archivo
└── recursos/            # imágenes y archivos referenciados por los pasos
```

Documentación detallada:

- [`docs/formato-actividad.md`](docs/formato-actividad.md) — `actividad.yml` y los pasos.
- [`docs/directivas.md`](docs/directivas.md) — todas las directivas con ejemplos.
- [`docs/aulawork.md`](docs/aulawork.md) — el formato de entrega `.aulawork`.
- [`docs/correccion.md`](docs/correccion.md) — corrección por lotes con `aulastep grade`.
- [`docs/temas.md`](docs/temas.md) — los seis temas y cómo crear otros.
- [`AGENTS.md`](AGENTS.md) — reglas para editar actividades con agentes de IA.

## Actividad de ejemplo

`examples/dhcp-kea/` contiene una práctica completa y real: **Servidor DHCP con
Kea en Ubuntu Server 24.04** (7 pasos, preguntas de todos los tipos, evidencias,
adjunto de configuración y reflexión final).

```bash
aulastep preview examples/dhcp-kea
```

## Pruebas

```bash
pytest                    # generador (Python)
npm test                  # reproductor (Vitest, sin navegador)
npx playwright install chromium
npx playwright test       # E2E + accesibilidad (axe) sobre el ejemplo compilado
ruff check src tests/python
```

## Publicación en GitHub Pages

Cada actividad se publica en **su propia subcarpeta**, con un índice raíz que
las enlaza:

```bash
aulastep publish actividades --output _site --title "Mis actividades"
# _site/index.html  +  _site/<id-actividad>/  por cada una
```

El workflow `.github/workflows/pages.yml` hace esto en cada push a `main`
(tras lint y todas las pruebas) con la carpeta `examples/`; cambia esa ruta por
la carpeta donde guardes tus actividades. Las URLs resultantes son
`https://usuario.github.io/repo/` (índice) y
`https://usuario.github.io/repo/<id>/` (cada actividad). Como el reproductor
usa rutas relativas, cada subcarpeta funciona sin configuración adicional.

## Privacidad

Todo el trabajo del alumnado vive en su navegador (IndexedDB) y en los archivos
`.aulawork` que él mismo descarga. AulaStep no envía datos a ningún servidor.

## Skill para agentes de IA

`scripts/build_skill.sh` genera **aulastep-authoring.skill**: una skill
autocontenida (SKILL.md + referencias del formato + wheel de la herramienta)
que puede integrarse en otros proyectos con agentes (Claude Code, opencode…)
para que la IA cree actividades en este formato y las compile a HTML sin tener
el repositorio presente. Las referencias se copian de `docs/` en cada
generación: el repo es la única fuente de verdad. Requisito del entorno
destino: Python 3.12+ y acceso a PyPI para las dependencias.

## Licencia

MIT © Ayaya
