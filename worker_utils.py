from waivek import rel2abs
import os.path

def get_video_downloads_folder():
    return rel2abs("static/downloads/videos")

def get_chat_downloads_folder():
    return rel2abs("static/downloads/chats")

def has_video_part_file(portionurl_id):
    video_folder = get_video_downloads_folder()
    mp4_partial_path = os.path.join(video_folder, f"{portionurl_id}.mp4.part")
    webm_partial_path = os.path.join(video_folder, f"{portionurl_id}.webm.part")
    return os.path.exists(mp4_partial_path) or os.path.exists(webm_partial_path)

def is_video_fully_downloaded(portionurl_id):
    video_folder = get_video_downloads_folder()
    mp4_path = os.path.join(video_folder, f"{portionurl_id}.mp4")
    webm_path = os.path.join(video_folder, f"{portionurl_id}.webm")
    return os.path.exists(mp4_path) or os.path.exists(webm_path)

def has_chat_part_file(video_id):
    chat_folder = get_chat_downloads_folder()
    json_partial_path = os.path.join(chat_folder, f"{video_id}.json.part")
    return os.path.exists(json_partial_path)

def is_chat_downloaded(video_id):
    chat_folder = get_chat_downloads_folder()
    json_path = os.path.join(chat_folder, f"{video_id}.json.gz")
    return os.path.exists(json_path)
