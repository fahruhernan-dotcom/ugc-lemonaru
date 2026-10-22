import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TheBoldFont } from "../load-font";

interface OutroCTAProps {
  readonly headline?: string;
  readonly subheadline?: string;
  readonly startFromEndFrames?: number; // e.g. 100 frames from the end
}

export const OutroCTA: React.FC<OutroCTAProps> = ({
  headline = "CHECKOUT SEKARANG!",
  subheadline = "⚡ Diskon Terbatas Hari Ini Saja",
  startFromEndFrames = 100,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();

  const triggerFrame = Math.max(0, durationInFrames - startFromEndFrames);

  if (frame < triggerFrame) {
    return null;
  }

  const relativeFrame = frame - triggerFrame;

  // Spring pop-up
  const enterSpring = spring({
    frame: relativeFrame,
    fps,
    config: {
      damping: 12,
      mass: 0.7,
      stiffness: 160,
    },
  });

  const bgOpacity = interpolate(relativeFrame, [0, 15], [0, 0.45], {
    extrapolateRight: "clamp",
  });

  return (
    <div className="absolute inset-0 z-50 flex flex-col items-center justify-center pointer-events-none">
      {/* Dim Overlay */}
      <div
        style={{ opacity: bgOpacity }}
        className="absolute inset-0 bg-black"
      />

      {/* Card Content */}
      <div
        style={{
          transform: `scale(${enterSpring})`,
          opacity: enterSpring,
        }}
        className="relative z-10 flex flex-col items-center bg-zinc-950/90 border-4 border-amber-400 p-8 rounded-3xl shadow-2xl max-w-lg mx-6 text-center"
      >
        <div
          style={{ fontFamily: TheBoldFont }}
          className="text-red-500 text-2xl tracking-widest uppercase mb-2 animate-pulse"
        >
          {subheadline}
        </div>

        <h2
          style={{
            fontFamily: TheBoldFont,
            textShadow: "0 4px 12px rgba(0,0,0,0.9)",
          }}
          className="text-white text-5xl font-black uppercase leading-tight mb-4"
        >
          {headline}
        </h2>

        {/* Big Yellow Button */}
        <div
          style={{ fontFamily: TheBoldFont }}
          className="w-full bg-gradient-to-r from-amber-400 to-yellow-500 text-black py-4 px-6 rounded-2xl text-2xl font-black tracking-wide shadow-xl flex items-center justify-center gap-3 border-2 border-black"
        >
          <span>KLIK KERANJANG KUNING</span>
          <span className="text-3xl">👇</span>
        </div>
      </div>
    </div>
  );
};
