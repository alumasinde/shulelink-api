import { api } from "./client";

export const system = {
  async health() {
    const { data } = await api.get("/health");
    return data;
  },

  async readiness() {
    const { data } = await api.get("/health/ready");
    return data;
  },
};
