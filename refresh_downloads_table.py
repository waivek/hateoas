
from dbutils import Connection
from portionurl_to_download_path import portionurl_to_download_path
import os.path
connection = Connection("data/main.db")

from enum import Enum

class Path(Enum):
    BOTH_EXIST = 1
    NEITHER_EXIST = 2
    ONLY_PATH_EXIST = 3
    ONLY_PART_EXIST = 4


def portionurl_id_to_enum(portionurl_id):
    path = portionurl_to_download_path(portionurl_id)
    part_path = path + ".part"
    both_exist = os.path.exists(path) and os.path.exists(part_path)
    if both_exist:
        return Path.BOTH_EXIST
    elif not os.path.exists(path) and not os.path.exists(part_path):
        return Path.NEITHER_EXIST
    elif os.path.exists(path) and not os.path.exists(part_path):
        return Path.ONLY_PATH_EXIST
    elif not os.path.exists(path) and os.path.exists(part_path):
        return Path.ONLY_PART_EXIST
    else:
        assert False, "Should not reach here."

def refresh_downloads_table():
    cursor = connection.execute("SELECT portionurl_id FROM downloads;")
    portionurl_ids = [row[0] for row in cursor.fetchall()]
    for portionurl_id in portionurl_ids:
        enum = portionurl_id_to_enum(portionurl_id)
        match enum:
            case Path.BOTH_EXIST:
                raise Exception(f"Both path and part file exist for portionurl_id {portionurl_id}.")
            case Path.NEITHER_EXIST:
                cursor = connection.execute("SELECT status FROM downloads WHERE portionurl_id = ?;", (portionurl_id,))
                status = cursor.fetchone()[0]
                if status in [ "downloading", "complete" ]:
                    connection.execute("UPDATE downloads SET status = 'pending' WHERE portionurl_id = ?;", (portionurl_id,))
            case Path.ONLY_PATH_EXIST:
                connection.execute("UPDATE downloads SET status = 'complete' WHERE portionurl_id = ?;", (portionurl_id,))
            case Path.ONLY_PART_EXIST:
                connection.execute("UPDATE downloads SET status = 'downloading' WHERE portionurl_id = ?;", (portionurl_id,))
            case _:
                assert False, "Should not reach here."
    connection.commit()

def loop():
    import time
    while True:
        refresh_downloads_table()
        time.sleep(1)

if __name__ == "__main__":
    refresh_downloads_table()
    print("Downloads table refreshed.")
