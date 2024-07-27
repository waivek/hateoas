
from waivek import rel2abs
# import Token from init file

import pytest

from chat_utils import read_json_gz_file

paths_D = {
    "fail_token": "sample-fail-token.json.gz",
    "pass_token": "sample-pass-token.json.gz",
    "pass_multiple_tokens": "sample-pass-multiple-tokens.json.gz"
}

def test_fail_token_pydantic():
    from models.model_pydantic import CommentsPage
    token_path = rel2abs(paths_D["fail_token"])
    D = read_json_gz_file(token_path)
    assert isinstance(D, dict)
    with pytest.raises(Exception):
        CommentsPage(**D)

def test_pass_token_pydantic():
    from models.model_pydantic import CommentsPage
    token_path = rel2abs(paths_D["pass_token"])
    D = read_json_gz_file(token_path)
    assert isinstance(D, dict)
    CommentsPage(**D)

def test_pass_read_multiple_tokens():
    from models.model_pydantic import CommentsPage
    token_path = rel2abs(paths_D["pass_multiple_tokens"])
    L = read_json_gz_file(token_path)
    assert isinstance(L, list)
    for i, D in enumerate(L):
        assert isinstance(D, dict)
        CommentsPage(**D)
        if i > 5:
            break


