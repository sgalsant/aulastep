---
id: arranque-servicio
titulo: Arranque del servicio
descripcion: Pon en marcha kea-dhcp4-server y comprueba que escucha
duracion_minutos: 15
obligatorio: true
---

## Arranca y habilita el servicio

```bash
sudo systemctl restart kea-dhcp4-server
sudo systemctl enable kea-dhcp4-server
systemctl status kea-dhcp4-server
```

El estado debe ser `active (running)`. Si aparece en fallo, consulta el
registro:

```bash
journalctl -u kea-dhcp4-server -n 30 --no-pager
```

## Comprueba que escucha en UDP 67

```bash
sudo ss -ulpn 'sport = :67'
```

Debes ver el proceso `kea-dhcp4` asociado al puerto 67.

:::tip{id="consejo-journal"}
`journalctl -u kea-dhcp4-server -f` deja el registro en directo: es la mejor
ventana para ver las peticiones DHCP entrando cuando conectes el cliente.
:::

:::task{id="tarea-arrancar" required="true"}
Arranca el servicio, habilítalo en el arranque y verifica que está
`active (running)` y escuchando en UDP 67.
:::

:::evidence{id="captura-servicio" type="screenshot" required="true"}
Captura donde se vean el `systemctl status` en verde y la salida de
`ss -ulpn` con el puerto 67.
:::

:::question{id="pregunta-diagnostico" type="long-text" required="false"}
Si el servicio arrancara pero ningún cliente recibiera IP, ¿qué dos
comprobaciones harías primero y por qué?
:::

:::hint{}
Piensa en las dos condiciones que ya has verificado en este paso: ¿el proceso
está **escuchando**? ¿Y en la **interfaz correcta**? El archivo de
configuración y `journalctl` responden a ambas.
:::
