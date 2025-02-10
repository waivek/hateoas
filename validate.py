from waivek import Timer
timer = Timer()
from waivek import handler, ic, ib , rel2abs
import sqlite3  # Import sqlite3 module
import rich
import json

console = rich.get_console()
console._highlight = False

def handle_integrity_error(e, column, constraint, value):  # Added value parameter
    # Create a dictionary to hold error details
    error_details = {
        "error": str(e),
        "column": column,  # Isolated column name
        "constraint": constraint,  # Isolated constraint type
        "value": value  # Added value to error details
    }
    console.print(f"[red bold]ERROR[/]: {e} (Value: {value})")  # Print the value that caused the error
    json_error = json.dumps(error_details, indent=6)
    print(json_error)

def create_table():
    # Connect to an in-memory SQLite database
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # Create a table with specified types and constraints
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS my_table (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE CHECK (trim(name) <> ''),
            value REAL NOT NULL
        ) STRICT
    ''')
    
    # Deliberately insert multiple rows that would cause constraint/integrity errors
    invalid_rows = [
        ("test", 10.0),  # First insert
        ("test", 20.0),  # Duplicate name, should cause UNIQUE constraint error
        (None, 30.0),    # NULL name, should cause NOT NULL constraint error
        ("", 40.0)       # Empty string, should cause NOT NULL constraint error
    ]
    
    for name, value in invalid_rows:
        try:
            cursor.execute("INSERT INTO my_table (name, value) VALUES (?, ?)", (name, value))
        except sqlite3.IntegrityError as e:
            handle_integrity_error(e, "name", "UNIQUE" if name == "test" else "NOT NULL" if name is None else "CHECK", name)  # Pass the name value

    # Commit changes and close the connection
    conn.commit()
    conn.close()

def main():
    create_table()  # Call the function to create the table
    rich.print("[green bold]DONE[/]")
    print()

if __name__ == "__main__":
    with handler():
        main()
