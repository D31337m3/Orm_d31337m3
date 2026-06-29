import React from "react";

const BrandMark = ({ size = 44, theme = "dark", showWordmark = true, showSubmark = false, className = "" }) => {
  const primary = theme === "light" ? "#7C3AED" : "#A855F7";
  const secondary = theme === "light" ? "#6D28D9" : "#8B5CF6";
  const text = theme === "light" ? "#0A0A0A" : "#FFFFFF";
  const muted = theme === "light" ? "#6B7280" : "#C4B5FD";
  const viewBox = `0 0 ${showWordmark ? 240 : 96} 72`;

  return (
    <div className={`inline-flex items-center gap-3 ${className}`.trim()} aria-label="d31337m3 brand mark">
      <svg width={size} height={size} viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-hidden="true">
        <defs>
          <linearGradient id="brand-gradient" x1="10" y1="12" x2="64" y2="60" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor={primary} />
            <stop offset="100%" stopColor={secondary} />
          </linearGradient>
        </defs>
        <path d="M24 16h16c9.941 0 18 8.059 18 18s-8.059 18-18 18H24" stroke="url(#brand-gradient)" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="18" cy="18" r="2.3" fill={primary} />
        <circle cx="12" cy="28" r="2.3" fill={primary} />
        <circle cx="23" cy="30" r="2.3" fill={secondary} />
        <circle cx="14" cy="40" r="2.3" fill={secondary} />
        <circle cx="27" cy="42" r="2.3" fill={primary} />
        <circle cx="20" cy="50" r="2.3" fill={secondary} />
        <circle cx="34" cy="16" r="2.3" fill={secondary} />
        <circle cx="41" cy="23" r="2.3" fill={primary} />
        <circle cx="46" cy="31" r="2.3" fill={secondary} />
        <circle cx="43" cy="41" r="2.3" fill={primary} />
      </svg>

      {showWordmark && (
        <div className="flex flex-col leading-none">
          <div className="flex items-end gap-1">
            <span className="font-display text-[1.55rem] font-black tracking-tighter" style={{ color: text }}>31.337m3</span>
            <span className="font-display text-[1rem] font-black tracking-tight" style={{ color: muted }}>.com</span>
          </div>
          {showSubmark && <span className="font-mono text-[9px] uppercase tracking-[0.32em]" style={{ color: muted }}>privacy ops platform</span>}
        </div>
      )}
    </div>
  );
};

export default BrandMark;
