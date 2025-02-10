from waivek import Timer
timer = Timer()
from waivek import Code, handler, ic, ib, rel2abs, truncate
import sys
import time
import json

import subprocess
from box import usable
import rich
from typing import TextIO
import tzlocal
from output_modifier import OutputModifier

def do_work_2():
    # print a message every 0.5 seconds
    for i in range(5):
        print(f"Message {i}, Time: {time.time()}", flush=True)
        time.sleep(0.1)
    1/0

def do_work_1():
    video_id = "kfchvCyHmsc"
    # video_id = "abcdcdefghi"
    process = subprocess.Popen(
        ["yt-dlp", "-j", "-o", f"tmp/{video_id}.%(ext)s",  f"https://www.youtube.com/watch?v={video_id}"],
        stdout=subprocess.PIPE,   # Capture the stdout
        stderr=subprocess.PIPE, # Capture the stderr
        text=True,                # Return stdout as string instead of bytes
        bufsize=1,                # Line buffered
    )
    return process

def run_do_work_1():
    process = do_work_1()
    assert process.stdout, "process.stdout is None"
    # assert process.stderr, "process.stderr is None"
    for line in iter(process.stdout.readline, ''):
        print(line, end='', flush=True)
    process.wait()
    return process

def do_work_3():
    video_id = "kfchvCyHmsc"
    # video_id = "abcdcdefghi"
    process = subprocess.Popen(
        ["yt-dlp", "-o", f"tmp/{video_id}.%(ext)s",  f"https://www.youtube.com/watch?v={video_id}"],
        text=True,                # Return stdout as string instead of bytes
        bufsize=1,                # Line buffered
        stdout=subprocess.PIPE,   # Capture the stdout
        stderr=subprocess.PIPE,   # Capture the stderr
    )
    return process

def run_do_work_3():
    import select
    process = do_work_3()
    while True:
        reads, _, _ = select.select([process.stdout, process.stderr], [], [])
        for read in reads:
            line = read.readline()
            if not line:
                break
            if read is process.stdout:
                sys.stdout.write(truncate(line, 80))
            elif read is process.stderr:
                sys.stderr.write(truncate(line, 80))
        if process.poll() is not None:
            break

def do_work_4():
    video_id = "kfchvCyHmsc"
    process = subprocess.run(
        ["yt-dlp", "-o", f"tmp/{video_id}.%(ext)s",  f"https://www.youtube.com/watch?v={video_id}"],
        text=True,                # Return stdout as string instead of bytes
        capture_output=True,      # Capture the stdout and stderr
        check=False,              # Do not raise an exception if the return code is non-zero
    )
    return process

def main():
    sys.stdout = OutputModifier(sys.stdout)
    sys.stderr = OutputModifier(sys.stderr)

    # do_work_2()
    # run_do_work_1()
    # run_do_work_3()
    # do_work_4()
    timer.start("print")
    print("print")

if __name__ == "__main__":
    main()

# run.vim: term python %
