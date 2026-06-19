import React, { useEffect, useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import api from "@/lib/api";
import { Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Play, AlertTriangle } from "lucide-react";

const ScoreGauge = ({ score }) => {
  const color = score >= 70 ? "#00FF41" : score >= 40 ? "#FFD700" : "#FF3333";
  return (
    <div className="brutal-card p-8" data-testid="reputation-gauge">
      <div className="overline mb-3">// reputation score</div>
      <div className="flex items-end gap-4 mb-4">
        <div className="font-display font-black text-7xl tracking-tighter" style={{ color }}>{score}</div>
        <div className="font-mono text-zinc-500 mb-3">/ 100</div>
      </div>
      <div className="h-1 bg-[#222] w-full"><div className="h-1" style={{ width: `${score}%`, background: color }} /></div>
      <div className="mt-3 font-mono text-xs text-zinc-500">{score >= 70 ? "EXPOSURE: LOW" : score >= 40 ? "EXPOSURE: MODERATE" : "EXPOSURE: CRITICAL"}</div>
    </div>
  );
};

const Stat = ({ label, value, accent, testid }) => (
  <div className="brutal-card p-6" data-testid={testid}>
    <div className="overline mb-2">{label}</div>
    <div className="font-display font-black text-4xl" style={{ color: accent || "#fff" }}>{value}</div>
  </div>
);

export default function Dashboard() {
  const { user } = useAuth();
  const [score, setScore] = useState(null);
  const [recent, setRecent] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [r1, r2] = await Promise.all([api.get("/reputation"), api.get("/findings")]);
    setScore(r1.data);
    setRecent(r2.data.findings.slice(0, 6));
  };
  useEffect(() => { load(); }, []);

  const runScan = async () => {
    setScanning(true); setMsg("");
    try {
      const r = await api.post("/scan/run", {});
      setMsg(r.data.message);
      setTimeout(load, 2500);
    } catch (e) { setMsg(e.response?.data?.detail || "Scan failed"); }
    finally { setScanning(false); }
  };

  if (!score) return <DashboardLayout title="Overview"><div className="font-mono">loading<span className="blink">_</span></div></DashboardLayout>;

  const subActive = user?.subscription_status === "active";

  return (
    <DashboardLayout title={`Welcome back, ${user?.name || user?.email}`}>
      {!subActive && (
        <div className="brutal-card border-[#FFD700] p-6 mb-6 flex items-center justify-between" data-testid="trial-banner">
          <div className="flex items-center gap-4">
            <AlertTriangle className="text-[#FFD700]" />
            <div>
              <div className="font-display font-bold">You&apos;re on a free trial.</div>
              <div className="font-mono text-xs text-zinc-500 mt-1">Subscribe to unlock unlimited scans, alerts, and removal requests.</div>
            </div>
          </div>
          <Link to="/billing" data-testid="upgrade-cta" className="brutal-btn brutal-btn-primary">Upgrade →</Link>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <ScoreGauge score={score.score} />
        <Stat label="Active Findings" value={score.breakdown.active} accent="#FF3333" testid="stat-active" />
        <Stat label="Removed" value={score.breakdown.removed} accent="#00FF41" testid="stat-removed" />
        <Stat label="Pending Removal" value={score.breakdown.pending_removal} accent="#FFD700" testid="stat-pending" />
        <Stat label="High Severity" value={score.breakdown.high_severity} accent="#FF3333" testid="stat-high-sev" />
        <div className="brutal-card p-6 flex flex-col justify-between">
          <div>
            <div className="overline mb-2">// run new scan</div>
            <div className="font-mono text-xs text-zinc-500">Trigger an immediate crawl across all data brokers using your monitored keywords.</div>
          </div>
          <button data-testid="run-scan-btn" disabled={scanning} onClick={runScan} className="brutal-btn brutal-btn-primary mt-4 flex items-center gap-2 justify-center">
            <Play size={14} /> {scanning ? "Scanning..." : "Run Scan Now"}
          </button>
          {msg && <div className="mt-2 font-mono text-xs text-zinc-400" data-testid="scan-message">› {msg}</div>}
        </div>
      </div>

      <div className="brutal-card p-6">
        <div className="overline mb-3">// recent findings</div>
        {recent.length === 0 ? (
          <div className="font-mono text-zinc-500 py-6">No findings yet. Add keywords and run a scan to start hunting.</div>
        ) : (
          <table className="w-full" data-testid="recent-findings-table">
            <thead><tr className="border-b border-[#222]">
              {["Broker","Keyword","Data","Severity","Date"].map(h=><th key={h} className="overline text-left py-2">{h}</th>)}
            </tr></thead>
            <tbody>
              {recent.map(f => (
                <tr key={f.id} className="border-b border-[#222] hover:bg-[#0a0a0a]">
                  <td className="py-3 font-mono text-sm">{f.broker}</td>
                  <td className="py-3 font-mono text-sm text-zinc-400">{f.keyword_value}</td>
                  <td className="py-3 font-mono text-xs text-zinc-500">{(f.data_found || []).join(", ")}</td>
                  <td className={`py-3 font-mono text-sm severity-${f.severity}`}>{(f.severity || "").toUpperCase()}</td>
                  <td className="py-3 font-mono text-xs text-zinc-500">{f.discovered_at?.slice(0,10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="mt-4"><Link to="/findings" data-testid="view-all-findings" className="font-mono text-sm text-[#FF3333] hover:text-white">view all findings →</Link></div>
      </div>
    </DashboardLayout>
  );
}
