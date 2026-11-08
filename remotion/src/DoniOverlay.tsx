import { Caption, createTikTokStyleCaptions } from "@remotion/captions";
import React, { useEffect, useMemo, useState } from "react";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
  useDelayRender,
  useVideoConfig,
} from "remotion";
import { z } from "zod";
import { loadFont, TheBoldFont } from "./load-font";
import { HookTitle } from "./components/HookTitle";
import SubtitlePage from "./CaptionedVideo/SubtitlePage";
import { OutroCTA } from "./components/OutroCTA";
import { StoryCoverCard } from "./components/StoryCoverCard";
import { ShortsSafeAreaGuide } from "./components/ShortsSafeAreaGuide";
import { DoubleTapPawPrompt } from "./components/DoubleTapPawPrompt";
import { YOUTUBE_SHORTS_SAFE_AREA } from "./constants/safeArea";

const SWITCH_CAPTIONS_EVERY_MS = 0; // 0ms = Strict Single-Word-by-Word Captioning (Alex Hormozi / MrBeast Style)

export const doniOverlaySchema = z.object({
  hookTitle: z.string().default("KENAPA KUCING SUKA DUDUK GINI?"),
  hookSubtitle: z.string().default("Duduk Sila Kayak Bapak-Bapak!"),
  badgeText: z.string().default("🐱 FAKTA ANABUL VIRAL"),
  captionsFile: z.string().default("doni-cat_belly_trap_scratch-captions.json"),
  durationInSeconds: z.number().default(15.0),
  showOutroCTA: z.boolean().default(true),
  showDoubleTapPrompt: z.boolean().optional().default(true),
  doubleTapPromptText: z.string().optional().default("PENCET LAYAR 2X LIAT ANIMASINYA! 🐾"),
  doubleTapStartFrame: z.number().optional().default(95),
  storyCardText: z.string().optional(),
  storyCardDuration: z.number().optional(),
  subtitleBottom: z.number().optional().default(YOUTUBE_SHORTS_SAFE_AREA.subtitleSafeBottom),
  showSafeAreaGuide: z.boolean().optional().default(false),
  layoutMode: z.enum(["youtube_shorts", "tiktok", "instagram_reels", "standard"]).optional().default("youtube_shorts"),
});

export type DoniOverlayProps = z.infer<typeof doniOverlaySchema>;

export const calculateDoniOverlayMetadata: CalculateMetadataFunction<
  DoniOverlayProps
> = async ({ props }) => {
  const fps = 30;
  const dur = props.durationInSeconds ?? 15.0;
  return {
    fps,
    durationInFrames: Math.round(dur * fps),
  };
};

export const DoniOverlay: React.FC<DoniOverlayProps> = ({
  hookTitle,
  hookSubtitle,
  badgeText,
  captionsFile,
  durationInSeconds,
  showOutroCTA,
  showDoubleTapPrompt = true,
  doubleTapPromptText = "PENCET LAYAR 2X LIAT ANIMASINYA! 🐾",
  doubleTapStartFrame = 95,
  storyCardText,
  storyCardDuration,
  subtitleBottom = YOUTUBE_SHORTS_SAFE_AREA.subtitleSafeBottom,
  showSafeAreaGuide = false,
}) => {
  const { delayRender, continueRender } = useDelayRender();
  const [handle] = useState(() => delayRender());
  const [captions, setCaptions] = useState<Caption[]>([]);
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();

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

  const { pages } = useMemo(() => {
    return createTikTokStyleCaptions({
      combineTokensWithinMilliseconds: SWITCH_CAPTIONS_EVERY_MS,
      captions: captions ?? [],
    });
  }, [captions]);

  // Subtle watermark animation (delayed slightly to not clash with Hook entrance)
  const watermarkOpacity = interpolate(frame, [25, 45], [0, 0.85], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const totalFrames = Math.round(durationInSeconds * fps);
  const outroStartFrame = Math.max(0, totalFrames - 4.5 * fps);

  return (
    <AbsoluteFill className="overflow-hidden select-none" style={{ backgroundColor: "transparent" }}>
      {/* 🛑 0. OPTIONAL SAFE AREA GUIDE OVERLAY (FOR QA / TESTING) */}
      {showSafeAreaGuide && <ShortsSafeAreaGuide />}

      {/* 🐾 1. WATERMARK (POSITIONED SAFELY IN TOP-LEFT SAFE MARGIN) */}
      <div
        style={{
          fontFamily: TheBoldFont,
          opacity: watermarkOpacity,
          top: YOUTUBE_SHORTS_SAFE_AREA.watermarkTop - 60, // Y = 180px, well below notch, clear of right action buttons
          left: YOUTUBE_SHORTS_SAFE_AREA.watermarkLeft,
        }}
        className="absolute bg-black/60 backdrop-blur-sm border border-white/20 px-4 py-1.5 rounded-full text-white text-lg tracking-wider flex items-center gap-2 pointer-events-none z-40"
      >
        <span>🐾</span>
        <span>@DoniesDaily</span>
      </div>

      {/* 🎣 2. ANIMATED HOOK TITLE (RESTRICTED WITHIN YOUTUBE SHORTS SAFE AREA) */}
      <HookTitle
        title={hookTitle}
        subtitle={hookSubtitle}
        badgeText={badgeText}
        top={YOUTUBE_SHORTS_SAFE_AREA.hookTitleTop}
      />

      {/* 👆 2.2 INTERACTIVE DOUBLE-TAP CURIOSITY TRIGGER (LIKE VELOCITY ACCELERATOR) */}
      {showDoubleTapPrompt && (
        <DoubleTapPawPrompt
          fromFrame={doubleTapStartFrame}
          durationInFrames={105}
          promptText={doubleTapPromptText}
        />
      )}

      {/* 📖 2.5 STORY COVER CARD (COVERS ORIGINAL TIKTOK ENGLISH BOX) */}
      {storyCardText && (
        <StoryCoverCard
          text={storyCardText}
          durationInSeconds={storyCardDuration ?? 42.0}
        />
      )}

      {/* 💬 3. SYNCHRONIZED TIKTOK/CAPCUT CAPTIONS (POSITIONED ABOVE SHORTS UI) */}
      {pages.map((page, index) => {
        const nextPage = pages[index + 1] ?? null;
        const subtitleStartFrame = (page.startMs / 1000) * fps;
        const maxDurationFrames = 2.5 * fps;
        const subtitleEndFrame = nextPage
          ? Math.min(
              (nextPage.startMs / 1000) * fps,
              subtitleStartFrame + maxDurationFrames
            )
          : subtitleStartFrame + maxDurationFrames;
        const durFrames = Math.max(1, subtitleEndFrame - subtitleStartFrame);

        // Don't overlap with outro
        if (subtitleStartFrame >= outroStartFrame) return null;

        return (
          <Sequence
            key={index}
            from={subtitleStartFrame}
            durationInFrames={durFrames}
          >
            <SubtitlePage
              page={page}
              bottom={subtitleBottom}
            />
          </Sequence>
        );
      })}

      {/* 📣 4. OUTRO CTA CARD */}
      {showOutroCTA && (
        <Sequence from={outroStartFrame} durationInFrames={Math.round(4.5 * fps)}>
          <OutroCTA
            headline="SUBSCRIBE @DoniesDaily"
            subheadline="Follow Buat Fakta Anabul Tiap Hari! 🐾"
            buttonText="KLIK TOMBOL SUBSCRIBE"
          />
        </Sequence>
      )}
    </AbsoluteFill>
  );
};
