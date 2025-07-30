import os
import requests
import json

def main(request):
    FB_TOKEN = os.environ.get("FB_TOKEN")
    BM_ID = os.environ.get("FB_BM_ID")  # Your Facebook Business Manager ID

    if not FB_TOKEN or not BM_ID:
        return {"statusCode": 500, "body": "Missing FB_TOKEN or FB_BM_ID env variable"}

    url = f"https://graph.facebook.com/v19.0/{BM_ID}/owned_pages?fields=name,id&access_token={FB_TOKEN}"
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        pages = data.get("data", [])
        return {"statusCode": 200, "body": json.dumps(pages)}
    return {"statusCode": resp.status_code, "body": resp.text}
