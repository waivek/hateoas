CREATE TABLE "videos" (
    id               TEXT    NOT NULL PRIMARY KEY,
    user_id          TEXT    NOT NULL,
    user_login       TEXT    NOT NULL,
    user_name        TEXT    NOT NULL,
    title            TEXT    NOT NULL,
    created_at       TEXT    NOT NULL,
    created_at_epoch INTEGER NOT NULL,
    url              TEXT    NOT NULL,
    thumbnail_url    TEXT    NOT NULL CHECK (thumbnail_url NOT LIKE '%\_404/%' ESCAPE '\'), -- _ is a wildcard character, we need to escape it
    duration         INTEGER NOT NULL,
    view_count       INTEGER NOT NULL,
    is_youtube       INTEGER NOT NULL,
    stream_id        TEXT,
    description      TEXT,
    published_at     TEXT,
    viewable         TEXT,
    language         TEXT,
    type             TEXT,
    muted_segments   TEXT
) STRICT;
