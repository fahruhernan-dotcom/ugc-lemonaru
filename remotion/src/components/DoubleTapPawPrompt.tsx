import React from "react";
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TheBoldFont } from "../load-font";

interface DoubleTapPawPromptProps {
  /** Frame when the prompt starts appearing (typically right after hook, e.g. frame 90 / 3.0s) */
  readonly fromFrame?: number;
  /** Duration in frames (default 105 frames / 3.5s) */
  readonly durationInFrames?: number;
  readonly promptText?: string;
}

/**
 * High-Production Motion Graphic: Interactive Double-Tap Velocity Catalyst
 * Crafted per Remotion Motion Graphics & Disney 12 Principles:
 * - Bespoke Vector SVGs (zero low-res emojis)
 * - Two-stage tactile tap rhythm (Tap 1 -> Tap 2) with crisp expanding concentric shockwave rings
 * - Explosive Golden Cat Paw with squash & stretch spring physics
 * - Multi-layered radiating sparkle particle burst
 * - Premium Frosted Glassmorphism Pill with dynamic specular sheen sweep
 * - Sine-wave breathing micro-motion
 */
export const DoubleTapPawPrompt: React.FC<DoubleTapPawPromptProps> = ({
  fromFrame = 95,
  durationInFrames = 105,
  promptText = "PENCET LAYAR 2X LIAT ANIMASINYA! 🐾",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Active frame window check
  if (frame < fromFrame || frame >= fromFrame + durationInFrames) {
    return null;
  }

  const relFrame = frame - fromFrame;

  // 1. Entrance Spring (Smooth upward slide + scale overshoot)
  const enterProgress = spring({
    frame: relFrame,
    fps,
    config: {
      damping: 14,
      mass: 0.8,
      stiffness: 160,
    },
  });

  // 2. Exit Spring / Interpolation (Snappy drop-down fade)
  const exitProgress = interpolate(
    relFrame,
    [durationInFrames - 14, durationInFrames],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  const containerOpacity = enterProgress * (1 - exitProgress);
  const containerScale =
    interpolate(enterProgress, [0, 1], [0.82, 1]) * (1 - exitProgress * 0.15);
  const containerTranslateY =
    interpolate(enterProgress, [0, 1], [40, 0]) - exitProgress * 20;

  // 3. Tactile Double-Tap Timing (Tap 1 at relFrame 12, Tap 2 at relFrame 26)
  const tap1Start = 12;
  const tap2Start = 26;

  // Tap 1 press down & rebound (Haptic squash)
  const tap1Press = spring({
    frame: Math.max(0, relFrame - tap1Start),
    fps,
    config: { damping: 9, stiffness: 260 },
  });
  const tap1Bounce =
    relFrame >= tap1Start && relFrame < tap1Start + 11
      ? Math.sin(tap1Press * Math.PI) * 0.28
      : 0;

  // Tap 2 press down & rebound (Stronger impact)
  const tap2Press = spring({
    frame: Math.max(0, relFrame - tap2Start),
    fps,
    config: { damping: 9, stiffness: 260 },
  });
  const tap2Bounce =
    relFrame >= tap2Start && relFrame < tap2Start + 11
      ? Math.sin(tap2Press * Math.PI) * 0.32
      : 0;

  const handScale = Math.max(0.7, 1 - tap1Bounce - tap2Bounce);

  // 4. Concentric Shockwave Rings (Crisp vector borders expanding outward from hand edge)
  // Ring 1A & 1B (First Tap)
  const r1Rel = Math.max(0, relFrame - tap1Start);
  const r1A_scale = interpolate(r1Rel, [0, 18], [0.95, 2.3], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const r1A_opacity = interpolate(r1Rel, [0, 5, 18], [0.95, 0.7, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const r1B_scale = interpolate(r1Rel, [2, 20], [0.95, 2.7], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const r1B_opacity = interpolate(r1Rel, [2, 7, 20], [0.7, 0.45, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Ring 2A & 2B (Second Tap - High Energy Burst)
  const r2Rel = Math.max(0, relFrame - tap2Start);
  const r2A_scale = interpolate(r2Rel, [0, 22], [0.95, 3.1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const r2A_opacity = interpolate(r2Rel, [0, 6, 22], [1, 0.8, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const r2B_scale = interpolate(r2Rel, [3, 25], [0.95, 3.6], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const r2B_opacity = interpolate(r2Rel, [3, 8, 25], [0.85, 0.5, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // 5. Golden Paw Bloom (Squash & Stretch Spring starting on 2nd tap)
  const pawBloomSpring = spring({
    frame: Math.max(0, relFrame - tap2Start),
    fps,
    config: {
      damping: 11,
      mass: 0.6,
      stiffness: 175,
    },
  });

  // Paw dynamic tilt on pop
  const pawRotation = interpolate(pawBloomSpring, [0, 0.5, 0.8, 1], [-14, 6, -2, 0]);

  // 6. Particle Burst Physics (12 golden sparkles and stars radiating out)
  const particleProgress = spring({
    frame: Math.max(0, relFrame - (tap2Start + 1)),
    fps,
    config: {
      damping: 12,
      mass: 0.5,
      stiffness: 140,
    },
  });

  const particleAngles = [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330];

  // 7. Specular Sheen Sweep across CTA Pill (sweeps across between frames 36 and 64)
  const sheenProgress = interpolate(
    relFrame,
    [36, 62],
    [-120, 220],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  // 8. Idle Micro-Motion (Subtle breathing float)
  const floatY = Math.sin(relFrame / 7.5) * 3.5;

  // Clean prompt text (remove any trailing raw emoji like 🐾 to avoid platform font glitches)
  const cleanedText = promptText.replace(/[🐾✨👆👇🔥❤️]/g, "").trim();

  return (
    <div
      style={{
        transform: `translate(-50%, -50%) translateY(${containerTranslateY + floatY}px) scale(${containerScale})`,
        opacity: containerOpacity,
      }}
      className="absolute left-1/2 top-[51%] z-40 pointer-events-none flex flex-col items-center justify-center select-none"
    >
      {/* 🌟 1. CENTRAL INTERACTIVE STAGE (Touch rings + Hand + Exploding Paw) */}
      <div className="relative w-56 h-56 flex items-center justify-center">
        {/* Soft Radial Ambient Glow */}
        <div
          style={{
            opacity: interpolate(pawBloomSpring, [0, 1], [0.3, 0.9]),
            transform: `scale(${interpolate(pawBloomSpring, [0, 1], [0.8, 1.35])})`,
          }}
          className="absolute w-48 h-48 rounded-full bg-gradient-to-tr from-amber-500/35 via-yellow-400/30 to-amber-300/10 blur-2xl pointer-events-none"
        />

        {/* --- SHOCKWAVE RINGS (FIRST TAP) --- */}
        {relFrame >= tap1Start && r1A_opacity > 0 && (
          <div
            style={{
              transform: `scale(${r1A_scale})`,
              opacity: r1A_opacity,
            }}
            className="absolute w-20 h-20 rounded-full border-2 border-amber-300 shadow-[0_0_12px_rgba(251,191,36,0.6)] pointer-events-none"
          />
        )}
        {relFrame >= tap1Start + 2 && r1B_opacity > 0 && (
          <div
            style={{
              transform: `scale(${r1B_scale})`,
              opacity: r1B_opacity,
            }}
            className="absolute w-20 h-20 rounded-full border border-yellow-200/80 pointer-events-none"
          />
        )}

        {/* --- SHOCKWAVE RINGS (SECOND TAP BURST) --- */}
        {relFrame >= tap2Start && r2A_opacity > 0 && (
          <div
            style={{
              transform: `scale(${r2A_scale})`,
              opacity: r2A_opacity,
            }}
            className="absolute w-20 h-20 rounded-full border-3 border-yellow-300 bg-amber-400/15 shadow-[0_0_24px_rgba(251,191,36,0.8)] pointer-events-none"
          />
        )}
        {relFrame >= tap2Start + 3 && r2B_opacity > 0 && (
          <div
            style={{
              transform: `scale(${r2B_scale})`,
              opacity: r2B_opacity,
            }}
            className="absolute w-20 h-20 rounded-full border-2 border-amber-400/70 shadow-[0_0_16px_rgba(245,158,11,0.5)] pointer-events-none"
          />
        )}

        {/* --- SPARKLE PARTICLE BURST ON TAP 2 --- */}
        {relFrame >= tap2Start + 1 && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            {particleAngles.map((angleDeg, idx) => {
              const rad = (angleDeg * Math.PI) / 180;
              const distance = interpolate(
                particleProgress,
                [0, 1],
                [18, 92 + (idx % 3) * 18]
              );
              const pX = Math.cos(rad) * distance;
              const pY = Math.sin(rad) * distance;
              const pScale = interpolate(
                particleProgress,
                [0, 0.35, 1],
                [0, 1.25, 0]
              );
              const pOpacity = interpolate(
                particleProgress,
                [0, 0.75, 1],
                [1, 1, 0]
              );
              const isStar = idx % 2 === 0;

              return (
                <div
                  key={idx}
                  style={{
                    transform: `translate(${pX}px, ${pY}px) scale(${pScale})`,
                    opacity: pOpacity,
                  }}
                  className="absolute"
                >
                  {isStar ? (
                    /* SVG 4-Point Star Sparkle */
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      className="drop-shadow-[0_0_8px_rgba(251,191,36,0.9)]"
                    >
                      <path
                        d="M12 0L14.5 9.5L24 12L14.5 14.5L12 24L9.5 14.5L0 12L9.5 9.5L12 0Z"
                        fill="#FDE047"
                      />
                    </svg>
                  ) : (
                    /* Glowing Mini Orb */
                    <div className="w-2.5 h-2.5 rounded-full bg-gradient-to-r from-amber-300 to-yellow-200 shadow-[0_0_10px_rgba(251,191,36,1)]" />
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* --- EXPLODING GOLDEN CAT PAW (VECTOR SVG) --- */}
        {pawBloomSpring > 0.05 && (
          <div
            style={{
              transform: `scale(${pawBloomSpring * 1.22}) rotate(${pawRotation}deg)`,
              opacity: Math.min(1, pawBloomSpring * 1.4),
            }}
            className="absolute z-20 flex items-center justify-center pointer-events-none drop-shadow-[0_10px_30px_rgba(245,158,11,0.7)]"
          >
            <svg
              width="106"
              height="106"
              viewBox="0 0 100 100"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <linearGradient
                  id="pawGradientPro"
                  x1="20"
                  y1="10"
                  x2="80"
                  y2="90"
                  gradientUnits="userSpaceOnUse"
                >
                  <stop offset="0%" stopColor="#FEF08A" />
                  <stop offset="35%" stopColor="#FBBF24" />
                  <stop offset="100%" stopColor="#EA580C" />
                </linearGradient>
                <linearGradient
                  id="pawHighlight"
                  x1="30"
                  y1="30"
                  x2="70"
                  y2="80"
                  gradientUnits="userSpaceOnUse"
                >
                  <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.5" />
                  <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
                </linearGradient>
                <filter id="neonGlowPro" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3.5" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              {/* Main Palm Pad */}
              <path
                d="M50 42C36 42 27 52 27 65C27 77 36 86 50 86C64 86 73 77 73 65C73 52 64 42 50 42Z"
                fill="url(#pawGradientPro)"
                filter="url(#neonGlowPro)"
              />
              {/* Palm Specular Highlight */}
              <ellipse cx="50" cy="54" rx="14" ry="7" fill="url(#pawHighlight)" />

              {/* 4 Toe Pads (Toe Beans) */}
              {/* Toe 1 (Far Left) */}
              <ellipse
                cx="23"
                cy="40"
                rx="7.5"
                ry="11"
                transform="rotate(-25 23 40)"
                fill="url(#pawGradientPro)"
              />
              {/* Toe 2 (Center Left) */}
              <ellipse
                cx="40"
                cy="27"
                rx="8"
                ry="12"
                transform="rotate(-8 40 27)"
                fill="url(#pawGradientPro)"
              />
              {/* Toe 3 (Center Right) */}
              <ellipse
                cx="60"
                cy="27"
                rx="8"
                ry="12"
                transform="rotate(8 60 27)"
                fill="url(#pawGradientPro)"
              />
              {/* Toe 4 (Far Right) */}
              <ellipse
                cx="77"
                cy="40"
                rx="7.5"
                ry="11"
                transform="rotate(25 77 40)"
                fill="url(#pawGradientPro)"
              />

              {/* Specular dots on toes */}
              <circle cx="40" cy="22" r="3" fill="#FFFFFF" fillOpacity="0.65" />
              <circle cx="60" cy="22" r="3" fill="#FFFFFF" fillOpacity="0.65" />
            </svg>
          </div>
        )}

        {/* --- TACTILE TOUCH POINTER (Fades out smoothly when Paw blooms) --- */}
        <div
          style={{
            transform: `scale(${handScale})`,
            opacity: interpolate(pawBloomSpring, [0, 0.7], [1, 0]),
          }}
          className="relative z-10 w-20 h-20 rounded-full bg-gradient-to-br from-neutral-900/90 via-zinc-900/95 to-neutral-950/95 backdrop-blur-md border-2 border-amber-400/90 flex items-center justify-center shadow-[0_10px_30px_rgba(0,0,0,0.8),0_0_15px_rgba(245,158,11,0.35)]"
        >
          {/* Custom SVG Stylized Pointer Gesture */}
          <svg
            width="38"
            height="38"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-amber-300 drop-shadow-[0_2px_8px_rgba(251,191,36,0.6)]"
          >
            <path d="M18 11V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v0" />
            <path d="M14 10V4a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v2" />
            <path d="M10 10.5V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v8" />
            <path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15" />
          </svg>

          {/* Touch Point Flash at moment of impact */}
          {(tap1Bounce > 0.08 || tap2Bounce > 0.08) && (
            <div className="absolute inset-0 rounded-full bg-amber-300/40 animate-ping pointer-events-none" />
          )}
        </div>
      </div>

      {/* 🏷️ 2. SLEEK GLASSMORPHIC CTA PILL (Studio Quality) */}
      <div className="relative mt-2 overflow-hidden rounded-full p-[1.5px] bg-gradient-to-r from-amber-400/70 via-yellow-300/40 to-amber-500/70 shadow-[0_12px_36px_rgba(0,0,0,0.85),0_0_24px_rgba(245,158,11,0.25)]">
        {/* Card Body */}
        <div className="relative px-7 py-3 rounded-full bg-gradient-to-r from-neutral-950/95 via-zinc-900/95 to-neutral-950/95 backdrop-blur-xl flex items-center gap-3.5 max-w-lg">
          {/* Left Mini Badge: 2X TAP */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-gradient-to-r from-amber-400 to-yellow-500 shadow-md">
            {/* Mini SVG Paw icon inside badge */}
            <svg width="12" height="12" viewBox="0 0 24 24" fill="#000000">
              <path d="M12 10.5c-2.5 0-4.5 1.8-4.5 4s2 4 4.5 4 4.5-1.8 4.5-4-2-4-4.5-4zM6.5 10c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm11 0c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm-7.5-3c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm4 0c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2z" />
            </svg>
            <span
              style={{ fontFamily: TheBoldFont }}
              className="text-black text-xs font-black tracking-wider uppercase"
            >
              2X TAP
            </span>
          </div>

          {/* Main Action Text */}
          <span
            style={{
              fontFamily: TheBoldFont,
              letterSpacing: "0.04em",
            }}
            className="text-transparent bg-clip-text bg-gradient-to-r from-white via-amber-100 to-amber-300 text-lg font-black uppercase tracking-wide text-center drop-shadow-sm"
          >
            {cleanedText}
          </span>

          {/* Right SVG Sparkle */}
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            className="text-amber-300 drop-shadow-[0_0_6px_rgba(251,191,36,0.8)]"
          >
            <path
              d="M12 0L14.5 9.5L24 12L14.5 14.5L12 24L9.5 14.5L0 12L9.5 9.5L12 0Z"
              fill="currentColor"
            />
          </svg>

          {/* Dynamic Light Sheen Sweep (Translates diagonally across pill) */}
          <div
            style={{
              transform: `translateX(${sheenProgress}%) skewX(-25deg)`,
            }}
            className="absolute inset-y-0 w-24 bg-gradient-to-r from-transparent via-white/20 to-transparent pointer-events-none"
          />
        </div>
      </div>
    </div>
  );
};