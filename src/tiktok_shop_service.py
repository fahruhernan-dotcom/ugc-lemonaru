"""TikTok Shop Open Platform & Creator Affiliate API Service for Velora AI.
Supports:
1. OAuth URL generation (Seller & Creator Affiliate)
2. Token exchange and refresh handling
3. Shop / Creator profile discovery
4. Automatic Showcase product management
"""

import json
import logging
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional

from src.config import (
    ROOT_DIR,
    TIKTOK_SHOP_APP_KEY,
    TIKTOK_SHOP_APP_SECRET,
    TIKTOK_SHOP_REDIRECT_URI
)

logger = logging.getLogger("tiktok_shop_service")

TOKENS_FILE = ROOT_DIR / "cookies" / "tiktok_shop_tokens.json"
TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)


class TikTokShopService:
    """Client for TikTok Shop Open Platform & Creator Affiliate APIs."""

    def __init__(
        self,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ):
        self.app_key = app_key or TIKTOK_SHOP_APP_KEY
        self.app_secret = app_secret or TIKTOK_SHOP_APP_SECRET
        self.redirect_uri = redirect_uri or TIKTOK_SHOP_REDIRECT_URI
        self.base_url = "https://open-api.tiktokglobalshop.com"
        self.auth_base_url = "https://auth.tiktok-shops.com"

    def get_creator_auth_url(self, state: str = "velora_auth") -> str:
        """Returns the Creator Affiliate OAuth URL (shop.tiktok.com/alliance/creator/auth)."""
        params = {
            "app_key": self.app_key,
            "state": state
        }
        return f"https://shop.tiktok.com/alliance/creator/auth?{urllib.parse.urlencode(params)}"

    def get_seller_auth_url(self, service_id: Optional[str] = None) -> str:
        """Returns the Seller Authorization URL for ROW / Southeast Asia / Indonesia."""
        sid = service_id or self.app_key
        params = {
            "service_id": sid
        }
        return f"https://services.tiktokshop.com/open/authorize?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, auth_code: str) -> Dict[str, Any]:
        """Exchanges authorization code for access_token and refresh_token."""
        url = f"{self.auth_base_url}/api/v2/token/get"
        params = {
            "app_key": self.app_key,
            "app_secret": self.app_secret,
            "auth_code": auth_code.strip(),
            "grant_type": "authorized_code"
        }
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        logger.info("Exchanging auth_code with TikTok Shop Token API...")

        req = urllib.request.Request(
            full_url,
            method="GET",
            headers={
                "User-Agent": "Velora-AI-Studio/1.0",
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") == 0 and "data" in data:
                    self.save_tokens(data["data"])
                    logger.info("Tokens successfully retrieved and stored!")
                    return data["data"]
                else:
                    err_msg = data.get("message", "Unknown error")
                    logger.error("Token exchange failed: %s (code: %s)", err_msg, data.get("code"))
                    return data
        except urllib.error.HTTPError as he:
            body = he.read().decode("utf-8") if hasattr(he, "read") else ""
            logger.error("HTTP error during token exchange: %s %s - %s", he.code, he.reason, body)
            return {"code": he.code, "message": str(he), "error_body": body}
        except Exception as e:
            logger.error("Exception during token exchange: %s", e)
            return {"code": -1, "message": str(e)}

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refreshes an expired access_token using refresh_token."""
        tokens = self.load_tokens()
        if not tokens or "refresh_token" not in tokens:
            return {"code": -1, "message": "No refresh_token found in storage."}

        url = f"{self.auth_base_url}/api/v2/token/refresh"
        params = {
            "app_key": self.app_key,
            "app_secret": self.app_secret,
            "refresh_token": tokens["refresh_token"],
            "grant_type": "refresh_token"
        }
        full_url = f"{url}?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(
            full_url,
            method="GET",
            headers={
                "User-Agent": "Velora-AI-Studio/1.0",
                "Accept": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") == 0 and "data" in data:
                    self.save_tokens(data["data"])
                    logger.info("Access token successfully refreshed!")
                    return data["data"]
                return data
        except Exception as e:
            logger.error("Error refreshing token: %s", e)
            return {"code": -1, "message": str(e)}

    def save_tokens(self, token_data: Dict[str, Any]) -> None:
        """Persists token data locally on Drive D."""
        TOKENS_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
        logger.info("Saved TikTok Shop tokens to: %s", TOKENS_FILE)

    def load_tokens(self) -> Optional[Dict[str, Any]]:
        """Loads saved tokens from Drive D if present."""
        if TOKENS_FILE.exists():
            try:
                return json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    def get_access_token(self) -> Optional[str]:
        """Returns the current access token string."""
        tokens = self.load_tokens()
        if tokens:
            return tokens.get("access_token")
        return None

    def generate_signature(
        self,
        path: str,
        query_params: Dict[str, Any],
        body_str: Optional[str] = None
    ) -> str:
        """Calculates TikTok Shop HMAC-SHA256 signature according to official spec:
        1. Extract query params excluding 'sign' and 'access_token'.
        2. Sort params alphabetically by key.
        3. Concatenate key+value without separator.
        4. Prepend path.
        5. Append raw body string (if present).
        6. Wrap with app_secret at both ends: {secret}{path}{kv}{body}{secret}
        7. HMAC-SHA256 hash using app_secret as key.
        """
        import hashlib
        import hmac

        # Filter out sign and access_token
        filtered_params = {
            k: v for k, v in query_params.items()
            if k not in ("sign", "access_token")
        }
        # Sort by key ASCII
        sorted_keys = sorted(filtered_params.keys())
        concat_params = "".join(f"{k}{filtered_params[k]}" for k in sorted_keys)

        body_part = body_str if body_str else ""
        sign_string = f"{self.app_secret}{path}{concat_params}{body_part}{self.app_secret}"

        signature = hmac.new(
            self.app_secret.encode("utf-8"),
            sign_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return signature

    def request(
        self,
        method: str,
        path: str,
        query_params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        shop_cipher: Optional[str] = None
    ) -> Dict[str, Any]:
        """Makes an authenticated and signed API call to TikTok Shop OpenAPI."""
        import time

        params = dict(query_params or {})
        params["app_key"] = self.app_key
        params["timestamp"] = int(time.time())
        if shop_cipher:
            params["shop_cipher"] = shop_cipher

        body_str = json.dumps(body) if body is not None else None

        # Sign request
        params["sign"] = self.generate_signature(path, params, body_str)

        full_url = f"{self.base_url}{path}?{urllib.parse.urlencode(params)}"
        headers = {
            "User-Agent": "Velora-AI-Studio/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        access_token = self.get_access_token()
        if access_token:
            headers["x-tts-access-token"] = access_token

        req_data = body_str.encode("utf-8") if body_str else None
        req = urllib.request.Request(
            full_url,
            data=req_data,
            headers=headers,
            method=method.upper()
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8") if hasattr(he, "read") else ""
            logger.error("HTTP error %s %s on %s: %s", he.code, he.reason, path, err_body)
            try:
                return json.loads(err_body)
            except Exception:
                return {"code": he.code, "message": str(he), "error_body": err_body}
        except Exception as e:
            logger.error("Request failed on %s: %s", path, e)
            return {"code": -1, "message": str(e)}

    def get_authorized_shops(self) -> Dict[str, Any]:
        """Calls GET /authorization/202309/shops to list authorized seller shops."""
        return self.request("GET", "/authorization/202309/shops")

    def get_creator_profile(self) -> Dict[str, Any]:
        """Calls GET /affiliate_creator/202405/profiles to get creator affiliate profile."""
        return self.request("GET", "/affiliate_creator/202405/profiles")

    def get_showcase_products(self, page_size: int = 20, page_token: str = "") -> Dict[str, Any]:
        """Calls GET /affiliate_creator/202405/showcases/products to list products in Showcase."""
        query: Dict[str, Any] = {"page_size": page_size, "origin": "SHOWCASE"}
        if page_token:
            query["page_token"] = page_token
        return self.request("GET", "/affiliate_creator/202405/showcases/products", query_params=query)

    def add_to_showcase(self, product_ids: list[str]) -> Dict[str, Any]:
        """Calls POST /affiliate_creator/202405/showcases/products/add to add products to creator Showcase."""
        body = {
            "add_type": "PRODUCT_ID",
            "product_ids": product_ids
        }
        return self.request("POST", "/affiliate_creator/202405/showcases/products/add", body=body)

    def is_authenticated(self) -> bool:
        """Returns True if a valid access token is present."""
        return bool(self.get_access_token())

