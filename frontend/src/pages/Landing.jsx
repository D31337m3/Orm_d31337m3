import React from "react";
import { Link } from "react-router-dom";
import Marquee from "react-fast-marquee";
import { Terminal, Shield, Database, Bell, Activity, Lock, Search } from "lucide-react";

const BROKERS = ["SPOKEO","WHITEPAGES","ACXIOM","BEENVERIFIED","INTELIUS","MYLIFE","RADARIS","PEOPLEFINDER","TRUTHFINDER","INSTANTCHECKMATE","EQUIFAX","PEEKYOU","USSEARCH","FASTPEOPLESEARCH"];

const Plan = ({ id, name, price, features, highlight }) => (
  <div data-testid={`plan-card-${id}`} className={`brutal-card p-8 ${highlight ? "border-[#FF3333]" : ""}`}>
    {highlight && <div className="overline text-[#FF3333] mb-3">// recommended</div>}
    <div className="font-display font-black text-3xl mb-1">{name}</div>
    <div className="font-mono text-zinc-500 mb-6">/* {id} */</div>
    <div className="font-display font-black text-5xl mb-1">${price}<span className="text-lg text-zinc-500">/mo</span></div>
    <ul className="mt-6 space-y-3 mb-8">
      {features.map(f => <li key={f} className="font-mono text-sm text-zinc-300 flex gap-2"><span className="text-[#FF3333]">›</span>{f}</li>)}
    </ul>
    <Link to="/register" data-testid={`select-plan-${id}`} className={`brutal-btn block text-center ${highlight ? "brutal-btn-primary" : ""}`}>Get Started</Link>
  </div>
);

export default function Landing() {
  return (
    <div className="min-h-screen bg-[#050505] text-white">
      {/* Nav */}
      <nav className="glass-nav sticky top-0 z-50 px-8 py-4 flex items-center justify-between">
        <Link to="/" data-testid="logo-link" className="flex items-center gap-2">
          <Terminal className="text-[#FF3333]" size={20} />
          <span className="font-display font-black text-xl">d31337m3</span>
        </Link>
        <div className="flex items-center gap-6 font-mono text-sm">
          <a href="#features" className="text-zinc-400 hover:text-white">Features</a>
          <a href="#pricing" className="text-zinc-400 hover:text-white">Pricing</a>
          <Link to="/login" data-testid="nav-login" className="text-zinc-400 hover:text-white">Login</Link>
          <Link to="/register" data-testid="nav-register" className="brutal-btn brutal-btn-primary !py-2 !px-4 text-xs">Start</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero-grain px-8 pt-24 pb-20 border-b border-[#222]">
        <div className="max-w-7xl mx-auto grid grid-cols-12 gap-6">
          <div className="col-span-12 md:col-span-8">
            <div className="overline text-[#FF3333] mb-6">// online reputation management</div>
            <h1 className="font-display font-black text-6xl md:text-8xl leading-[0.95] tracking-tighter uppercase mb-8">
              delete<br/>yourself<br/>
              <span className="text-[#FF3333]">from the internet.</span>
            </h1>
            <p className="font-mono text-lg text-zinc-400 max-w-2xl mb-10">
              We hunt down your data across 15+ data brokers, score your exposure, and submit removal requests on your behalf.<br/>
              No theatre. No fluff. Just clean.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link to="/register" data-testid="hero-cta-primary" className="brutal-btn brutal-btn-primary">Start Monitoring →</Link>
              <a href="#pricing" data-testid="hero-cta-secondary" className="brutal-btn">View Plans</a>
            </div>
          </div>
          <div className="col-span-12 md:col-span-4 border border-[#222] p-6 bg-[#0a0a0a] font-mono text-xs">
            <div className="overline mb-3">live.feed</div>
            <div className="space-y-2 text-zinc-400">
              <div>› <span className="text-[#00FF41]">spokeo.com</span> · 1,284 records removed</div>
              <div>› <span className="text-[#00FF41]">whitepages.com</span> · 892 records removed</div>
              <div>› <span className="text-[#00FF41]">beenverified.com</span> · 743 records removed</div>
              <div>› <span className="text-[#FFD700]">acxiom</span> · 312 pending</div>
              <div>› <span className="text-[#FF3333]">intelius</span> · scan in progress<span className="blink">_</span></div>
            </div>
            <div className="mt-6 pt-4 border-t border-[#222]">
              <div className="overline mb-2">reputation_score</div>
              <div className="font-display font-black text-5xl text-[#00FF41]">87<span className="text-base text-zinc-500">/100</span></div>
            </div>
          </div>
        </div>
      </section>

      {/* Marquee of brokers */}
      <section className="py-6 border-b border-[#222] bg-black">
        <div className="overline px-8 mb-3">// targets</div>
        <Marquee speed={40} gradient={false} className="font-display font-black text-3xl text-zinc-700">
          {BROKERS.concat(BROKERS).map((b, i) => (
            <span key={i} className="px-8 hover:text-[#FF3333] transition-colors">{b} <span className="text-[#FF3333]">×</span></span>
          ))}
        </Marquee>
      </section>

      {/* Features */}
      <section id="features" className="px-8 py-24 max-w-7xl mx-auto">
        <div className="overline text-[#FF3333] mb-4">// capabilities</div>
        <h2 className="font-display font-black text-5xl tracking-tighter mb-16 max-w-3xl">Every weapon you need to disappear, in one console.</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[
            {icon: Search, title: "Data Broker Crawling", body: "Real keyword scanning across 15+ broker sites. Name, email, phone, address — we find it all."},
            {icon: Activity, title: "Reputation Score", body: "0-100 score, weighted by severity & broker reach. Watch your exposure shrink in real-time."},
            {icon: Bell, title: "Email Alerts", body: "The moment new data surfaces, you know. Configurable thresholds per keyword."},
            {icon: Shield, title: "Removal Requests", body: "One-click submission. We handle the broker correspondence and track every status."},
            {icon: Database, title: "Keyword Monitoring", body: "Add names, aliases, emails, phone numbers. We watch them — forever."},
            {icon: Lock, title: "Pay Your Way", body: "Interac e-Transfer, PayPal, or USDC on Base/Polygon/ETH. No card needed."},
          ].map(({icon: Ic, title, body}) => (
            <div key={title} className="brutal-card p-6">
              <Ic className="text-[#FF3333] mb-4" size={24} />
              <div className="font-display font-bold text-xl mb-2">{title}</div>
              <div className="font-mono text-sm text-zinc-400 leading-relaxed">{body}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="px-8 py-24 border-t border-[#222] bg-black">
        <div className="max-w-7xl mx-auto">
          <div className="overline text-[#FF3333] mb-4">// pricing</div>
          <h2 className="font-display font-black text-5xl tracking-tighter mb-4">Pick your plan.</h2>
          <p className="font-mono text-zinc-500 mb-12">No contracts. Cancel any time. Pay in fiat or crypto.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Plan id="basic" name="Basic" price={29} features={["5 keywords","Weekly scans","Email alerts","Reputation score"]} />
            <Plan id="pro" name="Pro" price={79} highlight features={["25 keywords","Daily scans","Email alerts","Removal requests","Priority queue"]} />
            <Plan id="enterprise" name="Enterprise" price={199} features={["Unlimited keywords","Real-time scans","Dedicated specialist","API access","White-glove removals"]} />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#222] px-8 py-12 bg-black">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-3"><Terminal className="text-[#FF3333]" size={18}/><span className="font-display font-black">d31337m3</span></div>
            <div className="font-mono text-xs text-zinc-600">© 2026 · payments@d31337m3.com</div>
          </div>
          <div className="font-mono text-xs text-zinc-600 max-w-md text-right">delete me, dot com. an uncompromising privacy weapon.</div>
        </div>
      </footer>
    </div>
  );
}
