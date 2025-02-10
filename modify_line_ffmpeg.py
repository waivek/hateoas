
import re

def to_seconds(hhmmss):
    hh, mm, ss = map(float, hhmmss.split(":"))
    return hh * 3600 + mm * 60 + ss

def modify_line_ffmpeg(line: str, duration: float, prefix=""):
    if "frame=" not in line:
        return f"{prefix}{line}"
    match = re.search(r"time=(\d+:\d+:\d+\.\d+)", line)
    assert match
    time_hhmmss = match.group(1)
    time_float = to_seconds(time_hhmmss)
    fraction = time_float / duration
    progress = f"{fraction:.2%}"
    line = f"[progress={progress}] {line}"
    line = f"{prefix}{line}"
    return line

