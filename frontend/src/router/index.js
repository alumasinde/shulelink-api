import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/auth/LoginView.vue";
import ActivateAccountView from "../views/auth/ActivateAccountView.vue";
import PlatformDashboard from "../views/platform/PlatformDashboard.vue";
import TenantsView from "../views/platform/TenantsView.vue";
import AcademicSettingsView from "../views/platform/AcademicSettingsView.vue";
import RoleDashboardView from "../views/tenant/RoleDashboardView.vue";
import RolePortalView from "../views/tenant/RolePortalView.vue";
import SchoolStructureView from "../views/tenant/SchoolStructureView.vue";
import DataTransferView from "../views/tenant/DataTransferView.vue";
import StudentsView from "../views/tenant/StudentsView.vue";
import GuardiansView from "../views/tenant/GuardiansView.vue";
import PortalAccountsView from "../views/tenant/PortalAccountsView.vue";
import AcademicsView from "../views/tenant/AcademicsUnifiedView.vue";

const PLATFORM_HOSTS = new Set(["admin.localhost","admin.shulelink.co.ke","localhost","127.0.0.1"]);
const isPlatformHost = () => PLATFORM_HOSTS.has(window.location.hostname);
const portalPath = (user) => user?.user_type === "platform" ? "/platform" : "/school";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/login", name: "login", component: LoginView, meta: { guestOnly: true } },
    { path: "/activate", name: "activate", component: ActivateAccountView, meta: { guestOnly: true } },
    { path: "/platform", name: "platform-dashboard", component: PlatformDashboard, meta: { auth: true, platform: true } },
    { path: "/platform/tenants", name: "platform-tenants", component: TenantsView, meta: { auth: true, platform: true } },
    { path: "/platform/academic-settings", name: "platform-academic-settings", component: AcademicSettingsView, meta: { auth: true, platform: true } },
    { path: "/school", name: "tenant-dashboard", component: RoleDashboardView, meta: { auth: true, tenant: true } },
    { path: "/school/portal", name: "role-portal", component: RolePortalView, meta: { auth: true, tenant: true } },
    { path: "/school/structure", name: "school-structure", component: SchoolStructureView, meta: { auth: true, tenant: true } },
    { path: "/school/data-transfer", name: "school-data-transfer", component: DataTransferView, meta: { auth: true, tenant: true, permission: "school.structure.manage" } },
    { path: "/school/students", name: "students", component: StudentsView, meta: { auth: true, tenant: true } },
    { path: "/school/guardians", name: "guardians", component: GuardiansView, meta: { auth: true, tenant: true } },
    { path: "/school/portal-accounts", name: "portal-accounts", component: PortalAccountsView, meta: { auth: true, tenant: true, permission: "accounts.manage" } },
    { path: "/school/academics", name: "academics", component: AcademicsView, meta: { auth: true, tenant: true, permission: "academics.read" } },
    { path: "/school/academics/teacher-subjects", redirect: "/school/academics" },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
  scrollBehavior() { return { top: 0 }; },
});

let hydrated = false;
let hydrationPromise = null;
async function ensureHydrated(auth) {
  if (hydrated) return;
  hydrationPromise ||= auth.hydrate().finally(() => { hydrated = true; hydrationPromise = null; });
  await hydrationPromise;
}
router.beforeEach(async (to) => {
  const auth = useAuthStore(); await ensureHydrated(auth);
  if (to.meta.guestOnly && auth.isAuthenticated) return isPlatformHost() ? "/platform" : portalPath(auth.user);
  if (to.meta.auth && !auth.isAuthenticated) return { path: "/login", query: { redirect: to.fullPath } };
  if (to.meta.platform && (!isPlatformHost() || !auth.isPlatform)) return auth.isAuthenticated ? portalPath(auth.user) : "/login";
  if (to.meta.tenant && isPlatformHost()) return auth.isAuthenticated ? "/platform" : "/login";
  if (to.meta.permission && !auth.user?.permissions?.includes(to.meta.permission)) return auth.isAuthenticated ? portalPath(auth.user) : "/login";
  return true;
});
router.onError((error) => { if (import.meta.env.DEV) console.error("Navigation error:", error); });
export default router;
