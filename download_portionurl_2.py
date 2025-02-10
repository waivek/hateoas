import os
import sys
from waivek import Code, Connection, handler
import yt_dlp
from yt_dlp.utils import download_range_func

from Types import PortionUrl
from download_portionurl import colon_timestamp
from portionurl_to_download_path import downloads_folder

connection = Connection("data/main.db")

def portionurl_id_to_command(portionurl_id):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM portionurls WHERE id = ?", (portionurl_id,))
    row = cursor.fetchone()
    if row is None:
        print(Code.RED + f"portionurl_id {portionurl_id} not found", flush=True)
        cursor = connection.execute("SELECT id FROM portionurls")
        raise FileNotFoundError(f"portionurl_id {portionurl_id} not found")
    portionurl = PortionUrl(**row)

    cursor.execute("SELECT duration FROM portions WHERE id = ?", (portionurl.portion_id,))

    # duration = cursor.fetchone()[0]
    # MANUAL: OVERRIDE
    duration = 5
    url = portionurl.url
    offset = portionurl.offset()
    os.makedirs(downloads_folder(), exist_ok=True)

    # use yt-dlp to download `url` from `offset` to `offset + duration` and save it to `download_path`
    # --download-sections "*02:32:00-02:33:00"
    start = colon_timestamp(offset)
    end = colon_timestamp(offset + duration)
    args = f'--download-sections "*{start}-{end}"'
    download_ranges = { "*": [ (start, end) ] }

    # download_path = os.path.join(downloads_folder(), str(portionurl_id))
    # MANUAL: OVERRIDE
    download_path = "/home/vivek/hateoas/tmp/" + str(portionurl_id)
    # command = f"yt-dlp {url} -o '{download_path}.%(ext)s' {args} --force-keyframes-at-cuts"
    return { "url": url, "download_path": download_path, "start": offset, "end": offset + duration }

def clear_progress_file():
    progress_path = "/home/vivek/hateoas/tmp/progress.txt"
    with open(progress_path, "w") as f:
        f.write("")

counter = 0

def write_progress_file(message):
    global counter
    counter = counter + 1
    progress_path = "/home/vivek/hateoas/tmp/progress.txt"
    # append newline if not present
    message = f"[counter={counter}] {message.strip()}\n"
    with open(progress_path, "a") as f:
        f.write(message)

def print_progress_file():
    progress_path = "/home/vivek/hateoas/tmp/progress.txt"
    print(f"\n\n{progress_path}:\n")
    with open(progress_path, "r") as f:
        print(f.read())

def progress_hook(d):
    write_progress_file("progress_hook")

def post_hook(d):
    write_progress_file("post_hook")

def download_video(url, download_path, start, end):
    clear_progress_file()
    print(f"Downloading {url} to {download_path}.%(ext)s from {start} to {end}")
    ydl_opts = {
        'outtmpl': f'{download_path}.%(ext)s',  # Save format
        'force_keyframes_at_cuts': True,  # Equivalent to --force-keyframes-at-cuts
        'progress_hooks': [progress_hook],  # Hook to capture progress
        'post_hooks': [post_hook],  # Hook to capture post
        "download_ranges": download_range_func(None, [(start, end)]),  # Equivalent to --download-sections
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    print_progress_file()

def download_portionurl(portionurl_id):
    command = portionurl_id_to_command(portionurl_id)
    download_video(command["url"], command["download_path"], command["start"], command["end"])

if __name__ == "__main__":
    with handler():
        portionurl_id = sys.argv[1]
        download_portionurl(portionurl_id)

# run.vim: vert term python % 1
