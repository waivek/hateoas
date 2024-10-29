
import re
from dbutils import Connection
from Types import PortionUrl
import sys
import os
import os.path
from waivek import Timestamp, handler
from waivek import Code
from portionurl_to_download_path import downloads_folder
import yt_dlp
import subprocess
import shlex
import pathlib
from bat import bat
from modify_line_ffmpeg import modify_line_ffmpeg

connection = Connection("data/main.db")
videos_connection = Connection("data/videos.db")

def get_portion_duration(portion_id):
    cursor = connection.cursor()
    cursor.execute("SELECT duration FROM portions WHERE id = ?", (portion_id,))
    duration = cursor.fetchone()[0]
    return duration

def colon_timestamp(seconds):
    assert seconds >= 0, f"[colon_timestamp] seconds is negative: {seconds}"
    timestamp = Timestamp(seconds).timestamp
    return timestamp

def portionurl_id_to_command(portionurl_id):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM portionurls WHERE id = ?", (portionurl_id,))
    row = cursor.fetchone()
    if row is None:
        print(Code.RED + f"portionurl_id {portionurl_id} not found", flush=True)
        cursor = connection.execute("SELECT id FROM portionurls")
        raise FileNotFoundError(f"portionurl_id {portionurl_id} not found")

    portionurl = PortionUrl(**row)
    duration = get_portion_duration(portionurl.portion_id)
    # OVERWRITE
    # duration = 10
    url = portionurl.url
    offset = portionurl.offset()
    os.makedirs(downloads_folder(), exist_ok=True)

    # use yt-dlp to download `url` from `offset` to `offset + duration` and save it to `download_path`
    # --download-sections "*02:32:00-02:33:00"
    start = colon_timestamp(offset)
    end = colon_timestamp(offset + duration)
    args = f'--download-sections "*{start}-{end}"'

    download_path = os.path.join(downloads_folder(), str(portionurl_id))
    # download_path = "/home/vivek/hateoas/tmp/" + str(portionurl_id)
    command = f"yt-dlp {url} -o '{download_path}.%(ext)s' {args} --force-keyframes-at-cuts"
    return command

def locate_downloaded_video(portionurl_id):
    mp4_path = os.path.join(downloads_folder(), f"{portionurl_id}.mp4")
    webm_path = os.path.join(downloads_folder(), f"{portionurl_id}.webm")
    if os.path.exists(mp4_path):
        return mp4_path
    elif os.path.exists(webm_path):
        return webm_path
    else:
        raise FileNotFoundError(f"Neither {mp4_path} nor {webm_path} exists")

def run_command_and_modify_stdout(command, modify_fn=None):

    command = shlex.split(command)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
    assert process.stdout is not None, "process.stdout is None"

    for line in iter(process.stdout.readline, ''):
        if modify_fn:
            line = modify_fn(line)
        sys.stdout.write(line)
        sys.stdout.flush()

    return_code = process.wait()

    return return_code

def download_portionurl(portionurl_id):
    command = portionurl_id_to_command(portionurl_id)
    print("command: " + (Code.LIGHTCYAN_EX + command), flush=True)
    cursor = connection.execute("SELECT portion_id FROM portionurls WHERE id = ?", (portionurl_id,))
    duration = get_portion_duration(cursor.fetchone()[0])
    modify_fn = lambda line: modify_line_ffmpeg(line, duration)
    
    exit_code = run_command_and_modify_stdout(command, modify_fn)

    if exit_code == 0:
        downloaded_path = locate_downloaded_video(portionurl_id)
        print(Code.GREEN + f"Downloaded portionurl {portionurl_id} to {downloaded_path}", flush=True)
    else:
        print(Code.RED + f"Failed to download portionurl {portionurl_id}, exit code: {exit_code}", flush=True)
    return exit_code

def main():
    portionurl_id = int(sys.argv[1])
    exit_code = download_portionurl(portionurl_id)
    sys.exit(exit_code)

if __name__ == "__main__":
    with handler():
        main()

# run.vim: vert term python % 31
