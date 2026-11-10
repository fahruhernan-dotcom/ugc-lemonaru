/**
 * YouTube Shorts & Vertical Video Safe Area Constants
 * Canvas: 1080 x 1920 (9:16 Vertical Ratio)
 * 
 * YouTube Shorts Native UI Layout:
 * - Top Danger Zone: 0px - 220px (Status bar, Search, Camera button, 3-dots menu)
 * - Bottom Danger Zone: 1440px - 1920px (480px from bottom: Channel avatar, @DoniesDaily, Red SUBSCRIBE button, Sound title, Progress scrubber)
 * - Right Danger Zone: 920px - 1080px (160px from right: Like, Dislike, Comments, Share, Remix rotating disc)
 * - Left Edge: 0px - 60px (Standard margin)
 */

export const YOUTUBE_SHORTS_SAFE_AREA = {
  // Canvas dimensions
  canvasWidth: 1080,
  canvasHeight: 1920,

  // Danger margins (Avoid placing critical text / motion graphics here)
  dangerTop: 240,
  dangerBottom: 480,
  dangerRight: 160,
  dangerLeft: 60,

  // Safe bounding box for critical graphics & text
  safeMinX: 60,
  safeMaxX: 920, // 1080 - 160
  safeMinY: 240,
  safeMaxY: 1440, // 1920 - 480

  // Optimal placement for Remotion components
  hookTitleTop: 240, // Drops HookTitle below camera/search header
  subtitleSafeBottom: 500, // Hovers subtitle right above YouTube channel avatar & Subscribe button
  subtitleMaxWidth: 660, // Strict dead-center max width (210px / 19.4% clear margin on both left & right, guaranteed clear of 18% YouTube UI buttons)
  watermarkTop: 240, // Aligns channel watermark safely inside top-left zone
  watermarkLeft: 64,
} as const;
