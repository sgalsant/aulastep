---
id: instalacion-kea
titulo: Instalación de Kea
descripcion: Instala el paquete kea-dhcp4-server y reconoce sus archivos
duracion_minutos: 10
obligatorio: true
---

## Instala el servidor DHCPv4

Ubuntu 24.04 incluye Kea en sus repositorios oficiales:

```bash
sudo apt update
sudo apt install -y kea-dhcp4-server
```

Comprueba la versión instalada y el estado inicial del servicio:

```bash
kea-dhcp4 -V
systemctl status kea-dhcp4-server
```

:::tip{id="consejo-servicios-kea"}
Kea se divide en varios demonios (`kea-dhcp4-server`, `kea-dhcp6-server`,
`kea-ctrl-agent`…). En esta práctica solo nos interesa el de **DHCPv4**.
:::

## Archivos que debes conocer

| Ruta | Contenido |
|---|---|
| `/etc/kea/kea-dhcp4.conf` | Configuración del servidor DHCPv4 (formato JSON) |
| `/var/lib/kea/kea-leases4.csv` | Base de datos de concesiones (leases) |
| `journalctl -u kea-dhcp4-server` | Registro del servicio |

:::task{id="tarea-instalar" required="true"}
Instala el paquete y verifica con `kea-dhcp4 -V` que responde con su versión.
:::

:::question{id="pregunta-formato-config" type="single-choice" required="true"}
¿En qué formato está escrito el archivo de configuración de Kea?

- [ ] YAML
- [ ] INI
- [x] JSON
- [ ] XML
:::
