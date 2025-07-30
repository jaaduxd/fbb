import os
import tempfile
import requests
import json

def main(request):
    if request.method != "POST":
        return {"statusCode": 405, "body": "POST required"}

    FB_TOKEN = os.environ.get("FB_TOKEN")
    if not FB_TOKEN:
        return {"statusCode": 500, "body": "Missing FB_TOKEN"}

    try:
        # Parse the form data and files
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" not in content_type:
            return {"statusCode": 400, "body": "Only multipart/form-data supported"}

        data = request.form
        selected_pages = json.loads(data.get("pages", "[]"))
        caption = data.get("caption", "")

        file = request.files.get("media")
        if not file or not selected_pages:
            return {"statusCode": 400, "body": "Missing file or pages"}

        # Save file temporarily
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        file.save(tmp_file)
        tmp_file.close()

        results = []

        # Post on each page
        for page in selected_pages:
            # Get page access token
            r = requests.get(
                f"https://graph.facebook.com/v19.0/{page}?fields=access_token&access_token={FB_TOKEN}"
            )
            page_token = r.json().get("access_token")
            if not page_token:
                results.append({"page": page, "result": "Could not get page token."})
                continue

            # Decide API by file type (simple version)
            file_ext = file.filename.lower().split(".")[-1]
            if file_ext in ["jpg", "jpeg", "png"]:
                url = f"https://graph.facebook.com/v19.0/{page}/photos"
                files = {"source": open(tmp_file.name, "rb")}
                payload = {"access_token": page_token, "caption": caption}
            else:
                url = f"https://graph.facebook.com/v19.0/{page}/videos"
                files = {"source": open(tmp_file.name, "rb")}
                payload = {"access_token": page_token, "description": caption}

            post_resp = requests.post(url, data=payload, files=files)
            try: files["source"].close()
            except: pass

            results.append({
                "page": page,
                "response": post_resp.json()
            })

        # Delete temp file
        os.remove(tmp_file.name)

        return {"statusCode": 200, "body": json.dumps(results)}
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}
