
import os
import sys
import tzlocal
from datetime import datetime
from typing import TextIO

class OutputModifier:

    def __init__(self, stream: TextIO, path: str):
        try:
            stream.name
        except AttributeError:
            breakpoint()
        if stream.name not in ("<stdout>", "<stderr>"):
            raise ValueError(f"Unknown stream name: {stream.name}")
        self.stream   = stream
        # self.path     = sys._getframe(1).f_code.co_filename
        self.path     = path
        self.filename = os.path.basename(self.path)
        self.zone     = tzlocal.get_localzone()
        self.pid      = os.getpid()
        self.previous_line_ended_with_newline = True

    def _prefix(self) -> str:
        timestamp = datetime.now(self.zone).strftime("%Y-%m-%d %H:%M:%S %Z")
        if self.stream.name == "<stdout>":
            return f"[{timestamp}] [{self.filename}] [PID={self.pid}]"
        if self.stream.name == "<stderr>":
            return f"[{timestamp}] [{self.filename}] [PID={self.pid}] [STDERR]"
        raise ValueError(f"Unknown stream name: {self.stream.name}")

    def write(self, message: str):

        if self.previous_line_ended_with_newline:
            self.stream.write(self._prefix() + " " + message)
        else:
            # If the previous line did not end with a newline, then the current line is a continuation of the previous line.
            self.stream.write(message)
        self.previous_line_ended_with_newline = message.endswith("\n")

    def flush(self):
        self.stream.flush()
