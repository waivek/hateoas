
import sys
import os
import time
from output_modifier import OutputModifier
from worker_db_utils import worker_init, worker_start, worker_exists
from typing import Callable, TypeVar

T = TypeVar('T')  # Represents the type returned by get_task_id_func

# def worker_single(get_task_id_func, task_func: Callable[..., int]):
def worker_single(get_task_id_func: Callable[[], T], task_func: Callable[[T], int]):
    unmodified_stdout = sys.stdout
    caller_path = sys._getframe(1).f_globals["__file__"]
    sys.stdout = OutputModifier(sys.stdout, caller_path)
    sys.stderr = OutputModifier(sys.stderr, caller_path)
    if worker_exists(caller_path):
        return
    worker_init()
    worker_start(caller_path, os.getpid())
    print(f"[START] Worker: {task_func.__name__}", flush=True)
    while True:
        if task_id := get_task_id_func():
            print("JOB: task_id=%s" % task_id, flush=True)
            exit_code = task_func(task_id)
            print("exit_code=%s" % exit_code, flush=True)
            unmodified_stdout.write("\n")
            unmodified_stdout.flush()
        time.sleep(1)