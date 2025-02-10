from waivek import Connection, read, write
import os
from video_stats import stats
from worker_single import worker_single

from worker_utils import get_chapters_folder, get_offsets_downloads_folder, get_graph_payloads_downloads_folder
from box import usable

connection = Connection("data/main.db")

def should_write_graph_payload(video_id):
    offsets_folder = get_offsets_downloads_folder()
    graph_payloads_folder = get_graph_payloads_downloads_folder()
    offset_file_path = os.path.join(offsets_folder, f"{video_id}.json")
    offsets_exist = os.path.exists(offset_file_path)
    chapters_exist = os.path.exists(os.path.join(get_chapters_folder(), f"{video_id}.json"))
    graph_payload_file_path = os.path.join(graph_payloads_folder, f"{video_id}.json")
    if not usable(offset_file_path):
        # the function `stats` will fail if the offsets file is not usable
        return False
    graph_payload = read(graph_payload_file_path)
    if offsets_exist and "top_offsets" not in graph_payload:
        return True
    if offsets_exist and "countpairs" not in graph_payload:
        return True
    if chapters_exist and "chapters" not in graph_payload:
        return True
    return False

def get_video_id():
    cursor = connection.execute("SELECT video_id FROM queue_chat;")
    video_ids = [ video_id for video_id, in cursor.fetchall() ]
    video_ids = [ video_id for video_id in video_ids if should_write_graph_payload(video_id) ]
    if video_ids:
        return video_ids[0]
    return None

def write_graph_payload(video_id):
    try:
        graph_payloads_folder = get_graph_payloads_downloads_folder()
        graph_payload_file_path = os.path.join(graph_payloads_folder, f"{video_id}.json")
        graph_payload = stats(video_id)
        chapters_exist = os.path.exists(os.path.join(get_chapters_folder(), f"{video_id}.json"))
        if chapters_exist:
            chapters = read(os.path.join(get_chapters_folder(), f"{video_id}.json"))
            graph_payload["chapters"] = chapters
        path = write(graph_payload, graph_payload_file_path)
        print("[write_graph_payload] WRITE", path)
    except Exception as error:
        import traceback
        print("[write_graph_payload] ERROR", error)
        tb = traceback.format_exc()
        print(tb)
        return 1
    return 0

def main():
    worker_single(get_video_id, write_graph_payload)

if __name__ == "__main__":
    main()

# run.vim: term python %
