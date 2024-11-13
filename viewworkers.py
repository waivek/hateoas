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
from rich_table import print_rich_tuple_rows

worker_db_path = os.path.join(os.getcwd(), "data/workers.db")
if not os.path.exists(worker_db_path):
    rich.print(f"[black on red bold] MISSING [/] {worker_db_path}")
    import sys; sys.exit(1)
worker_connection = Connection(worker_db_path)

def worker_oneliner(worker):
    filename = worker["filename"].replace(os.path.expanduser("~"), "~")
    if not psutil.pid_exists(worker["pid"]):
        prefix = "[red bold]DEAD[/]"
    else:
        process = psutil.Process(worker["pid"])
        if process.status() == "stopped":
            prefix = "[red bold]SUSPENDED[/]"
        else:
            prefix = "[green bold]ALIVE[/]"
    date = datetime.fromtimestamp(int(worker["started_at"]), get_localzone())
    date = "{timeago_string} ({date_string})".format(
            date_string=date.strftime("%I:%M%p %b %e %z"),
            timeago_string=timeago.format(date, datetime.now(get_localzone()))
            )
    return [ prefix, f"[magenta bold]{worker['pid']}[/]", f"{filename}", f"[bright_black][{date}][/]"]

def main():
    worker_init()
    with worker_connection:
        cursor = worker_connection.execute("SELECT * FROM workers")
        workers = [ dict(row) for row in cursor.fetchall() ]
    if not workers:
        print("No workers found")
        return
    rows = [ worker_oneliner(worker) for worker in workers ]
    print_rich_tuple_rows(rows, headers=[])

if __name__ == "__main__":
    with handler():
        main()

# run.vim: term python %
