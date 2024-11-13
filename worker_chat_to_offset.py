from waivek import Connection, write
import os
from download_chat import get_chat_offsets_of_downloaded_video
from worker_single import worker_single
from worker_utils import get_offsets_downloads_folder, is_chat_downloaded

connection = Connection("data/main.db")

def get_video_id():
    # get_video_id {{{
    cursor = connection.execute("SELECT video_id FROM queue_chat;")
    video_ids = [ video_id for video_id, in cursor.fetchall() ]
    offsets_folder = get_offsets_downloads_folder()
    video_ids = [ video_id for video_id in video_ids if is_chat_downloaded(video_id) and not os.path.exists(os.path.join(offsets_folder, f"{video_id}.json")) ]
    if video_ids:
        return video_ids[0]
    return None
    # }}}

def write_offsets(video_id) -> int:
    # write_offsets {{{
    try:
        offset_file_path = os.path.join(get_offsets_downloads_folder(), f"{video_id}.json")
        offsets = get_chat_offsets_of_downloaded_video(video_id)
        write(offsets, offset_file_path)
        print(f"[WRITE] {offset_file_path}", flush=True)
    except Exception as e:
        print(f"[write_offsets] Error: {e}", flush=True)
        return 1
    return 0
    # }}}

def main():
    worker_single(get_video_id, write_offsets)

if __name__ == "__main__":
    main()
