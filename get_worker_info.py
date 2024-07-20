
import psutil
import os
from portionurl_to_download_path import downloads_folder
from waivek import ic

def get_portoinurl_id_to_pid_dict():
    directory = downloads_folder()
    extension = '.lock'
    lock_files = [f for f in os.listdir(directory) if f.endswith(extension)]
    D = {}
    for i, lock_file in enumerate(lock_files):
        lock_path = os.path.join(directory, lock_file)
        with open(lock_path, 'r') as f:
            pid = int(f.read())
        portionurl_id = os.path.basename(lock_file).replace(extension, '')
        # D = { 'portionurl_id': portionurl_id, 'pid': pid }
        # table.append(D)
        D[portionurl_id] = pid
    return D

def get_worker_info():
    lock_dir = '/tmp'
    lock_filename_prefix = 'download_worker_'
    lock_filename_suffix = '.lock'
    lock_filenames = [f for f in os.listdir(lock_dir) if f.startswith(lock_filename_prefix) and f.endswith(lock_filename_suffix)]
    pids_from_lock_files = []
    for lock_filename in lock_filenames:
        lock_path = os.path.join(lock_dir, lock_filename)
        with open(lock_path, 'r') as f:
            pid = int(f.read())
            pids_from_lock_files.append(pid)
    table = []
    for lock_filename, pid in zip(lock_filenames, pids_from_lock_files):
        lock_status = 'stale' if not psutil.pid_exists(pid) else 'active'
        table.append({ 'lock_filename': lock_filename, 'pid': pid, 'lock_status': lock_status })
    return table

def get_chat_worker_info():
    lock_dir = '/tmp'
    lock_filename_prefix = 'chat_download_worker_'
    lock_filename_suffix = '.lock'
    lock_filenames = [f for f in os.listdir(lock_dir) if f.startswith(lock_filename_prefix) and f.endswith(lock_filename_suffix)]
    pids_from_lock_files = []
    for lock_filename in lock_filenames:
        lock_path = os.path.join(lock_dir, lock_filename)
        with open(lock_path, 'r') as f:
            pid = int(f.read())
            pids_from_lock_files.append(pid)
    table = []
    for lock_filename, pid in zip(lock_filenames, pids_from_lock_files):
        lock_status = 'stale' if not psutil.pid_exists(pid) else 'active'
        table.append({ 'lock_filename': lock_filename, 'pid': pid, 'lock_status': lock_status })
    return table

if __name__ == '__main__':
    print(get_worker_info())
    # print(get_portionurl_lock_files())
