from typing_extensions import assert_type
from waivek import Connection, Timer, write   # Single Use
timer = Timer()
from waivek import Code    # Multi-Use
from waivek import handler # Single Use
from waivek import ic, ib     # Multi-Use, import time: 70ms - 110ms
from waivek import rel2abs
from waivek import read
from models.model_pydantic import CommentsPage as CommentsPagePydantic
from models.model_attrs import CommentsPage
from typing import cast

from chat_utils import read_json_gz_file

def get_page_pydantic():
    D = read_json_gz_file("tests/sample-pass-token.json.gz")
    assert isinstance(D, dict)
    page_pydantic = CommentsPagePydantic(**D)
    return page_pydantic

def main():
    x = 2
    y = cast(str, x)
    print("type(x): {}, type(y): {}".format(type(x), type(y)))

    page_pydantic = get_page_pydantic()
    page = cast(CommentsPage, page_pydantic)
    print("type(page_pydantic): {}, type(page): {}".format(type(page_pydantic), type(page)))
    ic(page.edges[0].node.contentOffsetSeconds)

if __name__ == "__main__":
    with handler():
        main()
