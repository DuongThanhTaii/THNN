import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { visualizer } from "rollup-plugin-visualizer";

export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    ...(mode === "analyze"
      ? [
          visualizer({
            filename: "stats.html",
            gzipSize: true,
            brotliSize: true,
            open: false,
            emitFile: true,
          }),
        ]
      : []),
  ],
  server: {
    port: 3000,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./vitest.setup.ts",
    css: true,
    include: ["src/**/*.test.{ts,tsx}"],
    exclude: ["tests/e2e/**"],
  },
}));
