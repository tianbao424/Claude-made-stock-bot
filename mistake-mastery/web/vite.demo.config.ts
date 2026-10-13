import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 预览版：纯前端演示，所有脚本、样式、字体都内联，再由 demo/build_preview.mjs 拼成一个 HTML 文件
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "dist-demo",
    emptyOutDir: true,
    assetsInlineLimit: 100_000_000,
    cssCodeSplit: false,
    modulePreload: false,
    chunkSizeWarningLimit: 5000,
    rollupOptions: { input: "demo.html", output: { inlineDynamicImports: true } },
  },
});
