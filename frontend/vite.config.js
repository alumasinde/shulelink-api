import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const developmentHosts = env.VITE_DEVELOPMENT_HOSTS?.trim();
  const developmentDomain = env.VITE_DEVELOPMENT_DOMAIN?.trim();
  const serverHost = env.VITE_DEV_SERVER_HOST?.trim();
  const serverPort = Number(env.VITE_DEV_SERVER_PORT);

  if (!developmentHosts || !developmentDomain || !serverHost || !Number.isInteger(serverPort)) {
    throw new Error(
      "VITE_DEVELOPMENT_HOSTS, VITE_DEVELOPMENT_DOMAIN, VITE_DEV_SERVER_HOST and VITE_DEV_SERVER_PORT are required",
    );
  }

  const allowedHosts = [
    ...developmentHosts.split(",").map((value) => value.trim()).filter(Boolean),
    `.${developmentDomain}`,
  ];

  return {
    plugins: [vue()],
    server: {
      host: serverHost,
      allowedHosts,
      port: serverPort,
    },
  };
});
