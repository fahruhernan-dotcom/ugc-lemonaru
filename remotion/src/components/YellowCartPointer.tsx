import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TheBoldFont } from "../load-font";

interface YellowCartPointerProps {
  readonly text?: string;
  readonly delayFrames?: number;
}

export const YellowCartPointer: React.FC<YellowCartPointerProps> = ({
  text = "KLIK KERANJANG KUNING DI SINI",
  delayFrames = 60,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (frame < delayFrames) {
    return null;
  }

  const relativeFrame = frame - delayFrames;

  // Spring entrance
  const enterSpring = spring({
    frame: relativeFrame,
    fps,
    config: {
      damping: 12,
      mass: 0.8,
      stiffness: 150,
    },
  });

  // Bouncing cycle for the arrow & pill (every ~20 frames / 0.67s)
  const bounceY = Math.sin((relativeFrame * Math.PI) / 12) * 8;
  const bounceX = Math.cos((relativeFrame * Math.PI) / 12) * 5;

  // Pulsing ring scale
  const ringScale = 1 + (relativeFrame % 30) / 30;
  const ringOpacity = 1 - (relativeFrame % 30) / 30;

  return (
    <div
      style={{
        transform: `scale(${enterSpring})`,
        opacity: enterSpring,
      }}
      className="absolute bottom-64 left-8 z-50 flex flex-col items-start gap-2 pointer-events-none select-none"
    >
      {/* Yellow Attention Pill */}
      <div
        style={{
          transform: `translateY(${bounceY}px)`,
          fontFamily: TheBoldFont,
        }}
        className="flex items-center gap-2 bg-gradient-to-r from-amber-300 to-yellow-400 text-black px-4 py-2.5 rounded-2xl font-black text-xl tracking-wider shadow-2xl border-2 border-amber-500/80"
      >
        {/* Shopping bag SVG */}
        <svg
          className="w-6 h-6 text-black"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M16 6V5a4 4 0 0 0-8 0v1H4v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6h-4zm-6-1a2 2 0 0 1 4 0v1h-4V5zm8 15H6V8h2v2h2V8h4v2h2V8h2v12z" />
        </svg>
        <span>{text}</span>
      </div>

      {/* Pulsing down-left arrow indicator */}
      <div
        style={{
          transform: `translate(${bounceX}px, ${bounceY}px)`,
        }}
        className="relative flex items-center justify-center ml-6 mt-1"
      >
        {/* Pulse Ring */}
        <div
          style={{
            transform: `scale(${ringScale})`,
            opacity: ringOpacity,
          }}
          className="absolute w-12 h-12 rounded-full border-4 border-yellow-400"
        />

        {/* Solid Arrow Circle */}
        <div className="w-12 h-12 bg-yellow-400 rounded-full flex items-center justify-center shadow-lg border-2 border-black">
          <svg
            className="w-7 h-7 text-black transform rotate-45"
            fill="none"
            stroke="currentColor"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            viewBox="0 0 24 24"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <polyline points="19 12 12 19 5 12" />
          </svg>
        </div>
      </div>
    </div>
  );
};
