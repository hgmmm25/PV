import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const pvRoot = path.resolve(__dirname, "..");

// Ensure node_modules is reachable from the PV root
const rootNodeModules = path.resolve(pvRoot, "node_modules");
if (!fs.existsSync(rootNodeModules)) {
  try {
    fs.symlinkSync(
      path.resolve(__dirname, "node_modules"),
      rootNodeModules,
      "junction"
    );
  } catch {
    /* already linked or permission issue */
  }
}

export default defineConfig({
  // Root = D:\PV → import.meta.glob("/history/*.json") just works
  root: pvRoot,

  plugins: [
    react(),
    {
      name: "redirect-root-to-viewer",
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url === "/" || req.url === "/index.html") {
            res.writeHead(302, { Location: "/history-viewer/" });
            res.end();
            return;
          }
          next();
        });
      },
    },
  ],

  css: {
    postcss: path.resolve(__dirname, "postcss.config.js"),
  },

  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },

  server: {
    port: 3200,
    open: "/history-viewer/",
    fs: {
      allow: [pvRoot, __dirname],
    },
  },
});
