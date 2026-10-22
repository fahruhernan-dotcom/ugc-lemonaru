"""Content brief generator for Hermes AI Operator and Velora Content Engine."""

import re
from typing import Any, Dict, List, Optional
from src.models import ContentBrief, Product, ProductScore, ShotItem
from src.dynamic_copywriter import DynamicUgcCopywriter


class BriefGenerator:
    """Generates structured, factually-grounded content briefs for eligible fashion products."""

    @classmethod
    def extract_product_facts(cls, product: Product) -> List[str]:
        """Extracts strictly factual assertions from product metadata without fabricating claims."""
        return DynamicUgcCopywriter.build_content_brief(product).product_facts

    @classmethod
    def generate_brief(cls, product: Product, score: Optional[ProductScore] = None) -> ContentBrief:
        """Constructs an actionable 9:16 video brief optimized for TikTok conversion."""
        brief = DynamicUgcCopywriter.build_content_brief(product)
        if score:
            brief.product_score_id = score.id
        return brief

