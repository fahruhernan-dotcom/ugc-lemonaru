"""YouTube API Official Publisher — Google Data API v3.
Automates video and YouTube Shorts upload directly using OAuth 2.0 credentials.
No browser, no Playwright, no login friction, 100% resilient.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger("youtube_api_publisher")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DEFAULT_OAUTH_PATH = Path("/home/ubuntu/.config/youtube/doniesdaily_oauth.json")


class YouTubeAPIPublisher:
    def __init__(self, oauth_path: Path = DEFAULT_OAUTH_PATH):
        self.oauth_path = oauth_path
        if not self.oauth_path.exists():
            raise FileNotFoundError(f"OAuth config not found at {self.oauth_path}")

        with open(self.oauth_path, "r", encoding="utf-8") as f:
            self.token_data = json.load(f)

        self.creds = Credentials(
            token=self.token_data.get("token"),
            refresh_token=self.token_data.get("refresh_token"),
            token_uri=self.token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=self.token_data.get("client_id"),
            client_secret=self.token_data.get("client_secret"),
            scopes=self.token_data.get("scopes", ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]),
        )

        self._ensure_valid_token()
        self.youtube = build("youtube", "v3", credentials=self.creds)

    def _ensure_valid_token(self):
        """Refreshes token if expired and saves new token to disk. Auto-heals via CDP if refresh_token is revoked."""
        if self.creds.expired or not self.creds.valid:
            logger.info("Access token expired, refreshing with refresh_token...")
            try:
                self.creds.refresh(Request())
                self.token_data["token"] = self.creds.token
                with open(self.oauth_path, "w", encoding="utf-8") as f:
                    json.dump(self.token_data, f, indent=2)
                logger.info("Updated token saved to config.")
            except Exception as e:
                logger.warning(f"Standard token refresh failed ({e}). Running OAuth Auto-Healer via CDP...")
                import subprocess
                subprocess.run([sys.executable, "/home/ubuntu/tools/doni_oauth_auto_healer.py"], check=True)
                with open(self.oauth_path, "r", encoding="utf-8") as f:
                    self.token_data = json.load(f)
                self.creds = Credentials(
                    token=self.token_data.get("token"),
                    refresh_token=self.token_data.get("refresh_token"),
                    token_uri=self.token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                    client_id=self.token_data.get("client_id"),
                    client_secret=self.token_data.get("client_secret"),
                    scopes=self.token_data.get("scopes", ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]),
                )
                logger.info("OAuth Auto-Healer succeeded and reloaded credentials!")

    def upload_short(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        privacy_status: str = "public",  # "public", "unlisted", "private"
        category_id: str = "15",  # 15 = Pets & Animals
    ) -> Dict[str, Any]:
        """Uploads a video to YouTube as a Short/Video via official API."""
        video_file = Path(video_path).resolve()
        if not video_file.exists():
            return {"success": False, "error": f"File not found: {video_file}"}

        self._ensure_valid_token()

        if tags is None:
            tags = ["Shorts", "Kucing", "Cat", "DoniesDaily", "FunFacts"]

        # Ensure #Shorts is in title or description for YouTube Shorts algorithm
        if "#Shorts" not in title and "#shorts" not in title:
            title = f"{title} #Shorts"

        body = {
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": tags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        logger.info(f"Uploading '{video_file.name}' ({video_file.stat().st_size / (1024*1024):.2f} MB)...")
        media = MediaFileUpload(
            str(video_file),
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 2,  # 2MB chunks
        )

        request = self.youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Uploaded {int(status.progress() * 100)}%...")
            except Exception as e:
                if "invalid_grant" in str(e) or "expired or revoked" in str(e):
                    logger.warning(f"OAuth token expired during upload ({e}). Triggering Auto-Healer...")
                    import subprocess
                    subprocess.run([sys.executable, "/home/ubuntu/tools/doni_oauth_auto_healer.py"], check=True)
                    self.__init__(self.oauth_path)
                    # Rebuild service and request
                    request = self.youtube.videos().insert(
                        part="snippet,status",
                        body=body,
                        media_body=media,
                    )
                    status, response = request.next_chunk()
                else:
                    raise e

        video_id = response.get("id")
        short_url = f"https://www.youtube.com/shorts/{video_id}"
        watch_url = f"https://youtu.be/{video_id}"

        logger.info(f"Upload complete! Video ID: {video_id} -> {short_url}")
        return {
            "success": True,
            "video_id": video_id,
            "short_url": short_url,
            "watch_url": watch_url,
            "title": title,
            "privacy_status": privacy_status,
        }

    def set_thumbnail(self, video_id: str, thumbnail_path: str) -> Dict[str, Any]:
        """Sets custom thumbnail for uploaded video via official YouTube Data API v3."""
        thumb_file = Path(thumbnail_path).resolve()
        if not thumb_file.exists():
            return {"success": False, "error": f"Thumbnail not found: {thumb_file}"}

        self._ensure_valid_token()
        logger.info(f"Setting custom thumbnail for video {video_id} from {thumb_file.name}...")
        try:
            media = MediaFileUpload(str(thumb_file), mimetype="image/jpeg", resumable=False)
            request = self.youtube.thumbnails().set(videoId=video_id, media_body=media)
            response = request.execute()
            logger.info(f"Thumbnail uploaded successfully for {video_id}!")
            return {"success": True, "video_id": video_id, "response": response}
        except Exception as e:
            logger.error(f"Failed to set thumbnail: {e}")
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Upload YouTube Shorts via official Data API v3")
    parser.add_argument("--video", required=True, help="Absolute path to MP4 video")
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--desc", default="", help="Video description")
    parser.add_argument("--tags", default="kucing,cat,shorts,anabul,funny cat,fakta kucing,doniesdaily", help="Comma-separated tags")
    parser.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"], help="Privacy status")
    args = parser.parse_args()

    tags_list = [t.strip() for t in args.tags.split(",") if t.strip()]

    pub = YouTubeAPIPublisher()
    res = pub.upload_short(
        video_path=args.video,
        title=args.title,
        description=args.desc,
        tags=tags_list,
        privacy_status=args.privacy
    )
    print(json.dumps(res, indent=2))
    if not res.get("success"):
        sys.exit(1)
