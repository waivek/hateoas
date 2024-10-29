import os
from waivek import Connection, ic
from download_portionurl import locate_downloaded_video
from modify_line_ffmpeg import modify_line_ffmpeg
from worker_single import worker_single
from portionurl_to_download_path import downloaded
from worker_utils import get_download_filename, get_encodes_folder, portionurl_id_to_filename
import subprocess
import sys

connection = Connection("data/main.db")
videos_connection = Connection("data/videos.db")

def encoded(portionurl_id):
    # encoded {{{
    filename = portionurl_id_to_filename(portionurl_id)
    path = os.path.join(get_encodes_folder(), filename)
    return os.path.exists(path)
    # }}}

def get_portionurl_id():
    # get_portionurl_id {{{
    global connection
    cursor = connection.execute("SELECT id FROM portionurls WHERE selected = 1;")
    portionurl_ids = [ id for id, in cursor.fetchall() if downloaded(id) and not encoded(id) ]
    if portionurl_ids:
        return portionurl_ids[0]
    return None
    # }}}

def get_duration_of_video_file_via_ffmpeg(video_path: str) -> float:
    # get_duration_of_video_file_via_ffmpeg {{{{{{
    process = subprocess.Popen([
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, universal_newlines=True, bufsize=1)
    assert process.stdout
    duration = float(process.stdout.read().strip())
    process.wait()
    return duration
    # }}}}}}

def status_encode(portionurl_id):
    # status_encode {{{
    from ffmpeg_download_progress import tail
    import re
    filename = portionurl_id_to_filename(portionurl_id)
    path = os.path.join(get_encodes_folder(), filename)
    if os.path.exists(path):
        return "encoded"
    hardcoded_log_file = os.path.expanduser("~/bash/logs/worker_encode_video.log")
    lines = tail(hardcoded_log_file, 100)
    pattern = "[progress=([0-9]+.[0-9]+)%]"
    for line in reversed(lines):
        if f"[portionurl_id={portionurl_id}]" in line:
            match = re.search(pattern, line)
            if match:
                return f"encoding: {match.group(1)}%"
    return "pending"
    # }}}

def encode_portionurl(portionurl_id):
    input_path = locate_downloaded_video(portionurl_id)

    filename = portionurl_id_to_filename(portionurl_id)
    output_path = os.path.join(get_encodes_folder(), filename)

    duration = get_duration_of_video_file_via_ffmpeg(input_path)

    print("Input Path: " + input_path)
    print("Output Path: " + output_path)
    process = subprocess.Popen([
        "ffmpeg",
        "-i", input_path,
        "-af", "aresample=async=1:first_pts=0", # without this, when we import into premiere pro, the audio is out of sync
        "-r", "30",
        "-ar", "48000",
        "-y",
        output_path
    ],

    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, universal_newlines=True, bufsize=1)
    assert process.stdout
    for line in iter(process.stdout.readline, ""):
        line = modify_line_ffmpeg(line, duration, prefix=f"[portionurl_id={portionurl_id}] ")
        sys.stdout.write(line)
        sys.stdout.flush()

    exit_code = process.wait()

    return exit_code

def main():
    # encode_portionurl(21)
    # if portionurl_id := get_portionurl_id():
    #     encode_portionurl(portionurl_id)
    worker_single(get_portionurl_id, encode_portionurl)

if __name__ == "__main__":
    # status_encode(8)
    main()

# run.vim: term python % 2>&1
