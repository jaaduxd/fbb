import os
import json
import random
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from moviepy.editor import VideoFileClip

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
GDRIVE_CREDENTIALS_FILE = "gdrive_credentials.json"
INPUT_FOLDER_ID = os.environ.get("GDRIVE_INPUT_FOLDER_ID")  # Put your Drive Input folder id in Vercel env vars
CAPTION_FILE = "caption.json"

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(GDRIVE_CREDENTIALS_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def list_files_in_folder(service, parent_id, media_type):
    media_map = {'photo': ['image/jpeg', 'image/png'],
                 'video': ['video/mp4', 'video/avi', 'video/mov'],
                 'reel': ['video/mp4', 'video/mov']}
    results = service.files().list(q=f"'{parent_id}' in parents and mimeType contains '{media_type[0:5]}'",
                                   fields="files(id, name, mimeType)").execute()
    files = [f for f in results.get('files', []) if f['mimeType'] in media_map[media_type]]
    return files

def download_file(service, file_id, file_name):
    request = service.files().get_media(fileId=file_id)
    with open(file_name, 'wb') as f:
        downloader = googleapiclient.http.MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return file_name

def load_captions():
    if not os.path.exists(CAPTION_FILE):
        return {}
    with open(CAPTION_FILE, "r") as f:
        return json.load(f)

def post_to_facebook(media_type, files, captions, token, page_id):
    for idx, media in enumerate(files):
        caption = captions.get(media_type, [])[idx % len(captions.get(media_type, []))] if captions.get(media_type, []) else ""
        file_name = media['name']
        download_file(service, media['id'], file_name)
        url = ""
        data = {}
        files_up = None

        if media_type == 'photo':
            url = f"https://graph.facebook.com/v23.0/{page_id}/photos"
            files_up = {"source": open(file_name, "rb")}
            if caption:
                data["caption"] = caption
        elif media_type in ['video', 'reel']:
            url = f"https://graph.facebook.com/v23.0/{page_id}/videos"
            files_up = {"source": open(file_name, "rb")}
            if caption:
                data["description"] = caption
            if media_type == 'reel':
                data["is_clip"] = "true"
        data["access_token"] = token
        try:
            resp = requests.post(url, files=files_up, data=data).json()
            print(f"{media_type.upper()} POSTED => {resp}")
        except Exception as e:
            print(e)
        finally:
            files_up["source"].close()
            os.remove(file_name)

def handler(request):
    FB_TOKEN = os.environ.get("FB_TOKEN")
    PAGE_ID = os.environ.get("FB_PAGE_ID")  # Add your page id as env var

    global service
    service = get_drive_service()

    # Google Drive Input folders, you must put correct folder IDs for each type
    FOLDERS = {
        "photo": os.environ.get("GDRIVE_PHOTO_FOLDER_ID"),
        "video": os.environ.get("GDRIVE_VIDEO_FOLDER_ID"),
        "reel": os.environ.get("GDRIVE_REEL_FOLDER_ID"),
    }

    captions = load_captions()
    for media_type, folder_id in FOLDERS.items():
        if folder_id:
            files = list_files_in_folder(service, folder_id, media_type)
            if files:
                post_to_facebook(media_type, files, captions, FB_TOKEN, PAGE_ID)
    return {"statusCode": 200, "body": "Done"}

# entry point for vercel python serverless
def main(request):
    return handler(request)
