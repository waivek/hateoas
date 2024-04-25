
from dbutils import Connection
from Types import PortionUrl, Portion
from waivek import rel2abs
import sys
import os
import os.path
from waivek import Timestamp
from waivek import Code
from waivek import ic

connection = Connection("data/main.db")
videos_connection = Connection("data/videos.db")

def portionurl_to_download_path(portionurl_id):
    return rel2abs(f"static/downloads/{portionurl_id}.mp4")

def colon_timestamp(seconds):
    assert seconds >= 0, f"[colon_timestamp] seconds is negative: {seconds}"
    timestamp = Timestamp(seconds).timestamp
    return timestamp

def download_portionurl(portionurl_id):
    cursor = connection.execute("SELECT * FROM portionurls WHERE id = ?", (portionurl_id,))
    portionurl = PortionUrl(**cursor.fetchone())
    cursor = connection.execute("SELECT duration FROM portions WHERE id = ?", (portionurl.portion_id,))

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

    print(f"{args = }")
    command = f"yt-dlp {url} -o {download_path} {args} --force-keyframes-at-cuts"
    print(command)
    exit_code = os.system(command)
    if exit_code == 0:
        print(Code.GREEN + f"Downloaded portionurl {portionurl_id} to {download_path}")
    if exit_code != 0:
        print(Code.RED + f"Failed to download portionurl {portionurl_id}, exit code: {exit_code}")
    return exit_code

def main():
    portionurl_id = 26
    exit_code = download_portionurl(portionurl_id)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()

