# El formato `.aulawork`

Un `.aulawork` es el **trabajo completo de un alumno** en un único archivo.
Técnicamente es un ZIP con esta estructura:

```
dhcp-kea-ubuntu_Ana-Perez_2026-07-02.aulawork
├── manifest.json        # formato, versiones, actividad e integridad
├── student.json         # campos de identificación del alumno
├── answers.json         # respuestas por id de directiva
├── progress.json        # paso actual, fechas y estados de tareas/checkpoints
├── attachments.json     # índice de evidencias y adjuntos
├── evidence/            # capturas (imágenes)
│   └── captura-servicio__pantallazo.jpg
└── files/               # adjuntos
    └── adjunto-config__kea-dhcp4.conf
```

## manifest.json

```json
{
  "format": "aulawork",
  "schemaVersion": "1.0",
  "generator": { "name": "AulaStep", "version": "0.1.0" },
  "activity": { "id": "dhcp-kea-ubuntu", "version": "1.0.0", "titulo": "…" },
  "exportedAt": "2026-07-02T10:05:00.000Z",
  "integrity": {
    "algorithm": "SHA-256",
    "files": { "answers.json": "9f86d0…", "evidence/…": "…" }
  }
}
```

La integridad se calcula con Web Crypto (`crypto.subtle.digest`) sobre cada
entrada. El esquema formal está en `schemas/manifest-aulawork.schema.json`.

## Reglas de importación

Al importar un `.aulawork`, el reproductor:

1. **Bloquea** si no es un ZIP válido, falta `manifest.json`, el formato no es
   `aulawork`, el `schemaVersion` es de otra versión mayor, el `id` de la
   actividad no coincide, alguna entrada declarada falta o **algún hash SHA-256
   no cuadra** (paquete alterado o corrupto).
2. **Avisa sin bloquear** si la versión de la actividad cambió, si algún
   adjunto supera los límites o tiene una ruta/tipo no válido (se omite ese
   adjunto, no todo el paquete).
3. **Conserva** las respuestas cuyo `id` ya no exista en la actividad actual,
   marcadas como huérfanas: no se pierden datos del alumno por una edición
   posterior de la práctica.
4. Sustituye por completo el trabajo local previo (pidiendo confirmación).

## Nombre de archivo

Configurable en `trabajo.patron_nombre` con los comodines `{actividad}`,
`{alumno}` (saneado) y `{fecha}` (AAAA-MM-DD).

## Privacidad y flujo de entrega

Nada sale del navegador salvo el archivo que el alumno descarga y te entrega
(Moodle, correo, carpeta compartida…). Para corregir, abre la misma actividad
publicada e importa el `.aulawork` del alumno: verás su trabajo exactamente
como lo dejó.
