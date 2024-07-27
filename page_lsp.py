from waivek import Timer   # Single Use
timer = Timer()
from waivek import Code    # Multi-Use
from waivek import handler # Single Use
from waivek import ic, ib     # Multi-Use, import time: 70ms - 110ms
from waivek import rel2abs
from waivek import read
from model_pydantic import CommentsPage as CommentsPagePydantic
from model_attrs import CommentsPage
from typing import cast

from chat_utils import read_json_gz_file

def main():
    D = read_json_gz_file("tests/sample-pass-token.json.gz")
    assert isinstance(D, dict)
    page_pydantic = CommentsPagePydantic(**D)
    page = cast(CommentsPage, page_pydantic)
    ic(page.edges[0].node.contentOffsetSeconds)

if __name__ == "__main__":
    with handler():
        main()

