"""Google Flow Prompt Synthesizer for Velora AI.
Translates factual fashion products and ContentBriefs into high-converting
prompts optimized for Google Flow models (Nano Banana 2.1 for image, Omni 1.1 Flash for video).
"""

from typing import Dict, List, Optional, Tuple
from src.models import ContentBrief, Product
from src.motion_planner import ProductMotionPlanner, MotionPhase, VideoChoreographyRegistry


class GoogleFlowPromptEngine:
    """Generates structured, cinematic 9:16 vertical prompts for Google Flow."""

    CHARACTER_ARCHETYPES = {
        "professional": "Chic, poised Indonesian female fashion model, elegant modern styling, confident look, natural warm makeup",
        "casual": "Lively, trendy Indonesian young woman, friendly smile, urban Korean-style street look",
        "luxury": "High-fashion Indonesian model, sleek hairstyle, sharp editorial posture, luxury boutique aesthetics",
    }

    @classmethod
    def synthesize_image_prompt(
        cls,
        product: Product,
        brief: Optional[ContentBrief] = None,
        archetype: str = "professional",
    ) -> str:
        """Constructs an image generation prompt for Nano Banana 2.1."""
        model_persona = cls.CHARACTER_ARCHETYPES.get(archetype, cls.CHARACTER_ARCHETYPES["professional"])
        
        # Factual details from product
        product_desc = f"wearing {product.name}"
        if product.category:
            product_desc += f", {product.category}"

        # Clean prompt structure
        prompt_parts = [
            f"Full-body vertical 9:16 portrait of a {model_persona}",
            product_desc,
            "crisp garment tailoring, authentic fabric texture",
            "minimalist soft luxury studio background with warm ambient light",
            "shot on 85mm portrait lens, photorealistic 8k, ultra-sharp detail, no distortion"
        ]
        return ", ".join(prompt_parts)

    @classmethod
    def synthesize_video_prompt(
        cls,
        product: Product,
        brief: Optional[ContentBrief] = None,
        archetype: str = "professional",
        camera_motion: str = "slow runway walk, camera smoothly tilting up",
    ) -> str:
        """Constructs a video generation prompt for Omni 1.1 Flash / Abra T2V."""
        model_persona = cls.CHARACTER_ARCHETYPES.get(archetype, cls.CHARACTER_ARCHETYPES["professional"])
        
        # Visual cues from brief shot list if available
        visual_cues = ""
        if brief and brief.shot_list:
            first_scene = brief.shot_list[0]
            visual_cues = f", {first_scene.visual_description}"

        prompt_parts = [
            f"Cinematic 9:16 vertical fashion lookbook video",
            f"{model_persona} showcasing {product.name}",
            camera_motion,
            "fluid fabric movement, elegant posture, soft studio lighting",
            "clean commercial fashion aesthetics, ultra-high quality, 24fps motion"
        ]
        if visual_cues:
            prompt_parts.append(visual_cues.strip(", "))

        return ", ".join(prompt_parts)

    @classmethod
    def synthesize_noface_video_prompt(
        cls,
        product: Product,
        brief: Optional[ContentBrief] = None,
        camera_motion: str = "natural outfit demonstration, adjusting neckline and ribbon, showing waist fit",
    ) -> str:
        """Constructs a high-converting No-Face Chin-Down fashion try-on prompt for Google Flow."""
        prompt_parts = [
            "Cinematic 9:16 vertical fashion try-on showcase",
            "framed strictly from chin to waist, no full face visible",
            f"model demonstrating the exact {product.name} from reference image",
            camera_motion,
            "turning slightly 45 degrees to show side silhouette and fabric drape",
            "aesthetic modern bedroom studio background with soft golden sunlight from window",
            "photorealistic, 8k fabric texture detail, 24fps smooth organic motion, no digital artifacts"
        ]
        return ", ".join(prompt_parts)

    @classmethod
    def synthesize_choreographed_tryon_prompt(
        cls,
        product: Product,
        scene: str = "front",
        duration_sec: int = 10,
    ) -> str:
        """Constructs a prompt with explicit 4-phase demonstration choreography:
        1. Establish outfit (0-2s)
        2. Detail feature (2-5s)
        3. Material demonstration (5-8s)
        4. Closing cut & proportions (8-10s)
        """
        timeline = ProductMotionPlanner.generate_timeline(product, duration_sec=duration_sec)
        choreography = ProductMotionPlanner.format_prompt_choreography(timeline)

        anatomy = ProductMotionPlanner.extract_anatomy(product)
        if "peplum" in product.name.lower() or "tessa" in product.name.lower():
            garment_desc = (
                f"exact outfit from reference image: a {anatomy['top_type']} "
                f"with {anatomy['closure']} and {anatomy['material']}, paired with {anatomy['bottom']}"
            )
            base_preamble = (
                f"Authentic unedited vertical try-on video wearing {garment_desc}. "
                f"Static eye-level camera framed strictly from lower neck down to mid-thigh, head naturally cropped out above upper frame edge, no face visible. "
                f"Shot on iPhone 15 Pro back camera, 4K 30fps, soft natural daylight, subtle camera sensor grain. "
            )
        elif "cardigan" in product.name.lower() or "rajut" in product.name.lower():
            garment_desc = (
                f"exact outfit from reference image: a fitted chocolate brown ribbed knit crop camisole "
                f"with delicate front center chest tie ribbon bow, layered with an unbuttoned matching brown cropped knit cardigan "
                f"with long slender sleeves, paired with {anatomy['bottom']}"
            )
            base_preamble = (
                f"Authentic unedited vertical try-on video of Velora wearing {garment_desc}. "
                f"Framed strictly from lower jaw down to waist, faceless aesthetic try-on. "
                f"Shot on iPhone 15 Pro back camera, 4K 30fps, natural indoor room daylight from window, subtle camera sensor grain. "
            )
        else:
            garment_desc = f"exact outfit from reference image ({product.name})"
            base_preamble = (
                f"Authentic unedited vertical try-on video wearing {garment_desc}. "
                f"Framed strictly from lower jaw down to waist. "
                f"Shot on iPhone 15 Pro back camera, 4K 30fps, natural indoor room daylight from window, subtle camera sensor grain. "
            )

        style_postamble = (
            " Real organic cloth drape, fabric wrinkles, natural human pacing, zero cinematic CGI smoothing, realistic candid lifestyle."
        )

        return f"{base_preamble}{choreography}{style_postamble}"

    @classmethod
    def synthesize_foundation_photo_prompt(
        cls,
        product: Product,
        photo_type: str = "close_up",
    ) -> str:
        """Constructs prompts for the Velora SOP 2-Foto Fondasi:
        1. 'close_up' (Foto 1 Dekat / Dagu ke Pinggang): Detail serat kain, kerah, dan kancing/tali.
        2. 'wide_silhouette' (Foto 2 Jauh / Siluet Full-Body): Potongan outfit lengkap dan proporsi tubuh.
        """
        anatomy = ProductMotionPlanner.extract_anatomy(product)
        cat = ProductMotionPlanner.detect_category(product)
        prod_title = product.name or "the stylish outfit"
        if "PKG_" in prod_title or "PROD-" in prod_title:
            prod_title = "the stylish outfit"

        if cat == ProductMotionPlanner.CATEGORY_PEPLUM_TOP:
            garment_macro = f"crisp white sleeveless cotton peplum top with {anatomy['closure']} and {anatomy['material']}"
            garment_full = f"{anatomy['top_type']}, paired with {anatomy['bottom']}"
        elif cat == ProductMotionPlanner.CATEGORY_SET or "cardigan" in prod_title.lower() or "rajut" in prod_title.lower():
            garment_macro = f"fitted chocolate brown ribbed knit crop camisole with {anatomy['closure']}, layered under an unbuttoned matching brown cropped knit cardigan"
            garment_full = f"2-piece layered outfit: unbuttoned cropped brown knit cardigan over fitted crop camisole, paired with {anatomy['bottom']}"
        elif cat == ProductMotionPlanner.CATEGORY_TOP_OUTERWEAR or "blouse" in prod_title.lower() or "kemeja" in prod_title.lower():
            garment_macro = f"{anatomy['top_type']} featuring {anatomy['collar']} and {anatomy['closure']}, crafted from {anatomy['material']}"
            garment_full = f"{anatomy['top_type']} with {anatomy['material']}, paired with {anatomy['bottom']}"
        else:
            garment_macro = f"{anatomy['top_type']} crafted from {anatomy['material']} with {anatomy['closure']}"
            garment_full = f"{anatomy['full_description']}"

        if photo_type == "wide_silhouette":
            return (
                f"Vertical 9:16 full-body fashion lookbook portrait of Velora wearing {garment_full}. "
                "Framed strictly from collarbone down to mid-thigh, head naturally cropped out above upper frame edge, faceless aesthetic try-on. "
                "Model standing naturally with relaxed posture in an aesthetic minimalist bedroom studio, "
                "showcasing outfit drape, waist proportions, and clean silhouette. "
                "Soft authentic daylight streaming from window, shot on iPhone 15 Pro back camera, "
                "natural smartphone sensor texture, realistic fabric weight, zero CGI waxy smoothing, candid lifestyle OOTD."
            )
        else:
            # Default to close_up
            return (
                f"Vertical 9:16 close-up fashion portrait of Velora wearing {garment_macro}. "
                "Framed strictly from lower jaw down to waist, head naturally cropped out above upper frame edge, faceless aesthetic try-on. "
                "Hands delicately touching the garment hem or collar, capturing tactile fabric weave, authentic seam stitching, and delicate closures in high definition. "
                "Soft natural room daylight from nearby window, shot on iPhone 15 Pro back camera, 4K crisp detail, "
                "realistic smartphone sensor grain, natural fabric creases and organic cloth folds, zero artificial CGI smoothing, authentic UGC aesthetic."
            )

    @classmethod
    def synthesize_ugc_realistic_tryon_prompt(
        cls,
        product: Product,
        scene: str = "front",
        garment_detail: Optional[str] = None
    ) -> str:
        """Constructs ultra-realistic UGC-style try-on prompts with strict garment anatomy fidelity
        dynamically adapted across all catalog categories (Peplum, Cardigan, Blouse, Sets).
        """
        prod_title = product.name or "the stylish outfit"
        if "PKG_" in prod_title or "PROD-" in prod_title:
            prod_title = "the stylish outfit"

        anatomy = ProductMotionPlanner.extract_anatomy(product)
        cat = ProductMotionPlanner.detect_category(product)

        # Build consistent dynamic garment description
        if garment_detail:
            garment_desc = garment_detail
        elif cat == ProductMotionPlanner.CATEGORY_PEPLUM_TOP:
            garment_desc = (
                f"the exact outfit from reference image: a {anatomy['top_type']} "
                f"with {anatomy['closure']} and {anatomy['material']}, paired with {anatomy['bottom']}"
            )
        elif cat == ProductMotionPlanner.CATEGORY_SET or "cardigan" in prod_title.lower() or "rajut" in prod_title.lower():
            garment_desc = (
                "the exact 2-piece outfit from reference image: a fitted chocolate brown ribbed knit crop camisole "
                "with delicate front center chest tie ribbon bow, layered with an unbuttoned matching brown cropped knit cardigan "
                f"with long slender sleeves, paired with {anatomy['bottom']}"
            )
        elif cat == ProductMotionPlanner.CATEGORY_TOP_OUTERWEAR or "blouse" in prod_title.lower() or "kemeja" in prod_title.lower():
            garment_desc = (
                f"the exact outfit from reference image: a {anatomy['top_type']} "
                f"featuring {anatomy['collar']} and {anatomy['closure']}, crafted from {anatomy['material']}, paired with {anatomy['bottom']}"
            )
        else:
            garment_desc = f"the exact outfit from reference image: {anatomy['full_description']}"

        # Build category-appropriate physical interaction cues
        if scene == "side_turn":
            if cat == ProductMotionPlanner.CATEGORY_PEPLUM_TOP:
                motion_cue = (
                    "Model gently turning 45 degrees left and right, hands resting lightly on waist, "
                    "showing the flared peplum cut, cinched waist proportion, and natural cotton drape with real gravity."
                )
            elif cat == ProductMotionPlanner.CATEGORY_TOP_OUTERWEAR:
                motion_cue = (
                    "Model gently turning 45 degrees left and right, hands resting naturally at sides, "
                    "showing the tailored sleeve fit, clean side profile, and crisp fabric drape with real gravity."
                )
            else:
                motion_cue = (
                    "Model gently turning 45 degrees left and right, hands resting lightly on waist, "
                    "showing sleeve cut, cropped waist fit, and natural fabric drape with real gravity."
                )

            return (
                f"Authentic vertical try-on video of Velora showcasing the side silhouette of {garment_desc}. "
                "Framed strictly from lower chin down to hips, faceless aesthetic try-on. "
                "Shot on iPhone 15 Pro back camera, 4K 30fps, natural indoor room daylight from window, subtle camera sensor grain. "
                f"{motion_cue} "
                "Authentic natural human speed, realistic casual pacing, organic cloth weave, zero CGI smoothing, realistic candid lifestyle."
            )
        else:
            # Front detail scene
            if cat == ProductMotionPlanner.CATEGORY_PEPLUM_TOP:
                motion_cue = (
                    "Model lightly touching the smocked waist and smoothing the bottom peplum ruffle hem, "
                    "fingers gently showcasing the shoulder tie ribbon straps and breathable fabric drape, "
                    "real fabric wrinkles, organic cotton drape, natural cloth folds reacting to movement."
                )
            elif cat == ProductMotionPlanner.CATEGORY_TOP_OUTERWEAR:
                motion_cue = (
                    "Model gently adjusting the collar and smoothing the front placket with delicate fingers, "
                    "showcasing the tailored fabric weave, crisp seams, and natural cloth drape reacting to movement."
                )
            else:
                motion_cue = (
                    "Model casually smoothing the open cardigan hem and gently adjusting the front chest tie ribbon bow with delicate fingers, "
                    "leaving cardigan unbuttoned to clearly display the inner camisole and ribbon, "
                    "real fabric wrinkles, organic ribbed cotton drape, natural cloth folds reacting to movement."
                )

            return (
                f"Authentic unedited vertical try-on video of Velora wearing {garment_desc}. "
                "Framed strictly from lower jaw down to waist, faceless aesthetic try-on. "
                "Shot on iPhone 15 Pro back camera, 4K 30fps, natural indoor room daylight from window, subtle camera sensor grain. "
                f"{motion_cue} "
                "Authentic natural human speed, realistic casual pacing, zero cinematic CGI smoothing, realistic candid lifestyle."
            )

    @classmethod
    def synthesize_concise_choreographed_prompt(
        cls,
        product: Product,
        reference_chip: str = "@garment_5_isolated_white_bg.jpg"
    ) -> str:
        """Constructs a concise (<150 words / ~800 chars) 4-phase micro-interaction prompt
        optimized for Google Flow Omni 1.1 Flash without attention drift or color bleed.
        """
        name_lower = (product.name or "").lower()
        if "peplum" in name_lower or "tessa" in name_lower:
            return (
                f"Static eye-level camera framed strictly from lower neck and collarbone down to mid-thigh, head naturally cropped out above upper frame edge, no face visible. "
                f"Wearing {reference_chip}: crisp white sleeveless cotton peplum top with shoulder tie ribbon straps, ruched smocked elastic waist, and flared peplum ruffle hem, paired with tailored blue denim high-waist jeans. "
                f"[0-2s: Establish Silhouette] Model stands centered, establishing clean outfit fit and silhouette. "
                f"[2-5s: Shoulder Straps Detail] Right hand gently lifts to touch and adjust the delicate shoulder tie ribbon strap. "
                f"[5-8s: Smocked Waist Demonstration] Hands lightly touch the smocked elastic waist, showcasing comfortable stretch and breathable cotton texture. "
                f"[8-10s: Peplum Flare & Cut] Fingers graze the bottom peplum ruffle hem, exhibiting waist-to-hip proportions before resting naturally. "
                f"Shot on iPhone back camera, soft natural daylight, organic cloth physics, 24fps motion, zero CGI smoothing."
            )
        elif "cardigan" in name_lower or "rajut" in name_lower:
            return (
                f"Static eye-level camera framed strictly from lower neck down to mid-thigh, head naturally cropped out above upper frame edge, no face visible. "
                f"Wearing {reference_chip}: chocolate brown ribbed knit crop camisole with front tie ribbon, unbuttoned matching brown cropped knit cardigan with long sleeves, paired with tailored white high-waist trousers. "
                f"[0-2s: Establish Silhouette] Model stands centered with natural posture, establishing 2-piece layered outfit fit. "
                f"[2-5s: Tie Ribbon Detail] Delicate fingers gently touch and adjust the front chest tie ribbon bow. "
                f"[5-8s: Knit Fabric Demonstration] Palm gently glides across the front bodice fabric, showcasing organic ribbed knit elasticity. "
                f"[8-10s: Cardigan Hem & Cut] Hands lightly smooth open cardigan hem before relaxing naturally. "
                f"Shot on iPhone back camera, soft natural daylight, organic cloth physics, 24fps motion, zero CGI smoothing."
            )
        else:
            return (
                f"Static eye-level camera framed strictly from lower neck down to mid-thigh, head naturally cropped out above upper frame edge, no face visible. "
                f"Wearing {reference_chip}: {product.name}. "
                f"[0-2s: Establish Silhouette] Model stands centered, establishing outfit silhouette. "
                f"[2-5s: Feature Detail] Gentle hand movement highlighting collar and focal construction. "
                f"[5-8s: Fabric Demonstration] Hand glides across bodice, showcasing fabric weave and texture. "
                f"[8-10s: Hemline & Cut] Relaxed posture showcasing clean garment proportions. "
                f"Shot on iPhone back camera, soft natural daylight, 24fps motion, zero CGI smoothing."
            )

    @classmethod
    def synthesize_choreographed_multiscene_prompts(
        cls,
        product: Product,
        style_name: str = "auto",
        duration_per_scene: int = 10,
    ) -> Tuple[str, List[str]]:
        """Synthesizes choreographed multi-scene video prompts using the VideoChoreographyRegistry.
        
        Args:
            product: The fashion product to generate prompts for.
            style_name: One of registered style IDs ('tryon_classic', 'walking_lookbook',
                        'fabric_stretch_test', 'candid_lifestyle', 'layering_styling') or 'auto'.
            duration_per_scene: Target duration per scene in seconds.
            
        Returns:
            Tuple containing:
            - selected_style_id (str): The actual style ID used.
            - scene_prompts (List[str]): List of prompt strings for Scene 1 and Scene 2.
        """
        if not style_name or style_name == "auto":
            chosen_style_id = VideoChoreographyRegistry.select_smart_style(product)
        else:
            chosen_style_id = style_name

        style = VideoChoreographyRegistry.get(chosen_style_id)
        if not style:
            chosen_style_id = "tryon_classic"
            style = VideoChoreographyRegistry.get("tryon_classic")

        anatomy = ProductMotionPlanner.extract_anatomy(product)
        prod_title = product.name or "the stylish outfit"

        scene1 = style.build_scene1(anatomy, prod_title)
        scene2 = style.build_scene2(anatomy, prod_title)

        return chosen_style_id, [scene1, scene2]



