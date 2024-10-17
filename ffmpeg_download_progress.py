from waivek import Timer   # Single Use
timer = Timer()
from waivek import Code    # Multi-Use
from waivek import handler # Single Use
from waivek import ic, ib     # Multi-Use, import time: 70ms - 110ms
from waivek import rel2abs
import os
import re

def tail(filename, lines=10, buffer_size=1024):
    with open(filename, 'rb') as f:
        f.seek(0, 2)  # Move to the end of the file
        file_size = f.tell()
        block = -1
        data = []
        while len(data) < lines and f.tell() > 0:
            if f.tell() < buffer_size:
                buffer_size = f.tell()  # Adjust buffer size for the first block
            f.seek(block * buffer_size, 2)  # Move backwards in blocks
            buffer = f.read(buffer_size).decode('utf-8')
            data = buffer.splitlines() + data
            block -= 1
        return data[-lines:]  # Return only the last `lines` number of lines

def ffmpeg_download_progress(log_path):
    lines = tail(log_path, 50)
    print("\n".join(lines))
    # frame= 3596 fps= 26 q=31.0 size=   20480kB time=00:00:59.92 bitrate=2799.7kbits/s dup=1 drop=0 speed=0.436x
    line = next((line for line in lines if "frame=" in line), None)
    if not line:
        return { "error": "No progress line found" }
    match = re.search(r"time=(\d+:\d+:\d+\.\d+)", line)
    assert match
    time = match.group(1)
    ic(time)

def main():
    log_path = os.path.expanduser("~/bash/logs/download_worker-red.log")
    ffmpeg_download_progress(log_path)
    print("")

if __name__ == "__main__":
    with handler():
        main()

# run.vim: term python %
