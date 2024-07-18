BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS sequences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS portions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    epoch INTEGER NOT NULL,
    duration INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    `order` INTEGER NOT NULL,
    FOREIGN KEY (sequence_id) REFERENCES sequences (id) ON DELETE CASCADE
) STRICT;

CREATE TABLE IF NOT EXISTS portionurls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portion_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    selected INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    FOREIGN KEY (portion_id) REFERENCES portions (id) ON DELETE CASCADE,
    UNIQUE (portion_id, url)
) STRICT;

CREATE TABLE IF NOT EXISTS queue_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portionurl_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'paused' CHECK (status IN ('paused', 'pending', 'downloading', 'complete', 'failed')),
    pid INTEGER UNIQUE,
    -- if pid is assigned, then the status is 'downloading'
    CHECK ((status = 'downloading' AND pid IS NOT NULL) OR (status != 'downloading' AND pid IS NULL)),
    FOREIGN KEY (portionurl_id) REFERENCES portionurls (id) ON DELETE CASCADE
) STRICT;

CREATE TABLE IF NOT EXISTS download_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portionurl_id INTEGER NOT NULL UNIQUE,
    FOREIGN KEY (portionurl_id) REFERENCES portionurls (id) ON DELETE CASCADE
) STRICT;

END TRANSACTION;
-- -- Constraints
-- -- Table: portions. Purpose: ensure that the order is unique for each sequence
-- UNIQUE(sequence_id, [order])
