"""Product Motion Planning Engine for Velora AI UGC Demonstrations.
Reverse-engineers the 4-phase micro-motion interaction pattern:
1. Establish Outfit (0-2s): Static frame, posture, silhouette, framing chin down.
2. Detail Feature (2-5s): Hand directs attention to focal construction (collar, tie ribbon, neckline).
3. Material Demonstration (5-8s): Hand glides across fabric, exhibiting texture, weave, drape.
4. Closing & Cut (8-10s): Hand showcases hemline, waist proportion, cut length.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re
from src.models import Product


@dataclass
class MotionPhase:
    """A chronologically distinct interaction phase within a product video."""
    start_sec: float
    end_sec: float
    name: str
    focal_zone: str
    hand_action: str
    framing: str
    sensory_cue: str
    audience_intent: str

    def to_prompt_clause(self) -> str:
        """Render phase into natural, photorealistic prompt instruction."""
        return (
            f"[{int(self.start_sec)}-{int(self.end_sec)}s: {self.name}] "
            f"{self.framing}. {self.hand_action}, highlighting {self.focal_zone}. "
            f"Revealing {self.sensory_cue} to establish {self.audience_intent}."
        )


class DynamicGarmentParser:
    """Intelligent semantic parser that breaks down ANY fashion product title
    into factual visual attributes (color, fabric, silhouette, closures, category, pairing).
    """

    COLORS = {
        "sage green": "sage green",
        "sage": "sage green",
        "dusty pink": "dusty pink",
        "dusty": "dusty pink",
        "broken white": "broken white",
        "bw": "broken white",
        "putih": "crisp white",
        "white": "crisp white",
        "hitam": "black",
        "black": "black",
        "cokelat": "chocolate brown",
        "coklat": "chocolate brown",
        "brown": "chocolate brown",
        "mocca": "mocca beige",
        "moka": "mocca beige",
        "terracotta": "terracotta rust",
        "teracotta": "terracotta rust",
        "navy": "navy blue",
        "biru navy": "navy blue",
        "biru": "soft blue",
        "blue": "soft blue",
        "maroon": "deep maroon red",
        "merah": "classic red",
        "lilac": "pastel lilac lavender",
        "lavender": "soft lavender",
        "mustard": "mustard yellow",
        "kuning": "soft warm yellow",
        "krem": "warm cream",
        "cream": "warm cream",
        "beige": "neutral beige",
        "khaki": "khaki",
        "army": "army olive green",
        "olive": "olive green",
        "mint": "soft mint green",
        "abu-abu": "heather grey",
        "abu": "heather grey",
        "grey": "heather grey",
        "gray": "heather grey",
        "emerald": "emerald green",
        "peach": "soft peach",
        "coral": "warm coral",
    }

    MATERIALS = {
        "crinkle airflow": "textured crinkle airflow fabric",
        "crinkle": "breathable crinkle airflow fabric",
        "airflow": "breathable airflow fabric",
        "ribbed knit": "elastic ribbed knit weave",
        "rajut": "ribbed knit cotton",
        "knit": "soft knit cotton",
        "knitwear": "soft ribbed knitwear",
        "waffle": "textured waffle knit fabric",
        "linen rami": "crisp natural linen rami",
        "linen": "breathable natural woven linen",
        "rayon": "smooth flowy rayon viscose",
        "katun combed": "premium combed cotton",
        "katun": "breathable crisp cotton",
        "cotton": "breathable white cotton",
        "ceruty babydoll": "flowy layered ceruty babydoll chiffon",
        "ceruty": "delicate sheer ceruty fabric",
        "chiffon": "delicate airy chiffon",
        "satin": "glossy liquid silk satin",
        "silk": "smooth lustrous silk",
        "sutra": "smooth lustrous silk",
        "denim": "classic durable woven denim",
        "jeans": "authentic washed denim",
        "scuba": "structured smooth scuba fabric",
        "fleece": "cozy plush fleece cotton",
        "babyterry": "soft absorbent babyterry knit",
        "wool": "warm textured wool blend",
        "corduroy": "ribbed textured velvet corduroy",
        "tweed": "sophisticated woven textured tweed",
        "plisket": "permanently pleated accordion fabric",
        "pleated": "crisp accordion pleated fabric",
    }

    SILHOUETTES = {
        "peplum": "flared peplum silhouette with cinched waist",
        "crop": "modern cropped waistline cut",
        "oversized": "relaxed loose oversized boxy drape",
        "loose": "relaxed airy loose fit silhouette",
        "slim fit": "tailored form-fitting silhouette",
        "slim": "slender flattering fit",
        "flowy": "graceful flowy cascading silhouette",
        "a-line": "flattering A-line flared silhouette",
        "span": "sleek pencil span silhouette",
        "maxi": "elegant full-length maxi drape",
        "midi": "chic mid-calf midi length",
        "sleeveless": "clean sleeveless cut",
        "tanpa lengan": "flattering sleeveless cut",
        "halter": "high halter-neck cut",
        "sabrina": "romantic off-shoulder sabrina neckline",
        "drop shoulder": "casual slouchy drop-shoulder sleeves",
    }

    COLLARS = {
        "peter pan": "scalloped Peter Pan collar",
        "kancing": "buttoned front placket",
        "shanghai": "mandarin stand collar",
        "v-neck": "flattering V-neckline",
        "square neck": "chic square neckline",
        "sabrina": "off-shoulder sabrina neckline",
        "turtleneck": "cozy folded turtleneck",
        "polo": "classic ribbed polo collar",
        "lapel": "tailored notch lapels",
        "boat": "boat neckline with shoulder tie ribbons",
        "hoodie": "cozy drawstring hood",
    }

    CLOSURES = {
        "shoulder tie": "shoulder tie ribbon straps",
        "tali bahu": "shoulder tie ribbon straps",
        "ribbon": "front center tie ribbon bow",
        "tali pita": "front center tie ribbon bow",
        "pita": "delicate tie ribbon bow",
        "kancing mutiara": "lustrous front pearl buttons",
        "kancing": "pearly buttons",
        "buttons": "front button placket",
        "resleting": "clean invisible zipper closure",
        "zipper": "front metallic zipper closure",
        "smocked": "smocked elastic waist",
        "serut": "adjustable cinch drawstring",
        "drawstring": "adjustable cinch drawstring",
        "karet": "comfortable elasticized waist",
    }

    @classmethod
    def parse(cls, product: Product) -> Dict[str, str]:
        name_lower = (product.name or "").lower()
        cat_lower = (product.category or "").lower()
        full_text = f"{name_lower} {cat_lower}"

        # 1. Color extraction
        detected_color = ""
        for key, val in cls.COLORS.items():
            if re.search(r'\b' + re.escape(key) + r'\b', full_text):
                detected_color = val
                break

        # 2. Material extraction
        detected_material = ""
        for key, val in cls.MATERIALS.items():
            if re.search(r'\b' + re.escape(key) + r'\b', full_text):
                detected_material = val
                break
        if not detected_material:
            detected_material = "breathable textile"

        # 3. Silhouette extraction
        detected_silhouette = ""
        for key, val in cls.SILHOUETTES.items():
            if re.search(r'\b' + re.escape(key) + r'\b', full_text):
                detected_silhouette = val
                break

        # 4. Collar & Closure extraction
        detected_collar = "delicate neckline"
        for key, val in cls.COLLARS.items():
            if re.search(r'\b' + re.escape(key) + r'\b', full_text):
                detected_collar = val
                break

        detected_closure = "clean finished seams"
        for key, val in cls.CLOSURES.items():
            if re.search(r'\b' + re.escape(key) + r'\b', full_text):
                detected_closure = val
                break

        # Backward-compatible defaults for known items
        is_peplum = "peplum" in full_text or "tessa" in full_text
        is_cardigan = "cardigan" in full_text or "rajut" in full_text
        is_blouse = "blouse" in full_text or "kemeja" in full_text
        is_dress = any(k in full_text for k in ["dress", "gamis", "abaya", "kaftan", "one piece"])
        is_outerwear = any(k in full_text for k in ["blazer", "jaket", "jacket", "coat", "hoodie", "sweater", "vest"])
        is_bottom = any(k in full_text for k in ["celana", "pants", "kulot", "jeans", "rok", "skirt", "trouser", "cargo"])

        color_prefix = f"{detected_color} " if detected_color else ""

        if is_peplum:
            color_str = detected_color or "crisp white"
            mat_str = "breathable white cotton with smocked elastic waist" if not detected_material or detected_material == "breathable textile" else detected_material
            top_type = f"{color_str} sleeveless cotton peplum top with shoulder tie ribbon straps"
            collar = "boat neckline with shoulder tie ribbons"
            closure = "shoulder tie ribbon straps"
            material = mat_str
            bottom = "tailored blue denim high-waist jeans"
            cat_name = "fashion_peplum_top"
        elif is_cardigan:
            color_str = detected_color or "chocolate brown"
            top_type = f"unbuttoned cropped knit cardigan layered over fitted crop camisole"
            material = "ribbed knit cotton"
            closure = "front chest tie ribbon bow on inner camisole"
            collar = "delicate collar neckline"
            bottom = "tailored white high-waist pants"
            cat_name = "fashion_set"
        elif is_dress:
            color_str = detected_color or "elegant"
            top_type = f"{color_str} {detected_silhouette or 'flowy'} dress crafted from {detected_material}"
            collar = detected_collar
            closure = detected_closure
            material = detected_material
            bottom = "matching flowy dress hemline"
            cat_name = "fashion_dress"
        elif is_outerwear:
            if "blazer" in full_text:
                color_str = detected_color or "black"
                top_type = f"{color_str} tailored structured blazer crafted from {detected_material}"
                collar = "tailored notch lapels"
                closure = "pearly buttons"
                material = detected_material
                bottom = "tailored pleated high-waist trousers"
            else:
                top_type = f"{color_prefix}{detected_silhouette or 'casual'} outerwear crafted from {detected_material}"
                collar = detected_collar
                closure = detected_closure
                material = detected_material
                bottom = "tailored white high-waist pants"
            cat_name = "fashion_top_outerwear"
        elif is_blouse:
            color_str = detected_color or "crisp"
            top_type = f"collared tailored blouse"
            material = "crisp breathable cotton" if detected_material == "breathable textile" else detected_material
            closure = "pearly buttons"
            collar = "collared tailored neckline"
            bottom = "tailored blue denim high-waist jeans" if "jeans" in full_text else "pleated wide-leg high-waist pants"
            cat_name = "fashion_top_outerwear"
        elif is_bottom:
            top_type = "minimalist fitted white ribbed cotton top"
            collar = "clean neckline"
            closure = detected_closure
            material = detected_material
            bottom = f"{color_prefix}{detected_silhouette or 'tailored'} pants in {detected_material}"
            cat_name = "fashion_bottoms"
        else:
            top_type = f"{color_prefix}{product.name}"
            collar = detected_collar
            closure = detected_closure
            material = detected_material
            bottom = "tailored neutral high-waist trousers"
            cat_name = "fashion_top_outerwear"

        if "jeans" in full_text or "denim" in full_text:
            bottom = "tailored blue denim high-waist jeans"
        elif "kulot" in full_text or "pants" in full_text or "celana" in full_text:
            bottom = "pleated wide-leg high-waist pants"

        return {
            "category": cat_name,
            "color": detected_color or "neutral tone",
            "material": material,
            "silhouette": detected_silhouette or "tailored silhouette",
            "collar": collar,
            "closure": closure,
            "top_type": top_type,
            "bottom": bottom,
            "full_description": f"{top_type}, paired with {bottom}"
        }


@dataclass
class ChoreographyStyle:
    """Defines a distinct TikTok fashion demonstration choreography."""
    id: str
    name: str
    description: str
    build_scene1: Any
    build_scene2: Any


class VideoChoreographyRegistry:
    """Registry of diverse video styles and choreographies to prevent TikTok content fatigue."""

    _STYLES: Dict[str, ChoreographyStyle] = {}

    @classmethod
    def register(cls, style: ChoreographyStyle):
        cls._STYLES[style.id] = style

    @classmethod
    def get(cls, style_id: str) -> Optional[ChoreographyStyle]:
        return cls._STYLES.get(style_id)

    @classmethod
    def list_styles(cls) -> List[Dict[str, str]]:
        return [
            {"id": s.id, "name": s.name, "description": s.description}
            for s in cls._STYLES.values()
        ]

    @classmethod
    def select_smart_style(cls, product: Product) -> str:
        """Selects the best style for product to keep feed varied."""
        text = f"{product.name} {product.category}".lower()
        if any(k in text for k in ["rajut", "knit", "ribbed", "crinkle", "waffle", "stretch"]):
            return "fabric_stretch_test"
        elif any(k in text for k in ["dress", "gamis", "abaya", "flowy", "maxi", "rok", "skirt"]):
            return "walking_lookbook"
        elif any(k in text for k in ["blazer", "set", "outer", "jacket", "cardigan"]):
            return "layering_styling"
        elif any(k in text for k in ["kaos", "t-shirt", "tee", "oversize", "casual"]):
            return "candid_lifestyle"
        return "tryon_classic"


# Register the 5 Master Choreography Styles
def _build_tryon_classic_scene1(anatomy: Dict[str, str], prod_title: str) -> str:
    return (
        f"Authentic unedited vertical try-on video of Velora wearing the exact outfit from reference image: {anatomy['full_description']}. "
        "Framed strictly from lower jaw down to waist, faceless aesthetic try-on. "
        "Shot on iPhone 15 Pro back camera, 4K 30fps, natural indoor room daylight from window, subtle camera sensor grain. "
        f"Model casually smoothing the {anatomy['top_type']} and delicately highlighting the {anatomy['closure']} and {anatomy['collar']} with gentle fingers, "
        "showcasing real fabric wrinkles, natural cloth drape reacting to movement. "
        "Authentic natural human speed, realistic casual pacing, zero cinematic CGI smoothing, realistic candid lifestyle."
    )

def _build_tryon_classic_scene2(anatomy: Dict[str, str], prod_title: str) -> str:
    return (
        f"Authentic vertical try-on video of Velora showcasing the side silhouette of {anatomy['full_description']}. "
        "Framed strictly from lower chin down to hips, faceless aesthetic try-on. "
        "Shot on iPhone 15 Pro back camera, 4K 30fps, natural indoor room daylight from window, subtle camera sensor grain. "
        "Model gently turning 45 degrees left and right, hands resting lightly on waist, "
        "showing side profile, waist cut proportion, and natural fabric drape with real gravity. "
        "Authentic natural human speed, realistic casual pacing, organic cloth weave, zero CGI smoothing, realistic candid lifestyle."
    )

def _build_walking_lookbook_scene1(anatomy: Dict[str, str], prod_title: str) -> str:
    return (
        f"Dynamic unedited vertical lookbook video of Velora wearing {anatomy['full_description']}. "
        "Eye-level camera tracking shot framed from chin down to hemline, faceless aesthetic. "
        "Shot on iPhone 15 Pro back camera, soft natural daylight. "
        f"Model taking 2-3 casual, graceful steps forward toward camera in an aesthetic minimalist room, "
        f"demonstrating how the {anatomy['material']} sways and moves organically with natural body motion, exhibiting clean garment drape and flow. "
        "Realistic candid lifestyle, authentic human pace, zero CGI smoothing."
    )

def _build_walking_lookbook_scene2(anatomy: Dict[str, str], prod_title: str) -> str:
    return (
        f"Dynamic vertical lookbook video of Velora wearing {anatomy['full_description']}. "
        "Camera framed from collarbone down to mid-thigh, faceless aesthetic try-on. "
        "Shot on iPhone 15 Pro back camera, authentic room daylight. "
        "Model pauses and performs a fluid, gentle 360-degree slow rotation, showcasing back tailoring, side silhouette, "
        "and complete outfit balance before resting naturally with hands relaxed at sides. "
        "Zero CGI waxy smoothing, authentic organic smartphone aesthetic."
    )

def _build_fabric_stretch_scene1(anatomy: Dict[str, str], prod_title: str) -> str:
    return (
        f"Authentic tactile material proof video of Velora wearing {anatomy['full_description']}. "
        "Macro close-up framing strictly from lower jaw down to waist, faceless aesthetic try-on. "
        "Shot on iPhone 15 Pro back camera, 4K crisp detail, honest window daylight. "
        f"Model's delicate fingers gently grasping and lightly stretching the {anatomy['material']} across the bodice, "
        "showcasing its rich textile elasticity, softness, and breathable weave quality in high definition. "
        "Real organic cloth physics, zero digital smoothing."
    )

def _build_fabric_stretch_scene2(anatomy: Dict[str, str], prod_title: str) -> str:
    return (
        f"Authentic fabric recovery video of Velora wearing {anatomy['full_description']}. "
        "Framing from lower jaw to waist, faceless aesthetic try-on. "
        "Shot on iPhone 15 Pro back camera, natural room daylight. "
        "Model releases the fabric and gently smooths the surface with open palms, highlighting the instant wrinkle recovery "
        f"and clean {anatomy['silhouette']} contour. Real fabric weave, organic drape, authentic candid lifestyle."
    )

def _build_candid_lifestyle_scene1(anatomy: Dict[str, str], prod_title: str) -> str:
    return (
        f"Candid unedited lifestyle OOTD video of Velora wearing {anatomy['full_description']}. "
        "Mirror-check perspective framed from collarbone down to hips, faceless aesthetic try-on. "
        "Shot on iPhone 15 Pro back camera, natural warm morning daylight streaming from bedroom window, subtle sensor grain. "
        "Model casually adjusting her posture and checking the fit in the mirror, hands gently grazing the hemline in a relaxed, effortless everyday routine. "
        "Zero staging, 100% candid UGC authenticity."
    )

def _build_candid_lifestyle_scene2(anatomy: Dict[str, str], prod_title: str) -> str:
    return (
        f"Candid casual lifestyle video of Velora wearing {anatomy['full_description']}. "
        "Framing from collarbone down to mid-thigh, faceless aesthetic try-on. "
        "Shot on iPhone 15 Pro back camera, soft ambient room daylight. "
        "Model sways gently with natural body language, shifting weight casually between feet and gesturing softly, "
        "showcasing authentic everyday wearability and flattering drape from every angle. "
        "Authentic natural human speed, zero artificial CGI polish."
    )

def _build_layering_styling_scene1(anatomy: Dict[str, str], prod_title: str) -> str:
    return (
        f"Chic outfit styling video of Velora wearing {anatomy['full_description']}. "
        "Medium eye-level shot framed from lower neck down to mid-thigh, faceless aesthetic try-on. "
        "Shot on iPhone 15 Pro back camera, clean modern daylight. "
        f"Model establishes the base outfit silhouette, smoothing the waistline and highlighting the versatile clean cut of the {anatomy['top_type']}. "
        "Organic cloth folds, authentic smartphone camera texture."
    )

def _build_layering_styling_scene2(anatomy: Dict[str, str], prod_title: str) -> str:
    return (
        f"Chic mix-and-match styling video of Velora wearing {anatomy['full_description']}. "
        "Framed from collarbone down to mid-thigh, faceless aesthetic try-on. "
        "Shot on iPhone 15 Pro back camera, natural soft daylight. "
        "Model demonstrates versatile day-to-night styling, resting hands lightly on a minimalist leather bag strap and gesturing softly, "
        "exhibiting complete outfit cohesion and fashionable silhouette balance. Zero CGI smoothing, realistic candid lifestyle."
    )

VideoChoreographyRegistry.register(ChoreographyStyle("tryon_classic", "Classic OOTD Try-On", "Front detail + 45-degree side turn silhouette", _build_tryon_classic_scene1, _build_tryon_classic_scene2))
VideoChoreographyRegistry.register(ChoreographyStyle("walking_lookbook", "Dynamic Runway Walk", "Casual forward walk + 360-degree rotation spin", _build_walking_lookbook_scene1, _build_walking_lookbook_scene2))
VideoChoreographyRegistry.register(ChoreographyStyle("fabric_stretch_test", "Tactile Quality & Stretch", "Fabric pull/elasticity test + wrinkle recovery", _build_fabric_stretch_scene1, _build_fabric_stretch_scene2))
VideoChoreographyRegistry.register(ChoreographyStyle("candid_lifestyle", "Candid Bedroom UGC", "Mirror-check OOTD + casual room movement", _build_candid_lifestyle_scene1, _build_candid_lifestyle_scene2))
VideoChoreographyRegistry.register(ChoreographyStyle("layering_styling", "Mix & Match Styling", "Base outfit cut + accessory styling demonstration", _build_layering_styling_scene1, _build_layering_styling_scene2))


class ProductMotionPlanner:
    """Plans realistic micro-interactions tailored to product categories."""

    CATEGORY_SET = "fashion_set"
    CATEGORY_TOP_OUTERWEAR = "fashion_top_outerwear"
    CATEGORY_PEPLUM_TOP = "fashion_peplum_top"
    CATEGORY_BOTTOMS = "fashion_bottoms"
    CATEGORY_SKINCARE = "skincare"
    CATEGORY_ACCESSORY = "accessory"

    @classmethod
    def detect_category(cls, product: Product) -> str:
        """Infer granular subcategory from product metadata and title."""
        text = f"{product.name} {product.category}".lower()
        
        # Peplum tops & sleeveless blouses
        if any(k in text for k in ["peplum", "tessa", "tanpa lengan", "sleeveless"]):
            return cls.CATEGORY_PEPLUM_TOP

        # 2-piece sets or layered camisole + cardigan
        if any(k in text for k in ["set", "2 piece", "2in1", "inner", "camisole", "twopiece"]):
            return cls.CATEGORY_SET
            
        # Skincare & cosmetics
        if any(k in text for k in ["serum", "cream", "moisturizer", "sunscreen", "toner", "skincare", "lotion"]):
            return cls.CATEGORY_SKINCARE
            
        # Bags & accessories
        if any(k in text for k in ["tas", "bag", "clutch", "tote", "dompet", "kalung", "necklace", "jam", "watch"]):
            return cls.CATEGORY_ACCESSORY
            
        # Bottoms
        if any(k in text for k in ["celana", "pants", "kulot", "jeans", "rok", "skirt", "trouser"]):
            return cls.CATEGORY_BOTTOMS
            
        # Default to tops / outerwear
        return cls.CATEGORY_TOP_OUTERWEAR

    @classmethod
    def extract_anatomy(cls, product: Product) -> Dict[str, str]:
        """Extract explicit garment features from product title dynamically."""
        return DynamicGarmentParser.parse(product)

    @classmethod
    def generate_timeline(cls, product: Product, duration_sec: int = 10) -> List[MotionPhase]:
        """Generate a structured 4-phase micro-interaction timeline."""
        cat = cls.detect_category(product)
        anatomy = cls.extract_anatomy(product)

        if cat == cls.CATEGORY_PEPLUM_TOP:
            return [
                MotionPhase(
                    start_sec=0.0,
                    end_sec=2.0,
                    name="Establish Silhouette",
                    focal_zone="cinched waist and peplum silhouette paired with blue denim jeans",
                    hand_action="Model stands centered with natural posture, establishing clean outfit fit and silhouette",
                    framing="Static eye-level camera framed strictly from neckline down to mid-thigh, head naturally cropped out above upper frame edge, no face visible",
                    sensory_cue="organic shape of the peplum top and flattering waist contour",
                    audience_intent="instant outfit appeal and body silhouette compatibility"
                ),
                MotionPhase(
                    start_sec=2.0,
                    end_sec=5.0,
                    name="Shoulder Straps Detail",
                    focal_zone="shoulder tie ribbon straps and boat neckline",
                    hand_action="Right hand gently lifts to touch and adjust the delicate shoulder tie ribbon strap and boat neckline",
                    framing="Steady eye-level shot capturing upper body",
                    sensory_cue="delicate ribbon strap construction and collarbone framing",
                    audience_intent="focal neckline craftsmanship and adjustable strap detail"
                ),
                MotionPhase(
                    start_sec=5.0,
                    end_sec=8.0,
                    name="Smocked Waist Demonstration",
                    focal_zone="ruched smocked elastic waist",
                    hand_action="Both hands lightly touch and stretch the smocked elastic waist, feeling the ruched texture",
                    framing="Steady shot capturing waistline and torso",
                    sensory_cue="supple elasticity, comfortable stretch, and breathable cotton texture",
                    audience_intent="tactile fabric comfort, stretch flexibility, and waist cinching"
                ),
                MotionPhase(
                    start_sec=8.0,
                    end_sec=float(duration_sec),
                    name="Peplum Flare & Cut",
                    focal_zone="flared peplum ruffle hem and waist-to-hip proportions",
                    hand_action="Fingers lightly graze the flared peplum ruffle hem over the blue jeans before relaxing arms naturally",
                    framing="Lower neck down to mid-thigh",
                    sensory_cue="flared peplum drape and clean contrast against blue jeans",
                    audience_intent="final purchasing confidence in garment cut and waist-to-hip ratio"
                )
            ]
        elif cat == cls.CATEGORY_SET or cat == cls.CATEGORY_TOP_OUTERWEAR:
            return [
                MotionPhase(
                    start_sec=0.0,
                    end_sec=2.0,
                    name="Establish Outfit",
                    focal_zone="overall silhouette and clean fit",
                    hand_action="Model steps back into static frame with natural posture, holding casual clutch in left hand",
                    framing="Framed strictly from lower jaw down to waist, faceless aesthetic try-on",
                    sensory_cue=f"organic silhouette of the {anatomy['top_type']}",
                    audience_intent="instant outfit appeal and body silhouette compatibility"
                ),
                MotionPhase(
                    start_sec=2.0,
                    end_sec=5.0,
                    name="Feature & Focal Detail",
                    focal_zone=anatomy["closure"],
                    hand_action="Right hand gently reaches up to touch and delicate fingers gently adjust the tie ribbon bow and collar",
                    framing="Medium waist-up framing, camera stays still",
                    sensory_cue=f"intricate construction of the {anatomy['closure']}",
                    audience_intent="focal point craftsmanship and neck-framing design"
                ),
                MotionPhase(
                    start_sec=5.0,
                    end_sec=8.0,
                    name="Material Demonstration",
                    focal_zone=f"{anatomy['material']} on the front torso",
                    hand_action="Palm gently glides downward across the front bodice fabric, feeling the ribbed texture",
                    framing="Steady eye-level shot capturing fabric movement",
                    sensory_cue=f"supple elasticity, organic drape, and genuine texture of {anatomy['material']}",
                    audience_intent="tactile fabric quality, stretch, and softness"
                ),
                MotionPhase(
                    start_sec=8.0,
                    end_sec=float(duration_sec),
                    name="Closing & Proportions",
                    focal_zone="hemline cut and waist-to-hip ratio",
                    hand_action="Fingers lightly touch the bottom hem, smoothing the edge before resting naturally",
                    framing="Lower chin down to upper thigh, showing clean pairing with high-waist pants",
                    sensory_cue="crisp hemline finish and flattering cropped proportion",
                    audience_intent="final purchasing confidence in garment length and pairing"
                )
            ]
        elif cat == cls.CATEGORY_BOTTOMS:
            return [
                MotionPhase(
                    start_sec=0.0,
                    end_sec=2.0,
                    name="Establish Silhouette",
                    focal_zone="full leg length and waistline",
                    hand_action="Model stands centered, gentle half-step showcasing leg line",
                    framing="Framed from navel down to shoes",
                    sensory_cue="clean drape of trousers",
                    audience_intent="overall cut and silhouette verification"
                ),
                MotionPhase(
                    start_sec=2.0,
                    end_sec=5.0,
                    name="Waist & Pocket Detail",
                    focal_zone="waistband and side pockets",
                    hand_action="Hands slip casually into side pockets, then gently trace the high waistband",
                    framing="Waist to mid-thigh framing",
                    sensory_cue="waistband tailoring and pocket functionality",
                    audience_intent="fit comfort and structural utility"
                ),
                MotionPhase(
                    start_sec=5.0,
                    end_sec=8.0,
                    name="Fabric Stretch & Movement",
                    focal_zone="knee and thigh fabric drape",
                    hand_action="Subtle step forward showing movement fluidity without creasing",
                    framing="Full lower body shot",
                    sensory_cue="breathable flex and wrinkle resistance",
                    audience_intent="all-day movement comfort"
                ),
                MotionPhase(
                    start_sec=8.0,
                    end_sec=float(duration_sec),
                    name="Ankle Break & Closing",
                    focal_zone="cuff and hem break over footwear",
                    hand_action="Resting hands at sides with relaxed stance",
                    framing="Full pants length to shoes",
                    sensory_cue="clean hemline finish",
                    audience_intent="versatility with shoes and styling"
                )
            ]
        elif cat == cls.CATEGORY_SKINCARE:
            return [
                MotionPhase(
                    start_sec=0.0,
                    end_sec=2.0,
                    name="Product Presentation",
                    focal_zone="bottle packaging and label",
                    hand_action="Holding bottle upright steadily in palm towards camera",
                    framing="Chest-up framing with product centered",
                    sensory_cue="clean minimalist aesthetic",
                    audience_intent="product authenticity and branding"
                ),
                MotionPhase(
                    start_sec=2.0,
                    end_sec=5.0,
                    name="Dispensing Mechanism",
                    focal_zone="dropper or pump action",
                    hand_action="Gently pressing dropper to release clear luminous droplet onto back of hand",
                    framing="Close-up on hands and droplet",
                    sensory_cue="viscous, lightweight fluid texture",
                    audience_intent="ease of application and texture purity"
                ),
                MotionPhase(
                    start_sec=5.0,
                    end_sec=8.0,
                    name="Texture Swatch",
                    focal_zone="formula spread on skin",
                    hand_action="Fingertip smoothing formula across skin in circular motion",
                    framing="Close-up on skin surface",
                    sensory_cue="dewy hydration without greasy residue",
                    audience_intent="instant radiance and glide"
                ),
                MotionPhase(
                    start_sec=8.0,
                    end_sec=float(duration_sec),
                    name="Absorption & Glow",
                    focal_zone="hydrated, plump skin finish",
                    hand_action="Gently patting skin to exhibit immediate absorption",
                    framing="Skin close-up turning gently toward light",
                    sensory_cue="healthy glassy glow",
                    audience_intent="fast absorption and non-sticky finish"
                )
            ]
        else:
            # Default / Accessory
            return [
                MotionPhase(
                    start_sec=0.0,
                    end_sec=2.0,
                    name="Establish Accessory",
                    focal_zone="overall item in wearing context",
                    hand_action="Holding accessory naturally at waist level",
                    framing="Faceless waist-level framing",
                    sensory_cue="proportional size against body",
                    audience_intent="real-world scale and styling"
                ),
                MotionPhase(
                    start_sec=2.0,
                    end_sec=5.0,
                    name="Hardware & Clasp Showcase",
                    focal_zone="metallic clasp or buckle",
                    hand_action="Fingers opening and closing clasp with precision",
                    framing="Macro close-up on hardware",
                    sensory_cue="smooth mechanical action and metallic gleam",
                    audience_intent="durability and premium finish"
                ),
                MotionPhase(
                    start_sec=5.0,
                    end_sec=8.0,
                    name="Material & Texture Demonstration",
                    focal_zone="surface grain and stitching",
                    hand_action="Fingers tracing exterior texture and edge stitching",
                    framing="Clear close-up",
                    sensory_cue="luxurious tactile texture",
                    audience_intent="craftsmanship and material quality"
                ),
                MotionPhase(
                    start_sec=8.0,
                    end_sec=float(duration_sec),
                    name="Closing Presentation",
                    focal_zone="complete piece in final pose",
                    hand_action="Holding item steadily to allow 360 viewer appraisal",
                    framing="Clean medium shot",
                    sensory_cue="balanced silhouette",
                    audience_intent="styling completion and purchase impulse"
                )
            ]

    @classmethod
    def format_prompt_choreography(cls, phases: List[MotionPhase]) -> str:
        """Compose all motion phases into a chronological cinematic prompt block."""
        clauses = [phase.to_prompt_clause() for phase in phases]
        return " ".join(clauses)
