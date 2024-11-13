#!/usr/bin/env /home/vivek/hateoas/.direnv/python-3.10.12/bin/python
from tzlocal import get_localzone
from waivek import Connection, Timer

from rich_table import print_rich_dict_rows, print_rich_tuple_rows
from worker_db_utils import jobs_db_init
timer = Timer()
from waivek import handler, ic, ib , rel2abs
from datetime import datetime
import os
import timeago

# jobs_connection = Connection("data/jobs.db")
jobs_db_path = os.path.join(os.getcwd(), "data/jobs.db")
if not os.path.exists(jobs_db_path):
    import rich
    rich.print(f"[black on red bold] MISSING [/] {jobs_db_path}")
    import sys; sys.exit(1)

jobs_connection = Connection(jobs_db_path)

def jobs_oneliner(job):
    job_id = job["job_id"]
    filename = job["filename"].replace(os.path.expanduser("~"), "~")
    name = os.path.basename(filename).replace("worker_", "").replace("_", " ").upper()
    name = os.path.splitext(name)[0]
    name = "[bold]" + name + "[/]"
    pid = "[magenta bold]" + str(job["pid"]) + "[/]"
    if job["exit_code"] == 0:
        exit_code = "[green bold]0[/]"
    else:
        exit_code = f"[red bold]{job['exit_code']}[/]"
    task_id = job["task_id"]
    started_at = datetime.fromtimestamp(int(job["started_at"]), get_localzone())
    started_at_string = "{timeago_string} ({date_string})".format(
            date_string=started_at.strftime("%I:%M%p %b %e %z"),
            timeago_string=timeago.format(started_at, datetime.now(get_localzone()))
            )
    if not job["ended_at"]:
        ended_at_pair = [ None ]
    else:
        ended_at = datetime.fromtimestamp(int(job["ended_at"]), get_localzone())
        # ended_at_pair = "{timeago_string} ({date_string})".format(
        #         date_string=ended_at.strftime("%I:%M%p %b %e %z"),
        #         timeago_string=timeago.format(ended_at, datetime.now(get_localzone()))
        #         )
        timeago_string = timeago.format(ended_at, datetime.now(get_localzone()))
        date_string = ended_at.strftime("%I:%M%p %b %d %z")
        ended_at_pair = [ f"[bright_black][{timeago_string}[/]",  f"[bright_black]({date_string})][/]" ]

        return [
        job_id,
        name,
        pid,
        exit_code,
        task_id,
        *ended_at_pair,
    ]

def main():
    jobs_db_init()
    with jobs_connection:
        cursor = jobs_connection.execute("SELECT * FROM jobs")
        jobs = [ dict(row) for row in cursor.fetchall() ]
    if not jobs:
        print("No jobs found")
        return

    rows = [ jobs_oneliner(job) for job in jobs ]
    # header = ["FILENAME", "PID", "EXIT CODE", "TASK ID", "ENDED AT"]
    # header = [ f"[bright_black bold]{h}[/]" for h in header ]
    # rows.insert(0, header)
    print_rich_tuple_rows(rows, padding=(0, 2))

if __name__ == "__main__":
    with handler():
        main()

# run.vim: term python %
