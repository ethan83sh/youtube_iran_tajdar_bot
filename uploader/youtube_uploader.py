import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_youtube_service():
    token_path = os.environ.get("YT_TOKEN_PATH", "/tmp/token.json")

    if not os.path.exists(token_path):
        raise RuntimeError(
            "token.json پیدا نشد. باید YT_TOKEN_JSON را در Railway Variables ست کنی "
            "یا فایل token.json را در مسیر YT_TOKEN_PATH بسازی."
        )

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    return build("youtube", "v3", credentials=creds)


def upload_video(file_path: str, title: str, description: str, privacy_status: str = "public"):
    youtube = get_youtube_service()

    body = {
        "snippet": {"title": title, "description": description},
        "status": {"privacyStatus": privacy_status},
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()

    return response
