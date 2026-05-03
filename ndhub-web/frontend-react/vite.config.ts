import { defineConfig } from "vite";

export default defineConfig({
  base: "/web/react/",
  build: {
    outDir: "../backend/web/react",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/main.tsx",
      output: {
        entryFileNames: "ndhub-react.js",
        assetFileNames: "ndhub-react.[ext]",
      },
    },
  },
});

