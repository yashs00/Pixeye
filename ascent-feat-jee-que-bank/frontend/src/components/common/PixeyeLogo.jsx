import React, { useEffect, useRef } from 'react';

/**
 * PIXEYE mark — an eye whose iris is a grid of pixels.
 * The iris follows the cursor (eye tracking), and the eye blinks every few seconds.
 * Pure SVG + CSS; one shared mousemove listener, throttled with requestAnimationFrame.
 */
const PIX = [
  // (x, y, colour stop 0..1) — a 5x5 pixel iris with the centre cut out for the pupil
  [-2, -1, 0.0], [-2, 0, 0.1], [-2, 1, 0.2],
  [-1, -2, 0.1], [-1, -1, 0.25], [-1, 0, 0.35], [-1, 1, 0.45], [-1, 2, 0.55],
  [0, -2, 0.3], [0, 2, 0.7],
  [1, -2, 0.45], [1, -1, 0.55], [1, 0, 0.65], [1, 1, 0.8], [1, 2, 0.9],
  [2, -1, 0.8], [2, 0, 0.9], [2, 1, 1.0],
];

const lerp = (a, b, t) => a + (b - a) * t;
const hex = (c) => `#${c.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('')}`;
const CYAN = [34, 228, 255];
const VIOLET = [130, 87, 255];
const PINK = [255, 62, 201];
const stop = (t) => (t < 0.5 ? hex(CYAN.map((v, i) => lerp(v, VIOLET[i], t * 2))) : hex(VIOLET.map((v, i) => lerp(v, PINK[i], (t - 0.5) * 2))));

export default function PixeyeLogo({ size = 36, track = true, className = '' }) {
  const iris = useRef(null);

  useEffect(() => {
    if (!track || typeof window === 'undefined') return undefined;
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined;
    let raf = 0;
    let target = [0, 0];
    const onMove = (e) => {
      const el = iris.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      const d = Math.hypot(dx, dy) || 1;
      const reach = Math.min(1, d / 260);         // further away -> iris moves more, up to its limit
      target = [(dx / d) * 2.2 * reach, (dy / d) * 1.6 * reach];
      if (!raf) raf = requestAnimationFrame(apply);
    };
    const apply = () => {
      raf = 0;
      if (iris.current) iris.current.style.transform = `translate(${target[0]}px, ${target[1]}px)`;
    };
    window.addEventListener('mousemove', onMove, { passive: true });
    return () => { window.removeEventListener('mousemove', onMove); if (raf) cancelAnimationFrame(raf); };
  }, [track]);

  const px = 2.6; // pixel size in viewBox units
  return (
    <svg
      viewBox="-16 -16 32 32"
      width={size}
      height={size}
      className={`pixeye-logo ${className}`}
      role="img"
      aria-label="PIXEYE"
    >
      <defs>
        <linearGradient id="px-rim" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#22e4ff" />
          <stop offset="0.5" stopColor="#8257ff" />
          <stop offset="1" stopColor="#ff3ec9" />
        </linearGradient>
        <radialGradient id="px-glow" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#8257ff" stopOpacity="0.55" />
          <stop offset="1" stopColor="#8257ff" stopOpacity="0" />
        </radialGradient>
        <clipPath id="px-eye">
          <path d="M-14 0 C -9 -9.5, 9 -9.5, 14 0 C 9 9.5, -9 9.5, -14 0 Z" />
        </clipPath>
      </defs>

      {/* glow halo */}
      <circle r="15" fill="url(#px-glow)" />

      {/* eyelid group blinks */}
      <g className="pixeye-lid">
        {/* sclera */}
        <path d="M-14 0 C -9 -9.5, 9 -9.5, 14 0 C 9 9.5, -9 9.5, -14 0 Z" fill="#0b0d14" stroke="url(#px-rim)" strokeWidth="1.6" />

        {/* iris + pupil, clipped to the eye, tracks the cursor */}
        <g clipPath="url(#px-eye)">
          <g ref={iris} className="pixeye-iris" style={{ transition: 'transform 120ms ease-out' }}>
            {PIX.map(([x, y, t]) => (
              <rect
                key={`${x}${y}`}
                x={x * px - px / 2 + 0.2}
                y={y * px - px / 2 + 0.2}
                width={px - 0.4}
                height={px - 0.4}
                rx="0.5"
                fill={stop(t)}
                opacity={0.92}
              />
            ))}
            {/* pupil */}
            <rect x={-px / 2 + 0.2} y={-px / 2 + 0.2} width={px - 0.4} height={px - 0.4} rx="0.5" fill="#05060a" />
            {/* light glint */}
            <circle cx="-2.2" cy="-2.4" r="0.9" fill="#ffffff" opacity="0.9" />
          </g>
        </g>
      </g>
    </svg>
  );
}
