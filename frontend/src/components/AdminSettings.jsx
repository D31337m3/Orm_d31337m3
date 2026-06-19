import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Shield, Mail, Wallet, Globe, Settings as SettingsIcon } from "lucide-react";

const Row = ({ k, v, accent, mono = true }) => (
  <div className="grid grid-cols-2 gap-4 border-b border-[#222] py-2">
    <div className="overline">{k}</div>
    <div className={`${mono ? "font-mono" : "font-display"} text-sm break-all`} style={{ color: accent || "#fff" }}>
      {v === true ? <span className="text-[#00FF41]">enabled</span>
       : v === false ? <span className="text-[#FF3333]">disabled</span>
       : (v ?? <span className="text-zinc-600">—</span>)}
    </div>
  </div>
);

const Section = ({ icon: Ic, title, children }) => (
  <div className="brutal-card p-6">
    <div className="flex items-center gap-2 mb-4">
      {Ic && <Ic size={16} className="text-[#FF3333]"/>}
      <div className="overline">// {title}</div>
    </div>
    {children}
  </div>
);

export default function AdminSettings() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/admin/settings").then(r => setData(r.data));
  }, []);

  if (!data) return <div className="font-mono text-zinc-500">loading settings<span className="blink">_</span></div>;

  const e = data.environment;

  return (
    <div className="space-y-6" data-testid="admin-settings">
      <div className="brutal-card p-4 border-[#FFD700]/40 bg-[#1a1a08]/30">
        <div className="font-mono text-xs text-zinc-300">
          <span className="text-[#FFD700] font-bold">// READ-ONLY:</span>
          {" "}Most settings live in <code className="text-white">backend/.env</code>. Edit the file
          and run <code className="text-white">sudo supervisorctl restart d31337m3-backend</code> to apply.
          Broker contacts &amp; user-facing data are editable from their own tabs.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Section icon={SettingsIcon} title="core">
          <Row k="Database" v={e.mongo_db}/>
          <Row k="Admin email" v={e.admin_email}/>
          <Row k="CORS origins" v={e.cors_origins}/>
          <Row k="JWT algorithm" v={e.jwt_algorithm}/>
          <Row k="Token expiry (min)" v={e.token_expiry_minutes}/>
        </Section>

        <Section icon={Mail} title="email (smtp)">
          <Row k="Enabled" v={e.smtp_enabled}/>
          <Row k="Host" v={e.smtp_host}/>
          <Row k="Port" v={e.smtp_port}/>
          <Row k="Username" v={e.smtp_username}/>
          <Row k="Password" v={e.smtp_password_masked}/>
          <Row k="From" v={e.smtp_from}/>
        </Section>

        <Section icon={Wallet} title="payments">
          <Row k="Interac email" v={e.payments_email}/>
          <Row k="Crypto wallet" v={e.crypto_wallet}/>
          <Row k="PayPal configured" v={e.paypal_configured}/>
          <Row k="PayPal API base" v={e.paypal_api_base}/>
        </Section>

        <Section icon={Globe} title="blockchain rpcs">
          <Row k="Ethereum" v={e.ethereum_rpc}/>
          <Row k="Polygon" v={e.polygon_rpc}/>
          <Row k="Base" v={e.base_rpc}/>
        </Section>

        <Section icon={Shield} title="rate limiter">
          <Row k="Window" v={`${data.rate_limiter.window_seconds / 60} minutes`}/>
          <Row k="Max attempts / IP" v={data.rate_limiter.max_attempts}/>
          <Row k="Active buckets" v={data.rate_limiter.active_buckets}/>
        </Section>

        <Section icon={SettingsIcon} title="plans & coverage">
          {data.plans.map(p => <Row key={p.id} k={p.name} v={`$${p.price_usd}/mo · ${p.keyword_limit === 999 ? "∞" : p.keyword_limit} kw · ${p.scan_freq}`}/>)}
          <Row k="Countries" v={data.supported_countries.join(" · ")}/>
          <Row k="Brokers (DB)" v={data.broker_count_db}/>
          <Row k="Brokers (built-in)" v={data.broker_count_builtin}/>
        </Section>
      </div>
    </div>
  );
}
