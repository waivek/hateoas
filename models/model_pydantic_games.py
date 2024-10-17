# CREATE TABLE games (
#     id          TEXT NOT NULL PRIMARY KEY,
#     name        TEXT NOT NULL,
#     box_art_url TEXT NOT NULL,
#     igdb_id     TEXT
# ) STRICT;

from typing import List, Optional
from pydantic import BaseModel, Field

class Game(BaseModel):
    id: str
    name: str
    box_art_url: str
    igdb_id: str

