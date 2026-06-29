import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { motion } from "framer-motion";
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
         ResponsiveContainer, XAxis, YAxis, Tooltip, Legend } from "recharts";
import { DollarSign, TrendingUp, Users, FileSignature } from "lucide-react";

const COLORS = ["#FF3333", "#FFD700", "#00FF41", "#A1A1AA"];

const KPI = ({ icon: Icon, label, value, accent = "#fff", sub, testid }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
    className="brutal-card p-5" data-testid={testid}>
    <div className="flex items-start justify-between mb-2">
      <div className="overline">{label}</div>
      {Icon && <Icon size={16} className="text-[#FF3333]" />}
    </div>
    <div className="font-display font-black text-3xl" style={{ color: accent }}>{value}</div>
    {sub && <div className="font-mono text-xs text-zinc-500 mt-1">{sub}</div>}
  </motion.div>
);

const tooltipStyle = { background: "#0a0a0a", border: "1px solid #222", fontFamily: "JetBrains Mono", fontSize: 12 };
const labelStyle = { color: "#fff" };

export default function AdminAnalytics() {
  const [data, setData] = useState(null);

  const load = async () => {
    const r = await api.get("/admin/analytics");
    setData(r.data);
  };
  useEffect(() => { load(); }, []);

  if (!data) return <div className="font-mono text-zinc-500">loading analytics<span className="blink">_</span></div>;

  return (
    <div className="space-y-6" data-testid="admin-analytics">
      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPI icon={DollarSign} label="MRR" value={`$${data.mrr_total}`} accent="#00FF41" sub="recurring monthly" testid="kpi-mrr" />
        <KPI icon={TrendingUp} label="30-Day Revenue" value={`$${data.totals.total_revenue}`} sub="confirmed payments" testid="kpi-revenue" />
        <KPI icon={Users} label="Active Subs" value={data.totals.active_subs} accent="#00FF41" sub={`${data.totals.trial_users} trial · ${data.totals.suspended_users} suspended`} testid="kpi-subs" />
        <KPI icon={FileSignature} label="Signed Docs" value={data.totals.documents_signed} sub={`${data.totals.documents_dispatched} dispatched`} testid="kpi-docs" />
      </div>

      {/* Time series */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="brutal-card p-6 min-w-0" data-testid="chart-revenue">
          <div className="overline mb-3">// daily revenue · last 30 days</div>
          <div className="h-56 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <AreaChart data={data.timeseries} margin={{ top: 10, right: 10, bottom: 0, left: -25 }}>
                <defs><linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00FF41" stopOpacity={0.4}/>
                  <stop offset="100%" stopColor="#00FF41" stopOpacity={0}/>
                </linearGradient></defs>
                <XAxis dataKey="d" tick={{ fill: "#71717a", fontSize: 9, fontFamily: "JetBrains Mono" }} axisLine={{ stroke: "#222" }} tickLine={false} tickFormatter={(d) => d.slice(5)} />
                <YAxis tick={{ fill: "#71717a", fontSize: 10, fontFamily: "JetBrains Mono" }} axisLine={{ stroke: "#222" }} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} />
                <Area type="monotone" dataKey="revenue" stroke="#00FF41" fill="url(#rev)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="brutal-card p-6 min-w-0" data-testid="chart-signups">
          <div className="overline mb-3">// daily signups · last 30 days</div>
          <div className="h-56 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <BarChart data={data.timeseries} margin={{ top: 10, right: 10, bottom: 0, left: -25 }}>
                <XAxis dataKey="d" tick={{ fill: "#71717a", fontSize: 9, fontFamily: "JetBrains Mono" }} axisLine={{ stroke: "#222" }} tickLine={false} tickFormatter={(d) => d.slice(5)} />
                <YAxis tick={{ fill: "#71717a", fontSize: 10, fontFamily: "JetBrains Mono" }} axisLine={{ stroke: "#222" }} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} />
                <Bar dataKey="signups" fill="#FF3333" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="brutal-card p-6 min-w-0" data-testid="chart-findings">
          <div className="overline mb-3">// findings discovered · last 30 days</div>
          <div className="h-56 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <LineChart data={data.timeseries} margin={{ top: 10, right: 10, bottom: 0, left: -25 }}>
                <XAxis dataKey="d" tick={{ fill: "#71717a", fontSize: 9, fontFamily: "JetBrains Mono" }} axisLine={{ stroke: "#222" }} tickLine={false} tickFormatter={(d) => d.slice(5)} />
                <YAxis tick={{ fill: "#71717a", fontSize: 10, fontFamily: "JetBrains Mono" }} axisLine={{ stroke: "#222" }} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} />
                <Line type="monotone" dataKey="findings" stroke="#FFD700" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="removals" stroke="#00FF41" strokeWidth={2} dot={false} />
                <Legend wrapperStyle={{ fontFamily: "JetBrains Mono", fontSize: 10, color: "#71717a" }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="brutal-card p-6" data-testid="chart-mrr-plan">
          <div className="overline mb-3">// MRR by plan</div>
          <div className="space-y-3">
            {data.mrr_by_plan.map(p => (
              <div key={p.plan}>
                <div className="flex justify-between mb-1">
                  <div className="font-mono text-sm">{p.plan} <span className="text-zinc-500">· {p.subs} subs</span></div>
                  <div className="font-mono text-sm" style={{ color: p.color }}>${p.mrr}/mo</div>
                </div>
                <div className="h-2 bg-[#0a0a0a] border border-[#222]">
                  <motion.div initial={{ width: 0 }} animate={{ width: `${data.mrr_total ? (p.mrr / data.mrr_total) * 100 : 0}%` }} transition={{ duration: 0.8 }}
                    className="h-full" style={{ background: p.color }} />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-6 pt-4 border-t border-[#222] flex justify-between">
            <div className="overline">total mrr</div>
            <div className="font-display font-black text-2xl text-[#00FF41]">${data.mrr_total}</div>
          </div>
        </div>
      </div>

      {/* Pie charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="brutal-card p-6 min-w-0" data-testid="chart-methods">
          <div className="overline mb-3">// payment method split</div>
          <div className="h-56 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <PieChart>
                <Pie data={data.method_split} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={{ fill: "#fff", fontFamily: "JetBrains Mono", fontSize: 11 }}>
                  {data.method_split.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="brutal-card p-6 min-w-0" data-testid="chart-severity">
          <div className="overline mb-3">// active findings by severity</div>
          <div className="h-56 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <PieChart>
                <Pie data={data.severity_distribution} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={45} outerRadius={70} label={{ fill: "#fff", fontFamily: "JetBrains Mono", fontSize: 11 }}>
                  <Cell fill="#71717a"/><Cell fill="#FFD700"/><Cell fill="#fb923c"/><Cell fill="#FF3333"/>
                </Pie>
                <Tooltip contentStyle={tooltipStyle} labelStyle={labelStyle} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
