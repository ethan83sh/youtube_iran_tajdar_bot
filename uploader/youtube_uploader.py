import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_youtube_service():
    """
    Uses OAuth client secret + stored token to build YouTube API service.
    You must provide client_secret.json and persist token.json (Railway volume).
    """
    client_secret_path = os.environ.get("YT_CLIENT_SECRET_PATH", "client_secret.json")
    token_path = os.environ.get("YT_TOKEN_PATH", "token.json")

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        # First-time auth (do this locally once, then upload token.json to Railway volume)
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(
    file_path: str,
    title: str,
    description: str,
    privacy_status: str = "public",
):
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

    return response  # includes uploaded video id
