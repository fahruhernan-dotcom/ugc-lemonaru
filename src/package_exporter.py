"""Ready-to-Publish Package Exporter for Velora AI.
Exports complete content briefs and compliance metadata into ready_to_publish/
Clearly marked as UNPUBLISHED_DRAFT without pretending a live TikTok post exists.
"""

import json
from pathlib import Path
from typing import Optional

from src.config import PACKAGES_DIR, PACKAGES_PENDING_DIR
from src.models import ContentBrief, Product, ProductScore


class PackageExporter:
    """Exports structured content packages ready for human-assisted publishing on TikTok Mobile."""

    @classmethod
    def export_package(
        cls,
        product: Product,
        brief: ContentBrief,
        score: Optional[ProductScore] = None,
        base_dir: Optional[Path] = None
    ) -> Path:
        target_root = base_dir or PACKAGES_PENDING_DIR
        target_root.mkdir(parents=True, exist_ok=True)

        package_slug = f"PKG_{product.product_id}_{brief.id[:8]}"
        pkg_dir = target_root / package_slug
        pkg_dir.mkdir(parents=True, exist_ok=True)

        # 1. metadata.json (Explicitly UNPUBLISHED)
        metadata = {
            "package_id": package_slug,
            "brief_id": brief.id,
            "product_id": product.product_id,
            "pipeline_stage": "READY_FOR_ASSISTED_PUBLISHING",
            "publication_status": "UNPUBLISHED_DRAFT",
            "tiktok_post": {
                "is_published": False,
                "publish_id": None,
                "video_url": None,
                "published_at": None,
                "note": "Awaiting human operator execution in TikTok Mobile app"
            },
            "affiliate_anchor": {
                "status": "NOT_ATTACHED",
                "verified": False,
                "target_product_sku": product.product_id,
                "target_shop_name": product.shop_name,
                "expected_commission_idr": product.commission_amount_idr,
                "note": "Operator will attach yellow cart in official TikTok app"
            },
            "product_summary": {
                "name": product.name,
                "shop_name": product.shop_name,
                "price_idr": product.price_idr,
                "commission_rate": product.commission_rate,
                "stock_available": product.stock_available,
                "rating": product.rating
            },
            "content_summary": {
                "hook_type": brief.hook_type,
                "target_aspect_ratio": brief.target_aspect_ratio,
                "estimated_duration_seconds": brief.estimated_duration_seconds,
                "total_scenes": len(brief.shot_list)
            },
            "evaluation_score": {
                "final_score": score.final_score if score else None,
                "is_eligible": score.is_eligible if score else None
            },
            "created_at": brief.created_at
        }
        with open(pkg_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, default=str)

        # 2. caption.txt (Copy-paste friendly)
        with open(pkg_dir / "caption.txt", "w", encoding="utf-8") as f:
            f.write(brief.caption)

        # 3. compliance_checklist.json (5 Pre-Publish Quality Gates)
        compliance_data = {
            "package_id": package_slug,
            "status": "PENDING_OPERATOR_VERIFICATION",
            "checkpoints": [
                {
                    "step": 1,
                    "name": "commercial_content_disclosure",
                    "description": "Nyalakan toggle 'Pengungkapan Konten Komersial' / Paid Partnership di aplikasi TikTok",
                    "verified": False
                },
                {
                    "step": 2,
                    "name": "ai_generated_content_label",
                    "description": "Nyalakan toggle label 'Konten Buatan AI' (AI-Generated Content) di opsi tambahan postingan",
                    "verified": False
                },
                {
                    "step": 3,
                    "name": "product_claim_accuracy",
                    "description": "Pastikan narasi bebas dari klaim berlebihan / klaim medis yang menyesatkan",
                    "verified": True
                },
                {
                    "step": 4,
                    "name": "asset_usage_rights",
                    "description": "Gunakan audio komersial bebas royalti atau musik dari TikTok Commercial Music Library",
                    "verified": True
                },
                {
                    "step": 5,
                    "name": "exact_product_match",
                    "description": f"Verifikasi keranjang kuning terpasang ke produk: '{product.name}' dari toko '{product.shop_name}'",
                    "verified": False
                }
            ],
            "human_intervention_timing": {
                "package_delivered_at": brief.created_at,
                "operator_completed_at": None,
                "measured_duration_seconds": None
            }
        }
        with open(pkg_dir / "compliance_checklist.json", "w", encoding="utf-8") as f:
            json.dump(compliance_data, f, indent=2)

        # 4. shot_list.json
        with open(pkg_dir / "shot_list.json", "w", encoding="utf-8") as f:
            json.dump([item.model_dump() for item in brief.shot_list], f, indent=2)

        # 5. brief.md (Markdown document for operator reading)
        brief_md = f"""# Content Brief & Production Package: {product.name}
**Package ID:** `{package_slug}` | **Status:** `UNPUBLISHED_DRAFT`  
**Produk:** {product.name} ({product.shop_name})  
**Harga:** Rp {product.price_idr:,.0f} | **Komisi:** Rp {product.commission_amount_idr:,.0f} ({product.commission_rate * 100:.1f}%)

---

## 1. Naskah & Hook
- **Tipe Hook:** `{brief.hook_type}`
- **Hook Kalimat Pertama:**  
  > *"{brief.hook_text}"*
- **Naskah Lengkap (VO):**  
  {brief.script_body}
- **Call to Action (CTA):**  
  {brief.cta_text}

---

## 2. Storyboard & Shot List (9:16 Vertikal)

| Scene | Durasi | Visual & Framing | Gerakan Kamera | Teks di Layar |
|:---:|:---:|:---|:---|:---|
"""
        for item in brief.shot_list:
            brief_md += f"| {item.scene_number} | {item.time_range} | {item.visual_description} | {item.camera_movement} | `{item.on_screen_text}` |\n"

        brief_md += f"""
---

## 3. Fakta Produk Faktual (Terverifikasi Tanpa Halusinasi)
"""
        for fact in brief.product_facts:
            brief_md += f"- {fact}\n"

        brief_md += f"""
---

## 4. Caption & Tagar TikTok
```text
{brief.caption}
```

---

## 5. Instruksi Operator (Assisted Publishing TikTok Mobile)
1. Unduh video dari paket ini ke galeri HP.
2. Buka aplikasi TikTok, pilih video vertikal 9:16 ini.
3. Salin caption dari `caption.txt`.
4. Di halaman posting:
   - Aktifkan toggle **Pengungkapan Konten Komersial**.
   - Aktifkan toggle **Konten Buatan AI**.
   - Tambahkan Tautan Produk (Keranjang Kuning) $\\rightarrow$ cari `{product.name}` dari `{product.shop_name}`.
5. Tekan **Posting** dan catat URL video untuk rekonsiliasi.
"""
        with open(pkg_dir / "brief.md", "w", encoding="utf-8") as f:
            f.write(brief_md)

        # Update brief with export path
        brief.package_export_path = str(pkg_dir)
        return pkg_dir
