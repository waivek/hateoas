#!/usr/bin/env /home/vivek/hateoas/.direnv/python-3.10.12/bin/python
from waivek import Connection, Timer

from worker_db_utils import worker_init
timer = Timer()
from waivek import handler, ic, ib , rel2abs
import os
import psutil
from datetime import datetime
import timeago
from tzlocal import get_localzone
import rich

# import sys
# def foo():
#     frame = sys._getframe(1)
#     print(frame.f_code.co_filename)
# foo()

worker_connection = Connection(os.path.join(os.getcwd(), "data/worker.db"))

def worker_oneliner(worker):
    filename = worker["filename"].replace(os.path.expanduser("~"), "~")
    if not psutil.pid_exists(worker["pid"]):
        prefix = "[red bold]DEAD [/] "
    else:
        prefix = "[green bold]ALIVE[/] "
    date = datetime.fromtimestamp(int(worker["started_at"]), get_localzone())
    date = "{timeago_string} ({date_string})".format(
            date_string=date.strftime("%I:%M%p %b %e %z"),
            timeago_string=timeago.format(date, datetime.now(get_localzone()))
            )
    return prefix + f"[magenta bold]{worker['pid']}[/] {filename} [bright_black][{date}][/]"

def main():
    console = rich.get_console()
    console._highlight = False
    worker_init()
    with worker_connection:
        cursor = worker_connection.execute("SELECT * FROM workers")
        workers = [ dict(row) for row in cursor.fetchall() ]
    if not workers:
        print("No workers found")
        return
    for worker in workers:
        console.print(worker_oneliner(worker))


if __name__ == "__main__":
    with handler():
        main()

# run.vim: term python %
