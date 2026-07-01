import React from "react";

export default function USFlag({ size = 16, className = "" }) {
  return (
    <svg
      viewBox="0 0 190 100"
      width={size * 1.9}
      height={size}
      className={className}
      aria-label="United States flag"
    >
      <rect width="190" height="100" fill="#FFFFFF" />
      {[...Array(7)].map((_, i) => (
        <rect key={i} x="0" y={i * 14.2857} width="190" height="7.1429" fill="#B22234" />
      ))}
      <rect x="0" y="0" width="76" height="53.846" fill="#3C3B6E" />
      {[...Array(5)].map((_, row) =>
        [...Array(6)].map((__, col) => (
          <circle
            key={`a-${row}-${col}`}
            cx={6 + col * 12}
            cy={5.8 + row * 10.4}
            r="1.3"
            fill="#FFFFFF"
          />
        ))
      )}
      {[...Array(4)].map((_, row) =>
        [...Array(5)].map((__, col) => (
          <circle
            key={`b-${row}-${col}`}
            cx={12 + col * 12}
            cy={11 + row * 10.4}
            r="1.3"
            fill="#FFFFFF"
          />
        ))
      )}
    </svg>
  );
}
