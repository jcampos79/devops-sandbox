import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The frontend communicates exclusively with the FastAPI backend. In local
// dev, proxy /api and /ws to the backend so no CORS configuration is needed;
// in production this routing is done by the Ingress (see
// helm/sandbox-platform/templates/ingress.yaml).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
  },
});
