---
id: configuracion-ambito
titulo: Configuración del ámbito
descripcion: Define la subred, el rango y las opciones que recibirán los clientes
duracion_minutos: 25
obligatorio: true
---

## El archivo kea-dhcp4.conf

Haz una copia de seguridad antes de tocar nada:

```bash
sudo cp /etc/kea/kea-dhcp4.conf /etc/kea/kea-dhcp4.conf.original
```

Tienes una configuración base en el recurso
[kea-dhcp4-base.conf](recursos/kea-dhcp4-base.conf). Descárgala, revísala y
adáptala. Lo esencial:

```json
{
  "Dhcp4": {
    "interfaces-config": {
      "interfaces": [ "enp0s3" ]
    },
    "lease-database": {
      "type": "memfile",
      "persist": true,
      "name": "/var/lib/kea/kea-leases4.csv"
    },
    "valid-lifetime": 3600,
    "subnet4": [
      {
        "id": 1,
        "subnet": "192.168.50.0/24",
        "pools": [ { "pool": "192.168.50.100 - 192.168.50.150" } ],
        "option-data": [
          { "name": "routers", "data": "192.168.50.1" },
          { "name": "domain-name-servers", "data": "1.1.1.1, 8.8.8.8" },
          { "name": "domain-name", "data": "aula.local" }
        ]
      }
    ]
  }
}
```

:::danger{id="peligro-interfaz"}
Si en `interfaces-config` dejas una interfaz que no existe, el servicio
arrancará pero **no escuchará ninguna petición**. Pon exactamente el nombre
que te devolvió `ip -brief address`.
:::

## Valida antes de arrancar

Kea puede comprobar la sintaxis de la configuración sin ponerla en marcha:

```bash
sudo kea-dhcp4 -t /etc/kea/kea-dhcp4.conf
```

Si todo es correcto no mostrará errores. Corrige cualquier problema antes de
continuar con el [siguiente paso](paso:arranque-servicio).

:::task{id="tarea-editar-config" required="true"}
Adapta la configuración con la subred, el rango y las opciones de la tabla del
paso 1, y consigue que `kea-dhcp4 -t` la valide sin errores.
:::

:::evidence{id="captura-validacion" type="screenshot" required="true"}
Captura la ejecución de `sudo kea-dhcp4 -t /etc/kea/kea-dhcp4.conf` mostrando
que la configuración es válida.
:::

:::question{id="pregunta-lifetime" type="numeric" required="true"}
Según la configuración anterior, ¿cuántos **segundos** dura una concesión
(`valid-lifetime`)?
:::

:::question{id="pregunta-opciones" type="multi-choice" required="true"}
¿Qué información recibirán los clientes por DHCP con esta configuración?
Marca todas las correctas.

- [x] Dirección IP dentro del rango 100–150
- [x] Puerta de enlace 192.168.50.1
- [x] Servidores DNS
- [ ] Dirección MAC
- [x] Nombre de dominio aula.local
:::

:::details{id="detalle-json" summary="¿Por qué el id de subred?"}
Kea exige un `id` numérico único por subred. Le sirve internamente para asociar
concesiones a subredes aunque cambies el prefijo más adelante.
:::
