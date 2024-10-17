CREATE TABLE "clips" (
    id TEXT NOT NULL PRIMARY KEY,
    url TEXT NOT NULL,
    embed_url TEXT NOT NULL,
    broadcaster_id TEXT NOT NULL,
    broadcaster_name TEXT NOT NULL,
    creator_id TEXT NOT NULL,
    creator_name TEXT NOT NULL,
    game_id TEXT,
    title TEXT NOT NULL,
    view_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    thumbnail_url TEXT NOT NULL,
    language TEXT NOT NULL,
    duration INTEGER NOT NULL,
    created_at_epoch INTEGER NOT NULL,
    video_id TEXT,
    vod_offset INTEGER
) STRICT;
