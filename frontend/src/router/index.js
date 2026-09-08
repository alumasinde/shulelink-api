import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/auth/LoginView.vue";
import PlatformDashboard from "../views/platform/PlatformDashboard.vue";
import TenantsView from "../views/platform/TenantsView.vue";
import TenantDashboard from "../views/tenant/TenantDashboard.vue";

const isPlatformHost = () => {
  const host = window.location.hostname;
  return host === "admin.localhost" || host === "admin.shulelink.co.ke" || host === "localhost" || host === "127.0.0.1";
};

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/login", name: "login", component: LoginView, meta: { guestOnly: true } },
    { path: "/platform", name: "platform-dashboard", component: PlatformDashboard, meta: { auth: true, platform: true } },
    { path: "/platform/tenants", name: "platform-tenants", component: TenantsView, meta: { auth: true, platform: true } },
    { path: "/school", name: "tenant-dashboard", component: TenantDashboard, meta: { auth: true, tenant: true } },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (!auth.user && auth.isAuthenticated) await auth.hydrate();

  if (to.meta.guestOnly && auth.isAuthenticated) {
    return isPlatformHost() ? "/platform" : "/school";
  }
  if (to.meta.auth && !auth.isAuthenticated) return "/login";
  if (to.meta.platform && (!isPlatformHost() || !auth.isPlatform)) return auth.isAuthenticated ? "/school" : "/login";
  if (to.meta.tenant && (isPlatformHost() || auth.isPlatform)) return auth.isAuthenticated ? "/platform" : "/login";
});

export default router;
