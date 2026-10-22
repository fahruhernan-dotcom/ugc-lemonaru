"""Repository layer for Velora AI.
Provides unified access to Supabase PostgreSQL when credentials exist,
with transparent local SQLite/JSON fallback for offline testing and development.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.config import DATA_DIR, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL, has_supabase_credentials
from src.models import ContentBrief, Product, ProductMedia, ProductScore, UgcGeneration, WorkflowEvent

logger = logging.getLogger("velora.repository")


class BaseRepository(ABC):
    """Abstract interface for all persistence operations."""

    @abstractmethod
    def save_products(self, products: List[Product]) -> int:
        pass

    @abstractmethod
    def get_product(self, product_id_or_uuid: str) -> Optional[Product]:
        pass

    @abstractmethod
    def list_products(self) -> List[Product]:
        pass

    @abstractmethod
    def save_product_score(self, score: ProductScore) -> ProductScore:
        pass

    @abstractmethod
    def get_product_score(self, product_id: str) -> Optional[ProductScore]:
        pass

    @abstractmethod
    def list_product_scores(self) -> List[ProductScore]:
        pass

    @abstractmethod
    def list_eligible_products(self) -> List[Tuple[Product, ProductScore]]:
        pass

    @abstractmethod
    def save_content_brief(self, brief: ContentBrief) -> ContentBrief:
        pass

    @abstractmethod
    def get_content_brief(self, brief_id: str) -> Optional[ContentBrief]:
        pass

    @abstractmethod
    def list_content_briefs(self) -> List[ContentBrief]:
        pass

    @abstractmethod
    def save_product_media(self, media: ProductMedia) -> ProductMedia:
        pass

    @abstractmethod
    def list_product_media(self, product_id: str) -> List[ProductMedia]:
        pass

    @abstractmethod
    def save_ugc_generation(self, gen: UgcGeneration) -> UgcGeneration:
        pass

    @abstractmethod
    def get_ugc_generation(self, gen_id: str) -> Optional[UgcGeneration]:
        pass

    @abstractmethod
    def list_ugc_generations(self, product_id: Optional[str] = None) -> List[UgcGeneration]:
        pass

    @abstractmethod
    def record_event(self, event: WorkflowEvent) -> WorkflowEvent:
        pass


class LocalRepository(BaseRepository):
    """File-backed local persistence store for offline mode and tests."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or (DATA_DIR / "velora_store.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Dict[str, Any]] = {
            "products": {},
            "scores": {},
            "briefs": {},
            "media": {},
            "generations": {},
            "events": {}
        }
        self._load()

    def _load(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for k in ["products", "scores", "briefs", "media", "generations", "events"]:
                        if k in loaded:
                            self._data[k] = loaded[k]
            except Exception as e:
                logger.warning(f"Failed to load local store: {e}. Initializing clean state.")

    def _save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, default=str)

    def save_products(self, products: List[Product]) -> int:
        count = 0
        for p in products:
            self._data["products"][p.id] = p.model_dump()
            count += 1
        self._save()
        return count

    def get_product(self, product_id_or_uuid: str) -> Optional[Product]:
        # Check by id (uuid)
        if product_id_or_uuid in self._data["products"]:
            return Product(**self._data["products"][product_id_or_uuid])
        # Check by product_id (string external id)
        for p_dict in self._data["products"].values():
            if p_dict.get("product_id") == product_id_or_uuid:
                return Product(**p_dict)
        return None

    def list_products(self) -> List[Product]:
        return [Product(**p) for p in self._data["products"].values()]

    def save_product_score(self, score: ProductScore) -> ProductScore:
        self._data["scores"][score.id] = score.model_dump()
        self._save()
        return score

    def get_product_score(self, product_id: str) -> Optional[ProductScore]:
        prod = self.get_product(product_id)
        match_ids = {product_id}
        if prod:
            match_ids.update({prod.id, prod.product_id})
        for s_dict in self._data["scores"].values():
            if s_dict.get("product_id") in match_ids:
                return ProductScore(**s_dict)
        return None

    def list_product_scores(self) -> List[ProductScore]:
        return [ProductScore(**s) for s in self._data["scores"].values()]

    def list_eligible_products(self) -> List[Tuple[Product, ProductScore]]:
        eligible: List[Tuple[Product, ProductScore]] = []
        for s_dict in self._data["scores"].values():
            score = ProductScore(**s_dict)
            if score.is_eligible:
                prod = self.get_product(score.product_id)
                if prod:
                    eligible.append((prod, score))
        eligible.sort(key=lambda x: x[1].final_score, reverse=True)
        return eligible

    def save_content_brief(self, brief: ContentBrief) -> ContentBrief:
        self._data["briefs"][brief.id] = brief.model_dump()
        self._save()
        return brief

    def get_content_brief(self, brief_id: str) -> Optional[ContentBrief]:
        if brief_id in self._data["briefs"]:
            return ContentBrief(**self._data["briefs"][brief_id])
        return None

    def list_content_briefs(self) -> List[ContentBrief]:
        return [ContentBrief(**b) for b in self._data["briefs"].values()]

    def save_product_media(self, media: ProductMedia) -> ProductMedia:
        self._data["media"][media.id] = media.model_dump()
        self._save()
        return media

    def list_product_media(self, product_id: str) -> List[ProductMedia]:
        prod = self.get_product(product_id)
        match_ids = {product_id}
        if prod:
            match_ids.update({prod.id, prod.product_id})
        results = []
        for m_dict in self._data["media"].values():
            if m_dict.get("product_id") in match_ids:
                results.append(ProductMedia(**m_dict))
        return results

    def save_ugc_generation(self, gen: UgcGeneration) -> UgcGeneration:
        self._data["generations"][gen.id] = gen.model_dump()
        self._save()
        return gen

    def get_ugc_generation(self, gen_id: str) -> Optional[UgcGeneration]:
        if gen_id in self._data["generations"]:
            return UgcGeneration(**self._data["generations"][gen_id])
        return None

    def list_ugc_generations(self, product_id: Optional[str] = None) -> List[UgcGeneration]:
        match_ids = None
        if product_id is not None:
            prod = self.get_product(product_id)
            match_ids = {product_id}
            if prod:
                match_ids.update({prod.id, prod.product_id})
        results = []
        for g_dict in self._data["generations"].values():
            if match_ids is None or g_dict.get("product_id") in match_ids:
                results.append(UgcGeneration(**g_dict))
        return results

    def record_event(self, event: WorkflowEvent) -> WorkflowEvent:
        self._data["events"][event.id] = event.model_dump()
        self._save()
        return event


