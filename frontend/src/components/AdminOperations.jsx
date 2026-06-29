import React, { useEffect, useMemo, useState } from "react";
import adminApi from "@/lib/adminApi";
import { Activity, Server, Users, CreditCard, Wrench, RefreshCcw } from "lucide-react";

const StatusPill = ({ status }) => {
  const normalized = String(status || "unknown").toLowerCase();
  const color =
    normalized === "healthy" || normalized === "ok"
      ? "#00FF41"
      : normalized === "starting" || normalized === "stopping"
      ? "#FFD700"
      : "#FF3333";
  return (
    <span className="font-mono text-[10px] px-2 py-0.5 border" style={{ color, borderColor: color }}>
      {normalized.toUpperCase()}
    </span>
  );
};

const Card = ({ icon: Icon, title, children }) => (
  <div className="brutal-card p-5">
    <div className="flex items-center gap-2 mb-3">
      <Icon size={15} className="text-[#FF3333]" />
      <div className="overline">// {title}</div>
    </div>
    {children}
  </div>
);

export default function AdminOperations() {
  const [loading, setLoading] = useState(true);
  const [telemetry, setTelemetry] = useState(null);
  const [users, setUsers] = useState([]);
  const [payments, setPayments] = useState([]);
  const [notice, setNotice] = useState("");
  const [creating, setCreating] = useState(false);

  const [newUser, setNewUser] = useState({
    email: "",
    password: "",
    name: "",
    promo_code: "",
  });

  const refresh = async () => {
    setLoading(true);
    setNotice("");
    try {
      const [t, u, p] = await Promise.all([
        adminApi.telemetrySnapshot(),
        adminApi.listUsers(),
        adminApi.listPayments(),
      ]);
      setTelemetry(t);
      setUsers(u || []);
      setPayments(p || []);
    } catch (err) {
      setNotice(err?.response?.data?.detail || "Failed to load operations data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const startupSeq = telemetry?.startupSequence?.sequence_status || [];

  const pendingPayments = useMemo(
    () => (payments || []).filter((p) => ["awaiting_confirmation", "pending_manual_review", "awaiting_tx_hash"].includes(p.status)),
    [payments]
  );

  const createUser = async () => {
    if (!newUser.email || !newUser.password) {
      setNotice("Email and password are required");
      return;
    }
    setCreating(true);
    try {
      const res = await adminApi.createUser(newUser);
      if (res?.ok === false) {
        setNotice(res.message || "Create user endpoint unavailable");
      } else {
        setNotice(`User created: ${newUser.email}`);
        setNewUser({ email: "", password: "", name: "", promo_code: "" });
        await refresh();
      }
    } catch (err) {
      setNotice(err?.response?.data?.detail || "Failed to create user");
    } finally {
      setCreating(false);
    }
  };

  const setServiceStatus = async (serviceName, status) => {
    const res = await adminApi.updateServiceStatus(serviceName, status);
    if (res?.ok === false) {
      setNotice(`${serviceName}: ${res.message}`);
      return;
    }
    setNotice(`${serviceName} status -> ${status}`);
    await refresh();
  };

  const triggerHeartbeat = async (serviceName) => {
    const res = await adminApi.sendServiceHeartbeat(serviceName);
    if (res?.ok === false) {
      setNotice(`${serviceName}: ${res.message}`);
      return;
    }
    setNotice(`${serviceName} heartbeat sent`);
    await refresh();
  };

  const actPayment = async (id, action) => {
    const fn = action === "confirm" ? adminApi.confirmPayment : adminApi.rejectPayment;
    const res = await fn(id);
    if (res?.ok === false) {
      setNotice(res.message || `Unable to ${action} payment`);
      return;
    }
    setNotice(`Payment ${id.slice(0, 8)} ${action}ed`);
    await refresh();
  };

  if (loading) return <div className="font-mono text-zinc-500">loading operations<span className="blink">_</span></div>;

  return (
    <div className="space-y-6" data-testid="admin-operations">
      <div className="flex items-center justify-between">
        <div className="font-display font-bold text-xl">Admin Operations Center</div>
        <button className="brutal-btn !py-2 !px-3 flex items-center gap-2" onClick={refresh}>
          <RefreshCcw size={14} /> Refresh
        </button>
      </div>

      {notice && <div className="brutal-card p-3 font-mono text-xs text-zinc-300">{notice}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card icon={Activity} title="telemetry">
          <div className="font-mono text-xs text-zinc-400">Expected services: {telemetry?.summary?.expected ?? 6}</div>
          <div className="font-mono text-xs text-zinc-400">Registered: {telemetry?.summary?.registered ?? 0}</div>
          <div className="font-mono text-xs text-zinc-400">Unhealthy: {telemetry?.summary?.unhealthy ?? 0}</div>
          <div className="mt-2"><StatusPill status={telemetry?.summary?.allHealthy ? "healthy" : "degraded"} /></div>
        </Card>

        <Card icon={Server} title="service control">
          <div className="font-mono text-xs text-zinc-400">Control plane actions from orchestrator APIs.</div>
          <div className="font-mono text-[10px] text-zinc-500 mt-2">NOTE: host-level start/stop still lives in systemd runbooks.</div>
        </Card>

        <Card icon={Users} title="user admin">
          <div className="font-mono text-xs text-zinc-400">Users loaded: {users.length}</div>
          <div className="font-mono text-xs text-zinc-400">Admin creation + account lifecycle.</div>
        </Card>

        <Card icon={CreditCard} title="payments ops">
          <div className="font-mono text-xs text-zinc-400">Pending queue: {pendingPayments.length}</div>
          <div className="font-mono text-xs text-zinc-400">Manual confirm/reject where enabled.</div>
        </Card>
      </div>

      <Card icon={Server} title="services">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#222]">
                <th className="text-left overline py-2">service</th>
                <th className="text-left overline py-2">status</th>
                <th className="text-left overline py-2">host:port</th>
                <th className="text-left overline py-2">actions</th>
              </tr>
            </thead>
            <tbody>
              {startupSeq.map((s) => (
                <tr key={s.service_name} className="border-b border-[#222]">
                  <td className="font-mono text-xs py-2">{s.service_name}</td>
                  <td className="py-2"><StatusPill status={s.status} /></td>
                  <td className="font-mono text-xs py-2 text-zinc-400">{s.host ? `${s.host}:${s.port}` : "—"}</td>
                  <td className="py-2">
                    <div className="flex gap-2 flex-wrap">
                      <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => triggerHeartbeat(s.service_name)}>heartbeat</button>
                      <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => setServiceStatus(s.service_name, "healthy")}>mark healthy</button>
                      <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => setServiceStatus(s.service_name, "stopping")}>mark stopping</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card icon={Users} title="create user">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input className="brutal-input" placeholder="Email" value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} />
            <input className="brutal-input" placeholder="Password" type="password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} />
            <input className="brutal-input" placeholder="Name (optional)" value={newUser.name} onChange={(e) => setNewUser({ ...newUser, name: e.target.value })} />
            <input className="brutal-input" placeholder="Promo code (optional)" value={newUser.promo_code} onChange={(e) => setNewUser({ ...newUser, promo_code: e.target.value })} />
          </div>
          <button className="brutal-btn brutal-btn-primary mt-3" onClick={createUser} disabled={creating}>{creating ? "CREATING..." : "CREATE USER"}</button>
        </Card>

        <Card icon={Wrench} title="system maintenance">
          <div className="font-mono text-xs text-zinc-400 mb-3">Use these checks before cutover and after deploy.</div>
          <div className="flex gap-2 flex-wrap">
            <button className="brutal-btn !py-2 !px-3 text-xs" onClick={refresh}>Run telemetry sweep</button>
            <button className="brutal-btn !py-2 !px-3 text-xs" onClick={() => setNotice("Use host runbooks for service start/stop/restart via systemd")}>Show runbook hint</button>
          </div>
        </Card>
      </div>

      <Card icon={CreditCard} title="pending payments">
        <div className="space-y-2">
          {pendingPayments.length === 0 && <div className="font-mono text-xs text-zinc-500">No pending payments.</div>}
          {pendingPayments.map((p) => (
            <div key={p.id} className="flex flex-wrap items-center justify-between border border-[#222] px-3 py-2">
              <div className="font-mono text-xs text-zinc-300">
                <span className="text-white">{p.id?.slice(0, 8)}</span> · {p.plan_id} · {p.method} · ${p.amount_usd} · {p.status}
              </div>
              <div className="flex gap-2">
                <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => actPayment(p.id, "confirm")}>confirm</button>
                <button className="brutal-btn !py-1 !px-2 text-[10px]" onClick={() => actPayment(p.id, "reject")}>reject</button>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
