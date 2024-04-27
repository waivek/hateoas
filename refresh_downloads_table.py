
from dbutils import Connection
from download_portionurl import portionurl_to_download_path
import os.path
connection = Connection("data/main.db")
import Enum

# Enum for path files existing, BOTH_EXIST, NEITHER_EXIST, ONLY_PATH_EXIST, ONLY_PART_EXIST

    
Enum.BOTH_EXIST = 0
Enum.NEITHER_EXIST = 1
Enum.ONLY_PATH_EXIST = 2
Enum.ONLY_PART_EXIST = 3


def portionurl_id_to_enum(portionurl_id):
    path = portionurl_to_download_path(portionurl_id)
    part_path = path + ".part"
    both_exist = os.path.exists(path) and os.path.exists(part_path)
    if both_exist:
        return Enum.BOTH_EXIST
    elif not os.path.exists(path) and not os.path.exists(part_path):
        return Enum.NEITHER_EXIST
    elif os.path.exists(path) and not os.path.exists(part_path):
        return Enum.ONLY_PATH_EXIST
    elif not os.path.exists(path) and os.path.exists(part_path):
        return Enum.ONLY_PART_EXIST
    else:
        assert False, "Should not reach here."

def refresh_downloads_table_2():
    cursor = connection.execute("SELECT portionurl_id FROM downloads WHERE;")
    portionurl_ids = [row[0] for row in cursor.fetchall()]
    for portionurl_id in portionurl_ids:
        # use match case
        enum = portionurl_id_to_enum(portionurl_id)
        match enum:
            case Enum.BOTH_EXIST:
                raise Exception(f"Both path and part file exist for portionurl_id {portionurl_id}.")
            case Enum.NEITHER_EXIST:
                cursor = connection.execute("SELECT status FROM downloads WHERE portionurl_id = ?;", (portionurl_id,))
                status = cursor.fetchone()[0]
                if status in [ "downloading", "complete" ]:
                    connection.execute("UPDATE downloads SET status = 'pending' WHERE portionurl_id = ?;", (portionurl_id,))
            case Enum.ONLY_PATH_EXIST:
                connection.execute("UPDATE downloads SET status = 'complete' WHERE portionurl_id = ?;", (portionurl_id,))
            case Enum.ONLY_PART_EXIST:
                connection.execute("UPDATE downloads SET status = 'downloading' WHERE portionurl_id = ?;", (portionurl_id,))
            case _:
                assert False, "Should not reach here."
    connection.commit()



# def refresh_downloads_table():
#     cursor = connection.execute("SELECT portionurl_id FROM downloads WHERE status = 'downloading' OR status = 'pending';")
#     portionurl_ids = [row[0] for row in cursor.fetchall()]
#     for portionurl_id in portionurl_ids:
#         path = portionurl_to_download_path(portionurl_id)
#         if os.path.exists(path):
#             connection.execute("UPDATE downloads SET status = 'complete' WHERE portionurl_id = ?;", (portionurl_id,))
#         else:
#             connection.execute("UPDATE downloads SET status = 'pending' WHERE portionurl_id = ?;", (portionurl_id,))
#
#
#     
#     # complete -> pending if the file is missing
#     cursor = connection.execute("SELECT portionurl_id FROM downloads WHERE status = 'complete';")
#     portionurl_ids = [row[0] for row in cursor.fetchall()]
#     for portionurl_id in portionurl_ids:
#         path = portionurl_to_download_path(portionurl_id)
#         if not os.path.exists(path):
#             connection.execute("UPDATE downloads SET status = 'pending' WHERE portionurl_id = ?;", (portionurl_id,))
#
#
#     # set to downloading if path.part exists
#     cursor = connection.execute("SELECT id FROM portionurls;").fetchall()
#     all_portionurl_ids = [row[0] for row in cursor]
#     for portionurl_id in all_portionurl_ids:
#         path = portionurl_to_download_path(portionurl_id)
#         if os.path.exists(path + ".part"):
#             connection.execute("UPDATE downloads SET status = 'downloading' WHERE portionurl_id = ?;", (portionurl_id,))
#
#     
#     connection.commit()

if __name__ == "__main__":
    refresh_downloads_table()
    print("Downloads table refreshed.")
