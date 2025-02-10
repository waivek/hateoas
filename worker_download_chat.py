
from waivek import Connection
from download_chat import download_chat
from worker_single import worker_single
from worker_utils import is_chat_downloaded

connection = Connection("data/main.db")

def get_video_id():
    # get_video_id {{{
    global connection
    cursor = connection.execute("SELECT video_id FROM queue_chat;")
    video_ids = [ video_id for video_id, in cursor.fetchall() if not is_chat_downloaded(video_id) ]
    if video_ids:
        return video_ids[0]
    return None
    # }}}

def main():
    worker_single(get_video_id, download_chat)

if __name__ == "__main__":
    main()
