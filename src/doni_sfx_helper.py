"""DoniesDaily Dynamic SFX Helper — Milo Sound FX Integration.
Provides easy programmatic access to curated viral sound effects for DoniesDaily videos.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

SFX_DIR = Path("/home/ubuntu/apps/ugc-lemonaru/assets/audio/sfx")
CATALOG_PATH = SFX_DIR / "sfx_catalog.json"


def get_sfx_catalog() -> List[Dict[str, Any]]:
    """Loads all available sound effects from the master catalog."""
    if not CATALOG_PATH.exists():
        return []
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_sfx_by_id(sfx_id: str) -> Optional[Path]:
    """Retrieves path to an SFX file by ID or prefix (e.g. 'vine_boom', 'taco_bell')."""
    catalog = get_sfx_catalog()
    for item in catalog:
        if sfx_id in item["id"] or sfx_id in item["filename"]:
            path = Path(item["filepath"])
            if path.exists():
                return path
    return None


def list_sfx_summary() -> str:
    """Returns a formatted markdown summary of all registered sound effects."""
    catalog = get_sfx_catalog()
    lines = ["| ID | File | Durasi | Label | Rekomendasi Momen |", "| :--- | :--- | :---: | :--- | :--- |"]
    for c in catalog:
        lines.append(f"| `{c['id']}` | `{c['filename']}` | {c['duration_sec']}s | **{c['label']}** | {c['use_case']} |")
    return "\n".join(lines)


if __name__ == "__main__":
    print(list_sfx_summary())
