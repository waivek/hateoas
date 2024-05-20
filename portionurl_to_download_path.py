
from waivek import rel2abs
import os.path

def downloaded(portionurl_id):
    mp4_path = rel2abs(f"static/downloads/{portionurl_id}.mp4")
    webm_path = rel2abs(f"static/downloads/{portionurl_id}.webm")
    return os.path.exists(mp4_path) or os.path.exists(webm_path)

def downloads_folder():
    return rel2abs("static/downloads")

