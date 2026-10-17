import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 开发时把 /api 和 /p 转给后端（uv run python -m app）
export default defineConfig({
  plugins: [react()],
  build: { chunkSizeWarningLimit: 1000 },
  server: { host: true, proxy: { "/api": "http://localhost:8000" } },
});
