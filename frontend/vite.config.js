import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    allowedHosts: ["localhost", ".localhost", "admin.shulelink.co.ke", ".shulelink.co.ke"],
    port: 5173,
  },
});
