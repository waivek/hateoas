import os
import rich

# --- GLOBALS ---
console = rich.get_console()
foreground = "#ffffff"
foreground = "#000000"
path_style = "bold"
# --- GLOBALS [END] ---

def get_paths():
    # Folder Structure
    # worker_data
    # ├── logs_merged
    # ├── worker_info
    # │   └── worker
    # ├── logs_latest
    # └── worker
    worker_folder = os.path.expanduser("~/worker_data")
    f1 = os.path.join(worker_folder, "logs_latest")
    f2 = os.path.join(worker_folder, "worker_info")
    f3 = os.path.join(f2, "worker")
    f4 = os.path.join(worker_folder, "logs_merged")
    return {
        "worker_folder": worker_folder,
        "logs_latest_folder": f1,
        "worker_info_folder": f2,
        "worker_logs_folder": f4,
    }
def worker():
    from waivek import log as log_waivek, set_verbose_stdout
    from worker_utils import log as log_local
    # set_verbose_stdout()
    # worker()
    log_local("Local log")
    log_waivek("Waivek log")

def tear_down():
    paths = get_paths()


    if not os.path.exists(paths["worker_logs_folder"]):
        console.print(f"\n[{foreground} on red bold] MISSING [/] [{path_style}]{paths['worker_logs_folder']}[/]\n", highlight=False)
        raise Exception
    # check if worker_logs_folder is empty
    if os.listdir(paths["worker_logs_folder"]):
        console.print(f"\n[{foreground} on red bold] NOT EMPTY [/] [{path_style}]{paths['worker_logs_folder']}[/]\n", highlight=False)
        raise Exception
    os.rmdir(paths["worker_logs_folder"])
    console.print(f"[{foreground} on red bold] DELETED [/] [{path_style}]{paths['worker_logs_folder']}[/]", highlight=False)

    if not os.path.exists(paths["worker_folder"]):
        console.print(f"\n[{foreground} on red bold] MISSING [/] [{path_style}]{paths['worker_folder']}[/]\n", highlight=False)
        raise Exception
    os.rmdir(paths["worker_folder"])
    console.print(f"[{foreground} on red bold] DELETED [/] [{path_style}]{paths['worker_folder']}[/]", highlight=False)

def build_up():
    paths = get_paths()
    if os.path.exists(paths["worker_folder"]):
        console.print(f"\n[{foreground} on red bold] EXISTS [/] [{path_style}]{paths['worker_folder']}[/]\n", highlight=False)
        raise Exception
    os.makedirs(paths["worker_folder"])
    console.print(f"[{foreground} on green bold] CREATED [/] [{path_style}]{paths['worker_folder']}[/]", highlight=False)
    os.makedirs(paths["worker_logs_folder"])
    console.print(f"[{foreground} on green bold] CREATED [/] [{path_style}]{paths['worker_logs_folder']}[/]", highlight=False)
    print()

if __name__ == "__main__":
    tear_down()
    build_up()
    # sample_log_file_path = os.path.join(get_paths()["worker_logs_folder"], "sample.log")
    # with open(sample_log_file_path, "w") as f:
    #     f.write("sample log")
    # console.print(f"[{foreground} on green bold] CREATED [/] [{path_style}]{sample_log_file_path}[/]", highlight=False)
