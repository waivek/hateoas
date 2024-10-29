import sys
from waivek import Connection, rel2abs
import os.path

from Types import Portion, PortionUrl
from portionurl_to_download_path import downloads_folder

connection = Connection("data/main.db")
videos_connection = Connection("data/videos.db")

def convert(dt, tz):
    import pytz
    return dt.astimezone(pytz.timezone(tz))

def log(message: str, *args):
    from waivek import Code
    import os
    from datetime import datetime
    import tzlocal
    # dt = convert(datetime.now(), tzlocal.get_localzone())
    dt = datetime.now(tzlocal.get_localzone())
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

def get_encodes_folder():
    return rel2abs("static/downloads/encodes")

def get_crops_folder():
    return rel2abs("static/downloads/crops")

def get_chapters_folder():
    return rel2abs("static/downloads/chapters")

def get_download_filename(portionurl: PortionUrl, portion: Portion, video: dict) -> str:
    from slugify import slugify
    from waivek import Timestamp
    order = portion.order
    order_padded = str(order).zfill(2)
    user_name = video["user_name"]
    title = portion.title
    title_slug = slugify(title, separator="_")
    video_id = video["id"]
    offset = portion.epoch - video["created_at_epoch"]
    offset_hhmmss = Timestamp(offset).hh_mm_ss
    return ".".join([order_padded, title_slug, user_name, video_id, offset_hhmmss, "mp4"])

def portionurl_id_to_filename(portionurl_id):
    # portionurl_id_to_filename {{{
    cursor = connection.execute("SELECT * FROM portionurls WHERE id = ?;", (portionurl_id,))
    portionurl = PortionUrl(*cursor.fetchone())
    cursor = connection.execute("SELECT * FROM portions WHERE id = ?;", (portionurl.portion_id,))
    portion = Portion(*cursor.fetchone())
    video_id = portionurl.url.replace("https://www.youtube.com/watch?v=", "").replace("https://www.twitch.tv/videos/", "")
    cursor = videos_connection.execute("SELECT * FROM videos WHERE id = ?;", (video_id,))
    video_dict = dict(cursor.fetchone())
    filename = get_download_filename(portionurl, portion, video_dict)
    return filename
    # }}}

if __name__ == "__main__":
    log("Hello World! (sample log via worker_utils.log function)")

# run.vim: term python %
