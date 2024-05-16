
from waivek import ic
from dbutils import Connection
import psutil

connection = Connection("data/main.db")

def purge_dead_pids():
    global connection
    cursor = connection.execute("SELECT pid FROM download_pids")
    pids = cursor.fetchall()
    dead_pids = [ pid for pid in pids if not psutil.pid_exists(pid) ]
    for pid in dead_pids:
        connection.execute("DELETE FROM download_pids WHERE pid = ?", (pid,))
    connection.commit()

def assign():


    global connection
    purge_dead_pids()

    cursor = connection.execute("SELECT portionurl_id FROM downloads WHERE status = 'pending'")
    portionurl_ids = cursor.fetchall()

    # assign portionurl_id to a downloader pid in a queue, use new table
    cursor = connection.execute("SELECT pid FROM download_pids")
    pids = cursor.fetchall()
    if not pids:
        return

    for portionurl_id in portionurl_ids:
        if not pids:
            break
        pid = pids.pop(0)
        connection.execute("INSERT INTO download_assignments (pid, portionurl_id) VALUES (?, ?)", (pid, portionurl_id))
    connection.commit()


