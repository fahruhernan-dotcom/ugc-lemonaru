import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TheBoldFont } from "../load-font";

interface HookTitleProps {
  readonly title: string;
  readonly subtitle?: string;
  readonly badgeText?: string;
}

export const HookTitle: React.FC<HookTitleProps> = ({
  title,
  subtitle,
  badgeText = "🔥 RACUN TIKTOK OOTD",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entrance spring animation (0 - 15 frames)
  const enterSpring = spring({
    frame,
    fps,
    config: {
      damping: 12,
      mass: 0.8,
      stiffness: 140,
    },
  });

  // Exit fade & slide up (around 80 - 100 frames / 2.7s - 3.3s)
  const exitProgress = interpolate(frame, [75, 95], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const scale = enterSpring * (1 - exitProgress * 0.3);
  const opacity = interpolate(exitProgress, [0, 1], [1, 0]);
  const translateY = interpolate(exitProgress, [0, 1], [0, -60]);

  // Subtle floating wobble
  const wobble = Math.sin(frame / 8) * 1.5;

  return (
    <div
      style={{
        transform: `translateY(${translateY}px) scale(${scale}) rotate(${wobble - 1}deg)`,
        opacity,
      }}
      className="absolute top-28 left-6 right-6 flex flex-col items-center z-50 pointer-events-none"
    >
      {/* Top Pill Tag */}
      {badgeText && (
        <div
          style={{ fontFamily: TheBoldFont }}
          className="bg-amber-400 text-black px-5 py-1.5 rounded-full text-2xl font-black tracking-wider uppercase shadow-xl mb-3 border-2 border-black"
        >
          {badgeText}
        </div>
      )}

      {/* Main Punchy Hook Banner */}
      <div className="bg-black/85 backdrop-blur-md border-4 border-amber-300 rounded-3xl p-6 shadow-2xl max-w-2xl text-center">
        <h1
          style={{
            fontFamily: TheBoldFont,
            textShadow: "0 4px 14px rgba(0,0,0,0.8)",
          }}
          className="text-white text-5xl leading-tight tracking-wide uppercase"
        >
          {title}
        </h1>

        {subtitle && (
          <p className="mt-3 text-amber-300 text-2xl font-semibold tracking-normal">
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
};
