"""Deterministic 6D product scoring engine and eligibility gates."""

import math
from typing import Any, Dict, List, Tuple
from src.config import (
    MIN_COMMISSION_RATE_GATE,
    MIN_PRICE_IDR_GATE,
    MIN_STOCK_GATE,
    SCORE_THRESHOLD,
)
from src.models import Product, ProductScore

# Indonesian fashion keywords for Niche Fit scoring
HIGH_AFFINITY_FASHION_KEYWORDS = [
    "kemeja", "blouse", "dress", "tunik", "gamis", "rok", "kulot", 
    "cardigan", "outer", "blazer", "oversized", "linen", "katun",
    "jaket", "hoodie", "sweater", "celana", "hijab", "polo", "vest"
]


class ProductScorer:
    """Evaluates affiliate products across 6 documented dimensions and applies strict eligibility gates."""

    SCORING_VERSION = "v1.1"

    @classmethod
    def evaluate_gates(cls, product: Product) -> Tuple[bool, List[str]]:
        """Evaluates strict hard-stop gates. Returns (passed, list_of_reasons)."""
        reasons = []

        if product.stock_available < MIN_STOCK_GATE:
            reasons.append(f"Stock ({product.stock_available}) below minimum threshold ({MIN_STOCK_GATE})")

        if product.commission_rate < MIN_COMMISSION_RATE_GATE:
            reasons.append(
                f"Commission rate ({product.commission_rate * 100:.1f}%) below minimum {MIN_COMMISSION_RATE_GATE * 100:.1f}%"
            )

        if product.price_idr < MIN_PRICE_IDR_GATE:
            reasons.append(
                f"Price (Rp {product.price_idr:,.0f}) below minimum margin threshold Rp {MIN_PRICE_IDR_GATE:,.0f}"
            )

        if product.rating is not None and product.rating < 4.0:
            reasons.append(f"Product rating ({product.rating:.1f}) is below minimum acceptable quality 4.0")

        if product.status != "active":
            reasons.append(f"Product status is '{product.status}', not 'active'")

        return (len(reasons) == 0, reasons)

    @classmethod
    def score_commission_attractiveness(cls, product: Product) -> float:
        """C_attr: Evaluates net commission rupiah amount and rate (Weight 0.25)."""
        comm_amount = product.commission_amount_idr
        # Benchmark: Rp 50.000 commission amount = 70 points
        amount_score = min(70.0, (comm_amount / 50000.0) * 70.0)
        # Benchmark: 20% commission rate = 30 points
        rate_score = min(30.0, (product.commission_rate / 0.20) * 30.0)
        return round(amount_score + rate_score, 2)

    @classmethod
    def score_commission_stability(cls, product: Product) -> float:
        """C_stab: Evaluates commission rate stability (Weight 0.20)."""
        # Commission >= 10% is considered stable affiliate range in TikTok ID
        if product.commission_rate >= 0.15:
            return 95.0
        elif product.commission_rate >= 0.10:
            return 80.0
        elif product.commission_rate >= 0.07:
            return 65.0
        else:
            return 50.0

    @classmethod
    def score_sales_velocity(cls, product: Product) -> float:
        """V_sales: Evaluates historical proof of conversion using log scale (Weight 0.20)."""
        if product.sales_count <= 0:
            return 10.0
        # 10,000 sales = 100 score, 1,000 sales = 75 score, 100 sales = 50 score
        log_val = math.log10(product.sales_count + 1)
        score = min(100.0, (log_val / 4.0) * 100.0)
        return round(max(15.0, score), 2)

    @classmethod
    def score_creator_reputation(cls, product: Product) -> Tuple[float, Dict[str, Any]]:
        """R_creator: Evaluates rating and seller reputation without fabricating data (Weight 0.15)."""
        details: Dict[str, Any] = {}
        if product.rating is None:
            # Handle missing data honestly: assign neutral baseline (50.0) and flag as unverified
            details["rating_status"] = "UNVERIFIED_MISSING_DATA"
            details["uncertainty_penalty"] = True
            return 50.0, details

        details["rating_status"] = "VERIFIED"
        details["raw_rating"] = product.rating
        # Scale 4.0 -> 50, 4.5 -> 75, 5.0 -> 100
        score = max(0.0, min(100.0, ((product.rating - 3.5) / 1.5) * 100.0))
        return round(score, 2), details

    @classmethod
    def score_niche_fit(cls, product: Product) -> float:
        """N_fit: Evaluates fashion relevance and viral affinity (Weight 0.10)."""
        name_lower = product.name.lower()
        cat_lower = product.category.lower()

        matches = sum(1 for kw in HIGH_AFFINITY_FASHION_KEYWORDS if kw in name_lower)
        if matches >= 2 or "fashion" in cat_lower:
            return min(100.0, 70.0 + (matches * 15.0))
        elif matches == 1:
            return 75.0
        else:
            return 50.0

    @classmethod
    def score_content_adaptability(cls, product: Product) -> float:
        """A_adapt: Evaluates visual assets and faceless video readiness (Weight 0.10)."""
        score = 50.0
        # More image angles available increases adaptability
        if len(product.image_urls) >= 3:
            score += 30.0
        elif len(product.image_urls) >= 1:
            score += 15.0

        if product.stock_available >= 50:
            score += 20.0
        elif product.stock_available >= 20:
            score += 10.0

        return min(100.0, score)

    @classmethod
    def calculate_score(cls, product: Product) -> ProductScore:
        """Calculates 6D score, checks gates, and returns complete ProductScore."""
        gates_passed, gate_reasons = cls.evaluate_gates(product)

        c_attr = cls.score_commission_attractiveness(product)
        c_stab = cls.score_commission_stability(product)
        v_sales = cls.score_sales_velocity(product)
        r_rep, rep_details = cls.score_creator_reputation(product)
        n_fit = cls.score_niche_fit(product)
        a_adapt = cls.score_content_adaptability(product)

        # Weighted final score
        final_score = round(
            (0.25 * c_attr) +
            (0.20 * c_stab) +
            (0.20 * v_sales) +
            (0.15 * r_rep) +
            (0.10 * n_fit) +
            (0.10 * a_adapt),
            2
        )

        ineligibility_reasons = list(gate_reasons)
        if final_score < SCORE_THRESHOLD:
            ineligibility_reasons.append(
                f"Final score ({final_score:.1f}) is below recommendation threshold ({SCORE_THRESHOLD:.1f})"
            )

        is_eligible = gates_passed and (final_score >= SCORE_THRESHOLD)

        breakdown = {
            "formula": "0.25*C_attr + 0.20*C_stab + 0.20*V_sales + 0.15*R_rep + 0.10*N_fit + 0.10*A_adapt",
            "weights": {"c_attr": 0.25, "c_stab": 0.20, "v_sales": 0.20, "r_rep": 0.15, "n_fit": 0.10, "a_adapt": 0.10},
            "components": {
                "commission_attractiveness": c_attr,
                "commission_stability": c_stab,
                "sales_velocity": v_sales,
                "creator_reputation": r_rep,
                "niche_fit": n_fit,
                "content_adaptability": a_adapt
            },
            "reputation_details": rep_details,
            "gate_evaluation": {
                "gates_passed": gates_passed,
                "gate_reasons": gate_reasons
            }
        }

        return ProductScore(
            product_id=product.id,
            commission_attractiveness=c_attr,
            commission_stability=c_stab,
            sales_velocity=v_sales,
            creator_reputation=r_rep,
            niche_fit=n_fit,
            content_adaptability=a_adapt,
            final_score=final_score,
            is_eligible=is_eligible,
            ineligibility_reasons=ineligibility_reasons,
            score_breakdown=breakdown,
            scoring_version=cls.SCORING_VERSION
        )
