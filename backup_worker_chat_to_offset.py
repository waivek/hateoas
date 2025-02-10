import sys
from waivek import Timer, write

from download_chat import get_chat_offsets_of_downloaded_video
from video_stats import stats
from worker_utils import get_chat_downloads_folder, get_graph_payloads_downloads_folder, get_offsets_downloads_folder, is_chat_downloaded, log   # Single Use
timer = Timer()
from waivek import Code    # Multi-Use
from waivek import handler # Single Use
from waivek import ic, ib     # Multi-Use, import time: 70ms - 110ms
from waivek import rel2abs
import os
import time
from waivek import Connection

def tables_exist(connection, table_names: list[str]) -> bool:
    # get list of table-names in sqlite database
    cursor = connection.execute("SELECT name FROM sqlite_master WHERE type='table';")
    db_table_names = [ name for name, in cursor.fetchall() ]
    return all([ name in db_table_names for name in table_names ])

def get_missing_table_names(connection, table_names: list[str]) -> list[str]:
    # get list of table-names in sqlite database
    cursor = connection.execute("SELECT name FROM sqlite_master WHERE type='table';")
    db_table_names = [ name for name, in cursor.fetchall() ]
    return [ name for name in table_names if name not in db_table_names ]

def connection_to_db_path(connection):
    return connection.execute("PRAGMA database_list;").fetchone()[2]

def main():
    connection = Connection("data/main.db")
    if not tables_exist(connection, [ "queue_chat" ]):
        missing_table_names = get_missing_table_names(connection, [ "queue_chat" ])
        db_path = connection_to_db_path(connection)
        log(db_path)
        log("Missing tables: %s", missing_table_names)
        log("Exiting. (tables do not exist)")

        sys.exit(0)
    offsets_folder = get_offsets_downloads_folder()
    graph_payloads_folder = get_graph_payloads_downloads_folder()
    log("")
    while True:
        cursor = connection.execute("SELECT video_id FROM queue_chat;")
        video_ids = [ video_id for video_id, in cursor.fetchall() ]
        pending_video_ids = [ 
                             video_id for video_id in video_ids 
                             if      
                                 is_chat_downloaded(video_id)
                             and 
                                 not os.path.exists(os.path.join(offsets_folder, f"{video_id}.json")) 
                            ]
        for video_id in pending_video_ids:
            offset_file_path = os.path.join(offsets_folder, f"{video_id}.json")
            offsets = get_chat_offsets_of_downloaded_video(video_id)
            write(offsets, offset_file_path)
            log(f"[WRITE] {Code.LIGHTCYAN_EX + offset_file_path}")
        
        pending_video_ids = [ 
                             video_id for video_id in video_ids 
                             if os.path.exists(os.path.join(offsets_folder, f"{video_id}.json")) 
                             and not os.path.exists(os.path.join(graph_payloads_folder, f"{video_id}.json")) 
                            ]
        for video_id in pending_video_ids:
            stats(video_id)
            log(f"[STATS] {Code.LIGHTCYAN_EX + video_id}")

        time.sleep(1)

if __name__ == "__main__":
    main()

