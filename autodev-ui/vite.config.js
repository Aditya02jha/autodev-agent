import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/generate": "http://localhost:8000",
      "/apply": "http://localhost:8000",
      "/sandbox": "http://localhost:8000",
      "/ask": "http://localhost:8000",
      "/index": "http://localhost:8000",
      "/plan": "http://localhost:8000",
    },
  },
});
