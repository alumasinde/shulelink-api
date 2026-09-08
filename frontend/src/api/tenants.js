import { api } from "./client";

export async function listTenants() {
  const { data } = await api.get("/tenants");
  return data;
}

export async function createTenant(payload) {
  const { data } = await api.post("/tenants", payload);
  return data;
}

export async function createTenantUser(tenantId, payload) {
  const { data } = await api.post(`/tenants/${tenantId}/users`, payload);
  return data;
}

export async function establishTenantAccess(tenantId, reason) {
  const { data } = await api.post("/auth/platform/tenant-access", {
    tenant_id: tenantId,
    reason,
  });
  return data;
}

export async function tenantContext() {
  const { data } = await api.get("/tenant/context");
  return data;
}
