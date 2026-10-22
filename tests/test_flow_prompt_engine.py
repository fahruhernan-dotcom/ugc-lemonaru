"""Unit tests for GoogleFlowPromptEngine."""

from src.flow_prompt_engine import GoogleFlowPromptEngine
from src.models import ContentBrief, Product, ShotItem


def test_synthesize_image_prompt_contains_product_and_9_16():
    """Verifies image prompt generation contains 9:16 vertical styling and product name."""
    product = Product(
        product_id="TEST-001",
        name="Oversized Korean Blazer Sage Green",
        price_idr=189000.0,
        commission_rate=0.15,
        category="Women Fashion",
        shop_name="Velora Boutique",
    )
    prompt = GoogleFlowPromptEngine.synthesize_image_prompt(product=product, archetype="professional")
    assert "9:16" in prompt
    assert "Oversized Korean Blazer Sage Green" in prompt
    assert "Indonesian female fashion model" in prompt
    assert "photorealistic" in prompt


def test_synthesize_video_prompt_incorporates_brief_shots():
    """Verifies video prompt generation incorporates shot details and fluid motion."""
    product = Product(
        product_id="TEST-002",
        name="Linen Wide Leg Trousers",
        price_idr=149000.0,
        commission_rate=0.12,
        category="Pants",
        shop_name="Velora Boutique",
    )
    brief = ContentBrief(
        product_id="TEST-002",
        hook_type="CURIOSITY_GAP",
        hook_text="Celana yang bikin kaki keliatan jenjang seketika!",
        script_body="Linen trousers premium dengan potongan high-waist elegan.",
        cta_text="Cek keranjang kuning sekarang!",
        shot_list=[
            ShotItem(
                scene_number=1,
                time_range="00:00 - 00:03",
                visual_description="Model berjalan anggun memperlihatkan potongan celana linen high-waist",
                camera_movement="Slow tilt up",
                on_screen_text="Bikin Kaki Jenjang",
                spoken_script="Tampil modis dengan celana linen ini.",
            )
        ],
        product_facts=["Bahan linen premium breathable"],
        caption="Tampil stylish dengan linen trousers #ootd",
    )
    prompt = GoogleFlowPromptEngine.synthesize_video_prompt(product=product, brief=brief, archetype="professional")
    assert "9:16 vertical" in prompt
    assert "Linen Wide Leg Trousers" in prompt
    assert "Model berjalan anggun" in prompt
    assert "24fps motion" in prompt


def test_synthesize_concise_choreographed_prompt_peplum():
    product = Product(
        product_id="GARMENT-05",
        name="CLASSY - TESSA Peplum Top Wanita Blouse Tanpa Lengan",
        price_idr=129000.0,
        commission_rate=0.15,
        category="Fashion Wanita",
        shop_name="CLASSY Official",
    )
    prompt = GoogleFlowPromptEngine.synthesize_concise_choreographed_prompt(product)
    assert len(prompt) < 1200
    assert "faceless" not in prompt.lower()
    assert "peplum" in prompt.lower()
    assert "shoulder tie ribbon" in prompt.lower()
    assert "blue denim" in prompt.lower()
    assert "@garment_5_isolated_white_bg.jpg" in prompt


def test_synthesize_foundation_photo_prompts():
    """Verifies SOP 2-Foto Fondasi generation for close-up and wide silhouette."""
    peplum_prod = Product(
        product_id="GARMENT-05",
        name="CLASSY - TESSA Peplum Top Wanita Blouse Tanpa Lengan",
        category="fashion_peplum_top",
        price_idr=129000.0,
        commission_rate=0.15,
        shop_name="CLASSY Official"
    )

    p1 = GoogleFlowPromptEngine.synthesize_foundation_photo_prompt(peplum_prod, photo_type="close_up")
    assert "lower jaw down to waist" in p1
    assert "peplum" in p1.lower()
    assert "iphone 15 pro" in p1.lower()
    assert "photorealistic 8k" not in p1.lower()
    assert "luxury studio" not in p1.lower()

    p2 = GoogleFlowPromptEngine.synthesize_foundation_photo_prompt(peplum_prod, photo_type="wide_silhouette")
    assert "collarbone down to mid-thigh" in p2
    assert "iphone 15 pro" in p2.lower()
    assert "blue denim" in p2.lower()


def test_synthesize_ugc_realistic_tryon_prompt_dynamic_categories():
    """Verifies that peplum tops do NOT hallucinate cardigan actions and receive tailored motions."""
    peplum_prod = Product(
        product_id="GARMENT-05",
        name="CLASSY - TESSA Peplum Top Wanita Blouse Tanpa Lengan",
        category="fashion_peplum_top",
        price_idr=129000.0,
        commission_rate=0.15,
        shop_name="CLASSY Official"
    )

    front_peplum = GoogleFlowPromptEngine.synthesize_ugc_realistic_tryon_prompt(peplum_prod, scene="front")
    assert "peplum" in front_peplum.lower()
    assert "cardigan" not in front_peplum.lower()
    assert "smocked waist" in front_peplum.lower()

    side_peplum = GoogleFlowPromptEngine.synthesize_ugc_realistic_tryon_prompt(peplum_prod, scene="side_turn")
    assert "flared peplum cut" in side_peplum.lower()
    assert "cardigan" not in side_peplum.lower()

    # Cardigan test
    cardigan_prod = Product(
        product_id="GARMENT-01",
        name="Cardigan Rajut Crop Cokelat Set Inner Ribbon",
        category="fashion_set",
        price_idr=135000.0,
        commission_rate=0.15,
        shop_name="Daily Chic"
    )
    front_cardigan = GoogleFlowPromptEngine.synthesize_ugc_realistic_tryon_prompt(cardigan_prod, scene="front")
    assert "cardigan" in front_cardigan.lower()
    assert "ribbon" in front_cardigan.lower()


