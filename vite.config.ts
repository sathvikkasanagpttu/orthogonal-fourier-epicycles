import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  base: "./",
  root: "web",
  publicDir: "public",
  build: {
    outDir: "../dist",
    emptyOutDir: true,
  },
  css: {
    postcss: {},
  },
  server: {
    port: 3000,
    open: false,
  },
});
