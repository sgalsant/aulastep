/* E2E del recorrido completo del alumnado sobre la actividad de ejemplo.
   Se ejecuta con: npx playwright test  (requiere navegadores instalados). */
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const NOMBRE = "Ana Pérez";

async function empezarActividad(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Empezar la actividad" }).click();
  await page.getByLabel(/Nombre y apellidos/).fill(NOMBRE);
  await page.getByLabel(/^Grupo/).fill("2A");
  await page.getByRole("button", { name: "Comenzar" }).click();
  await expect(page.getByRole("heading", { name: "Presentación y objetivos" })).toBeVisible();
}

test.describe("Recorrido del alumno", () => {
  test("pantalla de inicio con metadatos de la actividad", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Servidor DHCP con Kea/ })).toBeVisible();
    await expect(page.getByText("Servicios en Red")).toBeVisible();
    await expect(page.getByRole("button", { name: "Empezar la actividad" })).toBeVisible();
  });

  test("la licencia se muestra en la portada y en el pie de la actividad", async ({ page }) => {
    await page.goto("/");
    const block = page.locator(".license-block");
    await block.locator("summary").click();
    await expect(block).toContainText("Santiago Galván Sánchez");
    await expect(block).toContainText("CC BY-NC-SA 4.0");
    await expect(block).toContainText("no se utilice con fines comerciales");
    await expect(block.getByRole("link")).toHaveAttribute("href", /by-nc-sa\/4\.0\/deed\.es/);

    await empezarActividad(page);
    const footer = page.locator(".license-footer");
    await expect(footer).toContainText("Santiago Galván Sánchez");
    await expect(footer.getByRole("link", { name: "CC BY-NC-SA 4.0" })).toBeVisible();
  });

  test("no deja empezar sin los campos obligatorios", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Empezar la actividad" }).click();
    await page.getByRole("button", { name: "Comenzar" }).click();
    await expect(page.getByText("Este campo es obligatorio.").first()).toBeVisible();
  });

  test("responde, navega y el trabajo sobrevive a una recarga", async ({ page }) => {
    await empezarActividad(page);

    // Pregunta larga + opción única + checkpoint del paso 1.
    await page.locator("#item-previo-que-es-dhcp textarea").fill("Reparte IPs automáticamente en la red.");
    await page.locator("#item-previo-puerto label", { hasText: "UDP 67" }).click();
    await page.locator("#item-check-maquinas-listas input[type=checkbox]").check();

    await page.getByRole("button", { name: "Siguiente →" }).click();
    await expect(page.getByRole("heading", { name: "IP estática del servidor" })).toBeVisible();

    // Recarga: debe ofrecer continuar y conservar lo respondido.
    await page.reload();
    await page.getByRole("button", { name: "Continuar mi trabajo" }).click();
    await expect(page.getByRole("heading", { name: "IP estática del servidor" })).toBeVisible();
    await page.locator(".step-rail").getByRole("button", { name: /Presentación/ }).click();
    await expect(page.locator("#item-previo-que-es-dhcp textarea")).toHaveValue(/Reparte IPs/);
    await expect(page.locator("#item-previo-puerto .choice.is-selected")).toContainText("UDP 67");
  });

  test("evidencia: sube una imagen, la describe y puede eliminarla", async ({ page }) => {
    await empezarActividad(page);
    await page.locator(".step-rail").getByRole("button", { name: /IP estática/ }).click();

    const png = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
      "base64"
    );
    const zone = page.locator("#item-captura-ip-servidor .dropzone");
    await zone.click();
    // El input de archivo se crea al vuelo: usamos el filechooser.
    // (repetimos el clic con el listener ya preparado)
    const [chooser] = await Promise.all([
      page.waitForEvent("filechooser"),
      zone.click(),
    ]);
    await chooser.setFiles({ name: "captura.png", mimeType: "image/png", buffer: png });

    await expect(page.locator("#item-captura-ip-servidor img")).toBeVisible();
    await page.locator("#item-captura-ip-servidor textarea").fill("IP estática aplicada");

    await page.locator("#item-captura-ip-servidor").getByRole("button", { name: "Eliminar" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Eliminar" }).click();
    await expect(page.locator("#item-captura-ip-servidor .dropzone")).toBeVisible();
  });

  test("exporta el trabajo, lo vacía y lo reimporta intacto", async ({ page }) => {
    await empezarActividad(page);
    await page.locator("#item-previo-que-es-dhcp textarea").fill("Respuesta que debe sobrevivir al viaje.");

    const [descarga] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Guardar copia" }).click(),
    ]);
    expect(descarga.suggestedFilename()).toMatch(/^dhcp-kea-ubuntu_.*\.aulawork$/);
    const ruta = await descarga.path();

    // Vaciar el trabajo local desde la pantalla de inicio.
    await page.goto("/");
    await page.getByRole("button", { name: "Vaciar y empezar de cero" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Vaciar todo" }).click();
    await expect(page.getByRole("button", { name: "Empezar la actividad" })).toBeVisible();

    // Importar el .aulawork descargado.
    const [chooser] = await Promise.all([
      page.waitForEvent("filechooser"),
      page.getByRole("button", { name: /Importar un trabajo/ }).click(),
    ]);
    await chooser.setFiles(ruta);
    await expect(page.getByRole("heading", { name: "Presentación y objetivos" })).toBeVisible();
    await expect(page.locator("#item-previo-que-es-dhcp textarea")).toHaveValue(/sobrevivir al viaje/);
    await expect(page.locator(".student-chip")).toContainText(NOMBRE);
  });

  test("el último paso muestra el resumen con pendientes navegables", async ({ page }) => {
    await empezarActividad(page);
    await page.locator(".step-rail").getByRole("button", { name: /Reflexión y entrega/ }).click();
    await expect(page.getByRole("heading", { name: "Resumen de tu trabajo" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Exportar trabajo para entregar" })).toBeVisible();
    const pendiente = page.locator(".pending-list button").first();
    await pendiente.click();
    await expect(page.locator(".step-eyebrow")).toContainText("Paso");
  });

  test("el selector de tema cambia la paleta y se recuerda", async ({ page }) => {
    await empezarActividad(page);
    await page.locator(".theme-select").selectOption("grafito");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "grafito");
    await page.reload();
    await page.getByRole("button", { name: "Continuar mi trabajo" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "grafito");
  });

  test("los bloques de código tienen botón de copiar", async ({ page }) => {
    await empezarActividad(page);
    await page.locator(".step-rail").getByRole("button", { name: /IP estática/ }).click();
    const primero = page.locator(".codeblock").first();
    await expect(primero.getByRole("button", { name: /Copiar/ })).toBeVisible();
  });

  test("la solución se desvela en dos pasos y la pista en uno", async ({ page }) => {
    await empezarActividad(page);

    // Pista (paso 5): un solo clic.
    await page.locator(".step-rail").getByRole("button", { name: /Arranque del servicio/ }).click();
    const hint = page.locator("details.as-details--hint");
    await hint.locator("summary").click();
    await expect(hint.locator(".as-details-body")).toContainText("escuchando");

    // Solución (paso 6): al abrir aparece la confirmación, no el contenido.
    await page.locator(".step-rail").getByRole("button", { name: /Prueba desde el cliente/ }).click();
    const solution = page.locator("details.as-details--solution");
    await solution.locator("summary").click();
    await expect(solution.locator(".solution-guard")).toBeVisible();
    await expect(solution.locator(".as-details-body")).toBeHidden();
    await solution.getByRole("button", { name: "Mostrar la solución" }).click();
    await expect(solution.locator(".as-details-body")).toContainText("DHCP4_QUERY_RECEIVED");
    await expect(solution.locator(".solution-guard")).toHaveCount(0);
  });
});

test.describe("Accesibilidad", () => {
  test("la pantalla de inicio no tiene violaciones graves de axe", async ({ page }) => {
    await page.goto("/");
    const resultados = await new AxeBuilder({ page }).analyze();
    const graves = resultados.violations.filter((v) => ["critical", "serious"].includes(v.impact));
    expect(graves, JSON.stringify(graves, null, 2)).toEqual([]);
  });

  test("un paso con formularios no tiene violaciones graves de axe", async ({ page }) => {
    await empezarActividad(page);
    const resultados = await new AxeBuilder({ page }).analyze();
    const graves = resultados.violations.filter((v) => ["critical", "serious"].includes(v.impact));
    expect(graves, JSON.stringify(graves, null, 2)).toEqual([]);
  });
});
