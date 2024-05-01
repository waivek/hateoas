BEGIN TRANSACTION;

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT 'incomplete' CHECK (status IN ('incomplete', 'progress', 'complete'))
);

CREATE TABLE completed_tasks (
    id INTEGER UNIQUE
);

END TRANSACTION;
