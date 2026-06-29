import api from "@/lib/api";

const tryGet = async (paths, fallback = null) => {
  for (const path of paths) {
    try {
      const res = await api.get(path);
      return res.data;
    } catch (err) {
      if (err?.response?.status === 404) continue;
      if (err?.response?.status === 405) continue;
      if (err?.response?.status === 401 || err?.response?.status === 403) throw err;
    }
  }
  return fallback;
};

const tryPost = async (paths, body, fallback = null) => {
  for (const path of paths) {
    try {
      const res = await api.post(path, body);
      return res.data;
    } catch (err) {
      if (err?.response?.status === 404) continue;
      if (err?.response?.status === 405) continue;
      if (err?.response?.status === 401 || err?.response?.status === 403) throw err;
    }
  }
  return fallback;
};

const tryPatch = async (paths, body, fallback = null) => {
  for (const path of paths) {
    try {
      const res = await api.patch(path, body);
      return res.data;
    } catch (err) {
      if (err?.response?.status === 404) continue;
      if (err?.response?.status === 405) continue;
      if (err?.response?.status === 401 || err?.response?.status === 403) throw err;
    }
  }
  return fallback;
};

export const adminApi = {
  async getServiceRegistry() {
    const data = await tryGet(["/services", "/orchestrator/services", "/admin/services"], { services: [] });
    return data?.services || [];
  },

  async getOrchestratorHealth() {
    return await tryGet(["/health", "/orchestrator/health", "/admin/health"], null);
  },

  async getServiceStartupSequence() {
    return await tryGet(["/health/startup-sequence", "/orchestrator/health/startup-sequence"], {
      sequence_status: [],
      all_services_healthy: false,
    });
  },

  async updateServiceStatus(serviceName, status) {
    return await tryPatch([
      `/services/${serviceName}/status`,
      `/orchestrator/services/${serviceName}/status`,
    ], { status }, { ok: false, message: "status endpoint unavailable" });
  },

  async sendServiceHeartbeat(serviceName) {
    return await tryPatch([
      `/services/${serviceName}/heartbeat`,
      `/orchestrator/services/${serviceName}/heartbeat`,
    ], {}, { ok: false, message: "heartbeat endpoint unavailable" });
  },

  async listUsers() {
    const data = await tryGet(["/admin/users", "/users"], { users: [] });
    return data?.users || [];
  },

  async createUser(payload) {
    return await tryPost(["/auth/register", "/users", "/admin/users"], payload, {
      ok: false,
      message: "create user endpoint unavailable",
    });
  },

  async listPayments() {
    const data = await tryGet(["/admin/payments", "/payments"], { payments: [] });
    return data?.payments || [];
  },

  async confirmPayment(paymentId) {
    return await tryPost([
      `/admin/payments/${paymentId}/confirm`,
      `/payments/${paymentId}/confirm`,
    ], {}, { ok: false, message: "confirm payment endpoint unavailable" });
  },

  async rejectPayment(paymentId) {
    return await tryPost([
      `/admin/payments/${paymentId}/reject`,
      `/payments/${paymentId}/reject`,
    ], {}, { ok: false, message: "reject payment endpoint unavailable" });
  },

  async telemetrySnapshot() {
    const [orch, seq, services] = await Promise.all([
      this.getOrchestratorHealth(),
      this.getServiceStartupSequence(),
      this.getServiceRegistry(),
    ]);

    const critical = ["auditor", "client_index", "data_handling", "payments", "watchdog", "orchestrator"];
    const unhealthy = (seq?.sequence_status || []).filter((s) => s.status && s.status !== "healthy");

    return {
      orchestrator: orch,
      startupSequence: seq,
      services,
      summary: {
        expected: critical.length,
        registered: services.length,
        unhealthy: unhealthy.length,
        allHealthy: !!seq?.all_services_healthy,
      },
    };
  },
};

export default adminApi;
