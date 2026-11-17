import { defineConfig } from "astro/config";

// PUBLIC_API_URL: URL de la API. En desarrollo la sirve uvicorn en :8000;
// en producción conviene exponerla bajo el mismo dominio (p. ej. /api vía proxy)
// y poner aquí solo la base.
export default defineConfig({
  output: "static",
});
