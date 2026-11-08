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
 * Interactive Double-Tap Curiosity Trigger Component for YouTube Shorts
 * Prompts viewers to double-tap their screen (triggering YouTube's native Like + custom animation).
 * Positioned strictly within the YouTube Shorts Safe Area (Center Sweet Spot).
 */
export const DoubleTapPawPrompt: React.FC<DoubleTapPawPromptProps> = ({
  fromFrame = 95,
  durationInFrames = 105,
  promptText = "PENCET LAYAR 2X LIAT ANIMASINYA! 🐾",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Active window check
  if (frame < fromFrame || frame >= fromFrame + durationInFrames) {
    return null;
  }

  const relFrame = frame - fromFrame;

  // Entrance spring animation
  const enterSpring = spring({
    frame: relFrame,
    fps,
    config: {
      damping: 12,
      mass: 0.6,
      stiffness: 150,
    },
  });

  // Exit transition (last 15 frames)
  const exitProgress = interpolate(
    relFrame,
    [durationInFrames - 15, durationInFrames],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  const opacity = enterSpring * (1 - exitProgress);
  const scale = enterSpring * (1 - exitProgress * 0.2);

  // Simulated double-tap rhythm (Tap 1 at frame 15, Tap 2 at frame 28)
  const tap1Progress = spring({
    frame: Math.max(0, relFrame - 12),
    fps,
    config: { damping: 10, stiffness: 200 },
  });
  const tap2Progress = spring({
    frame: Math.max(0, relFrame - 25),
    fps,
    config: { damping: 10, stiffness: 200 },
  });

  const tapScale =
    1 - (tap1Progress > 0 && tap1Progress < 1 ? Math.sin(tap1Progress * Math.PI) * 0.25 : 0) -
    (tap2Progress > 0 && tap2Progress < 1 ? Math.sin(tap2Progress * Math.PI) * 0.25 : 0);

  // Paw icon explosive pop after 2nd tap (from frame 28 onwards)
  const pawPop = spring({
    frame: Math.max(0, relFrame - 27),
    fps,
    config: { damping: 10, stiffness: 180 },
  });

  // Ripple effect waves
  const ripple1 = interpolate(Math.max(0, relFrame - 14), [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });
  const ripple2 = interpolate(Math.max(0, relFrame - 27), [0, 22], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Subtle floating wobble
  const wobble = Math.sin(relFrame / 6) * 1.5;

  return (
    <div
      style={{
        transform: `translate(-50%, -50%) scale(${scale}) translateY(${wobble}px)`,
        opacity,
      }}
      className="absolute left-1/2 top-[52%] z-40 pointer-events-none flex flex-col items-center justify-center select-none"
    >
      {/* 🐾 Tap Indicator + Paw Bloom Container */}
      <div className="relative w-36 h-36 flex items-center justify-center mb-3">
        {/* Ripple Wave 1 */}
        {ripple1 > 0 && ripple1 < 1 && (
          <div
            style={{
              transform: `scale(${1 + ripple1 * 1.8})`,
              opacity: (1 - ripple1) * 0.7,
            }}
            className="absolute inset-0 rounded-full border-4 border-amber-300 pointer-events-none"
          />
        )}

        {/* Ripple Wave 2 (Burst) */}
        {ripple2 > 0 && ripple2 < 1 && (
          <div
            style={{
              transform: `scale(${1 + ripple2 * 2.2})`,
              opacity: (1 - ripple2) * 0.9,
            }}
            className="absolute inset-0 rounded-full border-4 border-yellow-400 bg-amber-400/20 pointer-events-none"
          />
        )}

        {/* The Magic Paw Icon (Explodes on 2nd tap) */}
        {pawPop > 0 && (
          <div
            style={{
              transform: `scale(${pawPop * 1.15})`,
              opacity: Math.min(1, pawPop * 1.5),
            }}
            className="absolute z-20 flex items-center justify-center drop-shadow-[0_0_25px_rgba(251,191,36,0.95)]"
          >
            <span className="text-7xl animate-bounce">🐾</span>
          </div>
        )}

        {/* Interactive Hand Finger Icon */}
        <div
          style={{
            transform: `scale(${tapScale})`,
          }}
          className="relative z-10 w-20 h-20 rounded-full bg-black/75 backdrop-blur-md border-3 border-amber-400 flex items-center justify-center shadow-2xl"
        >
          <span className="text-4xl">👆</span>
        </div>
      </div>

      {/* 🏷️ Sleek Catchy Prompt Pill */}
      <div className="bg-black/90 backdrop-blur-md border-2 border-amber-400 px-6 py-2.5 rounded-full shadow-2xl flex items-center gap-2.5 max-w-md">
        <span className="text-xl">✨</span>
        <span
          style={{ fontFamily: TheBoldFont }}
          className="text-amber-300 text-xl font-black uppercase tracking-wider text-center"
        >
          {promptText}
        </span>
        <span className="text-xl">✨</span>
      </div>
    </div>
  );
};
