BEGIN TRANSACTION;

CREATE TABLE online_workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT
) STRICT;

CREATE TABLE acquired_portionurl_ids (
    worker_id INTEGER NOT NULL UNIQUE,
    portionurl_id INTEGER NOT NULL UNIQUE,
    FOREIGN KEY (worker_id) REFERENCES online_workers (id) ON DELETE CASCADE
) STRICT;

END TRANSACTION;
