import { TikTokPage } from "@remotion/captions";
import React from "react";
import {
  AbsoluteFill,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Page } from "./Page";
import { YOUTUBE_SHORTS_SAFE_AREA } from "../constants/safeArea";

const SubtitlePage: React.FC<{ readonly page: TikTokPage; readonly bottom?: number }> = ({
  page,
  bottom = YOUTUBE_SHORTS_SAFE_AREA.subtitleSafeBottom,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({
    frame,
    fps,
    config: {
      damping: 200,
    },
    durationInFrames: 5,
  });

  return (
    <AbsoluteFill>
      <Page enterProgress={enter} page={page} bottom={bottom} />
    </AbsoluteFill>
  );
};

export default SubtitlePage;
