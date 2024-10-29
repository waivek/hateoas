CREATE TABLE jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT    NOT NULL,
    task_id     TEXT    NOT NULL,
    pid         INTEGER NOT NULL,
    start_epoch INTEGER NOT NULL,
    end_epoch   INTEGER,
    exit_code   INTEGER
) STRICT;
