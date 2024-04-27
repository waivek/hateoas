
from waivek import rel2abs
def portionurl_to_download_path(portionurl_id):
    return rel2abs(f"static/downloads/{portionurl_id}.mp4")