def test_video_choreography_registry_all_styles_registered():
    """Verifies that all 5 choreography styles are properly registered."""
    from src.motion_planner import VideoChoreographyRegistry
    styles = VideoChoreographyRegistry.list_styles()
    style_ids = [s["id"] for s in styles]
    assert "tryon_classic" in style_ids
    assert "walking_lookbook" in style_ids
    assert "fabric_stretch_test" in style_ids
    assert "candid_lifestyle" in style_ids
    assert "layering_styling" in style_ids
    assert len(style_ids) >= 5


def test_synthesize_choreographed_multiscene_prompts_styles():
    """Verifies that different choreography styles generate distinct, realistic prompts."""
    prod = Product(
        product_id="TEST-STYLE",
        name="Gamis Abaya Crinkle Airflow Sage Green",
        price_idr=175000.0,
        commission_rate=0.15,
        category="Dress Muslim",
        shop_name="Hijab Chic"
    )

    # 1. walking_lookbook
    style_id, scenes = GoogleFlowPromptEngine.synthesize_choreographed_multiscene_prompts(
        prod, style_name="walking_lookbook", duration_per_scene=10
    )
    assert style_id == "walking_lookbook"
    assert len(scenes) == 2
    assert "steps forward" in scenes[0].lower() or "forward walk" in scenes[0].lower() or "lookbook" in scenes[0].lower()
    assert "360-degree" in scenes[1].lower() or "rotation" in scenes[1].lower()

    # 2. fabric_stretch_test
    style_id2, scenes2 = GoogleFlowPromptEngine.synthesize_choreographed_multiscene_prompts(
        prod, style_name="fabric_stretch_test", duration_per_scene=10
    )
    assert style_id2 == "fabric_stretch_test"
    assert "stretch" in scenes2[0].lower() or "elasticity" in scenes2[0].lower()
    assert "wrinkle recovery" in scenes2[1].lower() or "recovery" in scenes2[1].lower()

    # 3. candid_lifestyle
    style_id3, scenes3 = GoogleFlowPromptEngine.synthesize_choreographed_multiscene_prompts(
        prod, style_name="candid_lifestyle", duration_per_scene=10
    )
    assert style_id3 == "candid_lifestyle"
    assert "mirror-check" in scenes3[0].lower() or "mirror" in scenes3[0].lower()


def test_smart_style_selection():
    """Verifies that the auto selector picks the best choreography based on garment features."""
    from src.motion_planner import VideoChoreographyRegistry

    # Crinkle / Knit -> fabric_stretch_test
    knit_prod = Product(
        product_id="K-01", name="Cardigan Rajut Halus Ribbed", price_idr=99000.0,
        commission_rate=0.1, category="Atasan Rajut", shop_name="Test Boutique"
    )
    assert VideoChoreographyRegistry.select_smart_style(knit_prod) == "fabric_stretch_test"

    # Dress / Abaya -> walking_lookbook
    dress_prod = Product(
        product_id="D-01", name="Gamis Abaya Syari Flowy", price_idr=210000.0,
        commission_rate=0.15, category="Dress Muslim", shop_name="Test Boutique"
    )
    assert VideoChoreographyRegistry.select_smart_style(dress_prod) == "walking_lookbook"

    # Blazer / Set -> layering_styling
    blazer_prod = Product(
        product_id="B-01", name="Blazer Formal Wanita Modern", price_idr=189000.0,
        commission_rate=0.12, category="Outerwear", shop_name="Test Boutique"
    )
    assert VideoChoreographyRegistry.select_smart_style(blazer_prod) == "layering_styling"

    # T-shirt / Kaos -> candid_lifestyle
    tee_prod = Product(
        product_id="T-01", name="Kaos Oversize Lilac Cotton Combed", price_idr=75000.0,
        commission_rate=0.08, category="Kaos Casual", shop_name="Test Boutique"
    )
    assert VideoChoreographyRegistry.select_smart_style(tee_prod) == "candid_lifestyle"


def test_dynamic_garment_parser_diverse_catalog():
    """Verifies that DynamicGarmentParser parses diverse fashion products accurately."""
    from src.motion_planner import DynamicGarmentParser

    # 1. Dress / Gamis
    p_dress = Product(
        product_id="D-02", name="Gamis Abaya Crinkle Airflow Sage Green", price_idr=165000.0,
        commission_rate=0.15, category="Fashion Muslim", shop_name="Test Boutique"
    )
    parsed_dress = DynamicGarmentParser.parse(p_dress)
    assert "sage green" in parsed_dress["color"]
    assert "crinkle airflow" in parsed_dress["material"]
    assert parsed_dress["category"] == "fashion_dress"

    # 2. Outerwear / Blazer
    p_blazer = Product(
        product_id="B-02", name="Blazer Formal Hitam Wanita", price_idr=199000.0,
        commission_rate=0.15, category="Outerwear", shop_name="Test Boutique"
    )
    parsed_blazer = DynamicGarmentParser.parse(p_blazer)
    assert "black" in parsed_blazer["color"]
    assert "notch lapels" in parsed_blazer["collar"]
    assert parsed_blazer["category"] == "fashion_top_outerwear"

    # 3. Pants / Kulot
    p_pants = Product(
        product_id="P-01", name="Celana Kulot Linen Rami Broken White", price_idr=139000.0,
        commission_rate=0.12, category="Bawahan Celana", shop_name="Test Boutique"
    )
    parsed_pants = DynamicGarmentParser.parse(p_pants)
    assert "broken white" in parsed_pants["color"]
    assert "linen rami" in parsed_pants["material"]
    assert parsed_pants["category"] == "fashion_bottoms"



