# Formato de una actividad

Una actividad es una carpeta con esta estructura:

```
mi-practica/
├── actividad.yml
├── pasos/
│   ├── 01-presentacion.md
│   ├── 02-instalacion.md
│   └── 03-entrega.md
└── recursos/
```

## actividad.yml

Configuración global (validada contra `schemas/actividad.schema.json`):

```yaml
schema_version: "1.0"

actividad:
  id: dhcp-kea-ubuntu        # minúsculas, dígitos y guiones; identifica la actividad
  titulo: Servidor DHCP con Kea
  subtitulo: Despliegue y verificación     # opcional
  version: 1.0.0             # semántica; cámbiala al modificar la actividad
  descripcion: >             # se muestra en la pantalla de inicio
    Qué va a aprender el alumnado.
  autor: Ayaya
  modulo: Servicios en Red
  curso: 2º SMR
  duracion_minutos: 110
  tema: oceano               # oceano | bosque | indigo | ambar | grafito | coral | halloween
  publicada: true            # con false: borrador (se valida, no entra al catálogo)
  licencia:                  # opcional: si se omite, CC BY-NC-SA 4.0
    nombre: CC BY-NC-SA 4.0
    nombre_completo: Creative Commons Atribución-NoComercial-CompartirIgual 4.0 Internacional
    url: https://creativecommons.org/licenses/by-nc-sa/4.0/deed.es
    # condiciones: lista opcional de viñetas; por defecto, las cuatro de CC BY-NC-SA

navegacion:
  modo: asistente            # asistente | libre | secuencial
  permitir_anterior: true    # volver atrás nunca se bloquea de verdad
  permitir_saltar: true      # saltos desde el índice (modo asistente)
  mostrar_indice: true
  mostrar_progreso: true
  exigir_obligatorios_para_avanzar: false   # bloquea «Siguiente» con pendientes

alumno:
  campos:                    # formulario inicial de identificación
    - id: nombre
      etiqueta: Nombre y apellidos
      tipo: texto
      obligatorio: true

trabajo:
  autoguardado: true
  intervalo_autoguardado_segundos: 5
  permitir_exportar: true
  permitir_importar: true
  extension: aulawork
  patron_nombre: "{actividad}_{alumno}_{fecha}.aulawork"

limites:
  tamano_maximo_captura_mb: 8
  tamano_maximo_adjunto_mb: 20
  tamano_maximo_paquete_mb: 100
```

### Modos de navegación

| Modo | Índice | «Siguiente» |
|---|---|---|
| `libre` | salta a cualquier paso | siempre |
| `asistente` | salta si `permitir_saltar` | según `exigir_obligatorios_para_avanzar` |
| `secuencial` | solo hasta un paso más allá del máximo visitado | según `exigir_obligatorios_para_avanzar` |

Volver a pasos anteriores está **siempre permitido** en los tres modos.

### Licencia de la actividad

Toda actividad muestra **siempre** su referencia de licencia: en la ficha de la
portada, en un desplegable «Licencia» con el texto completo (autoría, permisos
y condiciones, con enlace al texto legal) y en el pie de todos los pasos del
reproductor. Si `actividad.licencia` no se indica, se aplica **CC BY-NC-SA 4.0**
con sus cuatro condiciones estándar; puedes sustituirla por cualquier otra
rellenando `nombre`, `nombre_completo`, `url` y, si procede, `condiciones`.

No confundas esta licencia (la del **contenido docente** de cada actividad,
p. ej. CC BY-NC-SA 4.0) con la licencia del código de AulaStep (MIT, en el
archivo `LICENSE` del repositorio): son independientes.

## Los pasos

**Los pasos no se declaran en el YAML.** La carpeta `pasos/` es la única fuente
de verdad: cada archivo `NN-nombre-del-paso.md` es un paso y el prefijo numérico
marca el orden. Reordenar es renombrar archivos.

Reglas del nombre (patrón `^\d{2,3}-[a-z0-9][a-z0-9-]*\.md$`):

- prefijo de 2 o 3 dígitos + guion + nombre en minúsculas/dígitos/guiones;
- prefijos duplicados → **error**; saltos de numeración → aviso.

### Metadatos de otros sistemas: el cajón `meta:`

Si tu flujo (una wiki, un LMS, un pipeline de IA) necesita metadatos propios
en `actividad.yml` o en el front matter de un paso, anídalos bajo `meta:`:

```yaml
---
id: instalacion-kea
titulo: Instalación de Kea
meta:
  tipo: practica
  dominio: Servicios en Red
  estado: publicado
  tags: [dhcp, kea]
---
```

`meta:` admite cualquier contenido, no afecta a la validación del resto y
**jamás se publica** en la web compilada. Cualquier campo desconocido *fuera*
de `meta:` sigue siendo un error (protección frente a erratas).

Cada paso comienza con front matter YAML:

```markdown
---
id: instalacion-kea      # estable: NO cambiarlo una vez publicado
titulo: Instalación de Kea
descripcion: Instala el paquete y reconoce sus archivos   # opcional
duracion_minutos: 10     # opcional
obligatorio: true        # por defecto true
---

Contenido en Markdown (CommonMark + tablas + tachado + notas al pie)…
```

### Markdown admitido

- CommonMark completo, tablas, `~~tachado~~` y notas al pie.
- **El HTML embebido se escapa**: no se interpreta (seguridad).
- Imágenes y enlaces a recursos usan **rutas relativas al propio archivo del
  paso** (semántica Markdown estándar): desde `pasos/01-x.md`, escribe
  `../recursos/imagen.png`. Se validan (deben existir, quedar dentro de la
  actividad y vivir en `recursos/`, que es lo único que viaja a la
  publicación) y los enlaces a archivos se marcan como descargables. La
  convención antigua (`recursos/imagen.png` a secas) sigue funcionando con un
  aviso de obsolescencia; en la web publicada ambas quedan normalizadas igual.
- Enlaces entre pasos con el esquema `paso:`: `[ver el paso 5](paso:arranque-servicio)`.
  Se validan contra los IDs reales.
- Los bloques de código vallados reciben barra de terminal y botón **Copiar**.

Las directivas interactivas se documentan en [`directivas.md`](directivas.md).
