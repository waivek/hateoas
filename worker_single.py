
import sys
import os
import time

import psutil
from output_modifier import OutputModifier
from worker_db_utils import job_end, job_start, jobs_db_init, worker_init, worker_start, worker_exists
from typing import Callable, TypeVar

T = TypeVar('T')  # Represents the type returned by get_task_id_func

def stop():
    # stop() {{{
    process = psutil.Process(os.getpid())
    stop_time = time.time() + 60
    while time.time() < stop_time:
        if os.fork() == 0:
            time.sleep(1)
            process.resume()
            os._exit(0)
        process.suspend()
    # }}}

def worker_single(get_task_id_func: Callable[[], T], task_func: Callable[[T], int]):
    unmodified_stdout = sys.stdout
    caller_path = sys._getframe(1).f_globals["__file__"]
    sys.stdout = OutputModifier(sys.stdout, caller_path)
    sys.stderr = OutputModifier(sys.stderr, caller_path)
    if worker_exists(caller_path):
        return
    worker_init()
    jobs_db_init()
    worker_start(caller_path, os.getpid())
    print(f"[START] Worker: {task_func.__name__}", flush=True)
    while True:
        if task_id := get_task_id_func():
            print("JOB: task_id=%s" % task_id, flush=True)
            job_id = job_start(caller_path, os.getpid(), task_id)
            exit_code = task_func(task_id)
            job_end(job_id, exit_code)
            print("exit_code=%s" % exit_code, flush=True)
            if exit_code != 0:
                print("[exit_code=%s] [task_id=%s] Suspending / Stopping worker for 1 minute" % (exit_code, task_id), flush=True)
                stop()
            unmodified_stdout.write("\n")
            unmodified_stdout.flush()
        time.sleep(1)
