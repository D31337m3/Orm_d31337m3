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

  async listAuditLog() {
    const data = await tryGet(["/admin/audit-log"], { audit: [] });
    return data?.audit || [];
  },

  async supportAdminChats() {
    const data = await tryGet(["/support/admin/chats"], { chats: [] });
    return data?.chats || [];
  },

  async supportAdminChatMessages(chatId) {
    const data = await tryGet([`/support/admin/chats/${chatId}/messages`], { messages: [] });
    return data;
  },

  async supportAdminSendMessage(chatId, text) {
    return await tryPost([`/support/admin/chats/${chatId}/messages`], { text }, { ok: false, message: "support reply endpoint unavailable" });
  },

  async supportAdminTickets() {
    const data = await tryGet(["/support/admin/tickets"], { tickets: [] });
    return data?.tickets || [];
  },

  async supportAdminCreateTicketFromChat(chatId, payload) {
    return await tryPost([`/support/admin/tickets/from-chat/${chatId}`], payload, { ok: false, message: "ticket-from-chat endpoint unavailable" });
  },

  async supportAdminPatchTicket(ticketId, payload) {
    return await tryPatch([`/support/admin/tickets/${ticketId}`], payload, { ok: false, message: "ticket update endpoint unavailable" });
  },

  async workforceAdminShifts() {
    const data = await tryGet(["/workforce/admin/shifts"], { shifts: [] });
    return data?.shifts || [];
  },

  async workforceAdminCreateShift(payload) {
    return await tryPost(["/workforce/admin/shifts"], payload, { ok: false, message: "create shift endpoint unavailable" });
  },

  async workforceAdminPatchShift(shiftId, payload) {
    return await tryPatch([`/workforce/admin/shifts/${shiftId}`], payload, { ok: false, message: "update shift endpoint unavailable" });
  },

  async workforceAdminTimesheets() {
    const data = await tryGet(["/workforce/admin/timesheets"], { timesheets: [] });
    return data?.timesheets || [];
  },

  async workforceAdminCreateTimesheet(payload) {
    return await tryPost(["/workforce/admin/timesheets"], payload, { ok: false, message: "create timesheet endpoint unavailable" });
  },

  async workforceAdminPatchTimesheet(timesheetId, payload) {
    return await tryPatch([`/workforce/admin/timesheets/${timesheetId}`], payload, { ok: false, message: "update timesheet endpoint unavailable" });
  },

  async workforceAdminPayrollRuns() {
    const data = await tryGet(["/workforce/admin/payroll-runs"], { payroll_runs: [] });
    return data?.payroll_runs || [];
  },

  async workforceAdminCreatePayrollRun(payload) {
    return await tryPost(["/workforce/admin/payroll-runs"], payload, { ok: false, message: "create payroll endpoint unavailable" });
  },

  async workforceAdminPatchPayrollRun(runId, payload) {
    return await tryPatch([`/workforce/admin/payroll-runs/${runId}`], payload, { ok: false, message: "update payroll endpoint unavailable" });
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

    const critical = [
      "auditor",
      "client_index",
      "data_handling",
      "payments",
      "support_hub",
      "workforce_ops",
      "watchdog",
      "orchestrator",
    ];
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

  async getOpsCapabilities() {
    return await tryGet([
      "/admin/ops/capabilities",
    ], {
      host_controls_enabled: false,
      service_units: {},
    });
  },

  async restartService(serviceName) {
    return await tryPost([
      `/admin/ops/restart-service/${serviceName}`,
    ], {}, { ok: false, message: "restart service endpoint unavailable" });
  },

  async restartAllServices() {
    return await tryPost([
      "/admin/ops/restart-all",
    ], {}, { ok: false, message: "restart-all endpoint unavailable" });
  },

  async rebootServer() {
    return await tryPost([
      "/admin/ops/reboot-server",
    ], { confirm: "REBOOT_PHYSICAL_SERVER" }, { ok: false, message: "reboot endpoint unavailable" });
  },
};

export default adminApi;
