import React from "react";

const BrandMark = ({ size = 44, theme = "dark", showWordmark = true, showSubmark = false, className = "" }) => {
  const muted = theme === "light" ? "#6B7280" : "#C4B5FD";
  const iconSize = Number(size) || 44;
  const wordmarkHeight = Math.max(16, Math.round(iconSize * 0.5));

  return (
    <div className={`inline-flex items-center gap-3 ${className}`.trim()} aria-label="d31337m3 brand mark">
      <img
        src="/brand-logo-square.png"
        alt="D31337m3 brand icon"
        width={iconSize}
        height={iconSize}
        className="rounded-md object-contain"
        loading="eager"
        decoding="async"
      />

      {showWordmark && (
        <div className="flex flex-col leading-none">
          <img
            src="/brand-logo-wide.png"
            alt="D31337m3"
            height={wordmarkHeight}
            className="w-auto object-contain"
            loading="eager"
            decoding="async"
          />
          {showSubmark && <span className="font-mono text-[9px] uppercase tracking-[0.32em]" style={{ color: muted }}>privacy ops platform</span>}
        </div>
      )}
    </div>
  );
};

export default BrandMark;
