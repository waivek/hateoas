
from dbutils import Connection
from Types import PortionUrl, Portion
from waivek import rel2abs
import sys
import os
import os.path
from waivek import Timestamp
from waivek import Code
from waivek import ic
from refresh_downloads_table import refresh_downloads_table
from portionurl_to_download_path import portionurl_to_download_path
import time

connection = Connection("data/main.db")
videos_connection = Connection("data/videos.db")


def colon_timestamp(seconds):
    assert seconds >= 0, f"[colon_timestamp] seconds is negative: {seconds}"
    timestamp = Timestamp(seconds).timestamp
    return timestamp

def portionurl_id_to_command(portionurl_id):
    cursor = connection.execute("SELECT * FROM portionurls WHERE id = ?", (portionurl_id,))
    portionurl = PortionUrl(**cursor.fetchone())
    cursor = connection.execute("SELECT duration FROM portions WHERE id = ?", (portionurl.portion_id,))

    # assert cursor.rowcount == 1, f"portion_id {portionurl.portion_id} not found"
    duration = cursor.fetchone()[0]
    url = portionurl.url
    offset = portionurl.offset()
    download_path = portionurl_to_download_path(portionurl_id)
    download_dir = os.path.dirname(download_path)
    os.makedirs(download_dir, exist_ok=True)

    # use yt-dlp to download `url` from `offset` to `offset + duration` and save it to `download_path`
    # --download-sections "*02:32:00-02:33:00"
    start = colon_timestamp(offset)
    end = colon_timestamp(offset + duration)
    ic(start)
    ic(end)
    ic(duration)
    args = f'--download-sections "*{start}-{end}"'

    command = f"yt-dlp {url} -o {download_path} {args} --force-keyframes-at-cuts"
    return command

def download_portionurl(portionurl_id):
    command = portionurl_id_to_command(portionurl_id)
    ic(command)
    exit_code = os.system(command)
    if exit_code == 0:
        print(Code.GREEN + f"Downloaded portionurl {portionurl_id} to {portionurl_to_download_path(portionurl_id)}")
    else:
        print(Code.RED + f"Failed to download portionurl {portionurl_id}, exit code: {exit_code}")
    return exit_code

def loop():
    loop_duration_seconds = 50
    for i in range(loop_duration_seconds):
        cursor = connection.execute("SELECT id FROM portionurls WHERE status = 'pending' LIMIT 1")
        portionurl_id = cursor.fetchone()
        if portionurl_id:
            portionurl_id = portionurl_id[0]
            print(f"Downloading portionurl {portionurl_id}")
            download_portionurl(portionurl_id)
        time.sleep(1)

def main():
    portionurl_id = 3
    exit_code = download_portionurl(portionurl_id)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
# else:
# if __name__ == "__main__":
#     if sys.argv[1]:
#         refresh_downloads_table()
#         portionurl_id = int(sys.argv[1])
#         connection.execute("UPDATE downloads SET status = 'downloading' WHERE portionurl_id = ?", (portionurl_id,))
#         connection.commit()
#         assert portionurl_id >= 0, f"portionurl_id is negative: {portionurl_id}"
#         ic(portionurl_id)
#         exit_code = download_portionurl(portionurl_id)
#         refresh_downloads_table()
#         sys.exit(exit_code)
#     else:
#         print("No argument passed.")
#     print("Done")
