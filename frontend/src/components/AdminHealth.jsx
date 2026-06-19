import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw, Send } from "lucide-react";

const STATUS_MAP = {
  ok:   { icon: CheckCircle2,   color: "#00FF41", label: "HEALTHY" },
  warn: { icon: AlertTriangle,  color: "#FFD700", label: "WARNING" },
  fail: { icon: XCircle,        color: "#FF3333", label: "FAILED" },
};

export default function AdminHealth() {
  const [data, setData] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [testEmail, setTestEmail] = useState("");
  const [testResult, setTestResult] = useState("");

  const load = async () => {
    setRefreshing(true);
    try {
      const r = await api.get("/admin/health");
      setData(r.data);
    } finally { setRefreshing(false); }
  };
  useEffect(() => { load(); }, []);

  const sendTest = async () => {
    if (!testEmail) return;
    setTestResult("Sending…");
    try {
      const r = await api.post("/admin/health/smtp-test", { to: testEmail });
      setTestResult(r.data.ok ? `✓ Sent to ${testEmail} (check the Email Log)` : `✗ Failed (see Email Log)`);
    } catch (e) {
      setTestResult(`✗ ${e.response?.data?.detail || "Failed"}`);
    }
  };

  if (!data) return <div className="font-mono text-zinc-500">loading health<span className="blink">_</span></div>;

  return (
    <div className="space-y-6" data-testid="admin-health">
      {/* Overall + refresh */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${data.ok ? "bg-[#00FF41]" : "bg-[#FF3333]"} animate-pulse`}/>
          <div className="font-display font-bold text-xl">{data.ok ? "All systems operational" : "Degraded service"}</div>
          <div className="font-mono text-xs text-zinc-500">checked: {data.checked_at?.slice(0,19)}Z</div>
        </div>
        <button onClick={load} data-testid="health-refresh" className="brutal-btn flex items-center gap-2 !py-2"><RefreshCw size={14} className={refreshing ? "animate-spin" : ""}/>Refresh</button>
      </div>

      {/* Check cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.checks.map((c, i) => {
          const m = STATUS_MAP[c.status] || STATUS_MAP.warn;
          const Ic = m.icon;
          return (
            <div key={i} className="brutal-card p-5" data-testid={`health-check-${c.name.toLowerCase().replace(/\s+/g, '-')}`}
              style={{ borderColor: m.color + "55" }}>
              <div className="flex items-center justify-between mb-3">
                <div className="font-display font-bold text-base">{c.name}</div>
                <Ic size={18} style={{ color: m.color }}/>
              </div>
              <div className="font-mono text-[10px] tracking-widest" style={{ color: m.color }}>{m.label}</div>
              <div className="font-mono text-xs text-zinc-400 mt-2 break-all">{c.detail}</div>
            </div>
          );
        })}
      </div>

      {/* SMTP test */}
      <div className="brutal-card p-6" data-testid="smtp-test-panel">
        <div className="overline mb-3">// smtp ping</div>
        <p className="font-mono text-xs text-zinc-400 mb-4">Send a test email to verify SMTP delivery end-to-end. Result is also visible in the Email Log tab.</p>
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center">
          <input
            data-testid="smtp-test-to"
            type="email"
            value={testEmail}
            onChange={(e) => setTestEmail(e.target.value)}
            placeholder="recipient@example.com"
            className="brutal-input md:flex-1"
          />
          <button onClick={sendTest} disabled={!testEmail} data-testid="smtp-test-send" className="brutal-btn brutal-btn-primary flex items-center gap-2 justify-center">
            <Send size={14}/>Send Test
          </button>
        </div>
        {testResult && <div data-testid="smtp-test-result" className="mt-3 font-mono text-xs text-zinc-300">{testResult}</div>}
      </div>
    </div>
  );
}
