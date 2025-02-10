from waivek import Timer   # Single Use
timer = Timer()
from waivek import Code    # Multi-Use
from waivek import handler # Single Use
from waivek import ic, ib     # Multi-Use, import time: 70ms - 110ms
from waivek import rel2abs
import psutil
import sys

# open_files            Return files opened by process as a list of                         
# cmdline
# exe
# environ
# num_fds
def pid_info(pid):
    pid = int(pid)
    process = psutil.Process(pid)
    ic(process.num_fds())
    if process.open_files():
        ic([ x._asdict() for x in process.open_files() ])
    ic(" ".join(process.cmdline()) + "\n")
    ic(process.exe() + "\n")
    ic(process.environ())
    ic(process.terminal())


def main():
    pid = sys.argv[1]

    pid_info(pid)

if __name__ == "__main__":
    with handler():
        main()

# run.vim: vert term python % 41299
# run.vim: vert term python % 746722
