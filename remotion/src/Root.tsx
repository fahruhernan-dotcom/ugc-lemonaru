import "./index.css";
import { Composition, staticFile } from "remotion";
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

export const RemotionRoot: React.FC = () => {
  return (
    <>
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
