from waivek.reltools import pathjoin
import sys
import os

def longest_existing_parent(path):
    while not os.path.exists(path):
        path = os.path.dirname(path)
    return path

def raise_for_missing_dirs(paths):
    frame = sys._getframe(1)

    paths = [ os.path.expanduser(path) for path in paths ]
    paths = [ path if os.path.isabs(path) else pathjoin(frame, path) for path in paths ]
    dirs = [ os.path.dirname(path) for path in paths if not os.path.isdir(path) ]
    missing_dirs = [ directory for directory in dirs if not os.path.exists(directory) ]
    if not missing_dirs:
        print(f"Exist Paths: {paths}")
        return

    import rich
    console = rich.get_console()
    console.print("\n[black on red bold] MISSING DIRECTORIES [/]\n")
    for missing_dir in missing_dirs:
        existing_parent = longest_existing_parent(missing_dir)
        assert existing_parent
        missing_portion = missing_dir[len(existing_parent):]
        console.print(" "* 4 + f"[green]{existing_parent}[/][red bold]{missing_portion}[/]", highlight=False)
    console.print()

    raise FileNotFoundError

def main():
    paths = [ "test1/item.txt", "test2/item.txt", "test3/item.txt", "test4/test5/item.txt" ]
    raise_for_missing_dirs(paths)

if __name__ == "__main__":
    main()
