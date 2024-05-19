
from dbutils import Connection
connection = Connection("data/main.db")

def portionurl_id_queue_pop():
    # CREATE TABLE download_queue (
    #     id INTEGER PRIMARY KEY AUTOINCREMENT,
    #     portionurl_id INTEGER NOT NULL
    # ) STRICT;

    connection.execute("BEGIN IMMEDIATE TRANSACTION;")
    cursor = connection.execute("SELECT portionurl_id FROM download_queue LIMIT 1;")
    row = cursor.fetchone()
    if row is None:
        connection.execute("END TRANSACTION;")
        return None
    portionurl_id = row[0]
    connection.execute("DELETE FROM download_queue WHERE portionurl_id = ?;", (portionurl_id,))
    connection.execute("END TRANSACTION;")
    connection.commit()
    return portionurl_id

def add_portionurl_ids_to_queue(portionurl_ids):
    connection.execute("BEGIN IMMEDIATE TRANSACTION;")
    connection.executemany("INSERT INTO download_queue (portionurl_id) VALUES (?);", [(portionurl_id,) for portionurl_id in portionurl_ids])
    connection.execute("END TRANSACTION;")
    connection.commit()

def recover_from_crash():
    import os.path
    import glob
    import psutil
    from waivek import read
    from portionurl_to_download_path import portionurl_to_download_path
    downloads_folder = os.path.dirname(portionurl_to_download_path(1))
    lock_file_glob = os.path.join(downloads_folder, "*.lock")
    lock_files = glob.glob(lock_file_glob)
    for lock_file in lock_files:
        lock_D = read(lock_file)
        pid = lock_D["pid"]
        portionurl_id = lock_D["portionurl_id"]
        if psutil.pid_exists(pid):
            pass
        else:
            os.remove(lock_file)
            print("Removed lock file: %s", lock_file)
            connection.execute("BEGIN IMMEDIATE TRANSACTION;")
            connection.execute("INSERT INTO download_queue (portionurl_id) VALUES (?);", (portionurl_id,))
            connection.execute("END TRANSACTION;")
            connection.commit()
            print("Recovered portionurl_id: %s", portionurl_id)

