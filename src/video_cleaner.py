"""Video Storage Lifecycle Manager & Garbage Cleaner for Velora AI.
Enforces strict folder separation (pending vs posted), automatic retention cleanup
for VPS deployment (3-day posted video retention, 1-day temp clips retention),
and 2 GB emergency storage quota capping with hard security guards.
"""

from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from src.config import (
    PACKAGES_DIR,
    PACKAGES_PENDING_DIR,
    PACKAGES_POSTED_DIR,
    TEMP_DIR,
    FLOW_CLIPS_DIR,
    OUTPUT_DIR,
    MAX_VIDEO_STORAGE_MB,
    RETENTION_POSTED_HOURS,
    RETENTION_TEMP_HOURS,
    ROOT_DIR,
    DATA_DIR
)


class SecurityViolationError(Exception):
    """Raised when an operation attempts to delete or alter files outside allowed directories."""
    pass


class VideoLifecycleManager:
    """Manages the end-to-end lifecycle, isolation, and pruning of video assets."""

    GRACE_PERIOD_MINUTES: int = 15

    @classmethod
    def get_whitelist_dirs(cls) -> List[Path]:
        """Returns the strictly whitelisted directories where cleanup operations are permitted."""
        return [
            PACKAGES_POSTED_DIR.resolve(),
            TEMP_DIR.resolve(),
            FLOW_CLIPS_DIR.resolve(),
            OUTPUT_DIR.resolve(),
        ]

    @classmethod
    def validate_safety(cls, target_path: Union[str, Path]) -> Path:
        """Enforces that target_path resides STRICTLY inside whitelisted video directories.
        Guards against path traversal, deletion of source code, databases, .env, or templates.
        """
        resolved = Path(target_path).resolve()
        
        # Absolute safety check: Never delete project root or critical parents
        if resolved == ROOT_DIR.resolve() or resolved == DATA_DIR.resolve():
            raise SecurityViolationError(f"Fatal safety violation: Target is a root system directory: {resolved}")
        
        # Check against critical assets
        sensitive_keywords = [".git", ".env", "data/tiktok.db", "templates", "src", "tests"]
        resolved_str = str(resolved).lower().replace("\\", "/")
        for keyword in sensitive_keywords:
            if f"/{keyword.lower()}" in resolved_str or resolved_str.endswith(f"/{keyword.lower()}"):
                raise SecurityViolationError(f"Security violation: Target contains sensitive keyword '{keyword}': {resolved}")

        # Must reside strictly within at least one whitelist root
        whitelists = cls.get_whitelist_dirs()
        is_safe = False
        for wl in whitelists:
            try:
                resolved.relative_to(wl)
                is_safe = True
                break
            except ValueError:
                continue

        if not is_safe:
            raise SecurityViolationError(
                f"Security violation: Target '{resolved}' is outside allowed video directories: "
                f"{[str(w) for w in whitelists]}"
            )
        return resolved

    @classmethod
    def is_in_flight(cls, file_or_dir: Path, grace_minutes: Optional[int] = None) -> bool:
        """Determines if a file or directory is actively being written/rendered/uploaded.
        Files modified within the grace period (default 15 mins) or having a lockfile are protected.
        """
        grace = grace_minutes if grace_minutes is not None else cls.GRACE_PERIOD_MINUTES
        if not file_or_dir.exists():
            return False

        # Check lockfile
        lock_file = file_or_dir.with_suffix(file_or_dir.suffix + ".lock") if file_or_dir.is_file() else file_or_dir / ".lock"
        if lock_file.exists():
            return True

        # Check modification age
        mtime = file_or_dir.stat().st_mtime
        age_seconds = time.time() - mtime
        if age_seconds < (grace * 60):
            return True

        return False

    @classmethod
    def mark_as_posted(
        cls,
        package_dir: Union[str, Path],
        status_label: str = "STAGED_AS_DRAFT"
    ) -> Path:
        """Transitions a completed video package from pending to posted state.
        Moves the package to PACKAGES_POSTED_DIR and updates metadata.json with posted_at.
        """
        pkg_path = Path(package_dir).resolve()
        if not pkg_path.exists():
            raise FileNotFoundError(f"Package directory not found: {pkg_path}")

        PACKAGES_POSTED_DIR.mkdir(parents=True, exist_ok=True)
        dest_path = PACKAGES_POSTED_DIR / pkg_path.name

        # If already in posted, simply update metadata
        if pkg_path != dest_path:
            # If destination already exists, remove it first
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.move(str(pkg_path), str(dest_path))

        # Update metadata.json
        meta_file = dest_path / "metadata.json"
        now_iso = datetime.now(timezone.utc).isoformat()
        metadata: Dict[str, Any] = {}
        if meta_file.exists():
            try:
                metadata = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        metadata["pipeline_stage"] = "COMPLETED_AND_POSTED"
        metadata["publication_status"] = status_label
        metadata["posted_at"] = now_iso
        if "tiktok_post" in metadata:
            metadata["tiktok_post"]["is_published"] = (status_label == "PUBLISHED")
            metadata["tiktok_post"]["published_at"] = now_iso

        meta_file.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
        return dest_path

    @classmethod
    def calculate_dir_size_bytes(cls, path: Path) -> int:
        """Calculates recursive total size of a path in bytes."""
        if not path.exists():
            return 0
        if path.is_file():
            return path.stat().st_size
        total = 0
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except (OSError, FileNotFoundError):
                    pass
        return total

    @classmethod
    def get_storage_breakdown(cls) -> Dict[str, Any]:
        """Provides an audit breakdown of disk usage across all video pipelines."""
        # Pending packages: check PACKAGES_PENDING_DIR plus legacy root PACKAGES_DIR
        pending_pkgs = []
        if PACKAGES_PENDING_DIR.exists():
            pending_pkgs.extend([p for p in PACKAGES_PENDING_DIR.iterdir() if p.is_dir()])
        if PACKAGES_DIR.exists():
            for p in PACKAGES_DIR.iterdir():
                if p.is_dir() and p.name not in ["pending", "posted"]:
                    pending_pkgs.append(p)

        posted_pkgs = [p for p in PACKAGES_POSTED_DIR.iterdir() if p.is_dir()] if PACKAGES_POSTED_DIR.exists() else []

        pending_bytes = sum(cls.calculate_dir_size_bytes(p) for p in pending_pkgs)
        posted_bytes = sum(cls.calculate_dir_size_bytes(p) for p in posted_pkgs)
        temp_bytes = cls.calculate_dir_size_bytes(TEMP_DIR)
        output_bytes = cls.calculate_dir_size_bytes(OUTPUT_DIR)

        total_bytes = pending_bytes + posted_bytes + temp_bytes + output_bytes
        total_mb = total_bytes / (1024 * 1024)

        return {
            "pending": {
                "count": len(pending_pkgs),
                "bytes": pending_bytes,
                "mb": round(pending_bytes / (1024 * 1024), 2),
            },
            "posted": {
                "count": len(posted_pkgs),
                "bytes": posted_bytes,
                "mb": round(posted_bytes / (1024 * 1024), 2),
            },
            "temp": {
                "bytes": temp_bytes,
                "mb": round(temp_bytes / (1024 * 1024), 2),
            },
            "output": {
                "bytes": output_bytes,
                "mb": round(output_bytes / (1024 * 1024), 2),
            },
            "total_bytes": total_bytes,
            "total_mb": round(total_mb, 2),
            "max_storage_mb": MAX_VIDEO_STORAGE_MB,
            "usage_percent": round((total_mb / MAX_VIDEO_STORAGE_MB) * 100, 1) if MAX_VIDEO_STORAGE_MB > 0 else 0.0
        }

    @classmethod
    def clean_expired_videos(
        cls,
        dry_run: bool = False,
        max_storage_mb: Optional[float] = None,
        posted_retention_hours: Optional[int] = None,
        temp_retention_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """Cleans expired video garbage according to the 3-day posted retention rule,
        1-day temp retention rule, and 2 GB emergency FIFO storage capping.
        """
        cap_mb = max_storage_mb if max_storage_mb is not None else MAX_VIDEO_STORAGE_MB
        posted_hours = posted_retention_hours if posted_retention_hours is not None else RETENTION_POSTED_HOURS
        temp_hours = temp_retention_hours if temp_retention_hours is not None else RETENTION_TEMP_HOURS

        now = time.time()
        posted_cutoff = now - (posted_hours * 3600)
        temp_cutoff = now - (temp_hours * 3600)
        output_cutoff = now - (posted_hours * 3600)

        deleted_posted_pkgs: List[str] = []
        deleted_temp_files: List[str] = []
        deleted_output_files: List[str] = []
        reclaimed_bytes = 0

        # --- Rule 1: Clean Expired Posted Packages (> 72 Hours) ---
        if PACKAGES_POSTED_DIR.exists():
            for pkg_dir in sorted(PACKAGES_POSTED_DIR.iterdir()):
                if not pkg_dir.is_dir():
                    continue
                if cls.is_in_flight(pkg_dir):
                    continue

                # Determine age from metadata.json posted_at or mtime
                pkg_time = pkg_dir.stat().st_mtime
                meta_file = pkg_dir / "metadata.json"
                if meta_file.exists():
                    try:
                        meta = json.loads(meta_file.read_text(encoding="utf-8"))
                        posted_at_str = meta.get("posted_at")
                        if posted_at_str:
                            dt = datetime.fromisoformat(posted_at_str)
                            pkg_time = dt.timestamp()
                    except Exception:
                        pass

                if pkg_time < posted_cutoff:
                    cls.validate_safety(pkg_dir)
                    sz = cls.calculate_dir_size_bytes(pkg_dir)
                    reclaimed_bytes += sz
                    deleted_posted_pkgs.append(pkg_dir.name)
                    if not dry_run:
                        shutil.rmtree(pkg_dir)

        # --- Rule 2: Clean Stale Temp Clips & Files (> 24 Hours) ---
        if TEMP_DIR.exists():
            for item in sorted(TEMP_DIR.rglob("*")):
                if not item.is_file():
                    continue
                if cls.is_in_flight(item):
                    continue

                if item.stat().st_mtime < temp_cutoff:
                    try:
                        cls.validate_safety(item)
                        sz = item.stat().st_size
                        reclaimed_bytes += sz
                        deleted_temp_files.append(str(item.relative_to(TEMP_DIR)))
                        if not dry_run:
                            item.unlink()
                    except (SecurityViolationError, PermissionError):
                        continue

        # --- Rule 3: Clean Debug Screenshots in output/ (> 72 Hours) ---
        if OUTPUT_DIR.exists():
            for item in sorted(OUTPUT_DIR.iterdir()):
                if not item.is_file():
                    continue
                if cls.is_in_flight(item):
                    continue

                # Only prune screenshots and debug video snippets
                if item.suffix.lower() in [".png", ".jpg", ".mp4", ".log"]:
                    if item.stat().st_mtime < output_cutoff:
                        try:
                            cls.validate_safety(item)
                            sz = item.stat().st_size
                            reclaimed_bytes += sz
                            deleted_output_files.append(item.name)
                            if not dry_run:
                                item.unlink()
                        except (SecurityViolationError, PermissionError):
                            continue

        # --- Rule 4: Emergency Storage Cap (FIFO on remaining posted packages) ---
        breakdown = cls.get_storage_breakdown()
        current_total_mb = breakdown["total_mb"] - (reclaimed_bytes / (1024 * 1024) if dry_run else 0.0)

        if current_total_mb > cap_mb and PACKAGES_POSTED_DIR.exists():
            remaining_posted = [p for p in PACKAGES_POSTED_DIR.iterdir() if p.is_dir() and p.name not in deleted_posted_pkgs]
            # Sort by oldest mtime first (FIFO)
            remaining_posted.sort(key=lambda p: p.stat().st_mtime)

            for pkg_dir in remaining_posted:
                if current_total_mb <= cap_mb:
                    break
                if cls.is_in_flight(pkg_dir):
                    continue

                cls.validate_safety(pkg_dir)
                sz = cls.calculate_dir_size_bytes(pkg_dir)
                reclaimed_bytes += sz
                current_total_mb -= (sz / (1024 * 1024))
                deleted_posted_pkgs.append(f"{pkg_dir.name} (FIFO_CAP)")
                if not dry_run:
                    shutil.rmtree(pkg_dir)

        final_breakdown = cls.get_storage_breakdown()
        return {
            "dry_run": dry_run,
            "reclaimed_bytes": reclaimed_bytes,
            "reclaimed_mb": round(reclaimed_bytes / (1024 * 1024), 2),
            "deleted_posted_packages": deleted_posted_pkgs,
            "deleted_temp_files_count": len(deleted_temp_files),
            "deleted_output_files_count": len(deleted_output_files),
            "storage_after_mb": final_breakdown["total_mb"],
            "usage_percent": final_breakdown["usage_percent"]
        }
