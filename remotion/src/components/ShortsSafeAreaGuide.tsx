import React from "react";
import { AbsoluteFill } from "remotion";
import { YOUTUBE_SHORTS_SAFE_AREA } from "../constants/safeArea";

/**
 * Visual Overlay Guide for YouTube Shorts Native UI Layout
 * Displays danger zones (red semi-transparent) and safe area (neon green outline)
 * Useful for visual QA, Remotion Studio testing, and ensuring 0% occlusion.
 */
export const ShortsSafeAreaGuide: React.FC<{ readonly opacity?: number }> = ({
  opacity = 0.85,
}) => {
  const {
    dangerTop,
    dangerBottom,
    dangerRight,
    dangerLeft,
    safeMinX,
    safeMaxX,
    safeMinY,
    safeMaxY,
  } = YOUTUBE_SHORTS_SAFE_AREA;

  const safeWidth = safeMaxX - safeMinX;
  const safeHeight = safeMaxY - safeMinY;

  return (
    <AbsoluteFill
      style={{ opacity }}
      className="pointer-events-none z-[999] select-none font-sans"
    >
      {/* 🛑 1. TOP DANGER ZONE (Search, Camera, Back Button) */}
      <div
        style={{ height: dangerTop }}
        className="absolute top-0 left-0 right-0 bg-red-600/25 border-b-2 border-dashed border-red-500 flex flex-col justify-end px-8 pb-3"
      >
        <div className="flex justify-between items-center text-red-200 text-lg font-bold">
          <span>⚠️ TOP DANGER ZONE (Search & Camera UI)</span>
          <span>0 — {dangerTop}px</span>
        </div>
      </div>

      {/* 🛑 2. RIGHT DANGER ZONE (Like, Dislike, Comment, Share, Sound Disc) */}
      <div
        style={{
          width: dangerRight,
          top: dangerTop,
          bottom: dangerBottom,
        }}
        className="absolute right-0 bg-red-600/30 border-l-2 border-dashed border-red-500 flex flex-col items-center justify-around py-8 text-red-200 text-xs font-bold"
      >
        <div className="bg-black/60 px-2 py-1 rounded text-center">👍 Like</div>
        <div className="bg-black/60 px-2 py-1 rounded text-center">👎 Dislike</div>
        <div className="bg-black/60 px-2 py-1 rounded text-center">💬 Comments</div>
        <div className="bg-black/60 px-2 py-1 rounded text-center">↗️ Share</div>
        <div className="bg-black/60 px-2 py-1 rounded text-center">💿 Remix</div>
      </div>

      {/* 🛑 3. BOTTOM DANGER ZONE (Channel, Title, Subscribe Button, Audio) */}
      <div
        style={{ height: dangerBottom }}
        className="absolute bottom-0 left-0 right-0 bg-red-600/30 border-t-2 border-dashed border-red-500 flex flex-col justify-start px-8 pt-4 text-red-200"
      >
        <div className="flex justify-between items-center text-lg font-bold mb-3">
          <span>⚠️ BOTTOM DANGER ZONE (Channel, Description & Subscribe)</span>
          <span>{1920 - dangerBottom} — 1920px</span>
        </div>
        <div className="flex items-center gap-3 bg-black/60 p-3 rounded-xl max-w-md border border-white/20">
          <div className="w-10 h-10 rounded-full bg-amber-400" />
          <div className="text-sm">
            <p className="font-bold text-white">@DoniesDaily</p>
            <p className="text-xs text-zinc-300">Video Title & Description...</p>
          </div>
          <div className="ml-auto bg-red-600 text-white font-black text-xs px-3 py-1.5 rounded-full">
            SUBSCRIBE
          </div>
        </div>
      </div>

      {/* 🛑 4. LEFT EDGE MARGIN */}
      <div
        style={{
          width: dangerLeft,
          top: dangerTop,
          bottom: dangerBottom,
        }}
        className="absolute left-0 bg-yellow-500/10 border-r border-yellow-500/30"
      />

      {/* ✅ 5. SAFE ACTION BOUNDING BOX */}
      <div
        style={{
          left: safeMinX,
          top: safeMinY,
          width: safeWidth,
          height: safeHeight,
        }}
        className="absolute border-4 border-emerald-400 rounded-3xl shadow-[0_0_30px_rgba(52,211,153,0.3)] pointer-events-none flex flex-col justify-between p-4"
      >
        <div className="bg-emerald-500/80 text-black text-xs font-black uppercase px-3 py-1 rounded-full self-start">
          ✓ MILO SHORTS SAFE ACTION AREA ({safeWidth}x{safeHeight}px)
        </div>
        <div className="border-t-2 border-dashed border-emerald-400/50 w-full flex justify-between items-center text-emerald-300 text-xs py-1">
          <span>KINETIC SUBTITLE ANCHOR (Y ~ 1420px / Bottom: 500px)</span>
          <span>✓ 100% CLEAR OF OVERLAYS</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
