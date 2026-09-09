import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap-icons/font/bootstrap-icons.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";
import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./assets/main.css";
import "./assets/students.css";

const app = createApp(App);

// Never expose component internals, response payloads, or stack traces to end users.
// Vue's production build also removes dev-only diagnostics automatically.
app.config.errorHandler = (error, instance, info) => {
  if (import.meta.env.DEV) {
    console.error("Vue error:", error, info, instance);
  }
};

window.addEventListener("error", (event) => {
  if (import.meta.env.DEV) console.error("Window error:", event.error || event.message);
});

window.addEventListener("unhandledrejection", (event) => {
  if (import.meta.env.DEV) console.error("Unhandled promise rejection:", event.reason);
});

app.use(createPinia()).use(router).mount("#app");
