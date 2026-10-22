import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { TheBoldFont } from "../load-font";

interface ProductBadgeProps {
  readonly productName: string;
  readonly originalPrice?: string;
  readonly discountPrice: string;
  readonly discountBadge?: string;
  readonly delayFrames?: number;
}

export const ProductBadge: React.FC<ProductBadgeProps> = ({
  productName,
  originalPrice,
  discountPrice,
  discountBadge = "DISKON 50%",
  delayFrames = 85, // Enters as the hook title exits
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Trigger entrance after hook title finishes
  const relativeFrame = Math.max(0, frame - delayFrames);

  const enterSpring = spring({
    frame: relativeFrame,
    fps,
    config: {
      damping: 14,
      mass: 0.9,
      stiffness: 120,
    },
  });

  if (frame < delayFrames) {
    return null;
  }

  // Soft breathing pulse
  const pulse = 1 + Math.sin(relativeFrame / 15) * 0.02;

  return (
    <div
      style={{
        transform: `scale(${enterSpring * pulse}) translateX(${interpolate(
          enterSpring,
          [0, 1],
          [-120, 0]
        )}px)`,
        opacity: enterSpring,
      }}
      className="absolute top-28 left-8 max-w-sm z-40 pointer-events-none"
    >
      <div className="bg-black/80 backdrop-blur-md border-2 border-amber-400 rounded-2xl p-4 shadow-2xl flex flex-col gap-1.5">
        {/* Top Badges */}
        <div className="flex items-center gap-2">
          <span
            style={{ fontFamily: TheBoldFont }}
            className="bg-red-600 text-white text-xs px-2.5 py-0.5 rounded-md font-bold uppercase tracking-wider animate-pulse"
          >
            🔥 {discountBadge}
          </span>
          <span className="text-zinc-300 text-xs font-medium">Spill Outfit</span>
        </div>

        {/* Product Title */}
        <div className="text-white text-lg font-bold leading-tight line-clamp-2">
          {productName}
        </div>

        {/* Price Row */}
        <div className="flex items-baseline gap-2 mt-1">
          <span
            style={{ fontFamily: TheBoldFont }}
            className="text-amber-400 text-3xl font-black tracking-tight"
          >
            {discountPrice}
          </span>
          {originalPrice && (
            <span className="text-zinc-400 text-base line-through font-normal">
              {originalPrice}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
