import { defineConfig } from "astro/config";

// El frontend llama a la API con rutas relativas (/api/...), así funciona
// igual en local, en un túnel de Cloudflare y en producción tras un proxy.
//
// PUBLIC_API_URL solo hace falta si la API vive en otro dominio distinto
// (por defecto: mismo origen, con proxy en desarrollo hacia :8000).
export default defineConfig({
  output: "static",
  vite: {
    server: {
      // En desarrollo, las peticiones /api van al backend de FastAPI
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
      // Permite acceder al servidor de desarrollo vía túnel de Cloudflare
      allowedHosts: [".trycloudflare.com"],
    },
  },
});
