import os
import json
import random
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# Google Drive Setup
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
GDRIVE_CREDENTIALS_FILE = "gdrive_credentials.json"

# Caption file (local in project)
CAPTION_FILE = "caption.json"

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(GDRIVE_CREDENTIALS_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    return service

def list_files(service, folder_id):
    # List all files in the folder (no mimeType filtering to keep simple)
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name)",
        pageSize=100
    ).execute()
    return results.get('files', [])

def download_file(service, file_id, file_name):
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    fh.close()
    return file_name

def load_captions():
    if not os.path.exists(CAPTION_FILE):
        print(f"{CAPTION_FILE} file nahi mila. Captions empty rahenge.")
        return {}
    with open(CAPTION_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def post_media_to_facebook(media_type, files, captions, token, page_id):
    for idx, file_meta in enumerate(files):
        caption_list = captions.get(media_type, [])
        caption = caption_list[idx % len(caption_list)] if caption_list else ""
        file_name = file_meta['name']

        # Download file from Drive
        download_file(service, file_meta['id'], file_name)

        post_url = ''
        post_data = {'access_token': token}
        post_files = {"source": open(file_name, "rb")}

        if media_type == 'photo':
            post_url = f"https://graph.facebook.com/v23.0/{page_id}/photos"
            if caption:
                post_data['caption'] = caption
        elif media_type == 'video':
            post_url = f"https://graph.facebook.com/v23.0/{page_id}/videos"
            if caption:
                post_data['description'] = caption
        elif media_type == 'reel':
            post_url = f"https://graph.facebook.com/v23.0/{page_id}/videos"
            post_data['is_clip'] = 'true'
            if caption:
                post_data['description'] = caption
        else:
            print(f"Unknown media type {media_type}, skipping file {file_name}")
            os.remove(file_name)
            continue

        try:
            response = requests.post(post_url, files=post_files, data=post_data)
            result = response.json()
            print(f"Posted {media_type.upper()} '{file_name}': {result}")
        except Exception as e:
            print(f"Error posting {file_name}: {e}")
        finally:
            post_files["source"].close()
            os.remove(file_name)

def handler(request):
    global service
    FB_TOKEN = os.environ.get("FB_TOKEN")
    PAGE_ID = os.environ.get("FB_PAGE_ID")

    if not FB_TOKEN or not PAGE_ID:
        return {"statusCode": 500, "body": "Environment variables FB_TOKEN or FB_PAGE_ID missing"}

    # Setup Drive service
    service = get_drive_service()

    # Folder IDs for media, set as env variables in Vercel dashboard
    FOLDERS = {
        "photo": os.environ.get("GDRIVE_PHOTO_FOLDER_ID"),
        "video": os.environ.get("GDRIVE_VIDEO_FOLDER_ID"),
        "reel": os.environ.get("GDRIVE_REEL_FOLDER_ID")
    }

    captions = load_captions()

    for media_type, folder_id in FOLDERS.items():
        if not folder_id:
            print(f"Folder ID for {media_type} not set. Skipping.")
            continue
        files = list_files(service, folder_id)
        if not files:
            print(f"Koi files nahi mila folder {media_type} me.")
            continue
        post_media_to_facebook(media_type, files, captions, FB_TOKEN, PAGE_ID)

    return {"statusCode": 200, "body": "All media posted successfully"}

# Vercel entrypoint
def main(request):
    return handler(request)
