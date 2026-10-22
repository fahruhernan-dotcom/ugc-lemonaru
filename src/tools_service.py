"""Executable Tool Service for Hermes AI Operator.
Exposes deterministic pipeline capabilities: ingest, score, select, brief, and package.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.brief_generator import BriefGenerator
from src.ingestion import CatalogIngestor
from src.models import ContentBrief, Product, ProductScore, WorkflowEvent
from src.package_exporter import PackageExporter
from src.repository import BaseRepository, get_repository
from src.scoring import ProductScorer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("velora.tools")


class HermesToolService:
    """Service providing core capabilities to Hermes AI Orchestrator."""

    def __init__(self, repo: Optional[BaseRepository] = None):
        self.repo = repo or get_repository()

    def ingest_catalog(self, csv_file_path: str) -> Dict[str, Any]:
        """Ingests a CSV catalog file, validates, deduplicates, and persists valid products."""
        logger.info(f"Ingesting catalog from: {csv_file_path}")
        p = Path(csv_file_path)
        if not p.exists():
            return {"status": "ERROR", "message": f"File not found: {csv_file_path}"}

        products, stats = CatalogIngestor.ingest_csv(p)
        saved_count = self.repo.save_products(products)

        # Record workflow event
        event = WorkflowEvent(
            event_type="CATALOG_INGESTED",
            aggregate_type="catalog",
            aggregate_id=p.name,
            payload={
                "file_path": str(p),
                "total_rows": stats.total_rows,
                "valid_count": stats.valid_count,
                "saved_count": saved_count,
                "rejected_count": stats.rejected_count,
                "duplicate_count": stats.duplicate_count
            }
        )
        self.repo.record_event(event)

        return {
            "status": "SUCCESS",
            "file": p.name,
            "total_processed": stats.total_rows,
            "valid_imported": len(products),
            "duplicates_resolved": stats.duplicate_count,
            "rejected_records": stats.rejected_count,
            "rejection_sample": stats.rejection_reasons[:3] if stats.rejection_reasons else []
        }

    def score_all_products(self) -> Dict[str, Any]:
        """Calculates deterministic 6D scores and evaluates gates for all stored products."""
        products = self.repo.list_products()
        if not products:
            return {"status": "WARNING", "message": "No products in database to score."}

        scored_count = 0
        eligible_count = 0
        scores_list = []

        for prod in products:
            score = ProductScorer.calculate_score(prod)
            self.repo.save_product_score(score)
            scored_count += 1
            if score.is_eligible:
                eligible_count += 1
            scores_list.append({
                "product_id": prod.product_id,
                "name": prod.name,
                "final_score": score.final_score,
                "is_eligible": score.is_eligible,
                "reasons": score.ineligibility_reasons
            })

        event = WorkflowEvent(
            event_type="PRODUCTS_SCORED",
            aggregate_type="scoring_batch",
            aggregate_id="batch_latest",
            payload={"total_scored": scored_count, "eligible_count": eligible_count}
        )
        self.repo.record_event(event)

        return {
            "status": "SUCCESS",
            "total_scored": scored_count,
            "eligible_count": eligible_count,
            "top_candidates": sorted(scores_list, key=lambda x: x["final_score"], reverse=True)[:5]
        }

    def get_top_eligible_product(self) -> Dict[str, Any]:
        """Returns the highest-scoring eligible product ready for content creation."""
        eligible = self.repo.list_eligible_products()
        if not eligible:
            return {
                "status": "NONE_FOUND",
                "message": "No products passed both hard gates and score threshold (>=70.0)."
            }

        top_prod, top_score = eligible[0]
        return {
            "status": "SUCCESS",
            "product": top_prod.model_dump(),
            "score": top_score.model_dump()
        }

    def create_and_export_brief(self, product_id_or_uuid: str) -> Dict[str, Any]:
        """Generates a complete 9:16 brief and exports a real Ready-to-Publish package."""
        prod = self.repo.get_product(product_id_or_uuid)
        if not prod:
            return {"status": "ERROR", "message": f"Product not found: {product_id_or_uuid}"}

        score = self.repo.get_product_score(prod.id)
        brief = BriefGenerator.generate_brief(prod, score)
        pkg_dir = PackageExporter.export_package(prod, brief, score)

        self.repo.save_content_brief(brief)

        event = WorkflowEvent(
            event_type="BRIEF_AND_PACKAGE_CREATED",
            aggregate_type="content_brief",
            aggregate_id=brief.id,
            payload={
                "product_id": prod.product_id,
                "product_name": prod.name,
                "hook_type": brief.hook_type,
                "package_path": str(pkg_dir)
            }
        )
        self.repo.record_event(event)

        return {
            "status": "SUCCESS",
            "brief_id": brief.id,
            "product_id": prod.product_id,
            "product_name": prod.name,
            "hook_type": brief.hook_type,
            "package_path": str(pkg_dir),
            "publication_status": "UNPUBLISHED_DRAFT",
            "ready_files": [
                "metadata.json",
                "brief.md",
                "caption.txt",
                "compliance_checklist.json",
                "shot_list.json"
            ]
        }

    def run_end_to_end_slice(self, csv_file_path: str) -> Dict[str, Any]:
        """Executes the complete Milestone 0.1 vertical slice: Ingest -> Score -> Select -> Brief -> Package."""
        ingest_res = self.ingest_catalog(csv_file_path)
        if ingest_res.get("status") != "SUCCESS":
            return {"status": "FAILED_AT_INGESTION", "details": ingest_res}

        score_res = self.score_all_products()
        if score_res.get("status") != "SUCCESS":
            return {"status": "FAILED_AT_SCORING", "details": score_res}

        top_res = self.get_top_eligible_product()
        if top_res.get("status") != "SUCCESS":
            return {"status": "NO_ELIGIBLE_PRODUCT", "details": top_res}

        top_prod_id = top_res["product"]["product_id"]
        brief_res = self.create_and_export_brief(top_prod_id)

        return {
            "status": "SUCCESS_VERTICAL_SLICE",
            "ingestion": ingest_res,
            "scoring": score_res,
            "selected_product": {
                "id": top_prod_id,
                "name": top_res["product"]["name"],
                "score": top_res["score"]["final_score"]
            },
            "exported_package": brief_res
        }


def main():
    parser = argparse.ArgumentParser(description="Hermes Tool Service CLI for Velora AI.")
    sub = parser.add_subparsers(dest="command", required=True)

    # Ingest
    p_ingest = sub.add_parser("ingest", help="Ingest CSV catalog")
    p_ingest.add_argument("file_path", help="Path to CSV catalog file")

    # Score
    sub.add_parser("score", help="Score all stored products")

    # Top
    sub.add_parser("top", help="Get top eligible product")

    # Brief
    p_brief = sub.add_parser("brief", help="Generate brief and export package for product")
    p_brief.add_argument("product_id", help="Product ID or UUID")

    # Pipeline
    p_pipe = sub.add_parser("pipeline", help="Run full vertical slice (ingest -> score -> brief -> package)")
    p_pipe.add_argument("file_path", help="Path to CSV catalog file")

    args = parser.parse_args()
    svc = HermesToolService()

    if args.command == "ingest":
        res = svc.ingest_catalog(args.file_path)
    elif args.command == "score":
        res = svc.score_all_products()
    elif args.command == "top":
        res = svc.get_top_eligible_product()
    elif args.command == "brief":
        res = svc.create_and_export_brief(args.product_id)
    elif args.command == "pipeline":
        res = svc.run_end_to_end_slice(args.file_path)
    else:
        res = {"error": f"Unknown command: {args.command}"}

    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
