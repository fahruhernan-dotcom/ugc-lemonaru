import "./index.css";
import { Composition, Still, staticFile } from "remotion";
import {
  CaptionedVideo,
  calculateCaptionedVideoMetadata,
  captionedVideoSchema,
} from "./CaptionedVideo";
import {
  VeloraUGC,
  calculateVeloraUGCMetadata,
  veloraUGCSchema,
} from "./VeloraUGC";
import {
  DoniShort,
  calculateDoniShortMetadata,
  doniShortSchema,
} from "./DoniShort";
import {
  DoniOverlay,
  calculateDoniOverlayMetadata,
  doniOverlaySchema,
} from "./DoniOverlay";
import {
  DoniThumbnail,
  doniThumbnailSchema,
} from "./DoniThumbnail";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* 📸 Remotion High-CTR Cover Thumbnail (Alex Hormozi / MrBeast Style) */}
      <Still
        id="DoniThumbnail"
        component={DoniThumbnail}
        schema={doniThumbnailSchema}
        width={1080}
        height={1920}
        defaultProps={{
          title: "KENAPA KUCING TIBA-TIBA GIGIT?",
          subtitle: "BUKAN KARENA MARAH LHO!",
          badgeText: "🐱 FAKTA ANABUL VIRAL",
          bgImage: "",
        }}
      />
      {/* 🐾 Remotion Overlay Component (Zero-video bottleneck) */}
      <Composition
        id="DoniOverlay"
        component={DoniOverlay}
        calculateMetadata={calculateDoniOverlayMetadata}
        schema={doniOverlaySchema}
        width={1080}
        height={1920}
        defaultProps={{
          hookTitle: "KENAPA KUCING SUKA DUDUK GINI?",
          hookSubtitle: "Duduk Sila Kayak Bapak-Bapak!",
          badgeText: "🐱 FAKTA ANABUL VIRAL",
          captionsFile: "doni-cat_belly_trap_scratch-captions.json",
          durationInSeconds: 15.0,
          showOutroCTA: true,
          showDoubleTapPrompt: true,
          doubleTapPromptText: "PENCET LAYAR 2X LIAT ANIMASINYA! 🐾",
          doubleTapStartFrame: 95,
          subtitleBottom: 500,
          showSafeAreaGuide: false,
          layoutMode: "youtube_shorts",
        }}
      />
      {/* 🛡️ Remotion Overlay With Safe Area Guide (Milo Visual QA & Studio Debugging) */}
      <Composition
        id="DoniOverlayWithSafeArea"
        component={DoniOverlay}
        calculateMetadata={calculateDoniOverlayMetadata}
        schema={doniOverlaySchema}
        width={1080}
        height={1920}
        defaultProps={{
          hookTitle: "KENAPA KUCING SUKA DUDUK GINI?",
          hookSubtitle: "Duduk Sila Kayak Bapak-Bapak!",
          badgeText: "🐱 FAKTA ANABUL VIRAL",
          captionsFile: "doni-cat_belly_trap_scratch-captions.json",
          durationInSeconds: 15.0,
          showOutroCTA: true,
          showDoubleTapPrompt: true,
          doubleTapPromptText: "PENCET LAYAR 2X LIAT ANIMASINYA! 🐾",
          doubleTapStartFrame: 95,
          subtitleBottom: 500,
          showSafeAreaGuide: true,
          layoutMode: "youtube_shorts",
        }}
      />
      {/* 🐾 Master Composition: DoniesDaily Cat Shorts */}
      <Composition
        id="DoniShort"
        component={DoniShort}
        calculateMetadata={calculateDoniShortMetadata}
        schema={doniShortSchema}
        width={1080}
        height={1920}
        defaultProps={{
          hookTitle: "KENAPA KUCING SUKA NGADON ROTI? 🐾",
          hookSubtitle: "Bukan cuma manja biasa lho! 🐱✨",
          badgeText: "🐱 FAKTA ANABUL VIRAL",
          captionsFile: "doni-flow-captions.json",
          audioFile: "flow_synced_master.mp3",
          videoFile: "flow_bg_concat.mp4",
          durationInSeconds: 47.0,
          videoDurationInSeconds: 35.0,
        }}
      />
      {/* 🎬 1. Master Composition: Velora Brown Cardigan (Real UGC AI Video) */}
      <Composition
        id="VeloraUGC"
        component={VeloraUGC}
        calculateMetadata={calculateVeloraUGCMetadata}
        schema={veloraUGCSchema}
        width={1080}
        height={1920}
        defaultProps={{
          videoSrc: staticFile("velora-tryon.mp4"),
          hookTitle: "SPILL CARDIGAN RAJUT COKLAT! 😱",
          hookSubtitle: "Jatuh & adem banget pas dipake, aesthetic clean girl ✨",
          badgeText: "🔥 RACUN TIKTOK OOTD",
          productName: "Cardigan Rajut Crop Cokelat Set Inner Ribbon",
          originalPrice: "Rp 189.000",
          discountPrice: "Rp 79.000",
          discountBadge: "DISKON 58%",
          showCartPointer: true,
          cartPointerText: "KLIK KERANJANG KUNING",
          showOutroCTA: true,
          outroHeadline: "CHECKOUT SEKARANG!",
          outroSubheadline: "⚡ PROMO TERBATAS HARI INI",
        }}
      />

      {/* 🎬 2. Master Composition: Velora Peplum Top */}
      <Composition
        id="VeloraPeplumTop"
        component={VeloraUGC}
        calculateMetadata={calculateVeloraUGCMetadata}
        schema={veloraUGCSchema}
        width={1080}
        height={1920}
        defaultProps={{
          videoSrc: staticFile("velora-peplum.mp4"),
          hookTitle: "RACUN PEPLUM TOP VIRAL! 😍",
          hookSubtitle: "Bikin siluet ramping & super manis pas dipake!",
          badgeText: "✨ BEST SELLER TIKTOK",
          productName: "Korean Feminine Peplum Top Casual",
          originalPrice: "Rp 159.000",
          discountPrice: "Rp 69.000",
          discountBadge: "DISKON 56%",
          showCartPointer: true,
          cartPointerText: "KLIK KERANJANG KUNING",
          showOutroCTA: true,
          outroHeadline: "CHECKOUT SEKARANG!",
          outroSubheadline: "⚡ STOK TERBATAS JANGAN SAMPAI HABIS",
        }}
      />

      {/* 💬 Dedicated Captioned Video Template: Cardigan */}
      <Composition
        id="CaptionedVideo"
        component={CaptionedVideo}
        calculateMetadata={calculateCaptionedVideoMetadata}
        schema={captionedVideoSchema}
        width={1080}
        height={1920}
        defaultProps={{
          src: staticFile("velora-tryon.mp4"),
        }}
      />

      {/* 💬 Dedicated Captioned Video Template: Peplum */}
      <Composition
        id="CaptionedPeplum"
        component={CaptionedVideo}
        calculateMetadata={calculateCaptionedVideoMetadata}
        schema={captionedVideoSchema}
        width={1080}
        height={1920}
        defaultProps={{
          src: staticFile("velora-peplum.mp4"),
        }}
      />
    </>
  );
};
