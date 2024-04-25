
from dbutils import Connection
from download_portionurl import portionurl_to_download_path
import os.path
connection = Connection("data/main.db")
def refresh_downloads_table():
    cursor = connection.execute("SELECT portionurl_id FROM downloads WHERE status = 'downloading' OR status = 'pending';")
    portionurl_ids = [row[0] for row in cursor.fetchall()]
    for portionurl_id in portionurl_ids:
        path = portionurl_to_download_path(portionurl_id)
        if os.path.exists(path):
            connection.execute("UPDATE downloads SET status = 'complete' WHERE portionurl_id = ?;", (portionurl_id,))
        else:
            connection.execute("UPDATE downloads SET status = 'pending' WHERE portionurl_id = ?;", (portionurl_id,))

    # complete -> pending if the file is missing
    cursor = connection.execute("SELECT portionurl_id FROM downloads WHERE status = 'complete';")
    portionurl_ids = [row[0] for row in cursor.fetchall()]
    for portionurl_id in portionurl_ids:
        path = portionurl_to_download_path(portionurl_id)
        if not os.path.exists(path):
            connection.execute("UPDATE downloads SET status = 'pending' WHERE portionurl_id = ?;", (portionurl_id,))

    connection.commit()

if __name__ == "__main__":
    refresh_downloads_table()
    print("Downloads table refreshed.")
