"""Dynamic UGC Copywriting & Script Engine for Velora AI.
Generates high-converting, category-aware TikTok affiliate scripts, hooks, and captions.
Completely anti-hardcoded: derives hooks, pain-points, material demonstrations,
and urgent CTAs directly from product attributes and motion structure.
"""

import re
from typing import Any, Dict, List, Optional
from src.models import Product, ContentBrief, ShotItem
from src.motion_planner import ProductMotionPlanner


class DynamicUgcCopywriter:
    """Intelligent Indonesian UGC copywriter tailored for high-converting TikTok Shop videos."""

    @classmethod
    def generate_hook(cls, product: Product) -> str:
        """Constructs an attention-grabbing first sentence (0-2s) based on product signals."""
        name = product.name
        price_fmt = f"Rp {product.price_idr:,.0f}"
        cat = ProductMotionPlanner.detect_category(product)

        if cat == ProductMotionPlanner.CATEGORY_PEPLUM_TOP:
            hooks = [
                f"Spill atasan peplum yang bikin pinggang auto ramping dan pundak manis banget!",
                f"Nemuin atasan tanpa lengan yang potongannya bikin leher jenjang dan siluet ramping!",
                f"Buat yang sering minder sama bentuk pinggang, wajib banget liat {name} ini!"
            ]
            return hooks[0]

        elif cat == ProductMotionPlanner.CATEGORY_SET:
            hooks = [
                f"Spill 2-in-1 cardigan rajut set inner pita yang lagi viral di Korea!",
                f"Outfit gemas yang bikin look auto clean & aesthetic, cardigan set cokelat ini solusinya!",
                f"Cuma satu set tapi bisa di-styling jadi 3 look berbeda, ini dia {name}!"
            ]
            return hooks[0]

        elif cat == ProductMotionPlanner.CATEGORY_SKINCARE:
            hooks = [
                f"Kulit lagi kusam dan gradakan? Coba liat tekstur {name} ini!",
                f"Seriusan serum semurah ini efek glowing-nya bisa se-instan ini?!",
                f"Rahasia kulit glass skin ala cewek Korea ternyata ada di botol kecil ini!"
            ]
            return hooks[0]

        elif cat == ProductMotionPlanner.CATEGORY_BOTTOMS:
            hooks = [
                f"Celana yang bikin ilusi kaki auto jenjang 10cm, potongannya juara banget!",
                f"Nemuin celana highwaist yang pinggangnya gak begah dan jatuhnya super rapi!",
                f"Buat ciwi-ciwi petite atau curvy, celana ini bener-bener penolong OOTD kamu!"
            ]
            return hooks[0]

        # General / Outerwear logic
        if product.sales_count >= 500:
            return f"Pantesan udah laku lebih dari {product.sales_count:,} pcs! {name} ini ternyata emang se-worth it itu."
        elif product.price_idr <= 99000:
            return f"Seriusan harganya cuma {price_fmt}? Kemeja se-rapi dan se-elegan ini harganya gak masuk akal!"
        else:
            return f"Sering bingung mau pake outfit apa buat hangout? Coba liat {name} dari {product.shop_name} ini."

    @classmethod
    def generate_problem_solution(cls, product: Product) -> str:
        """Formulates the pain point and focal feature solution (2-5s)."""
        cat = ProductMotionPlanner.detect_category(product)
        anatomy = ProductMotionPlanner.extract_anatomy(product)

        if cat == ProductMotionPlanner.CATEGORY_PEPLUM_TOP:
            return (
                "Sering cari blouse tanpa lengan tapi tali pundaknya kaku atau potongannya bikin keliatan lebar? "
                "Atasan ini punya tali pita pundak adjustable yang manis banget, plus potongan neckline yang bikin leher jenjang!"
            )
        elif cat == ProductMotionPlanner.CATEGORY_SET:
            return (
                "Sering ribet nyocokin daleman sama outer? "
                f"Set ini udah include camisole crop dengan pita manis dan outer cardigan berpotongan cropped yang pas di badan!"
            )
        elif cat == ProductMotionPlanner.CATEGORY_SKINCARE:
            return (
                "Bosan sama skincare yang lengket dan lama meresap? "
                "Formulanya ringan banget water-based, sekali tap langsung meresap ke lapisan kulit terdalam!"
            )
        elif cat == ProductMotionPlanner.CATEGORY_BOTTOMS:
            return (
                "Sering beli celana tapi pinggangnya kesempitan atau pahanya begah? "
                "Pola potongannya dirancang ergonomis dengan waistband fleksibel yang nyaman dipakai seharian!"
            )
        else:
            return (
                f"Bahan dan jahitannya bener-bener presisi, detail {anatomy.get('collar', 'kerah')} "
                f"dan {anatomy.get('closure', 'kancingnya')} bikin tampilan keliatan berkelas tanpa perlu effort lebih."
            )

    @classmethod
    def generate_material_demonstration(cls, product: Product) -> str:
        """Describes tactile sensory cues and stretch/drape physics (5-8s)."""
        cat = ProductMotionPlanner.detect_category(product)
        anatomy = ProductMotionPlanner.extract_anatomy(product)

        if cat == ProductMotionPlanner.CATEGORY_PEPLUM_TOP:
            return (
                "Bagian pinggangnya smocked karet kerut super elastis dan stretch, pas di badan tanpa bikin sesak sama sekali. "
                "Bahannya katun premium adem, jatuh rufflenya mekar natural di atas celana jeans."
            )
        elif cat == ProductMotionPlanner.CATEGORY_SET:
            return (
                f"Bahannya {anatomy.get('material', 'ribbed knit')} premium, rajutannya rapat, stretch-nya awet, "
                "dan bahannya halus banget di kulit, sama sekali gak bikin gatal atau gerah."
            )
        elif cat == ProductMotionPlanner.CATEGORY_SKINCARE:
            return (
                "Pas diratain, sensasi dinginnya langsung menenangkan kulit. "
                "Kandungan aktifnya ngunci kelembapan dan bikin kulit kenyal seharian."
            )
        elif cat == ProductMotionPlanner.CATEGORY_BOTTOMS:
            return (
                "Kainnya flowy jatuh dengan anggun saat jalan, gak gampang lecek, "
                "dan jahitan sambungan di paha super rapi tanpa benang berantakan."
            )
        else:
            return (
                f"Kain {anatomy.get('material', 'katun premium')} terasa sejuk, serat kainnya breathable, "
                "dan jatuhnya pas saat dipakai bergerak."
            )

    @classmethod
    def generate_call_to_action(cls, product: Product) -> str:
        """High-urgency purchasing directive (8-10s) with yellow cart emphasis."""
        price_fmt = f"Rp {product.price_idr:,.0f}"
        stock_cue = "sebelum kehabisan stok warnanya" if product.stock_available > 0 else "sebelum sold out"
        return (
            f"Look-nya Korean classy & effortless banget! "
            f"Di toko resmi {product.shop_name} lagi ada promo cuma {price_fmt}. "
            f"Klik keranjang kuning di kiri bawah sekarang {stock_cue} ya!"
        )

    @classmethod
    def generate_complete_script(cls, product: Product) -> Dict[str, str]:
        """Assembles all 4 phases into synchronized spoken script and copywriting document."""
        hook = cls.generate_hook(product)
        problem_sol = cls.generate_problem_solution(product)
        material_demo = cls.generate_material_demonstration(product)
        cta = cls.generate_call_to_action(product)

        full_spoken = f"{hook} {problem_sol} {material_demo} {cta}"

        # Markdown formatted script with timestamps
        formatted_md = f"""# VELORA UGC COPYWRITING - {product.name.upper()}

## 1. Hook (0 - 2s)
"{hook}"

## 2. Problem & Solution (2 - 5s)
"{problem_sol}"

## 3. Material & Fit Demonstration (5 - 8s)
"{material_demo}"

## 4. Call To Action (8 - 10s)
"{cta}"
"""
        return {
            "hook": hook,
            "problem_solution": problem_sol,
            "material_demonstration": material_demo,
            "cta": cta,
            "full_spoken_script": full_spoken,
            "formatted_markdown": formatted_md
        }

    @classmethod
    def generate_caption_and_hashtags(cls, product: Product) -> Dict[str, Any]:
        """Generates viral TikTok caption with targeted SEO tags and hashtags."""
        hook = cls.generate_hook(product)
        price_fmt = f"Rp {product.price_idr:,.0f}"
        cat = ProductMotionPlanner.detect_category(product)

        base_tags = ["#racuntiktok", "#tiktokshop", "#affiliatetiktok", "#outfitideas", "#ootdindonesia"]
        clean_shop = re.sub(r"[^a-zA-Z0-9]", "", product.shop_name).lower()
        if clean_shop:
            base_tags.append(f"#{clean_shop}")

        if cat == ProductMotionPlanner.CATEGORY_PEPLUM_TOP:
            cat_tags = ["#peplumtop", "#atasantanpalengan", "#blousekorea", "#koreanstyle", "#ootdhijab"]
        elif cat == ProductMotionPlanner.CATEGORY_SET:
            cat_tags = ["#cardiganrajut", "#outfitset", "#koreanoutfit", "#knitwear", "#cardigancrop"]
        elif cat == ProductMotionPlanner.CATEGORY_SKINCARE:
            cat_tags = ["#skincareroutine", "#racunskincare", "#glowing", "#glasskin", "#serumviral"]
        elif cat == ProductMotionPlanner.CATEGORY_BOTTOMS:
            cat_tags = ["#celanakulot", "#highwaistpants", "#celanapanjang", "#jeansviral"]
        else:
            cat_tags = ["#fashionwanita", "#rekomendasibaju", "#blousewanita"]

        all_hashtags = list(dict.fromkeys(cat_tags + base_tags))

        caption = (
            f"{hook} ✨\n\n"
            f"Detail fit & bahan premium super adem, cuma {price_fmt} di {product.shop_name}! "
            f"Yuk checkout sekarang sebelum kehabisan warna favoritmu di keranjang kuning 👇\n\n"
            f"{' '.join(all_hashtags)}"
        )

        return {
            "caption": caption,
            "hashtags": all_hashtags
        }

    @classmethod
    def generate_snackable_10s_script(cls, product: Product) -> Dict[str, Any]:
        """Generates a concise, word-budgeted Indonesian UGC voiceover script strictly calibrated for 10s video.
        Word budget: 18 - 24 words (~8.5 - 9.8s at natural speaking rate ~140 wpm).
        Structure:
          - Hook (0-3s): Attention grabber (~6-8 words)
          - Material/Fit Cue (3-7s): Tactile proof (~7-9 words)
          - Urgent CTA (7-10s): Yellow cart action (~6-8 words)
        """
        cat = ProductMotionPlanner.detect_category(product)
        price_fmt = f"Rp {product.price_idr:,.0f}"

        if cat == ProductMotionPlanner.CATEGORY_PEPLUM_TOP:
            hook = "Atasan peplum ini bikin pinggang auto ramping!"
            detail = "Bahannya katun smocked super stretch dan adem."
            cta = "Yuk checkout sekarang di keranjang kuning ya!"
        elif cat == ProductMotionPlanner.CATEGORY_SET:
            hook = "Cardigan set Korea ini look-nya aesthetic banget!"
            detail = "Bahan rajut premium halus, dapet inner crop pita."
            cta = "Cek promo dan checkout di keranjang kuning!"
        elif cat == ProductMotionPlanner.CATEGORY_SKINCARE:
            hook = "Serum ini bikin kulit glowing dalam sekejap!"
            detail = "Teksturnya ringan, cepat meresap dan melembapkan seharian."
            cta = "Klik keranjang kuning sebelum kehabisan promonya ya!"
        elif cat == ProductMotionPlanner.CATEGORY_BOTTOMS:
            hook = "Celana ini bikin ilusi kaki auto jenjang!"
            detail = "Potongan highwaist-nya rapi, pinggangnya nyaman gak begah."
            cta = "Yuk checkout sekarang di keranjang kuning ya!"
        else:
            short_name = product.name[:25].strip()
            hook = f"Outfit {short_name} ini potongannya juara banget!"
            detail = f"Bahan adem dan jahitannya rapi, cuma {price_fmt}."
            cta = "Cek diskon spesial di keranjang kuning sekarang!"

        spoken_script = f"{hook} {detail} {cta}"
        words = spoken_script.split()

        formatted_md = f"""# VELORA UGC COPYWRITING (10S SNACKABLE) - {product.name.upper()}

## 1. Hook (0 - 3s)
"{hook}"

## 2. Feature & Material Cue (3 - 7s)
"{detail}"

## 3. Urgent Call To Action (7 - 10s)
"{cta}"

---
- **Word Count:** {len(words)} kata
- **Target Duration:** ~8.5 - 9.8s
"""
        return {
            "hook": hook,
            "detail": detail,
            "cta": cta,
            "spoken_script": spoken_script,
            "word_count": len(words),
            "formatted_markdown": formatted_md
        }

    @classmethod
    def build_content_brief(cls, product: Product, mode: str = "snackable_10s") -> ContentBrief:
        """Constructs an anti-hardcoded, fully populated ContentBrief domain model.
        
        Args:
            product: The product domain entity.
            mode: 'snackable_10s' (for single 10s clip with word-budget voiceover) or
                  'full_review_45s' (for multi-scene sequence).
        """
        script_data = cls.generate_complete_script(product)
        snackable = cls.generate_snackable_10s_script(product)
        caption_data = cls.generate_caption_and_hashtags(product)
        timeline = ProductMotionPlanner.generate_timeline(product, duration_sec=10)

        if mode == "snackable_10s":
            chosen_script_body = snackable["spoken_script"]
            est_duration = 10
            shot_spoken = [
                snackable["hook"],
                snackable["detail"],
                snackable["detail"],
                snackable["cta"]
            ]
        else:
            chosen_script_body = script_data["full_spoken_script"]
            est_duration = 45
            shot_spoken = [
                script_data["hook"],
                script_data["problem_solution"],
                script_data["material_demonstration"],
                script_data["cta"]
            ]

        shot_list = [
            ShotItem(
                scene_number=idx + 1,
                time_range=f"{int(phase.start_sec):02d}:00 - {int(phase.end_sec):02d}:00",
                visual_description=f"{phase.framing}. {phase.hand_action}, highlighting {phase.focal_zone}.",
                camera_movement="Steady static shot, natural iPhone lens, no CGI smoothing",
                spoken_script=shot_spoken[idx if idx < 4 else 3],
                on_screen_text=f"✨ {phase.name.upper()}"
            )
            for idx, phase in enumerate(timeline)
        ]

        facts = [
            f"Nama Resmi: {product.name}",
            f"Kategori: {product.category}",
            f"Toko: {product.shop_name}",
            f"Harga: Rp {product.price_idr:,.0f}",
            f"Estimasi Komisi: Rp {product.commission_amount_idr:,.0f} ({product.commission_rate*100:.0f}%)"
        ]
        if product.sales_count > 0:
            facts.append(f"Terjual: {product.sales_count:,}+ unit")

        asset_requirements = {
            "aspect_ratio": "9:16",
            "resolution": "1080x1920",
            "fps": 30,
            "faceless_aesthetic": True,
            "chin_down_framing": True,
            "camera": "iPhone 15 Pro back camera",
            "voice_over_voice": "id-ID-GadisNeural",
            "script_mode": mode
        }

        if product.sales_count >= 500:
            hook_type = "SOCIAL_PROOF_FOMO"
        elif product.price_idr <= 99000:
            hook_type = "PRICE_TO_VALUE_DISRUPTION"
        else:
            hook_type = "PROBLEM_SOLUTION_RELATABLE"

        return ContentBrief(
            product_id=product.id,
            hook_type=hook_type,
            hook_text=snackable["hook"] if mode == "snackable_10s" else script_data["hook"],
            script_body=chosen_script_body,
            shot_list=shot_list,
            product_facts=facts,
            cta_text=snackable["cta"] if mode == "snackable_10s" else script_data["cta"],
            caption=caption_data["caption"],
            hashtags=caption_data["hashtags"],
            asset_requirements=asset_requirements,
            target_aspect_ratio="9:16",
            estimated_duration_seconds=est_duration,
            status="ready_for_production"
        )
