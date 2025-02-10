
from io_utils import raise_for_missing_dirs

paths = [ "test1/item.txt", "test2/item.txt", "test3/item.txt", "test4/test5/item.txt" ]
raise_for_missing_dirs(paths)
