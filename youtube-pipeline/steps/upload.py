"""
Step 6: YouTube 自動アップロード (YouTube Data API v3)
動画・サムネイル・メタデータを YouTube にアップロードする。
"""

import logging
import os
import pickle
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))

# スコープ
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


# ---------------------------------------------------------------------------
# 認証
# ---------------------------------------------------------------------------

def get_authenticated_service(credentials_path: str, token_path: str):
    """OAuth 2.0 認証を行い YouTube サービスオブジェクトを返す"""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None

    # 既存トークンがあれば読み込む
    if Path(token_path).exists():
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    # トークンが無効・期限切れなら更新または再認証
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(credentials_path).exists():
                raise FileNotFoundError(
                    f"YouTube OAuth 認証情報が見つかりません: {credentials_path}\n"
                    "Google Cloud Console から OAuth 2.0 クライアント ID をダウンロードして "
                    f"{credentials_path} に配置してください。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # トークンを保存
        Path(token_path).parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


# ---------------------------------------------------------------------------
# アップロード
# ---------------------------------------------------------------------------

def upload_video(
    youtube,
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    category_id: str,
    privacy: str,
    publish_at: str | None,
) -> str:
    """動画をアップロードして動画 ID を返す"""
    from googleapiclient.http import MediaFileUpload

    # 予約投稿の場合は privacy を "private" に設定
    if publish_at:
        status = {
            "privacyStatus": "private",
            "publishAt": publish_at,
        }
    else:
        status = {"privacyStatus": privacy}

    body = {
        "snippet": {
            "title": title[:100],  # YouTube タイトル上限
            "description": description[:5000],
            "tags": tags[:500],  # YouTube タグ上限
            "categoryId": category_id,
            "defaultLanguage": "ja",
        },
        "status": status,
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10MB チャンク
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    video_id = None
    response = None
    logger.info(f"動画アップロード開始: {video_path.name}")

    while response is None:
        status_obj, response = request.next_chunk()
        if status_obj:
            progress = int(status_obj.progress() * 100)
            logger.info(f"アップロード進捗: {progress}%")

    video_id = response["id"]
    logger.info(f"アップロード完了: https://youtu.be/{video_id}")
    return video_id


def upload_thumbnail(youtube, video_id: str, thumbnail_path: Path):
    """サムネイルをアップロードする"""
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(
        str(thumbnail_path),
        mimetype="image/jpeg",
    )
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=media,
    ).execute()
    logger.info(f"サムネイルアップロード完了: {thumbnail_path.name}")


def add_to_playlist(youtube, video_id: str, playlist_id: str):
    """動画をプレイリストに追加する"""
    if not playlist_id:
        return
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        },
    ).execute()
    logger.info(f"プレイリスト追加完了: {playlist_id}")


def build_publish_at(days_ahead: int, publish_time: str) -> str:
    """予約公開日時 (RFC 3339) を生成"""
    target_date = datetime.now(JST) + timedelta(days=days_ahead)
    h, m, s = publish_time.split(":")
    publish_dt = target_date.replace(
        hour=int(h), minute=int(m), second=int(s), microsecond=0
    )
    # UTC に変換して RFC 3339 形式
    publish_utc = publish_dt.astimezone(timezone.utc)
    return publish_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")


# ---------------------------------------------------------------------------
# メイン関数
# ---------------------------------------------------------------------------

def run(
    script_data: dict,
    video_path: Path,
    thumbnail_path: Path,
    cfg: dict[str, Any],
) -> dict:
    """
    YouTube に動画をアップロードし、結果を返す。

    Args:
        script_data: script.py が返した台本データ
        video_path: video.py が返した動画ファイルパス
        thumbnail_path: thumbnail.py が返したサムネイルパス
        cfg: config.yaml の全体設定

    Returns:
        {"video_id": "...", "url": "...", "publish_at": "..."}
    """
    upload_cfg = cfg["upload"]
    channel_cfg = cfg["channel"]

    # dry_run モード
    if cfg["pipeline"]["dry_run"]:
        logger.info("[DRY RUN] アップロードをスキップします")
        return {"video_id": "dry_run", "url": "https://youtu.be/dry_run", "publish_at": None}

    # メタデータ
    title = script_data.get("video_title", "untitled")
    description = script_data.get("video_description", "")
    tags = script_data.get("tags", []) + channel_cfg.get("default_tags", [])
    tags = list(dict.fromkeys(tags))  # 重複除去

    # 説明欄にチャンネル共通フッターを追加
    footer = "\n\n---\n📢 チャンネル登録で最新の睡眠情報をお届けします！\n#睡眠 #快眠 #不眠症"
    description = description + footer

    # 予約投稿設定
    publish_at = None
    schedule_cfg = upload_cfg.get("schedule", {})
    if schedule_cfg.get("enabled", False):
        publish_at = build_publish_at(
            days_ahead=schedule_cfg.get("days_ahead", 1),
            publish_time=schedule_cfg.get("publish_time", "19:00:00"),
        )
        logger.info(f"予約公開: {publish_at}")

    # 認証
    youtube = get_authenticated_service(
        credentials_path=upload_cfg["credentials_path"],
        token_path=upload_cfg["token_path"],
    )

    # 動画アップロード
    video_id = upload_video(
        youtube=youtube,
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        category_id=channel_cfg.get("category_id", "27"),
        privacy=upload_cfg.get("privacy", "private"),
        publish_at=publish_at,
    )

    # サムネイルアップロード
    if thumbnail_path.exists():
        upload_thumbnail(youtube, video_id, thumbnail_path)

    # プレイリスト追加
    playlist_id = upload_cfg.get("playlist_id", "")
    if playlist_id:
        add_to_playlist(youtube, video_id, playlist_id)

    result = {
        "video_id": video_id,
        "url": f"https://youtu.be/{video_id}",
        "publish_at": publish_at,
        "title": title,
    }
    logger.info(f"アップロード結果: {result}")
    return result
