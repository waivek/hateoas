
import os
import os.path

def get_list_of_sql_files_in_cwd():
    return [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.sql')]

os.makedirs('data', exist_ok=True)

paths = get_list_of_sql_files_in_cwd()
db_paths = []
for path in paths:
    db_paths.append(f"data/{path[:-4]}.db")

for db_path, sql_path in zip(db_paths, paths):
    db_exists = os.path.exists(db_path)
    if db_exists:
        print(f"Database {db_path} already exists, skipping...")
        continue

    print(f"Creating database {db_path} from {sql_path}...")
    os.system(f"sqlite3 {db_path} < {sql_path}")
    print(f"Database {db_path} created successfully!")
    

