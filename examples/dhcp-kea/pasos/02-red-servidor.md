---
id: red-servidor
titulo: IP estática del servidor
descripcion: Configura la dirección fija del servidor con Netplan
duracion_minutos: 15
obligatorio: true
---

## Por qué una IP fija

Un servidor DHCP **no puede ser cliente DHCP de sí mismo**: necesita una
dirección estable que los clientes y tú podáis localizar siempre. Le daremos
la `192.168.50.10/24`.

## Configura Netplan

Identifica primero el nombre de tu interfaz:

```bash
ip -brief address
```

Edita el archivo de Netplan (el nombre puede variar, por ejemplo
`50-cloud-init.yaml`):

```bash
sudo nano /etc/netplan/50-cloud-init.yaml
```

Déjalo con este contenido, sustituyendo `enp0s3` por tu interfaz:

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: false
      addresses:
        - 192.168.50.10/24
      routes:
        - to: default
          via: 192.168.50.1
      nameservers:
        addresses: [1.1.1.1, 8.8.8.8]
```

:::warning{id="aviso-indentacion"}
Netplan es YAML: la **indentación con espacios** es significativa. Un tabulador
o un espacio de más provocan un error al aplicar.
:::

Aplica y comprueba:

```bash
sudo netplan apply
ip -brief address
ip route
```

:::task{id="tarea-netplan" required="true"}
Aplica la configuración anterior y comprueba que la interfaz muestra
`192.168.50.10/24` y que la ruta por defecto apunta a `192.168.50.1`.
:::

:::evidence{id="captura-ip-servidor" type="screenshot" required="true"}
Captura la salida de `ip -brief address` y `ip route` en el servidor, donde se
vea la IP estática y la puerta de enlace.
:::

:::question{id="pregunta-mascara" type="short-text" required="true"}
¿Qué máscara de red en notación decimal corresponde al prefijo `/24`?
:::
