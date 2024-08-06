import sys
from waivek import rel2abs
import os.path

def log(message: str, *args):
    from waivek import Code
    import os
    from datetime import datetime
    from date import convert
    dt = convert(datetime.now(), "UTC")
    dt = dt.replace(microsecond=0)
    date_string = dt.isoformat()

    frame = sys._getframe(1)
    filename = frame.f_code.co_filename
    script_name = os.path.basename(filename)
    prefix = Code.LIGHTBLACK_EX + f"[{date_string}] [{script_name}] [PID={os.getpid()}]"
    formatted_message = message % args
    output = " ".join([prefix, formatted_message])
    print(output, flush=True)

def get_video_downloads_folder():
    return rel2abs("static/downloads/videos")

def get_chat_downloads_folder():
    return rel2abs("static/downloads/chats")

def get_offsets_downloads_folder():
    return rel2abs("static/downloads/offsets")

def get_graph_payloads_downloads_folder():
    return rel2abs("static/downloads/graph_payloads")

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
