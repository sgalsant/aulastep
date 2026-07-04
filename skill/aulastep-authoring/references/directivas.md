# Directivas

Las directivas insertan componentes en un paso con la sintaxis:

```markdown
:::tipo{atributo="valor" otro="valor"}
Cuerpo en Markdown…
:::
```

- El cierre `:::` es obligatorio (su ausencia es un error de validación).
- No se anidan.
- Dentro de bloques de código vallados (``` ``` ```) los `:::` se ignoran.
- Las directivas **interactivas** exigen `id` único en toda la actividad
  (minúsculas, dígitos y guiones) y admiten `required="true|false"`
  (por defecto `false`). Ese `id` es la clave con la que se guarda la
  respuesta del alumno: **no lo cambies una vez repartida la actividad**.

## Avisos estáticos (sin `id` obligatorio)

```markdown
:::note{}
Información neutra.
:::

:::tip{}
Consejo práctico.
:::

:::warning{}
Atención: algo que suele salir mal.
:::

:::danger{}
Peligro real (pérdida de datos, cortar la red del aula…).
:::

:::details{summary="¿Por qué funciona así?"}
Contenido plegado que el alumno puede desplegar.
:::
```

## Pistas y soluciones desplegables

```markdown
:::hint{}
Piensa en qué dos condiciones has verificado ya en este paso.
:::

:::hint{summary="Pista sobre la máscara"}
Cuenta los bits a 1 del prefijo.
:::

:::solution{summary="Solución del apartado 2"}
La máscara de /24 es `255.255.255.0`.
:::
```

- `hint` se abre con un clic; `solution` exige un segundo clic de confirmación
  («Mostrar la solución»), una fricción deliberada que invita a intentarlo
  antes de mirar.
- Ambas admiten `summary` para personalizar el título (por defecto «Pista» y
  «Solución»). Son estáticas: no llevan `id` ni cuentan para el progreso.
- **Advertencia importante**: la web compilada es estática, así que el
  contenido de una `:::solution` viaja dentro de `activity.json` y un alumno
  con conocimientos puede leerlo sin pulsar el botón. Es una barrera
  pedagógica, no criptográfica. No la uses para soluciones de preguntas
  **evaluables**; para eso, las marcas `- [x]` siguen siendo el único
  mecanismo que jamás se publica.

## Interactivas

### task — tarea que se marca como hecha

```markdown
:::task{id="tarea-netplan" required="true"}
Aplica la configuración y comprueba la IP.
:::
```

### question — pregunta con respuesta guardada

Atributo `type`: `short-text` (por defecto), `long-text`, `numeric`,
`single-choice`, `multi-choice`.

```markdown
:::question{id="pregunta-mascara" type="short-text" required="true"}
¿Qué máscara corresponde a /24?
:::

:::question{id="previo-puerto" type="single-choice" required="true"}
¿En qué puerto escucha un servidor DHCP?

- [ ] TCP 67
- [x] UDP 67
- [ ] UDP 68
:::
```

En las de elección, cada opción es una línea `- [ ]`; la marcada `- [x]`
documenta la respuesta esperada **solo en el fuente**: nunca se publica en la
web compilada. `single-choice` debe tener exactamente una marca (aviso si no);
toda pregunta de elección necesita al menos dos opciones (error si no).

### evidence — captura de pantalla

```markdown
:::evidence{id="captura-servicio" type="screenshot" required="true"}
Captura donde se vea el servicio en verde y el puerto 67.
:::
```

El alumno puede **elegir, arrastrar o pegar (Ctrl+V)** una imagen,
previsualizarla, ampliarla, describirla, sustituirla o eliminarla. Si supera el
límite (`limites.tamano_maximo_captura_mb`) se comprime automáticamente.

### file — adjunto de archivo

```markdown
:::file{id="adjunto-config" accept=".conf,.json,.txt" required="true"}
Adjunta tu kea-dhcp4.conf final.
:::
```

`accept` admite extensiones (`.conf`), tipos (`text/plain`) o familias
(`image/*`), separados por comas.

### reflection — reflexión final

```markdown
:::reflection{id="reflexion-final" required="true"}
Qué te costó más y qué harías distinto.
:::
```

Texto largo sin respuesta correcta; pensado para metacognición.

### checkpoint — punto de autoverificación

```markdown
:::checkpoint{id="check-maquinas-listas" required="true"}
Tengo las dos máquinas virtuales conectadas a la misma red.
:::
```

Como una tarea, pero semánticamente es «confirmo que esto se cumple».

## Progreso y obligatoriedad

Cada directiva interactiva con `required="true"` cuenta para el progreso del
paso y de la actividad. Un paso está completo cuando todos sus obligatorios lo
están; el resumen del último paso lista los pendientes con enlaces directos.
