"""OPTIONAL: output/short.mp4 ke YouTube e upload kore.

Shudhu tokhon kaj korbe jokhon apnar Google Cloud project er YouTube API compliance audit pass kora.
Audit charai upload korle video private e lock hoye thake (Google er niyom).
Default privacy = private. Public korte YT_PRIVACY=public secret/env dien.
"""
import json
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

OUT = Path(__file__).parent / "output"


def main():
    meta = json.loads((OUT / "metadata.json").read_text())
    creds = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    yt = build("youtube", "v3", credentials=creds)

    def body(synthetic):
        status = {"privacyStatus": os.environ.get("YT_PRIVACY", "private"),
                  "selfDeclaredMadeForKids": False}
        if synthetic:
            status["containsSyntheticMedia"] = True   # AI-generated disclosure
        return {"snippet": {"title": meta["title"][:100], "description": meta["description"],
                            "tags": meta["tags"], "categoryId": "24"},
                "status": status}

    for synthetic in (True, False):
        try:
            media = MediaFileUpload(str(OUT / "short.mp4"), mimetype="video/mp4", resumable=True)
            req = yt.videos().insert(part="snippet,status", body=body(synthetic), media_body=media)
            resp = None
            while resp is None:
                _, resp = req.next_chunk()
            print("Uploaded: https://youtube.com/shorts/" + resp["id"])
            return
        except HttpError as e:
            if synthetic and e.resp.status == 400:
                continue  # field support na thakle ota chhara abar chesta
            raise


if __name__ == "__main__":
    main()
