"""Unit and integration tests for HermesToolService."""

from pathlib import Path
import pytest
from src.repository import LocalRepository
from src.tools_service import HermesToolService


def test_tool_service_end_to_end_vertical_slice(tmp_path):
    # Set up isolated repository for test run
    test_db_path = tmp_path / "test_store.json"
    repo = LocalRepository(storage_path=test_db_path)
    svc = HermesToolService(repo=repo)

    catalog_path = Path(__file__).resolve().parent.parent / "data" / "sample_fashion_catalog.csv"
    assert catalog_path.exists()

    # 1. Ingestion
    ingest_res = svc.ingest_catalog(str(catalog_path))
    assert ingest_res["status"] == "SUCCESS"
    assert ingest_res["valid_imported"] == 6

    # 2. Scoring
    score_res = svc.score_all_products()
    assert score_res["status"] == "SUCCESS"
    assert score_res["total_scored"] == 6
    assert score_res["eligible_count"] >= 1

    # 3. Top Product
    top_res = svc.get_top_eligible_product()
    assert top_res["status"] == "SUCCESS"
    assert top_res["score"]["is_eligible"] is True
    assert top_res["score"]["final_score"] >= 70.0
    winner_id = top_res["product"]["product_id"]

    # 4. Generate Brief & Export Package
    brief_res = svc.create_and_export_brief(winner_id)
    assert brief_res["status"] == "SUCCESS"
    assert brief_res["publication_status"] == "UNPUBLISHED_DRAFT"
    pkg_path = Path(brief_res["package_path"])
    assert pkg_path.exists()
    assert (pkg_path / "metadata.json").exists()
    assert (pkg_path / "brief.md").exists()
    assert (pkg_path / "caption.txt").exists()
    assert (pkg_path / "compliance_checklist.json").exists()
    assert (pkg_path / "shot_list.json").exists()

    # 5. Full Pipeline convenience method
    pipeline_res = svc.run_end_to_end_slice(str(catalog_path))
    assert pipeline_res["status"] == "SUCCESS_VERTICAL_SLICE"
