import { defineConfig } from "vite";

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    watch: {
      // Polling is required when source is bind-mounted from a host with a
      // different filesystem (macOS/Windows → Linux container).
      usePolling: true,
      interval: 500,
    },
  },
});
