import { Caption, createTikTokStyleCaptions } from "@remotion/captions";
import React, { useEffect, useMemo, useState } from "react";
import {
  AbsoluteFill,
  Audio,
  CalculateMetadataFunction,
  interpolate,
  Loop,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useDelayRender,
  useVideoConfig,
} from "remotion";
import { z } from "zod";
import { loadFont, TheBoldFont } from "../load-font";
import { HookTitle } from "../components/HookTitle";
import SubtitlePage from "../CaptionedVideo/SubtitlePage";
import { YOUTUBE_SHORTS_SAFE_AREA } from "../constants/safeArea";

const SWITCH_CAPTIONS_EVERY_MS = 1200;

export const doniShortSchema = z.object({
  hookTitle: z.string().default("KENAPA KUCING SUKA NGADON ROTI? 🐾"),
  hookSubtitle: z.string().default("Bukan cuma manja biasa lho! 🐱✨"),
  badgeText: z.string().default("🐱 FAKTA ANABUL VIRAL"),
  captionsFile: z.string().default("doni-flow-captions.json"),
  audioFile: z.string().default("flow_synced_master.mp3"),
  videoFile: z.string().default("flow_bg_concat.mp4"),
  durationInSeconds: z.number().optional().default(47.0),
  videoDurationInSeconds: z.number().optional().default(35.0),
});

export type DoniShortProps = z.infer<typeof doniShortSchema>;

export const calculateDoniShortMetadata: CalculateMetadataFunction<
  DoniShortProps
> = async ({ props }) => {
  const fps = 30;
  const dur = props.durationInSeconds ?? 47.0;
  return {
    fps,
    durationInFrames: Math.round(dur * fps),
  };
};

export const DoniShort: React.FC<DoniShortProps> = ({
  hookTitle,
  hookSubtitle,
  badgeText,
  captionsFile,
  audioFile,
  videoFile,
  videoDurationInSeconds = 35.0,
}) => {
  const { delayRender, continueRender } = useDelayRender();
  const [handle] = useState(() => delayRender());
  const [captions, setCaptions] = useState<Caption[]>([]);
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();

  const loopDurationFrames = Math.max(1, Math.round(videoDurationInSeconds * fps));

  useEffect(() => {
    Promise.all([
      loadFont(),
      fetch(staticFile(captionsFile))
        .then((res) => res.json())
        .then((data) => setCaptions(data))
        .catch(() => setCaptions([])),
    ])
      .then(() => continueRender(handle))
      .catch(() => continueRender(handle));
  }, [captionsFile, continueRender, handle]);

  // Group tokens into smooth TikTok-style caption pages
  const { pages } = useMemo(() => {
    return createTikTokStyleCaptions({
      combineTokensWithinMilliseconds: SWITCH_CAPTIONS_EVERY_MS,
      captions: captions ?? [],
    });
  }, [captions]);

  // Subtle watermark animation
  const watermarkOpacity = interpolate(frame, [0, 20], [0, 0.85], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill className="bg-black overflow-hidden select-none">
      {/* 🎬 1. CONTINUOUS GOOGLE FLOW AI VIDEO BACKGROUND (WITH SEAMLESS LOOP / WHAT-IF ANTI-DRIFT) */}
      <Loop durationInFrames={loopDurationFrames}>
        <OffthreadVideo
          src={staticFile(videoFile)}
          className="w-full h-full object-cover"
        />
      </Loop>

      {/* 🎵 2. ELEVENLABS KAK CERIA MASTER AUDIO + PLAYFUL BGM */}
      <Audio src={staticFile(audioFile)} />

      {/* 💬 3. SYNCHRONIZED TIKTOK/CAPCUT CAPTIONS */}
      {pages.map((page, index) => {
        const nextPage = pages[index + 1] ?? null;
        const subtitleStartFrame = (page.startMs / 1000) * fps;
        // Keep subtitle visible until next page starts, or max 2.5s
        const maxDurationFrames = 2.5 * fps;
        const subtitleEndFrame = nextPage
          ? Math.min(
              (nextPage.startMs / 1000) * fps,
              subtitleStartFrame + maxDurationFrames
            )
          : subtitleStartFrame + maxDurationFrames;
        const durationInFrames = Math.max(1, subtitleEndFrame - subtitleStartFrame);

        return (
          <Sequence
            key={index}
            from={subtitleStartFrame}
            durationInFrames={durationInFrames}
          >
            <SubtitlePage
              page={page}
              bottom={YOUTUBE_SHORTS_SAFE_AREA.subtitleSafeBottom}
            />
          </Sequence>
        );
      })}

      {/* 🚀 4. DYNAMIC HOOK TITLE OVERLAY (Frames 0 - 95 / ~3.2s) */}
      <HookTitle
        title={hookTitle}
        subtitle={hookSubtitle}
        badgeText={badgeText}
        top={YOUTUBE_SHORTS_SAFE_AREA.hookTitleTop}
      />

      {/* 🐾 5. ELEGANT CHANNEL WATERMARK (POSITIONED SAFELY IN TOP-LEFT SAFE MARGIN) */}
      <div
        style={{
          fontFamily: TheBoldFont,
          opacity: watermarkOpacity,
          top: YOUTUBE_SHORTS_SAFE_AREA.watermarkTop - 60,
          left: YOUTUBE_SHORTS_SAFE_AREA.watermarkLeft,
        }}
        className="absolute bg-black/60 backdrop-blur-sm border border-white/20 px-4 py-1.5 rounded-full text-white text-lg tracking-wider flex items-center gap-2 pointer-events-none z-40"
      >
        <span>🐾</span>
        <span>@DoniesDaily</span>
      </div>
    </AbsoluteFill>
  );
};
