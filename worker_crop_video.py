import os
import shlex
import subprocess
import sys

from waivek import Connection
from worker_encode_video import encoded
from worker_utils import get_crops_folder, get_download_filename, get_encodes_folder, portionurl_id_to_filename
from worker_single import worker_single

# CREATE TABLE IF NOT EXISTS queue_crop (id INTEGER PRIMARY KEY AUTOINCREMENT, portionurl_id INTEGER NOT NULL UNIQUE, x INTEGER NOT NULL, y INTEGER NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL, FOREIGN KEY (portionurl_id) REFERENCES portionurls (id) ON DELETE CASCADE) STRICT;
connection = Connection("data/main.db")
videos_connection = Connection("data/videos.db")

def cropped(portionurl_id):
    # cropped {{{
    filename = portionurl_id_to_filename(portionurl_id)  # Assuming this function exists in your context
    path = os.path.join(get_crops_folder(), filename)  # Assuming cropped files are stored in the crops folder
    return os.path.exists(path)
    # }}}

def get_crop_portionurl_id():
    # get_crop_portionurl_id {{{
    cursor = connection.execute("SELECT portionurl_id FROM queue_crop")
    ids = [ id for id, in cursor.fetchall() if encoded(id) and not cropped(id) ]
    if ids:
        return ids[0]
    return None
    # }}}

def in_crop_queue(portionurl_id):
    # in_crop_queue {{{
    # check if portionurl_id is in the crop queue
    cursor = connection.execute("SELECT 1 FROM queue_crop WHERE portionurl_id = ?", (portionurl_id,))
    return cursor.fetchone() is not None
    # }}}

def crop_video(portionurl_id):
    # crop_video {{{
    input_path = os.path.join(get_encodes_folder(), portionurl_id_to_filename(portionurl_id))
    output_path = os.path.join(get_crops_folder(), portionurl_id_to_filename(portionurl_id))
    cursor = connection.execute("SELECT x, y, width, height FROM queue_crop WHERE portionurl_id = ?", (portionurl_id,))
    x, y, width, height = cursor.fetchone()
    # ffmpeg -i 1.mp4 -filter:v "crop=358:370:1551:336" -c:a copy output_1_cropped.mp4
    command = f"ffmpeg -i {input_path} -filter:v 'crop={width}:{height}:{x}:{y}' -c:a copy {output_path}"
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
    assert process.stdout
    for line in iter(process.stdout.readline, ""):
        # line = modify_line_ffmpeg(line, duration, prefix=f"[portionurl_id={portionurl_id}] ")
        sys.stdout.write(line)
        sys.stdout.flush()
    exit_code = process.wait()
    return exit_code
    # }}}

def main():
    # crop_video(21)
    worker_single(get_crop_portionurl_id, crop_video)

if __name__ == "__main__":
    main()
