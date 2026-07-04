---
id: prueba-cliente
titulo: Prueba desde el cliente
descripcion: Comprueba la concesión desde un cliente y analiza el intercambio DORA
duracion_minutos: 20
obligatorio: true
---

## Pide una dirección desde el cliente

En un cliente Ubuntu conectado a la misma red:

```bash
sudo dhclient -v || sudo networkctl renew
ip -brief address
resolvectl status
```

En un cliente Windows:

```
ipconfig /release
ipconfig /renew
ipconfig /all
```

El cliente debe recibir una IP **entre la .100 y la .150**, la puerta de
enlace `.1`, los DNS y el sufijo `aula.local`.

## Observa la concesión en el servidor

```bash
sudo cat /var/lib/kea/kea-leases4.csv
journalctl -u kea-dhcp4-server -n 20 --no-pager
```

## El diálogo DORA

Toda concesión sigue cuatro mensajes: **D**iscover, **O**ffer, **R**equest y
**A**cknowledge. Localízalos en el registro del servidor.

:::solution{summary="Cómo se ven los cuatro mensajes en el registro"}
En `journalctl -u kea-dhcp4-server` aparecen como `DHCP4_QUERY_RECEIVED`
(Discover y Request, con el tipo entre corchetes) y `DHCP4_PACKET_SENT`
(Offer y Ack). La secuencia completa para una MAC concreta es:
Discover → Offer → Request → Ack, y justo después la concesión queda escrita
en `kea-leases4.csv`.
:::

:::task{id="tarea-cliente" required="true"}
Consigue que el cliente obtenga una dirección del rango configurado y localiza
su entrada en `kea-leases4.csv`.
:::

:::evidence{id="captura-cliente" type="screenshot" required="true"}
Captura del cliente mostrando la IP recibida y sus opciones (gateway, DNS,
dominio).
:::

:::question{id="pregunta-dora" type="single-choice" required="true"}
¿Cuál es el **orden correcto** de los mensajes de una concesión DHCP?

- [ ] Offer → Discover → Ack → Request
- [x] Discover → Offer → Request → Ack
- [ ] Request → Offer → Discover → Ack
- [ ] Discover → Request → Offer → Ack
:::

:::question{id="pregunta-quien-envia" type="multi-choice" required="true"}
¿Qué mensajes del diálogo DORA envía **el servidor**?

- [ ] Discover
- [x] Offer
- [ ] Request
- [x] Acknowledge
:::
