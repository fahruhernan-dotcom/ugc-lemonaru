import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

export interface StoryCoverCardProps {
  readonly text: string;
  readonly bottom?: number;
  readonly left?: number;
  readonly right?: number;
  readonly minHeight?: number;
  readonly durationInSeconds?: number;
}

export const StoryCoverCard: React.FC<StoryCoverCardProps> = ({
  text,
  bottom = 430,
  left = 40,
  right = 40,
  minHeight = 240,
  durationInSeconds = 42.0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const totalFrames = Math.round(durationInSeconds * fps);

  // Fade in at start
  const opacity = interpolate(
    frame,
    [0, 10, totalFrames - 15, totalFrames],
    [0, 1, 1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  if (frame >= totalFrames) {
    return null;
  }

  return (
    <div
      style={{
        position: "absolute",
        bottom: `${bottom}px`,
        left: `${left}px`,
        right: `${right}px`,
        minHeight: `${minHeight}px`,
        backgroundColor: "#FFFFFF",
        borderRadius: "28px",
        padding: "24px 32px",
        boxShadow: "0 12px 36px rgba(0, 0, 0, 0.35)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        textAlign: "center",
        opacity,
        zIndex: 40,
        pointerEvents: "none",
      }}
    >
      <p
        style={{
          color: "#0f172a",
          fontFamily: "Georgia, serif, 'Times New Roman'",
          fontWeight: "bold",
          fontSize: "36px",
          lineHeight: 1.35,
          margin: 0,
        }}
      >
        {text}
      </p>
    </div>
  );
};
