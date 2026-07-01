import React from "react";

export default function MexicoFlag({ size = 16, className = "" }) {
  return (
    <svg
      viewBox="0 0 180 100"
      width={size * 1.8}
      height={size}
      className={className}
      aria-label="Mexico flag"
    >
      <rect x="0" y="0" width="60" height="100" fill="#006847" />
      <rect x="60" y="0" width="60" height="100" fill="#FFFFFF" />
      <rect x="120" y="0" width="60" height="100" fill="#CE1126" />
      <circle cx="90" cy="50" r="9" fill="#A67C52" />
      <path d="M82 53 Q90 63 98 53" stroke="#006847" strokeWidth="2" fill="none" />
      <path d="M84 45 Q90 38 96 45" stroke="#8B5E3C" strokeWidth="2" fill="none" />
    </svg>
  );
}
