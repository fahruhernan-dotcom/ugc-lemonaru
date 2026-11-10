import { makeTransform, scale, translateY } from "@remotion/animation-utils";
import { TikTokPage } from "@remotion/captions";
import { fitText } from "@remotion/layout-utils";
import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TheBoldFont } from "../load-font";
import { YOUTUBE_SHORTS_SAFE_AREA } from "../constants/safeArea";

const fontFamily = TheBoldFont;

const container: React.CSSProperties = {
  justifyContent: "center",
  alignItems: "center",
  top: undefined,
  bottom: YOUTUBE_SHORTS_SAFE_AREA.subtitleSafeBottom,
  height: 180,
  paddingLeft: 0,
  paddingRight: 0,
  width: "100%",
};

const DESIRED_FONT_SIZE = 110;
const HIGHLIGHT_COLOR = "#FFE600";

export const Page: React.FC<{
  readonly enterProgress: number;
  readonly page: TikTokPage;
  readonly bottom?: number;
}> = ({ enterProgress, page, bottom = YOUTUBE_SHORTS_SAFE_AREA.subtitleSafeBottom }) => {
  const frame = useCurrentFrame();
  const { width, fps } = useVideoConfig();
  const timeInMs = (frame / fps) * 1000;

  // Enforce YouTube Shorts horizontal safe limit (max 660px with stroke buffer) to guarantee zero UI collision
  const strokeBuffer = 24; // Accounts for WebkitTextStroke: 20px
  const maxSafeWidth = Math.max(200, Math.min(width * 0.62, YOUTUBE_SHORTS_SAFE_AREA.subtitleMaxWidth) - strokeBuffer);

  const fittedText = fitText({
    fontFamily,
    text: page.text.replace(/,/g, ""),
    withinWidth: maxSafeWidth,
    textTransform: "uppercase",
  });

  const fontSize = Math.min(DESIRED_FONT_SIZE, fittedText.fontSize);

  return (
    <AbsoluteFill style={{ ...container, bottom }}>
      <div
        style={{
          fontSize,
          color: "white",
          WebkitTextStroke: "20px black",
          paintOrder: "stroke",
          transform: makeTransform([
            scale(interpolate(enterProgress, [0, 1], [0.8, 1])),
            translateY(interpolate(enterProgress, [0, 1], [50, 0])),
          ]),
          fontFamily,
          textTransform: "uppercase",
        }}
      >
        <span
          style={{
            transform: makeTransform([
              scale(interpolate(enterProgress, [0, 1], [0.8, 1])),
              translateY(interpolate(enterProgress, [0, 1], [50, 0])),
            ]),
          }}
        >
          {page.tokens.map((t, index) => {
            const startRelativeToSequence = t.fromMs - page.startMs;
            const endRelativeToSequence = t.toMs - page.startMs;

            const active =
              startRelativeToSequence <= timeInMs &&
              endRelativeToSequence > timeInMs;

            return (
              <span
                key={`${t.fromMs}-${index}`}
                style={{
                  display: "inline",
                  whiteSpace: "pre",
                  color: active ? HIGHLIGHT_COLOR : "white",
                }}
              >
                {t.text.replace(/,/g, "")}
              </span>
            );
          })}
        </span>
      </div>
    </AbsoluteFill>
  );
};
