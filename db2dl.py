
# lock file

import os
import sys
from dbutils import Connection
from download_portionurl import portionurl_to_download_path
from download_portionurl import download_portionurl
from waivek import ic

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
    connection.commit()


def main():


    refresh_downloads_table()

    # get 5 'pending' downloads
    cursor = connection.execute("SELECT portionurl_id FROM downloads WHERE status = 'pending' LIMIT 5;")
    pending_portionurl_ids = [row[0] for row in cursor.fetchall()]
    if len(pending_portionurl_ids) == 0:
        print("No pending downloads")
        return
    ic(pending_portionurl_ids)

    # in parallel, call download_portionurl for each pending download
    bash_command_format = "python download_portionurl.py {portionurl_id}"
    commands = [bash_command_format.format(portionurl_id=portionurl_id) for portionurl_id in pending_portionurl_ids]
    # run all 5 commands in parallel, using `xargs` or `parallel`

    for command in commands:
        ic(command)
        os.system(command)

    refresh_downloads_table()

lock_file = "/tmp/db2dl.py.lock"
if os.path.exists(lock_file):
    print("Lock file exists, exiting")
    sys.exit(1)

with open(lock_file, "w") as f:
    f.write(str(os.getpid()))

from waivek import handler
try:
    with handler():
        main()
except Exception as e:
    print("Error:", e)
    

os.remove(lock_file)
