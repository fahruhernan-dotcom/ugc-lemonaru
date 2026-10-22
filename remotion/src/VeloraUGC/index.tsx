import React, { useEffect, useState } from "react";
import {
  AbsoluteFill,
  Audio,
  CalculateMetadataFunction,
  OffthreadVideo,
  staticFile,
  useDelayRender,
} from "remotion";
import { getVideoMetadata } from "@remotion/media-utils";
import { z } from "zod";
import { loadFont } from "../load-font";
import { HookTitle } from "../components/HookTitle";
import { ProductBadge } from "../components/ProductBadge";
import { YellowCartPointer } from "../components/YellowCartPointer";
import { OutroCTA } from "../components/OutroCTA";

export const veloraUGCSchema = z.object({
  videoSrc: z.string(),
  audioSrc: z.string().optional(),
  hookTitle: z.string().default("SPILL CARDIGAN RAJUT COKLAT! 😱"),
  hookSubtitle: z
    .string()
    .default("Jatuh & adem banget pas dipake, aesthetic clean girl ✨"),
  badgeText: z.string().default("🔥 RACUN TIKTOK OOTD"),
  productName: z
    .string()
    .default("Cardigan Rajut Crop Cokelat Set Inner Ribbon"),
  originalPrice: z.string().default("Rp 189.000"),
  discountPrice: z.string().default("Rp 79.000"),
  discountBadge: z.string().default("DISKON 58%"),
  showCartPointer: z.boolean().default(true),
  cartPointerText: z.string().default("KLIK KERANJANG KUNING"),
  showOutroCTA: z.boolean().default(true),
  outroHeadline: z.string().default("CHECKOUT SEKARANG!"),
  outroSubheadline: z.string().default("⚡ PROMO TERBATAS HARI INI"),
});

export type VeloraUGCProps = z.infer<typeof veloraUGCSchema>;

export const calculateVeloraUGCMetadata: CalculateMetadataFunction<
  VeloraUGCProps
> = async ({ props }) => {
  const fps = 30;
  try {
    const src =
      props.videoSrc.startsWith("http") || props.videoSrc.startsWith("/")
        ? props.videoSrc
        : staticFile(props.videoSrc);
    const metadata = await getVideoMetadata(src);
    return {
      fps,
      durationInFrames: Math.max(
        90,
        Math.floor(metadata.durationInSeconds * fps)
      ),
    };
  } catch {
    return {
      fps,
      durationInFrames: 300, // 10s default fallback
    };
  }
};

export const VeloraUGC: React.FC<VeloraUGCProps> = ({
  videoSrc,
  audioSrc,
  hookTitle,
  hookSubtitle,
  badgeText,
  productName,
  originalPrice,
  discountPrice,
  discountBadge,
  showCartPointer,
  cartPointerText,
  showOutroCTA,
  outroHeadline,
  outroSubheadline,
}) => {
  const { delayRender, continueRender } = useDelayRender();
  const [handle] = useState(() => delayRender());

  useEffect(() => {
    loadFont()
      .then(() => continueRender(handle))
      .catch(() => continueRender(handle));
  }, [continueRender, handle]);

  const resolvedVideoSrc =
    videoSrc.startsWith("http") || videoSrc.startsWith("/")
      ? videoSrc
      : staticFile(videoSrc);

  const resolvedAudioSrc = audioSrc
    ? audioSrc.startsWith("http") || audioSrc.startsWith("/")
      ? audioSrc
      : staticFile(audioSrc)
    : undefined;

  return (
    <AbsoluteFill className="bg-black overflow-hidden select-none">
      {/* Background Video Layer */}
      <AbsoluteFill>
        <OffthreadVideo
          src={resolvedVideoSrc}
          className="w-full h-full object-cover"
        />
      </AbsoluteFill>

      {/* Optional Audio Track */}
      {resolvedAudioSrc && <Audio src={resolvedAudioSrc} />}

      {/* 1. Hook Title Overlay (Frames 0 - 95 / ~3.2 detik pertama) */}
      <HookTitle
        title={hookTitle}
        subtitle={hookSubtitle}
        badgeText={badgeText}
      />

      {/* 2. Product & Discount Badge (Frames 85 - selesai) */}
      <ProductBadge
        productName={productName}
        originalPrice={originalPrice}
        discountPrice={discountPrice}
        discountBadge={discountBadge}
        delayFrames={85}
      />

      {/* 3. Keranjang Kuning Pointer & Pulsing Indicator (Frames 70 - selesai) */}
      {showCartPointer && (
        <YellowCartPointer
          text={cartPointerText}
          delayFrames={70}
        />
      )}

      {/* 4. High-Urgency Outro CTA (Terakhir 90 frames / 3 detik terakhir) */}
      {showOutroCTA && (
        <OutroCTA
          headline={outroHeadline}
          subheadline={outroSubheadline}
          startFromEndFrames={90}
        />
      )}
    </AbsoluteFill>
  );
};
