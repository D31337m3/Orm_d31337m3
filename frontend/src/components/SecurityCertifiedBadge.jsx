import React from "react";
import { ShieldCheck } from "lucide-react";

export default function SecurityCertifiedBadge({ className = "" }) {
  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border border-[#1f7a44] bg-[#062614] px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-[#8cf5b3] ${className}`}
      aria-label="Security certified"
      title="Security-certified operations"
    >
      <ShieldCheck size={13} className="text-[#8cf5b3]" />
      Security Certified
      <span className="text-[#6dbf8f]">RSA-2048</span>
      <span className="text-[#6dbf8f]">TLS 1.3</span>
    </div>
  );
}
