
from dbutils import Connection
from Types import PortionUrl
import sys
import os
import os.path
from waivek import Timestamp
from waivek import Code
from portionurl_to_download_path import downloads_folder

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
    os.makedirs(downloads_folder(), exist_ok=True)

    # use yt-dlp to download `url` from `offset` to `offset + duration` and save it to `download_path`
    # --download-sections "*02:32:00-02:33:00"
    start = colon_timestamp(offset)
    end = colon_timestamp(offset + duration)
    print("start: " + (Code.LIGHTCYAN_EX + start), flush=True)
    print("end: " + (Code.LIGHTCYAN_EX + end), flush=True)
    print("duration: " + (Code.LIGHTCYAN_EX + str(duration)), flush=True)
    args = f'--download-sections "*{start}-{end}"'

    download_path = os.path.join(downloads_folder(), str(portionurl_id))
    command = f"yt-dlp {url} -o '{download_path}.%(ext)s' {args} --force-keyframes-at-cuts"
    return command

def get_downloaded_path(portionurl_id):
    mp4_path = os.path.join(downloads_folder(), str(portionurl_id) + ".mp4")
    webm_path = os.path.join(downloads_folder(), str(portionurl_id) + ".webm")
    if os.path.exists(mp4_path):
        return mp4_path
    elif os.path.exists(webm_path):
        return webm_path
    else:
        raise FileNotFoundError(f"Neither {mp4_path} nor {webm_path} exists")

def download_portionurl(portionurl_id):
    command = portionurl_id_to_command(portionurl_id)
    print("command: " + (Code.LIGHTCYAN_EX + command), flush=True)
    exit_code = os.system(command)
    if exit_code == 0:
        downloaded_path = get_downloaded_path(portionurl_id)
        print(Code.GREEN + f"Downloaded portionurl {portionurl_id} to {downloaded_path}", flush=True)
    else:
        print(Code.RED + f"Failed to download portionurl {portionurl_id}, exit code: {exit_code}", flush=True)
    return exit_code

def main():
    portionurl_id = 15
    exit_code = download_portionurl(portionurl_id)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
