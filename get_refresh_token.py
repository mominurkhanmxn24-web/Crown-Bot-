"""ONE-TIME (apnar laptop e): YouTube upload er jonno refresh token ber kore.

1. Google Cloud Console -> new project -> "YouTube Data API v3" enable
2. OAuth consent screen set korun, nijer email ke Test user dien
3. Credentials -> OAuth client ID (Desktop app) -> JSON download -> client_secret.json naam e ei folder e rakhen
4. pip install google-auth-oauthlib   ->   python get_refresh_token.py
5. Je refresh token print hobe oita GitHub Secret YT_REFRESH_TOKEN e dien
   (sathe YT_CLIENT_ID ar YT_CLIENT_SECRET - client_secret.json er bhitor ache)
"""
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json", ["https://www.googleapis.com/auth/youtube.upload"])
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
print("\nYT_REFRESH_TOKEN =", creds.refresh_token)
