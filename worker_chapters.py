from waivek import Connection, handler, ic, ib , rel2abs
import rich
import os

from chapters import write_chapters
from worker_single import worker_single
from worker_utils import get_chapters_folder

connection = Connection("data/main.db")

def chapters_exist(video_id):
    chapters_folder = get_chapters_folder()
    return os.path.exists(os.path.join(chapters_folder, f"{video_id}.json"))

def get_video_ids():
    global connection
    cursor = connection.execute("SELECT video_id FROM queue_chat;")
    video_ids = [ video_id for video_id, in cursor.fetchall() if not chapters_exist(video_id) ]
    if video_ids:
        return video_ids
    return None

def main():
    # import glob
    # for path in glob.glob(get_chapters_folder() + "/*.json"):
    #     os.remove(path)
    worker_single(get_video_ids, write_chapters)

if __name__ == "__main__":
    with handler():
        main()
