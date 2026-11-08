import React, { useEffect, useState } from "react";
import {
  AbsoluteFill,
  Img,
  staticFile,
  useDelayRender,
} from "remotion";
import { z } from "zod";
import { loadFont, TheBoldFont } from "./load-font";

export const doniThumbnailSchema = z.object({
  title: z.string().default("KENAPA KUCING TIBA-TIBA GIGIT?"),
  subtitle: z.string().default("BUKAN KARENA MARAH LHO!"),
  badgeText: z.string().default("🐱 FAKTA ANABUL VIRAL"),
  bgImage: z.string().default(""),
});

export type DoniThumbnailProps = z.infer<typeof doniThumbnailSchema>;

export const DoniThumbnail: React.FC<DoniThumbnailProps> = ({
  title,
  subtitle,
  badgeText = "🐱 FAKTA ANABUL VIRAL",
  bgImage = "",
}) => {
  const { delayRender, continueRender } = useDelayRender();
  const [handle] = useState(() => delayRender());

  useEffect(() => {
    loadFont()
      .then(() => continueRender(handle))
      .catch(() => continueRender(handle));
  }, [continueRender, handle]);

  return (
    <AbsoluteFill className="bg-slate-950 flex flex-col justify-between items-center overflow-hidden">
      {/* Background Layer: Image or Gradient */}
      {bgImage ? (
        <AbsoluteFill className="overflow-hidden">
          <Img
            src={bgImage.startsWith("http") || bgImage.startsWith("data:") ? bgImage : staticFile(bgImage)}
            className="w-full h-full object-cover scale-105"
            style={{ filter: "brightness(0.72) contrast(1.15)" }}
          />
          {/* Vignette & Contrast Overlay */}
          <AbsoluteFill
            style={{
              background:
                "radial-gradient(circle at center, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.75) 100%), linear-gradient(180deg, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.2) 45%, rgba(0,0,0,0.92) 100%)",
            }}
          />
        </AbsoluteFill>
      ) : (
        <AbsoluteFill
          style={{
            background:
              "radial-gradient(circle at 50% 30%, #1e293b 0%, #0f172a 60%, #020617 100%)",
          }}
        />
      )}

      {/* Top Header & Branding Bar */}
      <div className="w-full pt-16 px-8 flex justify-between items-center z-20">
        {/* Category Pill Badge */}
        <div
          style={{ fontFamily: TheBoldFont }}
          className="bg-amber-400 text-black px-6 py-2.5 rounded-full text-2xl font-black tracking-wider uppercase shadow-2xl border-3 border-black flex items-center gap-2"
        >
          <span>{badgeText}</span>
        </div>

        {/* Channel Watermark */}
        <div
          style={{ fontFamily: TheBoldFont }}
          className="bg-black/80 backdrop-blur-md text-amber-300 px-5 py-2 rounded-full text-xl font-bold border border-amber-400/40 shadow-xl"
        >
          🐾 @DoniesDaily
        </div>
      </div>

      {/* Central Punchy Title Box (Designed for Maximum Mobile Shorts CTR) */}
      <div className="w-full px-8 z-20 my-auto flex flex-col items-center">
        <div
          style={{
            background: "rgba(10, 15, 30, 0.88)",
            backdropFilter: "blur(20px)",
            borderColor: "#FFE600",
            boxShadow: "0 0 50px rgba(255, 230, 0, 0.35), 0 25px 50px -12px rgba(0, 0, 0, 0.85)",
          }}
          className="border-5 rounded-3xl p-8 max-w-3xl text-center w-full"
        >
          {/* Main Huge Hook Title */}
          <h1
            style={{
              fontFamily: TheBoldFont,
              color: "#FFFFFF",
              textShadow:
                "-4px -4px 0 #000, 4px -4px 0 #000, -4px 4px 0 #000, 4px 4px 0 #000, 0 8px 24px rgba(0,0,0,0.9)",
              lineHeight: 1.15,
            }}
            className="text-6xl md:text-7xl font-black tracking-wide uppercase mb-4"
          >
            {title}
          </h1>

          {/* Subtitle / Punchline */}
          {subtitle && (
            <div
              style={{
                fontFamily: TheBoldFont,
                color: "#FFE600",
                textShadow:
                  "-2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 0 4px 12px rgba(0,0,0,0.8)",
              }}
              className="text-3xl font-black tracking-wider uppercase"
            >
              ⚡ {subtitle} ⚡
            </div>
          )}
        </div>
      </div>

      {/* Bottom CTA / Shock Banner */}
      <div className="w-full pb-20 px-8 z-20 flex justify-center">
        <div
          style={{ fontFamily: TheBoldFont }}
          className="bg-red-600 text-white px-8 py-3 rounded-2xl text-2xl font-black tracking-widest uppercase border-3 border-white shadow-2xl animate-pulse"
        >
          🚨 TONTON SAMPAI HABIS! 🚨
        </div>
      </div>
    </AbsoluteFill>
  );
};
