
# usage:
# download.py <url> <offset> <duration> <output_file>

import sys
import os
import subprocess
import json


def download(url, offset, duration, output_file):
    command = f"youtube-dl -g {url}"
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    if error:
        print(error)
        return

    video_url = output.decode("utf-8").split("\n")[0]
    command = f"ffmpeg -ss {offset} -i {video_url} -t {duration} -c copy {output_file}"
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    if error:
        print(error)
        return


if __name__ == "__main__":
    url = sys.argv[1]
    offset = sys.argv[2]
    duration = sys.argv[3]
    output_file = sys.argv[4]
    download(url, offset, duration, output_file)

