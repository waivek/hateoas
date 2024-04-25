BEGIN TRANSACTION;

CREATE TABLE sequences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL
) STRICT;

CREATE TABLE portions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    epoch INTEGER NOT NULL,
    duration INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    `order` INTEGER NOT NULL,
    FOREIGN KEY (sequence_id) REFERENCES sequences (id) ON DELETE CASCADE
) STRICT;

CREATE TABLE portionurls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portion_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    selected INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    FOREIGN KEY (portion_id) REFERENCES portions (id) ON DELETE CASCADE, UNIQUE (portion_id, url)
) STRICT;

CREATE TABLE downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portionurl_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'paused' CHECK (status IN ('paused', 'pending', 'downloading', 'complete', 'failed')),
    FOREIGN KEY (portionurl_id) REFERENCES portionurls (id) ON DELETE CASCADE
) STRICT;

END TRANSACTION;
-- -- Constraints
-- -- Table: portions. Purpose: ensure that the order is unique for each sequence
-- UNIQUE(sequence_id, [order])