class SupabaseRepository(BaseRepository):
    """Production PostgreSQL persistence via Supabase client with local fallback."""

    def __init__(self):
        try:
            from supabase import create_client, Client
            key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
            self.client: Client = create_client(SUPABASE_URL, key)
            self._local_fallback = LocalRepository()
            logger.info("Connected to remote Supabase instance.")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    def save_products(self, products: List[Product]) -> int:
        if not products:
            return 0
        try:
            payload = []
            for p in products:
                d = p.model_dump()
                d.pop("commission_amount_idr", None)  # Generated ALWAYS in PostgreSQL
                payload.append(d)
            res = self.client.table("affiliate_products").upsert(payload, on_conflict="product_id").execute()
            self._local_fallback.save_products(products)
            return len(res.data) if res.data else len(products)
        except Exception as e:
            logger.warning("Supabase save_products failed (%s), using local store.", e)
            return self._local_fallback.save_products(products)


    def get_product(self, product_id_or_uuid: str) -> Optional[Product]:
        try:
            import uuid as _uuid
            is_uuid = False
            try:
                _uuid.UUID(str(product_id_or_uuid))
                is_uuid = True
            except (ValueError, AttributeError):
                is_uuid = False

            if is_uuid:
                res = self.client.table("affiliate_products").select("*").eq("id", product_id_or_uuid).execute()
                if res.data:
                    return Product(**res.data[0])
            else:
                res2 = self.client.table("affiliate_products").select("*").eq("product_id", product_id_or_uuid).execute()
                if res2.data:
                    return Product(**res2.data[0])
        except Exception as e:
            logger.debug("Supabase get_product failed (%s), checking local store.", e)
        return self._local_fallback.get_product(product_id_or_uuid)


    def list_products(self) -> List[Product]:
        try:
            res = self.client.table("affiliate_products").select("*").order("created_at", desc=True).execute()
            if res.data:
                return [Product(**row) for row in res.data]
        except Exception as e:
            logger.debug("Supabase list_products failed (%s), using local store.", e)
        return self._local_fallback.list_products()

    def save_product_score(self, score: ProductScore) -> ProductScore:
        try:
            payload = score.model_dump()
            self.client.table("product_scores").insert(payload).execute()
        except Exception as e:
            logger.warning("Supabase save_product_score failed (%s), using local store.", e)
        self._local_fallback.save_product_score(score)
        return score

    def _resolve_product_uuid(self, product_id_or_uuid: str) -> Optional[str]:
        import uuid as _uuid
        try:
            _uuid.UUID(str(product_id_or_uuid))
            return str(product_id_or_uuid)
        except (ValueError, AttributeError):
            prod = self.get_product(product_id_or_uuid)
            return prod.id if prod else None

    def get_product_score(self, product_id: str) -> Optional[ProductScore]:
        try:
            p_uuid = self._resolve_product_uuid(product_id)
            if p_uuid:
                res = self.client.table("product_scores").select("*").eq("product_id", p_uuid).order("evaluated_at", desc=True).limit(1).execute()
                if res.data:
                    return ProductScore(**res.data[0])
        except Exception as e:
            logger.debug("Supabase get_product_score failed (%s), checking local store.", e)
        return self._local_fallback.get_product_score(product_id)

    def list_product_scores(self) -> List[ProductScore]:
        try:
            res = self.client.table("product_scores").select("*").order("final_score", desc=True).execute()
            if res.data:
                return [ProductScore(**row) for row in res.data]
        except Exception as e:
            logger.debug("Supabase list_product_scores failed (%s), using local store.", e)
        return self._local_fallback.list_product_scores()

    def list_eligible_products(self) -> List[Tuple[Product, ProductScore]]:
        try:
            res = self.client.table("product_scores").select("*, affiliate_products(*)").eq("is_eligible", True).order("final_score", desc=True).execute()
            if res.data:
                results: List[Tuple[Product, ProductScore]] = []
                for row in res.data:
                    prod_data = row.get("affiliate_products")
                    if prod_data:
                        prod = Product(**prod_data)
                        score_data = {k: v for k, v in row.items() if k != "affiliate_products"}
                        score = ProductScore(**score_data)
                        results.append((prod, score))
                return results
        except Exception as e:
            logger.debug("Supabase list_eligible_products failed (%s), using local store.", e)
        return self._local_fallback.list_eligible_products()

    def save_content_brief(self, brief: ContentBrief) -> ContentBrief:
        try:
            payload = brief.model_dump()
            self.client.table("content_briefs").upsert(payload, on_conflict="id").execute()
        except Exception as e:
            logger.warning("Supabase save_content_brief failed (%s), using local store.", e)
        self._local_fallback.save_content_brief(brief)
        return brief

    def get_content_brief(self, brief_id: str) -> Optional[ContentBrief]:
        try:
            res = self.client.table("content_briefs").select("*").eq("id", brief_id).execute()
            if res.data:
                return ContentBrief(**res.data[0])
        except Exception as e:
            logger.debug("Supabase get_content_brief failed (%s), checking local store.", e)
        return self._local_fallback.get_content_brief(brief_id)

    def list_content_briefs(self) -> List[ContentBrief]:
        try:
            res = self.client.table("content_briefs").select("*").order("created_at", desc=True).execute()
            if res.data:
                return [ContentBrief(**row) for row in res.data]
        except Exception as e:
            logger.debug("Supabase list_content_briefs failed (%s), using local store.", e)
        return self._local_fallback.list_content_briefs()

    def save_product_media(self, media: ProductMedia) -> ProductMedia:
        try:
            payload = media.model_dump()
            self.client.table("product_media").insert(payload).execute()
        except Exception as e:
            logger.warning("Supabase save_product_media failed (%s), using local store.", e)
        self._local_fallback.save_product_media(media)
        return media

    def list_product_media(self, product_id: str) -> List[ProductMedia]:
        try:
            p_uuid = self._resolve_product_uuid(product_id)
            if p_uuid:
                res = self.client.table("product_media").select("*").eq("product_id", p_uuid).execute()
                if res.data:
                    return [ProductMedia(**row) for row in res.data]
        except Exception as e:
            logger.debug("Supabase list_product_media failed (%s), checking local store.", e)
        return self._local_fallback.list_product_media(product_id)

    def save_ugc_generation(self, gen: UgcGeneration) -> UgcGeneration:
        try:
            payload = gen.model_dump()
            self.client.table("ugc_generations").upsert(payload, on_conflict="id").execute()
        except Exception as e:
            logger.warning("Supabase save_ugc_generation failed (%s), using local store.", e)
        self._local_fallback.save_ugc_generation(gen)
        return gen

    def get_ugc_generation(self, gen_id: str) -> Optional[UgcGeneration]:
        try:
            res = self.client.table("ugc_generations").select("*").eq("id", gen_id).execute()
            if res.data:
                return UgcGeneration(**res.data[0])
        except Exception as e:
            logger.debug("Supabase get_ugc_generation failed (%s), checking local store.", e)
        return self._local_fallback.get_ugc_generation(gen_id)

    def list_ugc_generations(self, product_id: Optional[str] = None) -> List[UgcGeneration]:
        try:
            query = self.client.table("ugc_generations").select("*")
            if product_id:
                p_uuid = self._resolve_product_uuid(product_id)
                if p_uuid:
                    query = query.eq("product_id", p_uuid)
                else:
                    return self._local_fallback.list_ugc_generations(product_id)
            res = query.order("created_at", desc=True).execute()
            if res.data:
                return [UgcGeneration(**row) for row in res.data]
        except Exception as e:
            logger.debug("Supabase list_ugc_generations failed (%s), checking local store.", e)
        return self._local_fallback.list_ugc_generations(product_id)

    def record_event(self, event: WorkflowEvent) -> WorkflowEvent:
        try:
            payload = event.model_dump()
            self.client.table("workflow_events").insert(payload).execute()
        except Exception as e:
            logger.warning("Supabase record_event failed (%s), using local store.", e)
        self._local_fallback.record_event(event)
        return event

    def sync_local_to_supabase(self) -> Dict[str, int]:
        """Syncs all records from local fallback store to Supabase PostgreSQL."""
        counts = {"products": 0, "scores": 0, "media": 0, "briefs": 0, "generations": 0}
        local_data = self._local_fallback._load()

        # 1. Sync products
        local_prods = [Product(**p) for p in local_data.get("products", {}).values()]
        if local_prods:
            saved = self.save_products(local_prods)
            counts["products"] = saved

        # 2. Sync scores
        for score_dict in local_data.get("scores", {}).values():
            try:
                self.save_product_score(ProductScore(**score_dict))
                counts["scores"] += 1
            except Exception as e:
                logger.debug("Sync score failed: %s", e)

        # 3. Sync media
        for media_dict in local_data.get("media", {}).values():
            try:
                self.save_product_media(ProductMedia(**media_dict))
                counts["media"] += 1
            except Exception as e:
                logger.debug("Sync media failed: %s", e)

        # 4. Sync briefs
        for brief_dict in local_data.get("briefs", {}).values():
            try:
                self.save_content_brief(ContentBrief(**brief_dict))
                counts["briefs"] += 1
            except Exception as e:
                logger.debug("Sync brief failed: %s", e)

        # 5. Sync generations
        for gen_dict in local_data.get("generations", {}).values():
            try:
                self.save_ugc_generation(UgcGeneration(**gen_dict))
                counts["generations"] += 1
            except Exception as e:
                logger.debug("Sync generation failed: %s", e)

        logger.info("Local-to-Supabase sync complete: %s", counts)
        return counts


def get_repository() -> BaseRepository:
    """Factory: Returns SupabaseRepository if credentials configured, else LocalRepository."""
    if has_supabase_credentials():
        try:
            return SupabaseRepository()
        except Exception as e:
            logger.warning(f"Could not connect to Supabase: {e}. Falling back to LocalRepository.")
            return LocalRepository()
    return LocalRepository()

