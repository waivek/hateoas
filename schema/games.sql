CREATE TABLE games (
    id          TEXT NOT NULL PRIMARY KEY,
    name        TEXT NOT NULL,
    box_art_url TEXT NOT NULL,
    igdb_id     TEXT NOT NULL
) STRICT;
