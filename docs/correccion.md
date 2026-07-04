# Corrección de entregas

`aulastep grade` corrige un lote de archivos `.aulawork` de una sentada:

```bash
aulastep grade <carpeta-actividad> <carpeta-con-entregas> --output informe --title "UT6 · DHCP"
```

**Importante**: el primer argumento es la carpeta **fuente** de la actividad
(la que contiene los Markdown con las marcas `- [x]`), no su `dist/`. Las
respuestas correctas nunca se publican, así que solo el fuente puede
autocorregir.

## Qué genera

```
informe/
├── index.html      # informe navegable e imprimible
├── resumen.csv     # una fila por entrega (; como separador, apto para Excel/Calc)
└── evidencias/
    └── Ana-Perez-2A/…   # capturas y adjuntos extraídos, enlazados desde el informe
```

- **Tabla resumen**: alumno, obligatorios completados (n/m y %), aciertos en
  preguntas de elección, inicio, última actividad y **duración aparente** del
  trabajo (delata entregas "hechas en 4 minutos").
- **Detalle por alumno**: cada elemento de la actividad con su estado. Las
  preguntas de elección se autocorrigen (`✓`/`✗`, con `[=]` marcando la opción
  esperada no elegida); las de texto y reflexiones se muestran para corrección
  manual; las capturas aparecen como miniaturas con su descripción.

## Verificaciones de cada entrega

Cada `.aulawork` se somete a las mismas comprobaciones que hace el reproductor
al importar: ZIP válido, manifiesto presente, formato `aulawork`, mismo
`schema_version` (mayor), **mismo id de actividad** y **hash SHA-256 correcto
de cada entrada**. Una entrega alterada o corrupta se marca como inválida con
su motivo, en la tabla y en el CSV, **sin bloquear la corrección del resto del
grupo**. Un cambio de versión de la actividad se anota como aviso, no como
error.

## Qué se autocorrige y qué no

| Elemento | Corrección |
|---|---|
| `single-choice` / `multi-choice` | Automática contra las marcas `[x]` (multi: el conjunto exacto) |
| `short-text`, `long-text`, `numeric`, `reflection` | Manual: se muestran las respuestas |
| `task`, `checkpoint` | Estado hecho/pendiente |
| `evidence`, `file` | Presencia + miniatura/enlace para revisión visual |

## Límites honestos

La integridad detecta **manipulación del archivo**, no suplantación: un alumno
con conocimientos técnicos podría regenerar un paquete válido. La duración
aparente y las marcas temporales del informe son la mejor pista frente a eso.
Y la autocorrección de elección es aritmética, no juicio: revisa el detalle
antes de trasladar notas.
