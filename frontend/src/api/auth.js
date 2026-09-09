import { api } from "./client";

export async function login(credentials, type = "tenant") {
  const endpoint = type === "platform" ? "/auth/platform/login" : "/auth/login";
  const { data } = await api.post(endpoint, credentials);
  return data;
}

export async function verifyMfa(challengeId, code) {
  const { data } = await api.post("/auth/mfa/verify", { challenge_id: challengeId, code });
  return data;
}

export async function me() {
  const { data } = await api.get("/auth/me");
  return data;
}

export async function logout(refreshToken) {
  await api.post("/auth/logout", { refresh_token: refreshToken });
}

export async function refresh(refreshToken) {
  const { data } = await api.post("/auth/refresh", refreshToken ? { refresh_token: refreshToken } : {});
  return data;
}
