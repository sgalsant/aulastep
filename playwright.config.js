// Configuración de Playwright para las pruebas E2E de AulaStep.
// Compila la actividad de ejemplo y la sirve como web estática real.
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:8899",
    trace: "on-first-retry",
  },
  webServer: {
    command:
      "uv run aulastep build examples/dhcp-kea --output /tmp/aulastep-e2e --clean && uv run python -m http.server 8899 --directory /tmp/aulastep-e2e",
    url: "http://127.0.0.1:8899",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
