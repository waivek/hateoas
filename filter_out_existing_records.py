import sqlite3
from typing import List, Dict, Optional, Set, Union, Any

def get_existing_tables(cursor: sqlite3.Cursor) -> List[str]:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [row[0] for row in cursor.fetchall()]

def get_table_schema(cursor: sqlite3.Cursor, table_name: str) -> List[tuple]:
    cursor.execute(f"PRAGMA table_info({table_name});")
    return cursor.fetchall()

def get_primary_key(schema: List[tuple]) -> Optional[str]:
    for column in schema:
        if column[5] == 1:  # The 6th element (index 5) indicates if it's a primary key
            return column[1]  # Return the column name
    return None

def filter_out_existing_records(cursor: sqlite3.Cursor, data: List[Union[Dict, Any]], table_name: Optional[str] = None) -> List[Union[Dict, Any]]:
    # Step 1: Determine the table name
    tables = get_existing_tables(cursor)
    if table_name is None:
        if len(tables) == 0:
            raise ValueError("No tables found in the database.")
        elif len(tables) > 1:
            raise ValueError("Multiple tables found. Please specify a table name.")
        else:
            table_name = tables[0]
    if table_name not in tables:
        raise ValueError(f"Table '{table_name}' does not exist in the database.")
    
    # Step 2: Get the schema and check for primary key
    schema = get_table_schema(cursor, table_name)
    primary_key = get_primary_key(schema)
    if primary_key is None:
        print(f"No primary key found in table '{table_name}'.")
        return []
    
    # Step 3: Filter out existing records using SQLite
    temp_table_name = f"temp_{table_name}_ids"
    
    # Get the data type of the primary key
    primary_key_type = next(col[2] for col in schema if col[1] == primary_key)
    
    cursor.execute(f"CREATE TEMPORARY TABLE {temp_table_name} (id {primary_key_type})")
    
    # Check if data is a list of dictionaries or a list of IDs
    if data and isinstance(data[0], dict):
        # It's a list of dictionaries
        cursor.executemany(f"INSERT INTO {temp_table_name} (id) VALUES (?)",
                           [(d[primary_key],) for d in data])
    else:
        # It's a list of IDs
        cursor.executemany(f"INSERT INTO {temp_table_name} (id) VALUES (?)",
                           [(id,) for id in data])
    
    # Perform the filtering using SQLite JOIN
    cursor.execute(f"""
        SELECT t.id FROM {temp_table_name} t
        LEFT JOIN {table_name} m ON t.id = m.{primary_key}
        WHERE m.{primary_key} IS NULL
    """)
    new_ids = set(row[0] for row in cursor.fetchall())
    
    # Clean up the temporary table
    cursor.execute(f"DROP TABLE {temp_table_name}")
    
    # Filter the original data based on the new ids
    if data and isinstance(data[0], dict):
        new_records = [record for record in data if record[primary_key] in new_ids]
    else:
        new_records = [id for id in data if id in new_ids]
    
    return new_records

def get_existing_keys(cursor: sqlite3.Cursor, table_name: str, primary_key: str) -> Set:
    cursor.execute(f"SELECT {primary_key} FROM {table_name}")
    return set(row[0] for row in cursor.fetchall())

# Example usage:
if __name__ == "__main__":
    conn = sqlite3.connect(":memory:")  # Use an in-memory database for this example
    cursor = conn.cursor()
    
    # Create a sample table
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT
    )
    """)
    
    # Insert some initial data
    cursor.executemany("INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                       [(1, "Alice", "alice@example.com"),
                        (2, "Bob", "bob@example.com")])
    
    # Sample dictionaries including both existing and new records
    sample_dicts = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},  # Existing
        {"id": 2, "name": "Bob", "email": "bob@example.com"},      # Existing
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"},  # New
        {"id": 4, "name": "David", "email": "david@example.com"}   # New
    ]
    
    # Call the function
    new_records = filter_out_existing_records(cursor, sample_dicts)
    
    print("New records:", new_records)
    
    conn.close()
